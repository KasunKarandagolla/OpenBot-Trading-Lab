"""Independent fees/funding, opportunity/nonfill economics and time-window forensics."""
from collections import Counter
from decimal import Decimal as D
import numpy as np
import pandas as pd
from integrated_common import *

CACHE={}
def source(pair,tf,kind='futures'):
    key=(pair,tf,kind)
    if key not in CACHE: CACHE[key]=pd.read_feather(DATA/'gate/futures'/(slug(pair)+'-'+tf+'-'+kind+'.feather'))
    return CACHE[key]

def key(g,pair): return (pair,g['available_at'],g['recipe'],g['side'])

def reconcile(directory):
    result=next(iter(read(directory/'result.json')['strategy'].values()))
    states={(x['pair'],pd.Timestamp(x['open_date'])):x for x in read(directory/'states.json')}
    rows=[];timeframe=read(directory/'provenance.json')['timeframe']
    for t in result['trades']:
        st=states[(t['pair'],pd.Timestamp(t['open_date']))];g=st['plan'];sign=-1 if t['is_short'] else 1
        entries=[o for o in t['orders'] if o['ft_is_entry']];exits=[o for o in t['orders'] if not o['ft_is_entry']]
        qty=sum(D(str(o['amount'])) for o in entries)
        assert qty==sum(D(str(o['amount'])) for o in exits)
        a=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in entries)
        b=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in exits)
        gross=sign*(b-a);fees=a*D(str(t['fee_open']))+b*D(str(t['fee_close']));funding=D(str(t.get('funding_fees') or 0));net=gross-fees+funding
        assert abs(net-D(str(t['profit_abs'])))<D('.00000011')
        first=pd.Timestamp(min(o['order_filled_timestamp'] for o in entries),unit='ms',tz='UTC');end=pd.Timestamp(t['close_date'])
        f=source(t['pair'],'1h','funding_rate');marks=source(t['pair'],'1h','mark').set_index('date').open
        events=f.loc[(f.date>=first)&(f.date<=end)]
        recorded={pd.Timestamp(e['at']):e for e in st['funding']}
        assert set(events.date)==set(recorded),'funding event coverage mismatch'
        expected=D(0)
        for _,e in events.iterrows():
            ms=e.date.timestamp()*1000
            held=sum(D(str(o['amount'])) for o in entries if o['order_filled_timestamp']<=ms)-sum(D(str(o['amount'])) for o in exits if o['order_filled_timestamp']<ms)
            assert abs(float(held)-recorded[e.date]['quantity'])<1e-8
            mark=marks.loc[:e.date].iloc[-1]
            assert e.date-marks.loc[:e.date].index[-1]<=pd.Timedelta(hours=1)
            expected-=sign*held*D(str(e.funding_rate))*D(str(mark))
        assert abs(expected-funding)<D('.00000011')
        q=source(t['pair'],timeframe);q=q.loc[(q.date>=first)&(q.date<=end)]
        ambiguous=[]
        for _,r in q.iterrows():
            stop=r.low<=g['stop'] if sign==1 else r.high>=g['stop']
            target=r.high>=g['target'] if sign==1 else r.low<=g['target']
            if stop and target: ambiguous.append(r.date.isoformat())
        risk=float(qty)*abs(t['open_rate']-g['stop'])
        assert t['leverage']==1 and float(a)<=25.0000001
        rows.append(dict(pair=t['pair'],side=g['side'],playbook=g['recipe'],decision_id=g['decision_id'],setup_id=g.get('setup_id'),
            available_at=g['available_at'],entry=first.isoformat(),exit=end.isoformat(),planned_reference=g['reference'],entry_price=t['open_rate'],exit_price=t['close_rate'],
            entry_price_delta_bp=(t['open_rate']/g['reference']-1)*10000,entry_notional=float(a),gross=float(gross),fees=float(fees),funding=float(funding),net=float(net),
            turnover=float(a+b),stop_risk=risk,net_R_stop=float(net)/risk,net_R_modeled=float(net)/(risk+float(a)*.0038),
            actual_fill_after_cost_rr=(sign*(g['target']-t['open_rate'])/t['open_rate']-.0038)/(sign*(t['open_rate']-g['stop'])/t['open_rate']+.0038),
            hold_minutes=(end-first).total_seconds()/60,exit_reason=t['exit_reason'],partial_exits=max(0,len(exits)-1),funding_events=len(events),
            stress={str(k):float(net)-float(a+b)*k/10000 for k in (5,10,20)},ambiguous_same_candle=ambiguous,
            independent_quantity_fee_funding_net_verified=True))
    write(directory/'ledger.json',rows)
    pd.DataFrame(rows).to_csv(directory/'ledger.csv',index=False)
    return result,rows

def summary(native,rows,opportunities,original_keys):
    values=np.array([r['net'] for r in rows]);wins=values[values>0];loss=values[values<0]
    by={}
    for field in ('pair','side','playbook','exit_reason'):
        by[field]={v:dict(fills=sum(r[field]==v for r in rows),net=sum(r['net'] for r in rows if r[field]==v)) for v in sorted({r[field] for r in rows})}
    months={m:sum(r['net'] for r in rows if r['entry'].startswith(m)) for m in ('2026-09','2026-10','2026-11')}
    common=[r for r in rows if (r['pair'],r['available_at'],r['playbook'],r['side']) in original_keys]
    n=len(rows)
    daily=pd.Series(0.,index=pd.date_range('2026-09-01','2026-11-02',tz='UTC'))
    for r in rows: daily.loc[pd.Timestamp(r['exit']).floor('D')]+=r['net']
    # Weekly moving-block bootstrap, fixed seed, descriptive development uncertainty only.
    rng=np.random.default_rng(20261104);x=daily.to_numpy();totals=[]
    for _ in range(1000):
        sample=np.concatenate([x[(np.arange(7)+i)%len(x)] for i in rng.integers(0,len(x),size=9)])[:len(x)]
        totals.append(float(sample.sum()))
    return dict(fills=n,net=float(values.sum()),gross=sum(r['gross'] for r in rows),fees=sum(r['fees'] for r in rows),funding=sum(r['funding'] for r in rows),
        win_rate=len(wins)/n if n else None,profit_factor=float(wins.sum()/-loss.sum()) if len(loss) else None,
        average_winner=float(wins.mean()) if len(wins) else None,average_loser=float(loss.mean()) if len(loss) else None,
        net_expectancy_per_fill=float(values.mean()) if n else None,registered_opportunities=opportunities,
        net_expectancy_per_registered_opportunity=float(values.sum())/opportunities if opportunities else None,
        matched_original_fills=len(common),matched_original_opportunity_expectancy=sum(r['net'] for r in common)/len(original_keys) if original_keys else None,
        matched_original_net=sum(r['net'] for r in common),unmatched_fills=n-len(common),
        without_largest_winner=float(values.sum()-max(0,max(values,default=0))),
        leave_one_market_out={p:float(values.sum()-v['net']) for p,v in by['pair'].items()},
        chronological_months=months,weekly_block95_total=np.quantile(totals,[.025,.975]).tolist(),
        native_drawdown=native.get('max_drawdown_abs'),turnover=sum(r['turnover'] for r in rows),
        average_hold_minutes=float(np.mean([r['hold_minutes'] for r in rows])) if rows else None,
        net_R_stop=[r['net_R_stop'] for r in rows],net_R_modeled=[r['net_R_modeled'] for r in rows],
        additional_friction_ledger={str(k):sum(r['stress'][str(k)] for r in rows) for k in (5,10,20)},groups=by,
        native_rejected_signals=native.get('rejected_signals'),native_timedout_entry_orders=native.get('timedout_entry_orders'),
        native_canceled_entry_orders=native.get('canceled_entry_orders'),same_candle_ambiguous_trades=sum(bool(r['ambiguous_same_candle']) for r in rows),
        partial_exits=sum(r['partial_exits'] for r in rows))

def enrich_forensics():
    from integrated_forensics import audit
    audit()  # Deterministic reconstruction of generated files, never archived inputs.
    rows=read(OUT/'forensics-trades.json')
    for x in rows:
        pair=x['pair'];g=x['original_plan'];at=pd.Timestamp(g['available_at']);entry=pd.Timestamp(x['native_trade']['open_date']);end=pd.Timestamp(x['native_trade']['close_date'])
        f=pd.read_pickle(WORK/'features/new'/(slug(pair)+'.pkl'));old=pd.read_pickle(WORK/'features/v4'/(slug(pair)+'.pkl'))
        q=f.loc[f.date+pd.Timedelta(minutes=15)<=at]
        r=q.iloc[-1];o=old.loc[old.date.eq(r.date)].iloc[0]
        sign=1 if x['side']=='long' else -1
        x['asof_features']=dict(available_at=at.isoformat(),hour_known_at=(r.date_1h+pd.Timedelta(hours=1)).isoformat(),map4h_known_at=r.known4h.isoformat(),
            hour_direction=r.struct_direction_1h,parent_direction=r.direction_4h,regime=r.regime,
            ema20_1h=float(r.ema20_1h),ema50_1h=float(r.ema50_1h),ema20_15m=float(o.ema20),ema50_15m=float(o.ema50),adx_1h=float(r.adx_1h),
            vwap=float(r.vwap),prior_vwap=float(r.prior_vwap),rvol=float(r.rvol),atr=float(r.atr14),
            relative_btc=float(r.return4h-(0 if pair=='BTC/USDT:USDT' else pd.read_pickle(WORK/'features/new/BTC_USDT_USDT.pkl').loc[lambda f:f.date.eq(r.date),'return4h'].iloc[0])),
            flow='UNKNOWN',profile='NOT_USED')
        paths={}
        for tf,minutes in [('15m',15),('5m',5)]:
            candles=source(pair,tf)
            if entry<candles.date.min(): paths[tf]={'status':'SOURCE_NOT_AVAILABLE_AT_REQUIRED_HISTORICAL_WINDOW'};continue
            series={}
            for horizon in (5,15,30,60):
                if horizon<minutes: continue
                z=candles.loc[(candles.date>=entry)&(candles.date<min(entry+pd.Timedelta(minutes=horizon),end))]
                if len(z):
                    series[str(horizon)]=dict(favorable_bp=sign*((z.high.max() if sign==1 else z.low.min())/x['native_trade']['open_rate']-1)*10000,
                        adverse_bp=sign*((z.low.min() if sign==1 else z.high.max())/x['native_trade']['open_rate']-1)*10000,
                        status='FULL_CANDLE_BOUND_EXCLUDING_EXIT_CANDLE;NOT_EXECUTABLE_COUNTERFACTUAL')
            paths[tf]=series
        x['subsequent_path_separate_from_decision']=paths
        t=x['native_trade'];c=source(pair,'15m');c=c.loc[(c.date>=entry)&(c.date<=end)]
        x['including_exit_candle_upper_bound_bp']=sign*((c.high.max() if sign==1 else c.low.min())/t['open_rate']-1)*10000 if len(c) else None
        x['exit_candle_can_contain_post_exit_prices']=True
    write(OUT/'forensics-trades.json',rows)
    # Avoid duplicating 7MB of unchanged text while preserving every rejected event.
    import gzip
    rejected=OUT/'forensics-rejected.json'
    with gzip.open(OUT/'forensics-rejected.json.gz','wt') as handle: handle.write(rejected.read_text())
    rejected.unlink()

def report():
    registry=read(OUT/'plans.json');original=read(OUT/'opportunities.json')
    original_keys={key(x['plan'],x['pair']) for x in original}
    five=read(OUT/'five-opportunities.json');five_keys={key(y['plan'],x['pair']) for x in five for y in x.get('variants',{}).values() if y.get('plan')}
    portfolios={};ledgers={}
    for path in sorted((OUT/'native').glob('*/result.json')):
        directory=path.parent;p=read(directory/'provenance.json');variant=p['variant']
        native,rows=reconcile(directory);ledgers[directory.name]=rows
        denom=sum('opportunity' in x for x in five) if variant.startswith('five-') else 14 if variant=='control-pr12' else registry[variant]['plans'] if variant=='ema-context' else len(original)
        value=summary(native,rows,denom,original_keys)
        if variant.startswith('five-'):
            value['matched_original_opportunity_expectancy']=None
            value['cohort_note']='Shared 5m opportunity registry, different from archived V4 signals; 5m context frozen at arm.'
        audit=read(directory/'order-audit.json') if (directory/'order-audit.json').exists() else None
        plans=read(WORK/'plans'/(variant+'.json'))
        fills={r['decision_id']:r for r in rows}
        orders=[o for o in audit['orders'] if o['is_entry']] if audit else []
        contracts=read(OUT/'contracts.json')
        for order in orders:
            c=contracts[order['pair']];step=c['contract_size']*c['step_contracts'];tick=c['price_precision']
            assert order['entry_notional']<=25.0000001
            assert abs(order['amount']/step-round(order['amount']/step))<1e-5
            assert abs(order['native_price']/tick-round(order['native_price']/tick))<1e-4
            assert order['amount']+1e-12>=c['contract_size']*c['min_contracts']
            assert order['entry_notional']+1e-8>=c.get('min_notional',0)
        submitted={o['decision_id']:o for o in orders}
        funnel=[]
        for pair,items in plans.items():
            for at,g in items.items():
                status='FILLED_EXITED' if g['decision_id'] in fills else 'UNFILLED_NATIVE_ORDER' if g['decision_id'] in submitted else 'NOT_SUBMITTED_NATIVE_RISK_CAPACITY_COOLDOWN_OR_LEGALITY'
                funnel.append(dict(pair=pair,at=at,decision_id=g['decision_id'],status=status,order=submitted.get(g['decision_id']),outcome=fills.get(g['decision_id'])))
        write(directory/'execution-funnel.json',funnel)
        value.update(variant=variant,timeframe=p['timeframe'],fee_per_side=p['fee_per_side'],execution=p['execution'],
            qualified_plans=registry[variant]['plans'],plan_execution=dict(Counter(x['status'] for x in funnel)),
            submitted_orders=len(orders) if audit else None,filled_orders=sum(o['filled']>0 for o in orders) if audit else None,
            unfilled_orders=sum(o['filled']==0 for o in orders) if audit else None,
            fill_rate=sum(o['filled']>0 for o in orders)/len(orders) if orders else None,
            all_observed_order_ticks_lots_minima_and_25USDT_verified=True if audit else None)
        portfolios[directory.name]=value
    verification={}
    for variant,label,oldpath in [('control-v4','control-v4-touch-750','evidence/setup/run-002/native/v4-structure-fixed-touch-750'),('control-pr12','control-pr12-touch-750','evidence/setup/run-003/native/setup-fixed-touch-750')]:
        if label not in portfolios: continue
        new=next(iter(read(OUT/'native'/label/'result.json')['strategy'].values()))['trades']
        archived=next(iter(read(ROOT/oldpath/'result.json')['strategy'].values()))['trades']
        verification[variant]=dict(new_fills=len(new),archived_fills=len(archived),complete_trade_objects_equal=new==archived,
            new_net=portfolios[label]['net'],archived_net=sum(t['profit_abs'] for t in archived))
    if (OUT/'native/control-v4-touch-750-order-audit/result.json').exists():
        a=next(iter(read(OUT/'native/control-v4-touch-750/result.json')['strategy'].values()))['trades']
        b=next(iter(read(OUT/'native/control-v4-touch-750-order-audit/result.json')['strategy'].values()))['trades']
        verification['order_observer']=dict(complete_trade_objects_equal=a==b)
    write(OUT/'control-verification.json',verification)
    comparisons={}
    control=portfolios.get('control-v4-touch-750')
    for name,value in portfolios.items():
        if control and value['timeframe']=='15m':
            comparisons[name]=dict(net_minus_control=value['net']-control['net'],
                shared_entry_keys=len({(r['pair'],r['entry']) for r in ledgers[name]}&{(r['pair'],r['entry']) for r in ledgers['control-v4-touch-750']}),
                note='Separate native portfolios; changed exits/cost/selection can change later capacity. Ledger sensitivities do not rerun fills.')
    enrich_forensics()
    write(OUT/'economic-report.json',dict(portfolios=portfolios,comparisons=comparisons,control_verification=verification,
        registered_variants=list(registry),native_result_records=len(portfolios),
        source_count=len(read(OUT/'data.json')['files']),source_15m_hourly_hash_matches=read(OUT/'data.json')['prior_source_match'],
        original_selected_opportunities=len(original),raw_v4_candidates=len(read(OUT/'selection-audit.json')),
        five_location_candidates=len(five),five_registered=sum('opportunity' in x for x in five),
        five_missed_shortlist=sum(not x['shortlisted'] for x in five),
        decision='REJECTED_INTEGRATED_PROMOTION;INSUFFICIENT_5M_ECONOMICS',
        limitations=['INSPECTED_DEVELOPMENT_ONLY','CURRENT_SURVIVOR_UNIVERSE','CURRENT_CONTRACT_SPEC_NOT_HISTORICAL',
            'NATIVE_RANGE_TOUCH_NOT_EXCHANGE_QUEUE','SPREAD_AND_SIGNED_FLOW_UNKNOWN','PROFILE_ECONOMICS_NOT_TESTED',
            'FUNDING_MARK_USES_PRECEDING_HOURLY_OPEN_NOT_EXACT_SETTLEMENT_MARK','NO_RESERVED_HOLDOUT_ACCESS',
            'FIVE_MINUTE_EXPIRY_ON_NATIVE_15M_STEPS_CAN_INCLUDE_LATE_WITHIN_CANDLE_TOUCH;NO_EXACT_SUBBAR_FILL_CLOCK',
            'WEEKLY_BOOTSTRAP_DESCRIPTIVE_SMALL_DEPENDENT_SAMPLE','FIXED_TARGET_ADMISSION_AND_CAPACITY_EFFECTS_REPORTED']))
    lines=['| Native variant | Fills | Net USDT | Extra 10bp/side ledger |','|---|---:|---:|---:|']
    for name,v in portfolios.items(): lines.append(f"| {name} | {v['fills']} | {v['net']:+.6f} | {v['additional_friction_ledger']['10']:+.6f} |")
    (OUT/'portfolio-table.md').write_text('\n'.join(lines)+'\n')
    print('Reconciled',len(portfolios),'native result records,',sum(len(x) for x in ledgers.values()),'trade records',flush=True)

if __name__=='__main__': report()
