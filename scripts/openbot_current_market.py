"""Capture, build and verify a bounded Binance USD-M OpenBot research packet."""

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from urllib.parse import urlencode

from binance_research_data import (
    DataError, FUTURES_API_BASE, INTERVAL_MS, KLINE_COLUMNS, _request,
    convert_kline_frame, sha256, utc_now,
)


ROOT = Path(__file__).resolve().parents[1]
BASE = 'd88a3106886239a929989531faacf7b8d8d9b012'
MARKET = 'Binance public USD-M USDT perpetual'
SCHEMA = 'openbot.binance.current.v1'
LIMITS = {'1h': 721, '15m': 289, '5m': 865}
DEPTH = 6
CAP = Decimal('25')
CLOCK_MAX_MS = 5000
PACKET_FRESH_MS = 180_000
PROTOCOL = ROOT / 'research/local_recovery/protocol.json'
REQUIRED = {
    'candidate.json', 'features.json', 'source-receipts.json', 'chart-manifest.json',
    'execution-constraints.json', 'scanner-ledger.csv', 'charts/context.png',
    'charts/entry.png', 'candles/1h.json', 'candles/15m.json', 'candles/5m.json',
}


def write(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def now_ms():
    return time.time_ns() // 1_000_000


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec='milliseconds')


def rules(symbol):
    filters = {f['filterType']: f for f in symbol['filters']}
    price = filters['PRICE_FILTER']
    return {
        'tick_size': price['tickSize'], 'minimum_price': price['minPrice'], 'maximum_price': price['maxPrice'],
        'minimum_notional': filters['MIN_NOTIONAL']['notional'],
        'limit': {k: filters['LOT_SIZE'][k] for k in ('minQty', 'maxQty', 'stepSize')},
        'market': {k: filters['MARKET_LOT_SIZE'][k] for k in ('minQty', 'maxQty', 'stepSize')},
    }


def min_order_notional(price, lot, minimum_notional):
    step = Decimal(lot['stepSize'])
    min_qty = max(Decimal(lot['minQty']), minimum_notional / price)
    aligned = (min_qty / step).to_integral_value(rounding=ROUND_CEILING) * step
    if aligned > Decimal(lot['maxQty']):
        raise DataError('Minimum order exceeds the lot maximum')
    return aligned * price


def screen(panel, exchange, tickers, books, cutoff):
    symbols = {s['symbol']: s for s in exchange['symbols']}
    quotes = {s['symbol']: s for s in books}
    volume = {s['symbol']: s for s in tickers}
    ledger = []
    for name in panel:
        symbol = symbols.get(name, {})
        row = {'symbol': name, 'status': 'VENUE_INELIGIBLE'}
        ledger.append(row)
        if (symbol.get('status'), symbol.get('contractType'), symbol.get('quoteAsset'), symbol.get('marginAsset')) != (
            'TRADING', 'PERPETUAL', 'USDT', 'USDT'
        ):
            continue
        try:
            quote = quotes[name]
            ticker = volume[name]
            bid, ask = Decimal(quote['bidPrice']), Decimal(quote['askPrice'])
            observed = int(quote['time'])
            liquid = Decimal(ticker['quoteVolume'])
            spec = rules(symbol)
            if not (0 < bid <= ask and abs(observed - cutoff) <= PACKET_FRESH_MS
                    and abs(int(ticker['closeTime']) - cutoff) <= PACKET_FRESH_MS):
                raise DataError('Invalid or stale spread or volume snapshot')
            spread = (ask - bid) * 20_000 / (bid + ask)
            minimum = min_order_notional(ask, spec['limit'], Decimal(spec['minimum_notional']))
            row.update(bid=str(bid), ask=str(ask), quote_time_ms=observed,
                       quote_volume_time_ms=int(ticker['closeTime']), quote_volume_24h=str(liquid),
                       spread_bps=str(spread), minimum_aligned_limit_notional=str(minimum), rules=spec)
            row['status'] = 'ELIGIBLE'
            if liquid < 5_000_000 or spread > 10:
                row['status'] = 'REJECT_LIQUIDITY_OR_SPREAD'
            elif minimum > CAP:
                row['status'] = 'REJECT_MINIMUM_NOTIONAL'
        except (ArithmeticError, KeyError, TypeError, ValueError, DataError):
            row['status'] = 'REJECT_METADATA_OR_FRESHNESS'
    return ledger


def capture(out):
    out.mkdir()
    sources = {}

    def get(label, endpoint, **query):
        url = FUTURES_API_BASE + '/' + endpoint + ('?' + urlencode(query) if query else '')
        started = now_ms()
        data, status, final, _ = _request(url, timeout=12, max_bytes=4 * 1024 * 1024,
                                         request_headers={'Cache-Control': 'no-cache, no-store', 'Pragma': 'no-cache'})
        received = now_ms()
        if url != final or status != 200:
            raise DataError('Unexpected public transport result')
        (out / (label + '.json')).write_bytes(data)
        sources[label] = dict(url=final, status=status, bytes=len(data), sha256=sha256(data),
                              retrieved_at_utc=iso(received), request_started_ms=started,
                              observed_at_ms=received, venue='binance', market_type=MARKET)
        return json.loads(data)

    cutoff = int(get('time', 'time')['serverTime'])
    clock = sources['time']
    if clock['observed_at_ms'] - clock['request_started_ms'] > CLOCK_MAX_MS or abs(
        clock['observed_at_ms'] - cutoff
    ) > CLOCK_MAX_MS:
        raise DataError(f"Binance server clock freshness check failed "
                        f"(exchange-to-receive={clock['observed_at_ms'] - cutoff} ms, "
                        f"request elapsed={clock['observed_at_ms'] - clock['request_started_ms']} ms)")
    exchange = get('exchange', 'exchangeInfo')
    tickers = get('tickers', 'ticker/24hr')
    books = get('books', 'ticker/bookTicker')
    ledger = screen(load(PROTOCOL)['symbols'], exchange, tickers, books, cutoff)
    ranked = sorted((r for r in ledger if r['status'] == 'ELIGIBLE'),
                    key=lambda r: (-Decimal(r['quote_volume_24h']), Decimal(r['spread_bps'])))[:DEPTH]
    if not ranked:
        raise DataError('No symbol passed the venue, liquidity, spread and size screens')
    for row in ranked:
        for timeframe, limit in LIMITS.items():
            get(f"{row['symbol']}-{timeframe}", 'klines', symbol=row['symbol'],
                interval=timeframe, limit=limit, endTime=cutoff - 1)
    if now_ms() - cutoff > PACKET_FRESH_MS:
        raise DataError('Public capture exceeded its freshness budget')
    write(out / 'capture.json', {
        'schema': SCHEMA, 'market_type': MARKET, 'as_of_ms': cutoff, 'as_of': iso(cutoff),
        'observed_at': utc_now(), 'sources': sources, 'ranked': [r['symbol'] for r in ranked], 'ledger': ledger,
    })
    print(json.dumps({'public_requests': len(sources), 'as_of': iso(cutoff), 'shortlist': [r['symbol'] for r in ranked]}))


def source_data(directory, key, source):
    body = (directory / (key + '.json')).read_bytes()
    if (source['venue'] != 'binance' or source['market_type'] != MARKET or source['status'] != 200
            or not source['url'].startswith(FUTURES_API_BASE + '/') or len(body) != source['bytes']
            or sha256(body) != source['sha256']):
        raise DataError('Public capture provenance failed for ' + key)
    return json.loads(body)


def closed_rows(rows, tf, cutoff):
    width = INTERVAL_MS[tf]
    if any(not isinstance(row, list) or len(row) != len(KLINE_COLUMNS)
           or type(row[0]) is not int or type(row[6]) is not int
           or row[6] != row[0] + width - 1 for row in rows):
        raise DataError('Wrong Binance kline shape or clock')
    result = [row for row in rows if row[6] + 1 <= cutoff]
    if len(result) < LIMITS[tf] - 1 or result[-1][6] + 1 != cutoff // width * width:
        raise DataError('Missing or stale closed ' + tf + ' bars')
    if any(row[0] % width for row in result) or any(b[0] - a[0] != width for a, b in zip(result, result[1:])):
        raise DataError('Kline timestamps have a gap, duplicate or misalignment')
    return result


def build(raw, out, *, selected_symbol=None):
    import pandas as pd
    from local_recovery_charts import draw_board
    from local_recovery_convert import aggregate
    from local_recovery_scan import FIVE, candidate_rows, cheap_frame, entry_features, examine

    bundle = load(raw / 'capture.json')
    if bundle['schema'] != SCHEMA or bundle['market_type'] != MARKET:
        raise DataError('Wrong capture schema or venue')
    source_map = bundle['sources']
    cutoff_ms = bundle['as_of_ms']
    if source_data(raw, 'time', source_map['time'])['serverTime'] != cutoff_ms:
        raise DataError('Capture cutoff differs from Binance server time')
    for key in ('exchange', 'books', 'tickers'):
        source_data(raw, key, source_map[key])
    cutoff = pd.Timestamp(cutoff_ms, unit='ms', tz='UTC')
    gates = load(PROTOCOL)['gates']
    assessed = []
    ledger = bundle['ledger']
    for name in bundle['ranked']:
        if selected_symbol is not None and name != selected_symbol:
            continue
        row = next(r for r in ledger if r['symbol'] == name)
        frames, original, sources = {}, {}, {}
        try:
            for tf in LIMITS:
                key = f'{name}-{tf}'
                source = {**source_map[key], 'symbol': name, 'kind': 'klines', 'timeframe': tf}
                original[tf] = closed_rows(source_data(raw, key, source), tf, cutoff_ms)
                _, side = convert_kline_frame(pd.DataFrame(original[tf], columns=KLINE_COLUMNS),
                                              source, kind='klines', timeframe=tf)
                frames[tf] = side.rename(columns={'base_volume': 'volume'})
                sources[tf] = source
            q = cheap_frame(frames['1h'], frames['15m'])
            recent = candidate_rows(q, name, cutoff - 30 * pd.Timedelta(minutes=1),
                                    cutoff + pd.Timedelta(milliseconds=1), {}, {}, gates)
            feature_bars = entry_features(frames['5m'])
        except (DataError, ValueError) as exc:
            row.update(status='REJECT_CURRENT_BAR_DATA', reason=str(exc))
            continue
        selected = []
        for case in recent:
            if case['status'] != 'RESEARCHABLE':
                continue
            examine(case, feature_bars, gates, cutoff + pd.Timedelta(days=2))
            case['events'] = [e for e in case['events'] if pd.Timestamp(e['at']) <= cutoff]
            case['status'] = case['events'][-1]['state']
            plan = case.get('plan')
            if plan is not None:
                entry = Decimal(str(plan['entry']))
                quote = (Decimal(row['bid']) + Decimal(row['ask'])) / 2
                if (pd.Timestamp(plan['expires_at']) > cutoff and
                        abs(quote - entry) / entry <= Decimal(str(plan['max_deviation'])) and
                        min_order_notional(entry, row['rules']['limit'], Decimal(row['rules']['minimum_notional'])) <= CAP):
                    selected.append(case)
        last = q.iloc[-1]
        row.update(status='SETUP_FOR_REVIEW' if selected else 'NO_QUALIFIED_SETUP',
                   regime_1h=str(last.struct_direction), regime_4h=str(last.struct_direction_4h),
                   atr_1h_frac=float(last.atr_hour_frac), formations=len(recent),
                   qualified_formations=len(selected))
        best = max(selected, key=lambda c: c['plan']['net_rr'], default=None)
        assessed.append((row, frames, original, sources, best))
    if not assessed:
        raise DataError('All shortlisted symbols failed current-bar validation')
    assessed.sort(key=lambda a: (a[4] is None, -(a[4]['plan']['net_rr'] if a[4] else 0)))
    row, frames, original, sources, hypothesis = assessed[0]
    symbol = row['symbol']
    candidate_id = f'{symbol}-{cutoff:%Y%m%dT%H%M%S}-{sources["5m"]["sha256"][:10]}'
    result = out / candidate_id
    result.mkdir(parents=True)
    (result / 'candles').mkdir()
    (result / 'charts').mkdir()
    identity = dict(schema=SCHEMA, candidate_id=candidate_id, venue='binance', market_type=MARKET,
                    symbol=symbol, timezone='UTC', as_of=iso(cutoff_ms), as_of_ms=cutoff_ms,
                    observed_at=bundle['observed_at'], github_base=BASE, adapter_sha256=sha256(Path(__file__).read_bytes()))
    for tf, values in original.items():
        write(result / 'candles' / (tf + '.json'), {
            **identity, 'timeframe': tf, 'last_closed_available_ms': values[-1][6] + 1,
            'source': sources[tf], 'columns': list(KLINE_COLUMNS), 'bars': values,
        })

    hours, quarters, fives = (frames[tf] for tf in ('1h', '15m', '5m'))
    vwap = quarters.groupby(quarters.date.dt.floor('D'))
    quarters['vwap'] = vwap.quote_volume.cumsum() / vwap.volume.cumsum().replace(0, float('nan'))
    panels = {'1h': hours.tail(72), '15m': quarters.tail(288),
              '5m_overview': fives.tail(576), '5m_zoom': fives.tail(72)}
    for tf, interval, count, visible in (('1d', '1D', 24, 29), ('4h', '4h', 4, 120)):
        grouped = aggregate(hours, interval)
        panels[tf] = grouped.loc[grouped.components.eq(count)].tail(visible)
    participation = entry_features(fives).reset_index(drop=True).tail(72)
    pane_sets = {'context': ('1d', '4h', '1h', '15m'), 'entry': ('5m_overview', '5m_zoom')}
    images = []
    interval_minutes = {'1d': 1440, '4h': 240, '1h': 60, '15m': 15, '5m_overview': 5, '5m_zoom': 5}
    for label, names in pane_sets.items():
        file = result / 'charts' / (label + '.png')
        draw_board(file, symbol, cutoff, {p: panels[p] for p in names}, [], {'status': 'RESEARCH_REVIEW'},
                   participation=participation if label == 'entry' else None, venue_label=MARKET)
        coverage = {}
        for name in names:
            frame = panels[name]
            minutes = interval_minutes[name]
            availability = frame.date.iloc[-1] + pd.Timedelta(minutes=minutes)
            if availability > cutoff:
                raise DataError('Chart panel would expose an incomplete bar')
            source_tf = '1h' if name in ('1d', '4h') else '5m' if name.startswith('5m') else name
            coverage[name] = dict(rows=len(frame), first_open=frame.date.iloc[0].isoformat(),
                                  last_available_at=availability.isoformat(), interval_minutes=minutes,
                                  source_sha256=sources[source_tf]['sha256'])
        images.append(dict(file=file.relative_to(result).as_posix(), sha256=sha256(file.read_bytes()), panels=coverage))
    with (result / 'scanner-ledger.csv').open('w', newline='', encoding='utf-8') as stream:
        keys = sorted(set().union(*(r.keys() for r in ledger)) - {'rules'})
        writer = csv.DictWriter(stream, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(ledger)
    write(result / 'candidate.json', {**identity, 'review_type': row['status'],
          'reason': 'A closed setup passed preliminary geometry' if hypothesis else
          'No unexpired setup passed the registered 15m formation and later 5m confirmation/geometry rules',
          'hypothesis': hypothesis, 'research_only': True, 'director_decision': None})
    last5 = fives.iloc[-1]
    write(result / 'features.json', {**identity, 'closed_bar_source_sha256': sources['5m']['sha256'],
          'last_5m_available_at': iso(original['5m'][-1][6] + 1),
          'regime_1h': row['regime_1h'], 'regime_4h': row['regime_4h'], 'atr_1h_frac': row['atr_1h_frac'],
          'last_15m_utc_day_vwap': None if pd.isna(quarters.vwap.iloc[-1]) else float(quarters.vwap.iloc[-1]),
          'rvol_5m_prior_48': float(participation.rvol.iloc[-1]),
          'taker_buy_quote_share_5m': float(last5.taker_buy_quote_volume / last5.quote_volume) if last5.quote_volume else None,
          'participation': 'KLINE_AGGRESSOR_VOLUME_PROXY', 'cvd': 'UNAVAILABLE',
          'volume_profile': 'UNAVAILABLE', 'news_macro': 'NOT_FETCHED',
          'structure_and_vwap_sources': {tf: sources[tf] for tf in ('1h', '15m')}})
    write(result / 'execution-constraints.json', {**identity, 'public_symbol_status': 'TRADING',
          'public_quote': {k: row[k] for k in ('bid', 'ask', 'quote_time_ms', 'spread_bps')},
          'public_filters': row['rules'], 'quote_source': source_map['books'], 'rule_source': source_map['exchange'],
          'notional_cap_usdt': '25', 'positions_cap': 2, 'research_leverage_range': [10, 25],
          'demo_account': 'UNKNOWN', 'demo_filter_equivalence': 'UNKNOWN'})
    write(result / 'chart-manifest.json', {**identity, 'images': images, 'future_candles': 0,
          'renderer_sha256': sha256((ROOT / 'scripts/local_recovery_charts.py').read_bytes())})
    write(result / 'source-receipts.json', {**identity, 'selected_candles': sources,
          'public_request_count': len(source_map), 'requests': source_map})
    write(result / 'MANIFEST.json', {name: sha256((result / name).read_bytes()) for name in sorted(REQUIRED)})
    print(json.dumps(verify(result)))


def verify(packet, fresh=False):
    manifest_path = packet / 'MANIFEST.json'
    manifest = load(manifest_path)
    files = {p.relative_to(packet).as_posix() for p in packet.rglob('*') if p.is_file()}
    if set(manifest) != REQUIRED or files != REQUIRED | {'MANIFEST.json'}:
        raise DataError('Missing or unexpected packet files')
    for name, digest in manifest.items():
        path = packet / name
        body = path.read_bytes()
        if path.is_symlink() or sha256(body) != digest or (name.endswith('.png') and not body.startswith(b'\x89PNG\r\n\x1a\n')):
            raise DataError('Packet hash or PNG type failed for ' + name)
    data = load(packet / 'candidate.json')
    if (data['schema'] != SCHEMA or data['market_type'] != MARKET or data['venue'] != 'binance'
            or data['candidate_id'] != packet.name or not re.fullmatch(r'[A-Z0-9]+-\d{8}T\d{6}-[a-f0-9]{10}', packet.name)):
        raise DataError('Packet identity or market type failed')
    if fresh and not -CLOCK_MAX_MS <= now_ms() - data['as_of_ms'] <= PACKET_FRESH_MS:
        raise DataError('Packet as-of clock is stale or in the future')
    for tf in LIMITS:
        candles = load(packet / 'candles' / (tf + '.json'))
        if candles['symbol'] != data['symbol'] or candles['as_of_ms'] != data['as_of_ms']:
            raise DataError('Candle identity mismatch')
        if len(closed_rows(candles['bars'], tf, data['as_of_ms'])) != len(candles['bars']):
            raise DataError('Incomplete candle in sealed packet')
    return {'candidate_id': packet.name, 'as_of': data['as_of'], 'review_type': data['review_type'],
            'packet_sha256': sha256(manifest_path.read_bytes()), 'members': len(manifest)}


def stage(packet, shared):
    expected = verify(packet, fresh=True)
    if not shared.is_dir() or shared.name != 'Shared' or shared.parent.name != 'OpenBot':
        raise DataError('Stage requires the discovered OpenBot Shared directory')
    namespace = shared / 'TradingLab-Integration-v1' / 'staged'
    namespace.mkdir(parents=True, exist_ok=True)
    target = namespace / packet.name
    if target.exists():
        raise DataError('Candidate already staged')
    with tempfile.TemporaryDirectory(prefix='.incoming-', dir=namespace) as pending:
        copy = Path(pending) / packet.name
        shutil.copytree(packet, copy)
        if verify(copy, fresh=True) != expected:
            raise DataError('Staged packet receipt differs')
        copy.rename(target)
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('capture').add_argument('out', type=Path)
    build_args = actions.add_parser('build')
    build_args.add_argument('raw', type=Path)
    build_args.add_argument('out', type=Path)
    check_args = actions.add_parser('verify')
    check_args.add_argument('packet', type=Path)
    check_args.add_argument('--fresh', action='store_true')
    stage_args = actions.add_parser('stage')
    stage_args.add_argument('packet', type=Path)
    stage_args.add_argument('shared', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'capture':
            capture(args.out)
        elif args.action == 'build':
            build(args.raw, args.out)
        elif args.action == 'verify':
            print(json.dumps(verify(args.packet, args.fresh)))
        else:
            print(json.dumps(stage(args.packet, args.shared)))
    except (DataError, OSError, ValueError, KeyError) as exc:
        print(f'{args.action}: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
