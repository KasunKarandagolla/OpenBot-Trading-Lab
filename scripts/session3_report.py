"""Owner report from frozen scans, native ledgers and verification receipts."""
import argparse
from collections import Counter
import csv
import gzip
import io
import json
from pathlib import Path


def write(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')


def report(root):
    root=Path(root);matrix=[]
    for path in sorted(root.glob('final-w*/summary.json')):
        native=json.loads(path.read_text());ledger=json.loads((path.parent/'ledger.json').read_text())
        check=json.loads((path.parent/'independent-arithmetic-audit.json').read_text())
        if check['status']!='PASS':raise ValueError('UNVERIFIED_NATIVE_LEDGER')
        native.update(run=path.parent.name,fees_usdt=check['fees_usdt'],funding_net_usdt=check['funding_net_usdt'],
                      exit_reasons=check['exit_reasons'],source_funding_events=check['checks'].get('source_funding_events',0),
                      gross_price_pnl=sum((-1 if t['is_short'] else 1)*t['amount']*(t['close_rate']-t['open_rate']) for t in ledger))
        matrix.append(native)
        # Legacy controls lack their full custom plan in native exports. Explicitly
        # normalize to the exported initial protective bound, not an invented stop.
        if not (path.parent/'selected-plans.json').exists():
            values=[]
            for t in ledger:
                cash=t['amount']*abs(t['open_rate']-t['initial_stop_loss_abs'])
                values.append(dict(pair=t['pair'],open_timestamp=t['open_timestamp'],is_short=t['is_short'],
                                   native_initial_stop_cash=cash,net_usdt=t['profit_abs'],
                                   native_bound_R=t['profit_abs']/cash if cash else None,
                                   cost_inclusive_native_bound_R=t['profit_abs']/(cash+t['amount']*t['open_rate']*.0033) if cash else None,
                                   basis='Exported native initial protective bound; not a reconstructed custom structural plan'))
            write(path.parent/'control-initial-bound-r.json',values)
    if len(matrix)!=14:raise ValueError('EXPECTED_14_NATIVE_PORTFOLIOS')
    comparisons=[]
    def keyed(label):
        folder=root/label
        plans={p['decision_id']:p for p in json.loads((folder/'selected-plans.json').read_text())}
        return {plans[t['enter_tag']]['setup_key']:t for t in json.loads((folder/'ledger.json').read_text())}
    for base,variant in [('final-w1-breakout','final-w1-immediate'),('final-w1-reversal','final-w1-early'),
                         ('final-w1-breakout','final-w1-breakout-touch'),('final-w1-reversal','final-w1-reversal-touch')]:
        a,b=keyed(base),keyed(variant);common=set(a)&set(b)
        comparisons.append(dict(base=base,variant=variant,common_filled_setups=len(common),base_only_fills=len(set(a)-set(b)),
                                variant_only_fills=len(set(b)-set(a)),matched_base_net=sum(a[k]['profit_abs'] for k in common),
                                matched_variant_net=sum(b[k]['profit_abs'] for k in common),
                                full_portfolio_delta=sum(t['profit_abs'] for t in b.values())-sum(t['profit_abs'] for t in a.values()),
                                qualification='Same frozen setup identities; different timing/fills and portfolio occupancy. Not a fixed-entry causal treatment estimate.'))
    population=[]
    for phase in ['w1-retest','w2-retest']:
        folder=root/'registered-final'/phase
        scans=json.loads(gzip.decompress((folder/'scans.json.gz').read_bytes()))
        groups={}
        for row in scans:groups.setdefault(row['as_of'],[]).append(row)
        thin=[];selected_keys=set()
        for at,rows in sorted(groups.items()):
            possible=sorted([r for r in rows if r['status']=='DEVELOPING_WATCH'],key=lambda r:(r['distance_to_boundary_atr'],-r['quote_volume_24h'],r['symbol']))
            chosen={r['symbol'] for r in possible[:4]}
            for row in rows:
                selected=row['symbol'] in chosen
                if selected:selected_keys.update(s['setup_key'] for s in row['setups'])
                reason=('SHORTLISTED_PREKNOWN_BOUNDARY' if selected else 'HELD_OUTSIDE_FOUR_MARKET_ATTENTION_BUDGET' if row['status']=='DEVELOPING_WATCH' else '|'.join(row['reasons']))
                thin.append(dict(as_of=at,symbol=row['symbol'],status=row['status'],shortlisted=selected,reason=reason,
                                 regime=row.get('regime'),trend1h=row.get('trend1h'),trend4h=row.get('trend4h'),
                                 quote_volume_24h=row.get('quote_volume_24h'),distance_atr=row.get('distance_to_boundary_atr')))
        summary=json.loads((folder/'summary.json').read_text())
        if len(selected_keys)!=summary['selected_setups']:raise ValueError('SHORTLIST_AUDIT_DIVERGENCE')
        unselected=json.loads(gzip.decompress((folder/'unselected-plans.json.gz').read_bytes()))
        unselected_qualified=[p for p in unselected if p['diagnostics']=='GEOMETRY_PASS_RESEARCH_ONLY']
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(thin[0]));writer.writeheader();writer.writerows(thin)
        (folder/'population-audit.csv.gz').write_bytes(gzip.compress(stream.getvalue().encode(),mtime=0))
        population.append(dict(phase=phase,market_observations=len(thin),markets=len({x['symbol'] for x in thin}),
                               reasons=dict(Counter(x['reason'] for x in thin)),
                               unselected_geometry_admissible=len(unselected_qualified),
                               unselected_outcomes='NOT_EXECUTED_NATIVE; these are potential missed research proposals, not counted missed winners',
                               sampled_unselected=next((x for x in thin if not x['shortlisted'] and x['status']=='DEVELOPING_WATCH'),None),
                               sampled_no_setup=next((x for x in thin if x['status']=='INTERESTING'),None)))
    groups={'BreakoutAcceptanceRetest':['final-w1-breakout','final-w2-breakout'],
            'SweepReclaimReversal':['final-w1-reversal','final-w2-reversal'],
            'TrendPullbackBaselineV1':['final-w1-trend','final-w2-trend'],
            'VWAPTrendContinuationV1':['final-w1-vwap','final-w2-vwap'],
            'LiquiditySweepReversalV1':['final-w1-sweep','final-w2-sweep']}
    totals=[];byrun={row['run']:row for row in matrix}
    for strategy,names in groups.items():
        rows=[byrun[n] for n in names];net=sum(x['native_net_usdt'] for x in rows);stress=sum(x['stress_net_usdt']['10'] for x in rows)
        totals.append(dict(strategy=strategy,trades=sum(x['trades'] for x in rows),native_net_usdt=net,extra_10bp_side_net_usdt=stress,
                           verdict='REJECTED_UNDER_TESTED_ASSUMPTIONS' if net<0 else 'UNQUALIFIED_COST_FRAGILE' if stress<0 else 'PROMISING_UNQUALIFIED',
                           scope='Sum of two separate weekly portfolios, each reset to 1000 virtual USDT; not a combined or compounded account'))
    value=dict(status='HISTORICAL_VERTICAL_SLICE_IMPLEMENTED',economic_qualification='UNQUALIFIED',
               native_original_agents='AGENT_NOT_VERIFIED / NO ACTION',live_monitoring='NOT_ACCEPTED_NETWORK_BLOCKED_AND_LIVE_ADAPTER_UNVALIDATED',
               matrix=matrix,weekly_sums=totals,comparisons=comparisons,population=population,
               ledger_scope='Native historical Freqtrade, 1x, <=25 USDT initial notional, <=2 slots, 5bp/side assumed fees; source funding with hourly mark approximation. No queue/spread/impact/partial-fill proof.',
               cost_stress='Fixed-fill post-ledger additional 5/10/20 bp per side; no order-book or queue reflow.',execution_authority='NONE')
    write(root/'economic-report.json',value)
    lines=['# Native economic results — Session 3','',
           'All results are historical research on previously studied Binance data. Nothing is activated. Each row is a separate portfolio; do not add overlapping rows.',
           '', '| Run | Fills L/S | Net USDT | Extra 10 bp/side | Max native drawdown USDT |', '|---|---:|---:|---:|---:|']
    for v in matrix:lines.append(f"| {v['run']} | {v['longs']}/{v['shorts']} | {v['native_net_usdt']:.8f} | {v['stress_net_usdt']['10']:.8f} | {v['max_drawdown_abs']:.8f} |")
    lines+=['','Two weekly runs per main strategy (wallet resets; no compounding):','', '| Strategy | Fills | Net USDT | Extra 10 bp/side | Judgment |','|---|---:|---:|---:|---|']
    for v in totals:lines.append(f"| {v['strategy']} | {v['trades']} | {v['native_net_usdt']:.8f} | {v['extra_10bp_side_net_usdt']:.8f} | {v['verdict']} |")
    lines+=['','Native `ledger.json`, `orders.json`, `terminal.json`, `summary.json`, ZIP export and independent source-arithmetic audit are retained for every run. Challenger R uses the actual fill and frozen structural stop. Controls have separate `control-initial-bound-r.json`; their custom plan is not reconstructed from an incomplete export.',
            '', 'The second reversal week is positive. The combined reversal research result turns negative with 10 bp extra per side. The breakout retest loses overall; its immediate-entry comparator loses less in week one. The early-reclaim reversal loses substantially more. These are development observations, not evidence of edge or a recommendation to trade.',
            '', 'Historical metadata use a later public snapshot; actual historical account fee tiers, book spread, queue, impact, exact settlement mark and real partial fills remain unqualified. Funding events are independently recomputed from pinned sources using (actual entry fill, exit] and same-hour mark opens. No native original Risk receipt exists.']
    (root/'ECONOMICS.md').write_text('\n'.join(lines)+'\n')
    return value

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);a=p.parse_args()
    result=report(a.root);print(json.dumps(result['weekly_sums'],indent=2))
