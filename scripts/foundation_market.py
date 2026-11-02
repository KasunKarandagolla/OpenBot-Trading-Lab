"""Existing native pairlists/metadata filters, closed-data assessment and sources."""
import json
import math
import subprocess
import sys
import tarfile
import time
import pandas as pd
from foundation_common import *


def preflight(run_id):
    import ccxt
    import freqtrade
    out, data, spec = verify(run_id)
    path = out/'venue-access.json'
    if path.exists():
        raise ValueError('preserve access evidence')
    records = []
    for venue in ('binance', 'gate'):
        started = now()
        ex = public(venue)
        try:
            markets = ex.load_markets()
            symbol = spec['pairs'][0]
            bars = ex.fetch_ohlcv(symbol, '15m', limit=3)
            funding = ex.fetch_funding_rate(symbol)
            records.append(dict(venue=venue, status='ACCESSIBLE', requested_at=started,
                                observed_at=now(), candles=len(bars), contract_id=markets[symbol]['id'],
                                funding_timestamp=funding.get('timestamp'),
                                public_taker_rate=markets[symbol].get('taker')))
        except Exception as error:
            records.append(dict(venue=venue, status='BLOCKED', requested_at=started,
                                observed_at=now(), error=type(error).__name__+': '+str(error)[:2500]))
    # This registered sample is always Gate, including on hosts where Binance
    # works. A separate Binance cohort is required before venue-specific economics.
    write(path, dict(engine=freqtrade.__version__, ccxt=ccxt.__version__, venues=records,
                     research_venue='gate', binance_policy='Native Binance USD-M adapter tested once; no regional workaround. Separate cohort required.',
                     paper_mode='native dry_run=true; no sandbox/demo adapter', orders_created=False))
    if records[1]['status'] != 'ACCESSIBLE':
        raise ValueError('Gate public fallback unavailable; see venue-access.json')
    print(json.dumps(records, indent=2))


def scan(run_id):
    from scan_export import shortlist
    out, data, spec = verify(run_id)
    if (out/'scan.json').exists():
        raise ValueError('preserve scan; new run for another observation')
    cfg_path = config(run_id, 'TrendPullbackBaselineV1')
    cfg = read(cfg_path)
    cfg['pairlists'] = read(ROOT/'configs/scanner.json')['pairlists']
    cfg['exchange']['pair_whitelist'] = []
    scan_cfg = cfg_path.with_name('scanner.json')
    write(scan_cfg, cfg)
    result = subprocess.run(['freqtrade', 'test-pairlist', '--config', str(scan_cfg), '--print-json'],
                            capture_output=True, text=True)
    (out/'native-pairlist.txt').write_text(result.stdout+result.stderr)
    if result.returncode:
        raise ValueError('native pairlist failed; see native-pairlist.txt')
    native = None
    for line in result.stdout.splitlines():
        try:
            obj = json.loads(line)
            if isinstance(obj, list) and all(isinstance(s, str) for s in obj):
                native = set(obj)
        except json.JSONDecodeError:
            pass
    if native is None:
        raise ValueError('native shortlist JSON missing')
    ex = public()
    markets = ex.load_markets()
    tickers = ex.fetch_tickers(params={'type': 'swap', 'settle': 'usdt'})
    observed = now()
    rules = read(ROOT/'configs/scan-rules.json')
    eligible, rows, rejects, capped = shortlist(markets, tickers, rules, time.time()*1000, native)
    # Reuse exactly the existing cheap filter for rejected examples beyond the
    # native top-volume cap. No expensive history is requested for these markets.
    _, _, all_rejects, _ = shortlist(markets, tickers, rules, time.time()*1000)
    for row in all_rejects:
        row.update(status='REJECT', evidence_id='scan:'+row['symbol'])
    for row in rows:
        row.update(status='WATCH', reason='CHEAP_SCREEN_PASSED_REQUIRES_CLOSED_RECIPE',
                   evidence_id='scan:'+row['symbol'])
    ineligible = []
    for symbol, market in sorted(markets.items()):
        if not (market.get('swap') and market.get('settle') == 'USDT'):
            continue
        info = market.get('info', {})
        reasons = []
        if market.get('active') is not True: reasons.append('INACTIVE')
        if market.get('linear') is not True: reasons.append('NONLINEAR')
        if info.get('in_delisting') is not False: reasons.append('DELISTING_OR_UNKNOWN')
        if info.get('is_pre_market') is not False: reasons.append('PREMARKET_OR_UNKNOWN')
        if info.get('contract_type') != '': reasons.append('NONCRYPTO_OR_UNKNOWN_TYPE')
        launch = info.get('launch_time')
        if launch is None or time.time()-float(launch) < 30*86400: reasons.append('AGE_UNDER_30D_OR_UNKNOWN')
        if reasons: ineligible.append(dict(symbol=symbol, status='REJECT', reasons=reasons))
    raw = data.parent/'current/scan-source.json'
    write(raw, dict(observed_at=observed, markets={s: {'id': m['id'], 'active': m.get('active'),
          'linear': m.get('linear'), 'swap': m.get('swap'), 'settle': m.get('settle'),
          'contractSize': m.get('contractSize'), 'info': m['info']} for s, m in markets.items() if m.get('swap')},
          tickers=tickers))
    write(out/'scan.json', dict(schema_version=1, venue='gate', observed_at=observed,
          membership='CURRENT_SNAPSHOT_ONLY', source_sha256=sha(raw), native_pairlist_count=len(native),
          native_pairlist_sha256=sha(out/'native-pairlist.txt'), eligible_universe_count=eligible,
          shortlisted=rows, rejected=all_rejects, metadata_rejected=ineligible,
          valid_below_cap=capped, rules=rules, orders_created=False,
          timestamp_policy='Venue ticker clock may be UNKNOWN; observation time is never substituted.'))
    print(f'Scan: {eligible} eligible; native {len(native)}; shortlist {len(rows)}; liquidity rejects {len(all_rejects)}; metadata rejects {len(ineligible)}')


def acquire(run_id):
    out, data, spec = verify(run_id)
    if (out/'data-manifest.json').exists() or any(data.rglob('*.feather')):
        raise ValueError('refuse overwrite/redownload; preserve source or create a new run')
    ex = public(); markets = ex.load_markets()
    contracts = {}
    for symbol in spec['pairs']:
        market = markets[symbol]
        info = market['info']
        if not (market.get('active') and market.get('linear') and market.get('swap') and market.get('settle') == 'USDT'
                and info.get('in_delisting') is False and info.get('is_pre_market') is False):
            raise ValueError('ineligible contract '+symbol)
        taker = market.get('taker')
        if taker is None or not math.isfinite(float(taker)) or float(taker) > spec['fee_per_side']:
            raise ValueError('public taker rate missing or exceeds registered cost scenario')
        contracts[symbol] = {k: market.get(k) for k in ('id', 'symbol', 'type', 'linear', 'settle', 'contractSize', 'precision', 'limits', 'maker', 'taker')}
        contracts[symbol].update(funding_interval_seconds=int(info['funding_interval']),
                                 observed_at=now(), historical_identity='Current contract metadata; historical membership unverified')
    write(data.parent/'contracts.json', contracts)
    cfg = config(run_id, 'TrendPullbackBaselineV1')
    started = now()
    args = ['freqtrade', 'download-data', '--config', str(cfg), '--datadir', str(data),
            '--trading-mode', 'futures', '--timeframes', '15m', '1h', '--timerange', spec['download_timerange']]
    with (out/'native-download.txt').open('x') as log:
        result = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError('native download failed; preserve log and partial files')
    start, end = [pd.to_datetime(s, format='%Y%m%d', utc=True) for s in spec['download_timerange'].split('-')]
    files = []
    for path in sorted(data.rglob('*.feather')):
        df = pd.read_feather(path)
        df = df.loc[(df.date >= start) & (df.date < end)].reset_index(drop=True)
        df.to_feather(path)
        files.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path), bytes=path.stat().st_size,
                          rows=len(df), first_event_at=df.date.iloc[0].isoformat() if len(df) else None,
                          last_event_at=df.date.iloc[-1].isoformat() if len(df) else None))
    write(out/'data-manifest.json', dict(schema_version=1, venue='gate', source='Native Freqtrade/CCXT public REST',
          acquisition_started_at=started, acquisition_completed_at=now(), timerange=spec['download_timerange'],
          files=files, contracts=contracts, total_bytes=sum(r['bytes'] for r in files),
          boundary_policy='Trim to registered UTC end-exclusive interval; no filling/interpolation.',
          raw_redistribution=False))
    validate(run_id)
    # A bounded private bundle solves rolling endpoint retention for this cohort.
    vault = ROOT/'user_data/data/source-vault'/('foundation-'+run_id+'.tar.gz')
    vault.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(vault, 'x:gz') as archive:
        archive.add(data.parent, arcname='source', recursive=True)
        archive.add(out/'data-manifest.json', arcname='data-manifest.json')
        archive.add(out/'registration.json', arcname='registration.json')
    write(out/'source-vault.json', dict(sha256=sha(vault), bytes=vault.stat().st_size,
          local_path=str(vault.relative_to(ROOT)), policy='Private owner source preservation, excluded from Git. Copy off ephemeral workspace.',
          restore_command='python scripts/foundation_restore.py BUNDLE NEW_EMPTY_DIRECTORY'))
    print('Preserved source bundle:', vault.name, vault.stat().st_size, 'bytes')


def validate(run_id):
    from validate_data import inspect
    out, data, spec = verify(run_id)
    manifest = read(out/'data-manifest.json')
    start, end = [pd.to_datetime(s, format='%Y%m%d', utc=True) for s in spec['download_timerange'].split('-')]
    rows = []
    required = {(s, tf, kind) for s in spec['pairs'] for tf, kind in [('15m', 'futures'), ('1h', 'futures'), ('1h', 'mark'), ('1h', 'funding_rate')]}
    found = set()
    for item in manifest['files']:
        path = ROOT/item['path']
        if sha(path) != item['sha256']:
            raise ValueError('source hash mismatch '+path.name)
        symbol = next(s for s in spec['pairs'] if path.name.startswith(s.replace('/', '_').replace(':', '_')+'-'))
        tf, kind = path.stem.split('-', 1)[1].split('-', 1)
        interval = manifest['contracts'][symbol]['funding_interval_seconds'] if kind == 'funding_rate' else 900 if tf == '15m' else 3600
        df = pd.read_feather(path)
        result = inspect(df, interval, start, end, pd.Timestamp.now(tz='UTC'), kind == 'funding_rate')
        if kind == 'funding_rate':
            if result['irregular_intervals']: result['errors'].append('FUNDING_SCHEDULE_GAPS_OR_CHANGES')
            if df.empty or df.date.iloc[0] > start or df.date.iloc[-1]+pd.Timedelta(seconds=interval) < end:
                result['errors'].append('FUNDING_BOUNDARY_MISSING')
        found.add((symbol, tf, kind))
        rows.append(dict(symbol=symbol, timeframe=tf, candle_type=kind, sha256=item['sha256'], **result))
    missing = sorted(required-found)
    valid = not missing and len(rows) == len(required) and not any(r['errors'] for r in rows)
    write(out/'data-validation.json', dict(valid=valid, missing=missing, files=rows, checked_at=now(),
          warmup_hours=spec['warmup_hours'], source_clocks='Exchange candle-open/funding clocks; acquisition clock is separate.'))
    if not valid:
        raise ValueError('source validation failed; no native run admitted')
    print(f'Source validation: {len(rows)} files, hashes/UTC/continuity/funding PASS')


def assess(run_id):
    from freqtrade.strategy import merge_informative_pair
    from freqtrade.enums import CandleType
    from OpportunityRouterV1 import RouterOnlyV1
    from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
    from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
    from advanced_features import plan
    out, data, spec = verify(run_id)
    if (out/'opportunities.json').exists(): raise ValueError('preserve current assessment')
    scan = read(out/'scan.json'); ex = public(); markets = ex.load_markets()
    selected = scan['shortlisted'][:spec['max_deep_analysis']]
    candidates = []
    for candidate in selected:
        symbol = candidate['symbol']; asof = pd.Timestamp.now(tz='UTC')
        try:
            frames = {}
            for tf, delta in [('15m', pd.Timedelta(minutes=15)), ('1h', pd.Timedelta(hours=1))]:
                raw = ex.fetch_ohlcv(symbol, tf, limit=300)
                raw_path = data.parent/'current'/(symbol.split('/')[0]+'-'+tf+'.json')
                write(raw_path, dict(venue='gate', symbol=symbol, observed_at=now(), ohlcv=raw))
                d = pd.DataFrame(raw, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                d['date'] = pd.to_datetime(d.date, unit='ms', utc=True)
                frames[tf] = d.loc[d.date+delta <= asof].reset_index(drop=True)
                if len(frames[tf]) < 240 or frames[tf].date.duplicated().any() or not frames[tf].date.diff().iloc[1:].eq(delta).all():
                    raise ValueError('insufficient/gapped current candles '+tf)
            cfg = {'candle_type_def': CandleType.FUTURES}
            strategy = RouterOnlyV1(cfg)
            h = strategy.populate_indicators_1h(frames['1h'], {'pair': symbol})
            f = strategy.populate_indicators(merge_informative_pair(frames['15m'], h, '15m', '1h', ffill=True), {'pair': symbol})
            recipe_rows = {}
            for recipe, cls in [('vwap', VWAPTrendContinuationV1), ('sweep', LiquiditySweepReversalV1)]:
                recipe_rows[recipe] = cls(cfg).populate_entry_trend(f.copy(), {'pair': symbol})
            row = f.iloc[-1]
            relative = float(f.close.iloc[-1]/f.close.iloc[-17]-1)
            quote = ex.fetch_order_book(symbol, limit=20, params={'with_id': True})
            received = time.time()*1000
            qstamp = quote.get('timestamp')
            bids, asks = quote.get('bids', []), quote.get('asks', [])
            spread = 1-bids[0][0]/asks[0][0] if bids and asks and 0 < bids[0][0] <= asks[0][0] else None
            fresh = qstamp is not None and 0 <= received-float(qstamp) <= 5000 and spread is not None and spread <= .002
            write(data.parent/'current'/(symbol.split('/')[0]+'-quote.json'), dict(quote=quote, received_ms=received))
            for recipe, signals in recipe_rows.items():
                signal = signals.iloc[-1]
                for side in ('long', 'short'):
                    sign = 1 if side == 'long' else -1
                    active = int(signal['enter_'+side]) == 1
                    regime = ('TREND' if float(row.adx_1h) >= 25 else 'RANGE_OR_WEAK_TREND')
                    routed = (recipe == 'vwap') == (regime == 'TREND')
                    geometry = plan(row, recipe, side, integrated=False) if active else None
                    status = 'RESEARCH_CANDIDATE' if active and routed and geometry else 'WATCH' if routed else 'REJECT'
                    reason = 'CLOSED_RECIPE_AND_GEOMETRY' if status == 'RESEARCH_CANDIDATE' else 'WAIT_FOR_CLOSED_SETUP' if status == 'WATCH' else 'RECIPE_REGIME_MISMATCH'
                    # Signed impulse is context for the specific setup, never a
                    # rule that a large gainer automatically deserves a short.
                    signed = sign*relative
                    opposing = []
                    if signed < 0: opposing.append('OPPOSING_4H_IMPULSE')
                    hourly = row.get('struct_direction_1h')
                    if hourly == ('DOWN' if side == 'long' else 'UP'): opposing.append('OPPOSING_CONFIRMED_HOURLY_STRUCTURE')
                    if recipe == 'sweep' and not active: opposing.append('FAILED_BREAKOUT_RECLAIM_NOT_CONFIRMED')
                    if recipe == 'vwap' and not active: opposing.append('VWAP_CROSS_NOT_CONFIRMED')
                    gaps = ['ACCOUNT_MTM_PENDING_EXPOSURE_UNVERIFIED', 'HISTORICAL_QUEUE_AND_SLIPPAGE_UNKNOWN', 'NEWS_COVERAGE_NOT_COMPLETE']
                    if not fresh: gaps.append('CURRENT_QUOTE_CLOCK_OR_SPREAD_UNVERIFIED')
                    known_at = row.date+pd.Timedelta(minutes=15)
                    expires = known_at+pd.Timedelta(minutes=5)
                    if asof >= expires: gaps.append('CURRENT_SIGNAL_EXPIRED')
                    record = dict(schema_version=1, decision_id=f'{run_id}:{symbol}:{recipe}:{side}:{known_at.isoformat()}',
                        venue='gate', symbol=symbol, contract_id=markets[symbol]['id'], status=status, reason=reason,
                        observed_at=now(), available_at=known_at.isoformat(), expires_at=expires.isoformat(),
                        recipe=recipe, side=side, regime=regime, adx_1h=float(row.adx_1h),
                        return_4h=relative, signed_suitability=signed, geometry=geometry,
                        opposing_evidence=[dict(evidence_id=candidate['evidence_id']+':'+r, reason=r,
                             assessment='INVALIDATES_SETUP' if 'NOT_CONFIRMED' in r else 'CAUTION_REQUIRES_RECLAIM_AND_CLOSED_CONTEXT') for r in opposing],
                        quote=dict(venue_timestamp_ms=qstamp, received_ms=received, freshness='CHECKED' if fresh else 'UNKNOWN_OR_STALE',
                                   spread_ratio=spread, sequence_continuity='UNVERIFIED_SINGLE_REST_SNAPSHOT'),
                        data_gaps=gaps, execution_status='NO_TRADE', execution_reason='RESEARCH_ONLY_ACCOUNT_AND_ADMISSION_NOT_QUALIFIED',
                        source_manifest_sha256=sha(out/'scan.json'), orders_created=False)
                    candidates.append(record)
        except Exception as error:
            candidates.append(dict(schema_version=1, decision_id=run_id+':'+symbol+':error', venue='gate', symbol=symbol,
                 status='NO_TRADE', reason='SOURCE_OR_ASSESSMENT_FAILED', error=type(error).__name__+': '+str(error)[:1000],
                 observed_at=now(), data_gaps=['SOURCE_UNAVAILABLE'], orders_created=False))
    candidates.sort(key=lambda r: (r['status'] != 'RESEARCH_CANDIDATE', -r.get('signed_suitability', -999), r['decision_id']))
    write(out/'opportunities.json', dict(schema_version=1, venue='gate', evaluated_at=now(),
          source_scan_sha256=sha(out/'scan.json'), records=candidates,
          status='NO_TRADE' if not any(r['status'] == 'RESEARCH_CANDIDATE' for r in candidates) else 'RESEARCH_CANDIDATES_ONLY',
          authority='Research ranking is non-binding. Only native deterministic callbacks admit simulated trades.'))
    print('Current assessment:', {s: sum(r['status'] == s for r in candidates) for s in ['RESEARCH_CANDIDATE', 'WATCH', 'REJECT', 'NO_TRADE']})
