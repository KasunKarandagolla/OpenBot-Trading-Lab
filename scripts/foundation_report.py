"""Independent native-order economics and bounded sanitized reader snapshots."""
import csv
from decimal import Decimal as D
import json
import math
from pathlib import Path
import pandas as pd
from foundation_common import *


def report(run_id):
    from bonus_funding_audit import event_bounds
    out, data, spec = verify(run_id)
    if (out/'economic-report.json').exists(): raise ValueError('preserve economic report')
    events = {}
    for symbol in spec['pairs']:
        funding = frame(data, symbol, '1h', 'funding_rate')
        marks = frame(data, symbol, '1h', 'mark').set_index('date')
        events[symbol] = [dict(timestamp_ms=r.date.timestamp()*1000, rate=float(r.funding_rate),
                             mark_open=float(marks.loc[r.date, 'open'])) for _, r in funding.iterrows()]
    summaries, audits = {}, {}
    for name in spec['strategies']:
        result = read(out/'native-results'/(name+'.json'))['strategy'][name]
        trades = result['trades']; ledger = []; funding_rows = []
        maximum_residual = D(0)
        for trade in trades:
            entries = [o for o in trade['orders'] if o['ft_is_entry']]
            exits = [o for o in trade['orders'] if not o['ft_is_entry']]
            quantity = sum(D(str(o['amount'])) for o in entries)
            if quantity <= 0: raise ValueError('invalid native fill quantity')
            entry = sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in entries)/quantity
            if abs(sum(D(str(o['amount'])) for o in exits)-quantity) > D('.00000001'):
                raise ValueError('native fill quantities unbalanced')
            sign = D(-1 if trade['is_short'] else 1)
            gross = sum(sign*D(str(o['amount']))*(D(str(o['safe_price']))-entry) for o in exits)
            fees = sum(D(str(o['amount']))*D(str(o['safe_price']))*D(str(trade['fee_open'] if o['ft_is_entry'] else trade['fee_close'])) for o in trade['orders'])
            funding = D(str(trade.get('funding_fees', 0) or 0)); net = D(str(trade['profit_abs']))
            residual = abs(net-(gross-fees+funding)); maximum_residual = max(maximum_residual, residual)
            if residual > D('.00001'): raise ValueError('independent Decimal native ledger mismatch')
            turnover = sum(float(o['amount'])*float(o['safe_price']) for o in trade['orders'])
            low, high, observations = event_bounds(trade, events[trade['pair']])
            outside = max(low-float(funding), float(funding)-high, 0.)
            funding_rows.append(dict(pair=trade['pair'], open_date=trade['open_date'], native_funding=float(funding),
                source_funding_min=low, source_funding_max=high, outside_bounds_usdt=outside, events=observations))
            ledger.append(dict(pair=trade['pair'], side='short' if trade['is_short'] else 'long', open_date=trade['open_date'],
                close_date=trade['close_date'], open_timestamp=trade['open_timestamp'], close_timestamp=trade['close_timestamp'],
                entry_tag=trade.get('enter_tag'), exit_reason=trade['exit_reason'], duration_minutes=trade['trade_duration'],
                gross_usdt=float(gross), fees_usdt=float(fees), funding_usdt=float(funding), net_usdt=float(net),
                turnover_usdt=turnover, partial_exits=max(0, len(exits)-1)))
        ledger_dir = out/'trade-ledgers'; ledger_dir.mkdir(exist_ok=True)
        columns = list(ledger[0]) if ledger else ['pair', 'side', 'open_date', 'close_date', 'net_usdt']
        with (ledger_dir/(name+'.csv')).open('x', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=columns); writer.writeheader(); writer.writerows(ledger)
        net = sum(r['net_usdt'] for r in ledger)
        by_pair = {s: dict(trades=sum(r['pair'] == s for r in ledger), net_usdt=sum(r['net_usdt'] for r in ledger if r['pair'] == s)) for s in spec['pairs']}
        by_side = {s: dict(trades=sum(r['side'] == s for r in ledger), net_usdt=sum(r['net_usdt'] for r in ledger if r['side'] == s)) for s in ['long', 'short']}
        summaries[name] = dict(trades=len(ledger), native_net_usdt=net,
            gross_usdt=sum(r['gross_usdt'] for r in ledger), fees_usdt=sum(r['fees_usdt'] for r in ledger),
            signed_funding_usdt=sum(r['funding_usdt'] for r in ledger), fee_per_side=spec['fee_per_side'],
            win_count=sum(r['net_usdt'] > 0 for r in ledger), loss_count=sum(r['net_usdt'] < 0 for r in ledger),
            distinct_entry_days=len({r['open_date'][:10] for r in ledger}), by_pair=by_pair, by_side=by_side,
            partial_exits=sum(r['partial_exits'] for r in ledger),
            native_max_drawdown_usdt=result.get('max_drawdown_abs'),
            expectancy_usdt=net/len(ledger) if ledger else None,
            extra_cost_stress=[dict(extra_bps_per_side=b, net_usdt=net-sum(r['turnover_usdt'] for r in ledger)*b/10000) for b in spec['extra_cost_bps_per_side']],
            reconciliation_max_residual_usdt=str(maximum_residual),
            economic_status='ZERO_TRADES_INSUFFICIENT_EVIDENCE' if not ledger else 'REJECTED_UNDER_TESTED_ASSUMPTIONS' if net <= 0 else 'POSITIVE_DEVELOPMENT_UNQUALIFIED',
            best_trade=max(ledger, key=lambda r: r['net_usdt']) if ledger else None,
            worst_trade=min(ledger, key=lambda r: r['net_usdt']) if ledger else None)
        audits[name] = dict(trades=len(trades), outside_bounds_trades=sum(r['outside_bounds_usdt'] > 1e-8 for r in funding_rows), rows=funding_rows)
    write(out/'source-funding-audit.json', dict(schema_version=1, portfolios=audits,
        method='Source funding event x hourly mark open x native held-quantity bounds, independently reconstructed from fills',
        same_clock_priority='Venue UNKNOWN; interval bounds cover entry/exit before/after funding. Repair assumes event before exit.',
        persistent_partial_fill_restart_qualified=False))
    source_ok = all(r['outside_bounds_trades'] == 0 for name, r in audits.items() if name != 'RouterOnlyV1')
    old = read(out/'native-results/RouterOnlyV1.json')['strategy']['RouterOnlyV1']['trades']
    repaired = read(out/'native-results/FoundationRouterM0V1.json')['strategy']['FoundationRouterM0V1']['trades']
    keys = lambda ts: sorted((r['pair'], r['open_timestamp'], r['is_short']) for r in ts)
    write(out/'economic-report.json', dict(schema_version=1, environment='NATIVE_BACKTEST_DEVELOPMENT', venue='gate',
        generated_at=now(), evaluation_timerange=spec['evaluation_timerange'], protocol_sha256=sha(PROTOCOL),
        portfolios=summaries, all_order_accounting_reconciles=True, repaired_source_funding_within_bounds=source_ok,
        router_exit_comparison=dict(identical_entry_keys=keys(old) == keys(repaired),
            net_delta_usdt=summaries['FoundationRouterM0V1']['native_net_usdt']-summaries['RouterOnlyV1']['native_net_usdt'],
            interpretation='Inspected development comparison; changed position occupancy can change later admissions. No tuned parameters.'),
        cost_assumptions=dict(fee=spec['fee_evidence'], historical_account_fee_tier='UNKNOWN',
            funding='Actual Gate source events; native hourly mark-open valuation proxy',
            stress='Additional bps/side applied to actual fill turnover; no refill or stop-path simulation'),
        economic_qualification='BLOCKED',
        limits=['Current-survivor sample, not point-in-time historical discovery or an independent holdout',
            'No historical quote/depth/queue or actual fills; limit OHLCV fill model can overstate fillability',
            'No persistent native partial-fill/restart qualification or midnight account MTM baseline',
            'Historical news and original availability/receipt times UNKNOWN',
            'Separate portfolios are alternatives; never sum their performance.']))
    # Every candidate remains visible, including nonfills and subsequently missed
    # price paths. Subsequent paths are outcome evidence, never entry features.
    opportunities = read(out/'historical-opportunities.json')['records']
    fills = {(t['pair'], t['open_timestamp']): t for t in repaired}
    cases = []
    for record in opportunities:
        at = pd.Timestamp(record['available_at']); bars = frame(data, record['symbol'])
        future = bars.loc[(bars.date >= at) & (bars.date < at+pd.Timedelta(hours=4))]
        hit = fills.get((record['symbol'], at.timestamp()*1000))
        cases.append(dict(decision_id=record['decision_id'], status=record['status'], reason=record['reason'],
            available_at=record['available_at'], recipe=record['recipe'], side=record['side'], geometry=record['geometry'],
            native_fill=None if hit is None else dict(net_usdt=hit['profit_abs'], exit_reason=hit['exit_reason'], close_date=hit['close_date']),
            subsequent_path=dict(label='POST_DECISION_OUTCOME_NOT_ENTRY_INFORMATION', hours=4,
                high=float(future.high.max()) if len(future) else None, low=float(future.low.min()) if len(future) else None,
                last_close=float(future.close.iloc[-1]) if len(future) else None)))
    write(out/'casebook.json', dict(schema_version=1, cases=cases, join_policy='Exact native pair/entry timestamp; unfilled or delayed fills are not assumed executed'))
    if not source_ok: raise ValueError('source funding audit failed; economics BLOCKED')
    print(json.dumps({n: {'trades': r['trades'], 'net_usdt': r['native_net_usdt'], 'partial_exits': r['partial_exits']} for n, r in summaries.items()}, indent=2))


def export(run_id):
    import jsonschema
    out, _, _ = verify(run_id)
    target = out/'openbot'; target.mkdir()
    current = read(out/'opportunities.json'); hist = read(out/'historical-opportunities.json')
    events = read(out/('event-briefing-reparsed.json' if (out/'event-briefing-reparsed.json').exists() else 'event-briefing.json')); economics = read(out/'economic-report.json')
    scan = read(out/'scan.json')
    candidates = []
    allowed = {'schema_version', 'decision_id', 'venue', 'symbol', 'contract_id', 'status', 'reason', 'available_at', 'expires_at',
        'observed_at', 'observation_reason', 'environment', 'recipe', 'side', 'regime', 'adx_1h', 'return_4h', 'signed_suitability',
        'geometry', 'opposing_evidence', 'quote', 'data_gaps', 'execution_status', 'execution_reason', 'source_manifest_sha256', 'orders_created'}
    for row in current['records']+hist['records']:
        clean_row = {k: v for k, v in row.items() if k in allowed}
        clean_row['environment'] = row.get('environment', 'CURRENT_PUBLIC_RESEARCH')
        clean_row['event_context'] = dict(clearance='UNKNOWN', coverage='PARTIAL_OR_UNKNOWN',
            event_ids=[e['event_id'] for e in events['events'][:12]] if clean_row['environment'] == 'CURRENT_PUBLIC_RESEARCH' else [],
            reason='Current briefing is not historical event evidence' if clean_row['environment'] == 'BACKTEST_RESEARCH' else 'Unverified coverage cannot clear event risk')
        candidates.append(clean_row)
    snapshot = dict(schema_version=1, snapshot_id='foundation:'+run_id, generated_at=now(),
        mode='READ_ONLY_RESEARCH', execution_authority='NATIVE_DETERMINISTIC_ADMISSION_ONLY',
        venue='gate', source_provenance=dict(registration_sha256=sha(out/'registration.json'),
            data_manifest_sha256=sha(out/'data-manifest.json'), scan_sha256=sha(out/'scan.json')),
        candidates=candidates[:200], total_candidates=len(candidates), truncated=len(candidates) > 200,
        event_briefing=events, market_summary=dict(eligible=scan['eligible_universe_count'], shortlist=scan['shortlisted'],
            rejected_examples=scan['rejected'][:10]+scan['metadata_rejected'][:10], membership=scan['membership']),
        economic_summary=dict(qualification=economics['economic_qualification'], portfolios=economics['portfolios']),
        orders_created=False, uncertainty=['No account MTM/recovery qualification', 'No full point-in-time historical membership',
            'News coverage partial; no current execution from research files'])
    schema = read(ROOT/'research/foundation/openbot.schema.json')
    jsonschema.validate(snapshot, schema)
    serialized = json.dumps(snapshot, allow_nan=False)
    if len(serialized.encode()) > 1_000_000: raise ValueError('export exceeds 1MB bound')
    forbidden = ('sqlite', '/lab/', '/workspace/', 'api_server', 'jwt_secret', 'password', 'secret_key')
    if any(word in serialized.lower() for word in forbidden): raise ValueError('export contains forbidden runtime/admin details')
    write(target/'research-snapshot.json', snapshot)
    write(target/'manifest.json', dict(schema_version=1, snapshot_sha256=sha(target/'research-snapshot.json'),
        schema_sha256=sha(ROOT/'research/foundation/openbot.schema.json'), bytes=(target/'research-snapshot.json').stat().st_size,
        access='Copy only these ordinary JSON files into a separate read-only mount. Never mount the lab root, DB, config or auth overlay.',
        freshness='Use generated_at and each available_at/expires_at; historical candidates are already expired.'))
    for path in target.iterdir(): path.chmod(0o444)
    print('OpenBot export:', len(candidates[:200]), 'records;', (target/'research-snapshot.json').stat().st_size, 'bytes')
