"""Matched decision coverage and existing version-1 read-only export enrichment."""
import json
from collections import Counter
import pandas as pd
import numpy as np
from foundation_common import *


def key(record): return (record['symbol'],record['available_at'],record['recipe'],record['side'])


def compare(run_id):
    out,data,spec=verify(run_id); economic=read(out/'economic-report.json'); records=read(out/'intelligent-opportunities.json')['records']
    by={n:[r for r in records if r['variant']==n] for n in spec['strategies'] if n.startswith('Intelligence')}
    fills={n:read(out/'native-results'/(n+'.json'))['strategy'][n]['trades'] for n in spec['strategies']}
    summary={}; cases=[]
    for name,rows in by.items():
        trades=fills[name]; net=economic['portfolios'][name]['native_net_usdt']
        native=read(out/'native-results'/(name+'.json'))['strategy'][name]
        accepted={key(r) for r in rows if r['status']=='RESEARCH_CANDIDATE'}
        # Exact native signal-close timestamp/side/tag; delayed fills remain
        # explicitly unmatched rather than joined to a convenient later candle.
        matched=0
        for r in rows:
            at=pd.Timestamp(r['available_at']); side=r['side']=='short'
            hit=next((t for t in trades if t['pair']==r['symbol'] and t['open_timestamp']==int(at.timestamp()*1000) and t['is_short']==side and (t.get('enter_tag') or '').startswith(r['recipe']+':')),None)
            if hit: matched+=1
            cases.append(dict(decision_id=r['decision_id'],variant=name,candidate_key=list(key(r)),status=r['status'],reason=r['reason'],
                native_fill=None if hit is None else dict(net_usdt=hit['profit_abs'],open_rate=hit['open_rate'],close_rate=hit['close_rate'],exit_reason=hit['exit_reason']),
                geometry=r['geometry']))
        # Daily closed-trade net is a descriptive development metric; native
        # marked-account equity and risk-adjusted metrics remain separate.
        daily=pd.Series(0.,index=pd.date_range('2026-10-01','2026-10-31',tz='UTC'))
        for t in trades:
            day=pd.Timestamp(t['close_date']).floor('D')
            if day in daily.index: daily.loc[day]+=t['profit_abs']
        sharpe=float(np.sqrt(365)*daily.mean()/daily.std(ddof=1)) if daily.std(ddof=1)>0 else None
        summary[name]=dict(parent_recipe_opportunities=len(rows),accepted=len(accepted),decisions=dict(Counter(r['reason'] for r in rows)),
            actual_native_modeled_fills=len(trades),exact_candidate_fill_joins=matched,unmatched_native_fills=len(trades)-matched,
            accepted_without_exact_fill=len(accepted)-matched,net_usdt=net,
            native_sharpe=native.get('sharpe'),native_sortino=native.get('sortino'),native_profit_factor=native.get('profit_factor'),
            native_rejected_signals=native.get('rejected_signals'),native_timedout_entry_orders=native.get('timedout_entry_orders'),
            native_canceled_trade_entries=native.get('canceled_trade_entries'),
            realized_daily_sharpe_descriptive=sharpe,native_max_drawdown_usdt=native.get('max_drawdown_abs'),
            by_week={str(w):dict(trades=len(g),net_usdt=sum(t['profit_abs'] for t in g)) for w in range(40,45) if (g:=[t for t in trades if pd.Timestamp(t['open_date']).isocalendar().week==w])},
            by_regime={regime:dict(candidate_count=sum(r['regime']==regime for r in rows),accepted=sum(r['regime']==regime and r['status']=='RESEARCH_CANDIDATE' for r in rows)) for regime in ['TREND','RANGE_OR_WEAK_TREND']})
    comparisons=[]
    for control,arm in [('IntelligenceCostV2','IntelligenceSignedV2'),('IntelligenceSignedV2','IntelligenceRegimeV2'),('IntelligenceAllV2','IntelligenceRegimeV2'),('IntelligenceRegimeV2','IntelligenceStructureV2'),('IntelligenceRegimeV2','IntelligenceProfileV2'),('IntelligenceRegimeV2','IntelligenceTargetV2'),('IntelligenceRegimeV2','IntelligenceNearestV2'),('IntelligenceRegimeV2','IntelligenceEntryV2')]:
        accepted={key(r) for r in by[arm] if r['status']=='RESEARCH_CANDIDATE'}
        missed=[]
        for t in fills[control]:
            recipe=(t.get('enter_tag') or '').split(':')[0]
            k=(t['pair'],pd.Timestamp(t['open_timestamp'],unit='ms',tz='UTC').isoformat(),recipe,'short' if t['is_short'] else 'long')
            if k not in accepted:
                missed.append(dict(candidate_key=list(k),control_net_usdt=t['profit_abs'],control_exit=t['exit_reason']))
        delta=summary[arm]['net_usdt']-summary[control]['net_usdt']
        comparisons.append(dict(control=control,arm=arm,net_delta_usdt=delta,
            accepted_delta=summary[arm]['accepted']-summary[control]['accepted'],
            control_native_fills_excluded_by_arm=missed,excluded_winners=sum(t['control_net_usdt']>0 for t in missed),excluded_losers=sum(t['control_net_usdt']<0 for t in missed),
            interpretation='HARMFUL_DEVELOPMENT_DIFFERENCE' if delta<0 else 'POSITIVE_DEVELOPMENT_DIFFERENCE_NOT_HOLDOUT' if delta>0 else 'NO_OBSERVED_DIFFERENCE',
            limitation='Native portfolios can differ through position occupancy. Excluded control fills are counterfactual evidence, not trades executed by the arm.'))
    write(out/'comparison.json',dict(version=2,portfolios=summary,comparisons=comparisons,
        baseline_portfolios={n:p for n,p in economic['portfolios'].items() if not n.startswith('Intelligence')},
        orderflow_uplift='INSUFFICIENT_EVIDENCE_NO_GENUINE_HISTORICAL_FLOW',profile_fidelity='OHLCV_PROXY',
        conclusion='Development attribution only; no profitability or independent holdout qualification',reserved_holdout='UNOBSERVED_UNTOUCHED_20261117_20261201'))
    write(out/'intelligence-casebook.json',dict(version=2,cases=cases,join='EXACT_PAIR_SIDE_RECIPE_SIGNAL_CLOSE_NATIVE_ENTRY_TIME'))
    print(json.dumps({n:dict(accepted=p['accepted'],fills=p['actual_native_modeled_fills'],net=p['net_usdt']) for n,p in summary.items()},indent=2))


def export(run_id):
    import jsonschema
    from foundation_report import validate_reader_content
    out,_,spec=verify(run_id); target=out/'openbot'
    if target.exists(): raise ValueError('preserve snapshot')
    current=read(out/'opportunities.json')['records']; hist=read(out/'intelligent-opportunities.json')['records']
    events=read(out/'event-briefing.json'); scan=read(out/'scan.json'); economics=read(out/'economic-report.json'); flow=read(out/'orderflow.json')
    candidates=[]
    # Current records first, then diverse accepted/rejected examples from each
    # arm. Full candidate ledger stays available separately without truncation.
    selected=list(current)
    for name in spec['strategies']:
        rows=[r for r in hist if r['variant']==name]
        for status in ['RESEARCH_CANDIDATE','WATCH','REJECT']:
            selected += [r for r in rows if r['status']==status][:5]
    for r in selected[:200]:
        r=dict(r); current_env=r['environment']=='CURRENT_PUBLIC_RESEARCH'
        r['event_context']=dict(clearance='UNKNOWN',coverage='PARTIAL_OR_UNKNOWN',
            event_ids=[e['event_id'] for e in events['events'] if e['freshness']=='RECENT'][:8] if current_env else [],
            reason='Selected current briefing context only; event time must be verified before use' if current_env else 'Current briefing never represents historical news')
        if current_env:
            observed=next((s for s in flow['rest'] if s['symbol']==r['symbol']),None)
            ws=next((s for s in flow['websocket'] if s['symbol']==r['symbol']),None)
            if observed:
                obs=observed['observation']; r['orderflow']=dict(status='PARTIAL' if not ws or not ws['windows'] else ws['windows'][-1]['coverage_status'],
                    evidence_id=run_id+':flow:'+observed['contract'],observed_at=flow['observed_at'],
                    executed_buy_base=obs['buy_base'] if obs else None,executed_sell_base=obs['sell_base'] if obs else None,
                    delta_base=obs['delta_base'] if obs else None,profile_fidelity='OBSERVED_TRADES',
                    confirmation='UNKNOWN_CURRENT_WINDOW_IS_NOT_HISTORICAL_SIGNAL_WINDOW',economic_uplift='UNMEASURED')
                latest=ws['windows'][-1] if ws and ws['windows'] else obs
                if latest:
                    r['orderflow']['observed_window']={k:latest.get(k) for k in
                        ['start_ms','end_ms','asof_ms','coverage_status','trade_count','buy_base','sell_base','delta_base',
                         'cvd_base_window','cvd_resets_at','imbalance','price_return','divergence','max_latency_ms']}
                    r['orderflow']['observed_trade_profile']=latest.get('profile')
                    r['orderflow']['location_assessments']=[v for v in latest.get('location_assessments',[]) if v['side']==r.get('side')]
                    r['orderflow']['causal_use']='Later current observation only; never retroactive confirmation of the earlier candle setup'
        candidates.append(r)
    snapshot=dict(schema_version=1,snapshot_id='intelligence:'+run_id,generated_at=now(),mode='READ_ONLY_RESEARCH',
        execution_authority='NATIVE_DETERMINISTIC_ADMISSION_ONLY',venue='gate',orders_created=False,
        source_provenance=dict(registration_sha256=sha(out/'registration.json'),data_manifest_sha256=sha(out/'data-manifest.json'),scan_sha256=sha(out/'scan.json'),flow_sha256=sha(out/'orderflow.json')),
        candidates=candidates,total_candidates=len(current)+len(hist),truncated=len(candidates)<len(current)+len(hist),
        event_briefing=events,market_summary=dict(eligible=scan['eligible_universe_count'],shortlist=len(scan['shortlisted']),deep_budget=5),
        economic_summary=dict(qualification='BLOCKED',portfolios=economics['portfolios']),
        uncertainty=['Inspected October development only; future reserved holdout unobserved','Historical genuine flow, depth, queue, news, membership UNKNOWN','Research records carry no order authority'])
    jsonschema.validate(snapshot,read(ROOT/'research/foundation/openbot.schema.json')); validate_reader_content(snapshot)
    if len(json.dumps(snapshot).encode())>1000000: raise ValueError('export bound')
    write(target/'research-snapshot.json',snapshot)
    write(target/'manifest.json',dict(schema_version=1,snapshot_sha256=sha(target/'research-snapshot.json'),schema_sha256=sha(ROOT/'research/foundation/openbot.schema.json'),
        bytes=(target/'research-snapshot.json').stat().st_size,access='Ordinary read-only JSON only; no lab/config/DB mounts',extension_version=2))
    for p in target.iterdir(): p.chmod(0o444)
    print('OpenBot schema-v1 compatible enriched snapshot:',len(candidates),'records')
