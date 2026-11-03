"""Independent order-accounting, source funding bounds and schema-v1 handoff."""
from collections import Counter,defaultdict
from decimal import Decimal as D
from dataclasses import asdict
import csv
import json
import math
import numpy as np
import pandas as pd
from policy_common import *
from intelligence_features import COST


def report(run_id):
    from bonus_funding_audit import event_bounds
    out,data,spec=verify(run_id)
    if (out/'economic-report.json').exists():raise ValueError('preserve economic report')
    candidates=read(out/'opportunity-ledger.json')['records'];portfolios={};casebook=[];funding_audits={}
    events={};bars={}
    for symbol in spec['pairs']:
        f=frame(data,symbol,'1h','funding_rate');m=frame(data,symbol,'1h','mark').set_index('date')
        events[symbol]=[dict(timestamp_ms=r.date.timestamp()*1000,rate=float(r.funding_rate),mark_open=float(m.loc[r.date,'open'])) for _,r in f.iterrows()]
        bars[symbol]=frame(data,symbol)
    for path in sorted((out/'native-results').glob('*.json')):
        label=path.stem;name,period,lev=label.rsplit('-',2);result=read(path)['strategy'][name];trades=result['trades'];ledger=[];audit=[]
        states=read(out/'trade-states'/(label+'.json'));state_map={(s['pair'],pd.Timestamp(s['open_date']).timestamp()*1000):s for s in states}
        for t in trades:
            entries=[o for o in t['orders'] if o['ft_is_entry']];exits=[o for o in t['orders'] if not o['ft_is_entry']]
            quantity=sum(D(str(o['amount'])) for o in entries)
            avg=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in entries)/quantity
            if abs(quantity-sum(D(str(o['amount'])) for o in exits))>D('0.00000001'):raise ValueError('native quantities do not balance')
            sign=D(-1 if t['is_short'] else 1)
            gross=sum(sign*D(str(o['amount']))*(D(str(o['safe_price']))-avg) for o in exits)
            fees=sum(D(str(o['amount']))*D(str(o['safe_price']))*D(str(t['fee_open'] if o['ft_is_entry'] else t['fee_close'])) for o in t['orders'])
            funding=D(str(t.get('funding_fees') or 0));net=D(str(t['profit_abs']));residual=abs(net-(gross-fees+funding))
            if residual>D('.00001'):raise ValueError('independent Decimal PnL mismatch '+label)
            low,high,observations=event_bounds(t,events[t['pair']]);outside=max(low-float(funding),float(funding)-high,0)
            audit.append(dict(pair=t['pair'],open_date=t['open_date'],source_min=low,source_max=high,native=float(funding),outside=outside,events=observations))
            state=state_map.get((t['pair'],t['open_timestamp']),{});g=state.get('plan')
            side='short' if t['is_short'] else 'long';at=pd.Timestamp(t['open_timestamp'],unit='ms',tz='UTC')
            matches=[c for c in candidates if c['variant']==name and c['symbol']==t['pair'] and c['side']==side and c['reason']=='TRADE'
                and pd.Timestamp(c['available_at'])<=at<pd.Timestamp(c['expires_at']) and t.get('enter_tag','').startswith(c['recipe']+':')]
            if not g and len(matches)==1 and matches[0].get('geometry'):
                g=matches[0]['geometry']  # frozen control geometry, not its loose emergency stop
            if name.startswith('Policy') and (len(matches)!=1 or not g):raise ValueError('ambiguous native fill/decision join '+label)
            risk=float(quantity)*float(avg)*((abs(float(avg)-g['stop'])/float(avg)+COST) if g else abs(float(avg)-float(t['initial_stop_loss_abs']))/float(avg)+COST)
            b=bars[t['pair']];resolution='15m_BOUNDS_WITH_ENTRY_EXIT_CANDLE_CHRONOLOGY_UNKNOWN'
            if period in ('detail','newday'):
                b=frame(data,t['pair'],'1m');resolution='1m_BOUNDS_INTRAMINUTE_ORDER_UNKNOWN'
            b=b.loc[(b.date>=at)&(b.date<=pd.Timestamp(t['close_timestamp'],unit='ms',tz='UTC'))]
            mfe=(float(b.high.max())-float(avg)) if side=='long' else (float(avg)-float(b.low.min()))
            mae=(float(avg)-float(b.low.min())) if side=='long' else (float(b.high.max())-float(avg))
            r=dict(trade_id=t.get('trade_id',state.get('id')),decision_id=matches[0]['decision_id'] if len(matches)==1 else None,
                pair=t['pair'],side=side,recipe=t.get('enter_tag','').split(':')[0],open_date=t['open_date'],close_date=t['close_date'],
                open_timestamp=t['open_timestamp'],close_timestamp=t['close_timestamp'],exit_reason=t['exit_reason'],
                duration_minutes=t['trade_duration'],gross_usdt=float(gross),fees_usdt=float(fees),funding_usdt=float(funding),net_usdt=float(net),
                initial_risk_usdt=risk,risk_unit_basis='FROZEN_LOGICAL_STOP_PLUS_COST' if g else 'NATIVE_INITIAL_PROTECTIVE_STOP_PLUS_COST',net_r=float(net)/risk if risk else None,turnover_usdt=sum(float(o['amount'])*float(o['safe_price']) for o in t['orders']),
                partial_exits=max(0,len(exits)-1),mfe_price_bound=max(0,mfe) if len(b) else None,mae_price_bound=max(0,mae) if len(b) else None,
                excursion_resolution=resolution,pnl_residual=str(residual),entry_notional=float(avg*quantity),
                retained_fraction_of_full_quantity_mfe=float(gross)/(float(quantity)*max(0,mfe)) if len(b) and mfe>0 else None)
            ledger.append(r)
        p=out/'trade-ledgers'/(label+'.csv');p.parent.mkdir(exist_ok=True)
        with p.open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(ledger[0]) if ledger else ['decision_id','net_usdt']);writer.writeheader();writer.writerows(ledger)
        net=sum(r['net_usdt'] for r in ledger);wins=[r['net_usdt'] for r in ledger if r['net_usdt']>0];losses=[r['net_usdt'] for r in ledger if r['net_usdt']<0]
        monthly={}
        for month in sorted({r['open_date'][:7] for r in ledger}):
            subset=[r for r in ledger if r['open_date'].startswith(month)];monthly[month]=dict(trades=len(subset),net_usdt=sum(r['net_usdt'] for r in subset))
        daily=defaultdict(float)
        for r in ledger:daily[r['close_date'][:10]]+=r['net_usdt']
        # Whole UTC days resampled together; correlated symbols never independent samples.
        rng=np.random.default_rng(33003);values=np.array(list(daily.values()))
        bootstrap=[float(rng.choice(values,len(values),replace=True).sum()) for _ in range(1000)] if len(values)>1 else []
        eventpath=out/'position-events'/(label+'.jsonl');account_rows=[]
        if eventpath.exists():
            for line in eventpath.read_text().splitlines():
                event=json.loads(line)
                if event['event']=='ACCOUNT_SNAPSHOT':account_rows.append(event)
        peak=1000.;dd=0
        for a in account_rows:peak=max(peak,a['equity']);dd=max(dd,peak-a['equity'])
        allowed=[c for c in candidates if c['variant']==name and c['reason']=='TRADE']
        filled_ids={r['decision_id'] for r in ledger};wanted=len([c for c in allowed if period=='all' or ('2026-10-01'<=c['available_at']<'2026-11-01' if period=='october' else '2026-10-28'<=c['available_at']<'2026-11-02' if period=='detail' else '2026-11-01'<=c['available_at']<'2026-11-02')])
        portfolios[label]=dict(strategy=name,period=period,leverage=int(lev),trades=len(ledger),admitted_signals=wanted,filled_decisions=len(filled_ids-{None}),
            unfilled_or_capacity_or_risk_blocked=max(0,wanted-len(filled_ids-{None})),native_net_usdt=net,gross_usdt=sum(r['gross_usdt'] for r in ledger),
            fees_usdt=sum(r['fees_usdt'] for r in ledger),funding_usdt=sum(r['funding_usdt'] for r in ledger),
            expectancy_usdt=net/len(ledger) if ledger else None,net_r=sum(r['net_r'] for r in ledger),win_rate=len(wins)/len(ledger) if ledger else None,
            mean_win=float(np.mean(wins)) if wins else None,mean_loss=float(np.mean(losses)) if losses else None,
            profit_factor=sum(wins)/abs(sum(losses)) if losses else None,
            partial_exits=sum(r['partial_exits'] for r in ledger),by_month=monthly,
            by_side={s:dict(trades=sum(r['side']==s for r in ledger),net_usdt=sum(r['net_usdt'] for r in ledger if r['side']==s)) for s in ['long','short']},
            by_recipe={s:dict(trades=sum(r['recipe']==s for r in ledger),net_usdt=sum(r['net_usdt'] for r in ledger if r['recipe']==s)) for s in sorted({r['recipe'] for r in ledger})},
            by_pair={s:dict(trades=sum(r['pair']==s for r in ledger),net_usdt=sum(r['net_usdt'] for r in ledger if r['pair']==s)) for s in spec['pairs']},
            exit_contributions={s:dict(trades=sum(r['exit_reason']==s for r in ledger),net_usdt=sum(r['net_usdt'] for r in ledger if r['exit_reason']==s)) for s in sorted({r['exit_reason'] for r in ledger})},
            native_closed_drawdown_usdt=result.get('max_drawdown_abs'),hourly_mtm_drawdown_usdt=dd if account_rows else None,
            mark_equity_resolution='HOURLY_OPEN_MARK_PROXY_NOT_INTRAHOUR_DRAWDOWN',
            mean_hold_minutes=float(np.mean([r['duration_minutes'] for r in ledger])) if ledger else None,
            notional_minutes=sum(r['entry_notional']*r['duration_minutes'] for r in ledger),
            native_execution_counters={k:result.get(k) for k in ['rejected_signals','timedout_entry_orders','timedout_exit_orders','canceled_entry_orders','canceled_trade_entries','replaced_entry_orders']},
            extra_adverse_funding=[dict(extra_bps_per_initial_notional=b,net_usdt=net-sum(r['entry_notional'] for r in ledger)*b/10000,assumption='One additional adverse funding charge per trade, conservative sensitivity not observed source fees') for b in [3,10,25]],
            active_entry_days=len({r['open_date'][:10] for r in ledger}),active_realization_days=len(daily),
            daily_block_bootstrap_net_95=np.quantile(bootstrap,[.025,.975]).tolist() if bootstrap else None,
            uncertainty_method='UTC-day block resampling of realized net; shared crypto shocks and serial dependence remain, not independent trade CI',
            extra_cost_stress=[dict(bps_per_side=b,net_usdt=net-sum(r['turnover_usdt'] for r in ledger)*b/10000) for b in spec['cost_stress_bps_per_side']],
            max_pnl_residual=max((float(r['pnl_residual']) for r in ledger),default=0),funding_outside_bounds=sum(r['outside']>1e-8 for r in audit),
            status='ZERO_TRADES' if not ledger else 'POSITIVE_DEVELOPMENT_UNQUALIFIED' if net>0 else 'NEGATIVE_UNQUALIFIED')
        funding_audits[label]=audit
        if period=='all':
            for c in [x for x in candidates if x['variant']==name]:
                fills=[r for r in ledger if r['decision_id']==c['decision_id']]
                g=c['geometry'];path_info=None
                if g:
                    at=pd.Timestamp(c['available_at']);b=bars[c['symbol']];b=b.loc[(b.date>=at)&(b.date<at+pd.Timedelta(hours=g['max_hold_hours']))]
                    sg=1 if c['side']=='long' else -1
                    target=b.high.ge(g['target']) if sg==1 else b.low.le(g['target']);stop=b.low.le(g['stop']) if sg==1 else b.high.ge(g['stop'])
                    ti=b.loc[target,'date'].min() if target.any() else None;si=b.loc[stop,'date'].min() if stop.any() else None
                    path_info=dict(label='POST_DECISION_PRICE_PATH_NOT_A_COUNTERFACTUAL_NATIVE_TRADE',target_first_bar=str(ti),stop_first_bar=str(si),
                        ordering='SAME_BAR_UNKNOWN' if ti is not None and ti==si else 'TARGET_BEFORE_STOP' if ti is not None and (si is None or ti<si) else 'STOP_BEFORE_TARGET' if si is not None else 'NEITHER',
                        valid_until=c['expires_at'],queue='UNKNOWN')
                casebook.append(dict(decision_id=c['decision_id'],variant=name,status=c['status'],reason=c['reason'],geometry=g,native_fill=fills[0] if fills else None,subsequent_path=path_info))
    write(out/'source-funding-audit.json',dict(portfolios=funding_audits,method='Independent source event x native quantity before/after same-clock orders; venue boundary priority bounded'))
    write(out/'casebook.json',dict(cases=casebook,join='symbol/side/recipe and [available,expires); native persisted geometry required'))
    write(out/'economic-report.json',dict(schema_version=3,portfolios=portfolios,economic_qualification='PENDING_NO_PROMOTION',candidate='PolicyManagedV3',
        comparisons='Separate chronological portfolios, never additive; common 25USDT cap and 1x except explicitly named leverage scenarios',
        original_results_unchanged=True,source_comparison=read(out/'parent-source-comparison.json'),
        limits=['Current survivor cohort; historical membership unknown','August-October inspected development; November1 one completed day is not independent qualification',
            'Native range fills; intra-minute order and queue unknown','Historical real flow/news unknown; current observations never backdated','Hourly open mark proxy; no intrahour liquidation reconstruction'],
        reserved_holdout='20261117-20261201 UNOBSERVED_UNACQUIRED'))
    if any(p['funding_outside_bounds'] for p in portfolios.values()):raise ValueError('funding audit failed; retain results as blocked')
    print(json.dumps({k:{x:v[x] for x in ['trades','native_net_usdt','win_rate','partial_exits']} for k,v in portfolios.items()},indent=2),flush=True)


def scenarios(run_id):
    from policy_risk import Account,size
    out,data,spec=verify(run_id);contracts=read(out/'contracts.json');rows=[]
    clock=pd.Timestamp.now(tz='UTC').timestamp()
    for symbol,c in contracts.items():
        price=float(frame(data,symbol).close.iloc[-1])
        for side in ['long','short']:
            sign=1 if side=='long' else -1
            for lev in [1,10,20]:
                a=Account(1000,0,1000,0,0,0,0,0,0,0,1000,1000,asof=clock)
                for distance in [.005,.015,.025]:
                    v=size(a,clock=clock,side=side,entry=price,stop=price*(1-sign*distance),leverage=lev,contract=c,cap=100)
                    rows.append(dict(symbol=symbol,side=side,leverage=lev,logical_stop_distance=distance,verdict=v,classification='CURRENT_SPEC_SCENARIO_NOT_HISTORICAL_ACCOUNT_OR_OBSERVED_LIQUIDATION'))
    write(out/'leverage-scenarios.json',dict(rows=rows,constant_notional_cap=100,source_sha256=sha(out/'contracts.json'),
        distinction='Leverage changes margin and liquidation buffer, not the logical stop, notional cap or intended loss. Unsupported inputs reject.'))
    print('Contract-backed leverage scenarios',len(rows),Counter(r['verdict']['status'] for r in rows),flush=True)


def export(run_id):
    import jsonschema
    from foundation_report import validate_reader_content
    out,_,spec=verify(run_id);ledger=read(out/'opportunity-ledger.json')['records'];current=read(out/'opportunities.json')['records'];economics=read(out/'economic-report.json')
    release_path=ROOT/'research/policy/release.json'
    release=read(release_path) if release_path.exists() else None
    selected=release['strategy'] if release else spec['candidate']
    candidates=[]
    selected_records=sorted([r for r in ledger if r['variant']==selected],key=lambda r:(r['status']!='RESEARCH_CANDIDATE',r['available_at'],r['decision_id']))
    for row in current+selected_records:
        r=dict(row);r['event_context']=dict(clearance='UNKNOWN',coverage='PARTIAL_OR_UNKNOWN',event_ids=[],reason='Current context never confirms historical decisions')
        r['policy_id']=spec['policy_id'];r['risk_contract']=dict(policy_id=spec['policy_id'],reference='policy_contract.risk');r['execution_authority']='NATIVE_DETERMINISTIC_CALLBACKS_ONLY'
        candidates.append(r)
    flow=read(out/'orderflow.json') if (out/'orderflow.json').exists() else dict(status='UNKNOWN')
    # Only timestamped public interpretation goes to OpenBot, never private paths/raw prints.
    def sanitize(v):
        if isinstance(v,dict):return {k:sanitize(x) for k,x in v.items() if not k.endswith('local_path') and k not in ['footprint','cvd_checkpoints']}
        if isinstance(v,list):return [sanitize(x) for x in v]
        return v
    events=read(out/'event-briefing.json') if (out/'event-briefing.json').exists() else dict(schema_version=1,clearance='UNKNOWN',coverage='UNKNOWN',events=[])
    snap=dict(schema_version=1,snapshot_id='policy:'+run_id+':'+selected+(':'+('release' if release else 'preregistered')),generated_at=now(),mode='READ_ONLY_RESEARCH',venue='gate',orders_created=False,
        source_provenance=dict(registration_sha256=sha(out/'registration.json'),data_manifest_sha256=sha(out/'data-manifest.json'),opportunity_ledger_sha256=sha(out/'opportunity-ledger.json')),
        candidates=candidates[:200],total_candidates=len(candidates),truncated=len(candidates)>200,event_briefing=events,
        policy_contract=dict(policy_id=spec['policy_id'],risk=spec['risk'],strategy=selected,preregistered_strategy=spec['candidate'],selection='POST_DEVELOPMENT_REFERENCE_NOT_INDEPENDENT_QUALIFICATION' if release else 'PREREGISTERED_CANDIDATE',functional_status='NATIVE_FIXTURES_AND_BACKTESTS_SEE_ACCEPTANCE',economic_status='UNQUALIFIED',persistent_paper_allowed=False),
        market_summary={k:v for k,v in read(out/'scan.json').items() if k not in ['rejected','valid_below_cap']}|dict(rejected_count=len(read(out/'scan.json')['rejected']),rejected_examples=read(out/'scan.json')['rejected'][:10]),economic_summary=economics['portfolios'],current_qualified_flow=sanitize(flow),
        position_events=[],uncertainty=economics['limits'])
    # Selected deterministic lifecycle events preserve decision->trade->outcome joins.
    decision_lookup={r['geometry']['decision_id']:r['decision_id'] for r in selected_records if r.get('geometry') and r['geometry'].get('decision_id')}
    for p in sorted((out/'position-events').glob(selected+'-all-1.jsonl')):
        for line in p.read_text().splitlines():
            e=json.loads(line)
            if e['event']!='ACCOUNT_SNAPSHOT':
                e['native_event_id']=e['event_id'];e['event_id']='event:'+run_id+':'+selected+':all-1:'+e['event_id']
                e['portfolio_id']=selected+'-all-1'
                if e.get('decision_id'):
                    e['native_decision_id']=e['decision_id'];e['decision_id']=decision_lookup.get(e['decision_id'],e['decision_id'])
                if e.get('trade_id') is not None:
                    e['trade_id']=str(e['trade_id']);e['trade_uid']=run_id+':'+selected+':all-1:'+e['trade_id']
                snap['position_events'].append(e)
    snap['position_events_total']=len(snap['position_events']);snap['position_events_truncated']=len(snap['position_events'])>100
    snap['position_events']=snap['position_events'][:100]
    resultpath=out/'trade-ledgers'/(selected+'-all-1.csv')
    with resultpath.open() as f: outcomes=list(csv.DictReader(f))
    snap['trade_outcomes']=[dict(outcome_id='outcome:'+run_id+':'+selected+':all-1:'+str(r['trade_id']),trade_uid=run_id+':'+selected+':all-1:'+str(r['trade_id']),environment='NATIVE_BACKTEST_RESEARCH',portfolio_id=selected+'-all-1',**r) for r in outcomes]
    snap['account_constraints']=read(out/'leverage-scenarios.json')
    jsonschema.validate(snap,read(ROOT/'research/foundation/openbot.schema.json'));validate_reader_content(snap)
    text=json.dumps(snap,allow_nan=False,separators=(',',':'))+'\n'
    if len(text.encode())>1_000_000:raise ValueError('reader exceeds1MB')
    target=out/('openbot-release' if release else 'openbot');target.mkdir(exist_ok=True)
    if any(target.iterdir()):raise ValueError('preserve reader')
    (target/'research-snapshot.json').write_text(text)
    write(target/'manifest.json',dict(schema_version=1,sha256=sha(target/'research-snapshot.json'),bytes=(target/'research-snapshot.json').stat().st_size,access='Copy only these ordinary JSON files into isolated read-only OpenBot environment; no lab config, database or admin API'))
    print('OpenBot export',len(snap['candidates']),'candidate records',len(text.encode()),'bytes',flush=True)
