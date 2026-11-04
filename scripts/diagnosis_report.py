"""Independent order/funding reconciliation and fixed-denominator comparisons.

Only this session's namespace is written. Native portfolios remain the execution
authority; path extrema and turnover stresses never manufacture fills or profit.
"""
from collections import Counter
from decimal import Decimal as D
import math
import numpy as np
import pandas as pd
from diagnosis_common import *

CACHE={}
def source(provenance,pair,tf,kind='futures'):
    key=(provenance['data_dir'],pair,tf,kind)
    if key not in CACHE:
        CACHE[key]=pd.read_feather(ROOT/provenance['data_dir']/'futures'/(slug(pair)+'-'+tf+'-'+kind+'.feather'))
    return CACHE[key]

def reconcile(directory):
    p=read(directory/'provenance.json');native=next(iter(read(directory/'result.json')['strategy'].values()))
    states={(x['pair'],pd.Timestamp(x['open_date'])):x for x in read(directory/'states.json')}
    contracts=read(PARENT/'contracts.json');rows=[]
    for t in native['trades']:
        state=states[t['pair'],pd.Timestamp(t['open_date'])];g=state['plan'];sign=-1 if t['is_short'] else 1
        entries=[o for o in t['orders'] if o['ft_is_entry']];exits=[o for o in t['orders'] if not o['ft_is_entry']]
        quantity=sum(D(str(o['amount'])) for o in entries)
        assert quantity==sum(D(str(o['amount'])) for o in exits),'quantity conservation'
        entry=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in entries)
        exit=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in exits)
        gross=sign*(exit-entry);fees=entry*D(str(t['fee_open']))+exit*D(str(t['fee_close']))
        funding=D(str(t.get('funding_fees') or 0));net=gross-fees+funding
        assert abs(net-D(str(t['profit_abs'])))<D('.00000011'),'native net'
        first=pd.Timestamp(min(o['order_filled_timestamp'] for o in entries),unit='ms',tz='UTC');end=pd.Timestamp(t['close_date'])
        events=source(p,t['pair'],'1h','funding_rate');events=events.loc[(events.date>=first)&(events.date<=end)]
        marks=source(p,t['pair'],'1h','mark').set_index('date').open
        recorded={pd.Timestamp(e['at']):e for e in state['funding']};assert set(events.date)==set(recorded),'funding coverage'
        independently_funded=D(0)
        for _,event in events.iterrows():
            ms=event.date.timestamp()*1000
            held=sum(D(str(o['amount'])) for o in entries if o['order_filled_timestamp']<=ms)-sum(D(str(o['amount'])) for o in exits if o['order_filled_timestamp']<ms)
            assert abs(float(held)-recorded[event.date]['quantity'])<1e-8
            eligible=marks.loc[:event.date];assert len(eligible) and event.date-eligible.index[-1]<=pd.Timedelta(hours=1)
            independently_funded-=sign*held*D(str(event.funding_rate))*D(str(eligible.iloc[-1]))
        assert abs(independently_funded-funding)<D('.00000011'),'independent real-source funding'
        c=contracts[t['pair']];step=c['contract_size']*c['step_contracts'];tick=c['price_precision']
        assert t['leverage']==1 and float(entry)<=25.0000001
        for order in entries:
            assert abs(order['amount']/step-round(order['amount']/step))<1e-5
            assert abs(order['safe_price']/tick-round(order['safe_price']/tick))<1e-4
        risk=float(quantity)*abs(t['open_rate']-g['stop'])
        tf='5m' if p['detail_5m'] else '15m';candles=source(p,t['pair'],tf)
        held=candles.loc[(candles.date>=first)&(candles.date<=end)];collisions=[]
        for _,bar in held.iterrows():
            sl=bar.low<=g['stop'] if sign==1 else bar.high>=g['stop']
            tp=bar.high>=g['target'] if sign==1 else bar.low<=g['target']
            if sl and tp:collisions.append(bar.date.isoformat())
        rows.append(dict(key=opportunity_key(t['pair'],g),pair=t['pair'],side=g['side'],playbook=g['recipe'],decision_id=g['decision_id'],
            available_at=g['available_at'],entry=first.isoformat(),exit=end.isoformat(),entry_price=t['open_rate'],exit_price=t['close_rate'],
            frozen_stop=g['stop'],frozen_target=g['target'],planned_reference=g['reference'],quantity=float(quantity),entry_notional=float(entry),
            gross=float(gross),fees=float(fees),funding=float(funding),net=float(net),turnover=float(entry+exit),stop_risk=risk,
            net_R_stop=float(net)/risk,net_R_modeled=float(net)/(risk+float(entry)*.0038),
            after_cost_initial_rr=(sign*(g['target']-t['open_rate'])/t['open_rate']-.0038)/(sign*(t['open_rate']-g['stop'])/t['open_rate']+.0038),
            hold_minutes=(end-first).total_seconds()/60,exit_reason=t['exit_reason'],funding_events=len(events),same_candle_stop_target=collisions,
            independent_quantity_fees_funding_net_verified=True))
    write(directory/'ledger.json',rows);pd.DataFrame(rows).to_csv(directory/'ledger.csv',index=False)
    return p,native,rows

def bounds(p):
    name='detail_cohort' if p['short_window'] else p['cohort']
    _,start,end=read(ROOT/'research/diagnosis/protocol.json')['source_windows'][name]
    return pd.Timestamp(start,tz='UTC'),pd.Timestamp(end,tz='UTC')

def in_window(g,start,end):return start<=pd.Timestamp(g['available_at'])<end

def summarize(p,native,rows,funnel,union,original):
    start,end=bounds(p);values=np.array([r['net'] for r in rows]);wins=values[values>0];losses=values[values<0]
    total=float(values.sum());n=len(rows);groups={}
    for field in ('pair','side','playbook','exit_reason'):
        choices=pairs() if field=='pair' else sorted({r[field] for r in rows})
        groups[field]={v:dict(fills=sum(r[field]==v for r in rows),net=sum(r['net'] for r in rows if r[field]==v)) for v in choices}
    daily=pd.Series(0.,index=pd.date_range(start,end-pd.Timedelta(days=1),freq='D'))
    for row in rows:daily.loc[pd.Timestamp(row['exit']).floor('D')]+=row['net']
    weekly=daily.resample('W-SUN').sum();months=daily.resample('MS').sum()
    rng=np.random.default_rng(20261104);x=daily.to_numpy();totals=[]
    for _ in range(2000):
        sample=np.concatenate([x[(np.arange(7)+i)%len(x)] for i in rng.integers(0,len(x),size=math.ceil(len(x)/7))])[:len(x)]
        totals.append(float(sample.sum()))
    streak=worst=0
    for r in sorted(rows,key=lambda r:(r['exit'],r['pair'])):
        streak=streak+1 if r['net']<0 else 0;worst=max(worst,streak)
    matched=[r for r in rows if r['key'] in original];submitted=[r for r in funnel if r['order_submitted']]
    filled=sum(r['order_filled'] for r in submitted);grossprofit=float(wins.sum());grossloss=float(-losses.sum())
    return dict(fills=n,net=total,gross=sum(r['gross'] for r in rows),fees=sum(r['fees'] for r in rows),funding=sum(r['funding'] for r in rows),
        win_rate=len(wins)/n if n else None,profit_factor=grossprofit/grossloss if grossloss else None,
        average_winner=float(wins.mean()) if len(wins) else None,average_loser=float(losses.mean()) if len(losses) else None,
        average_trade=float(values.mean()) if n else None,median_trade=float(np.median(values)) if n else None,
        own_selected_plans=len(funnel),common_raw_union_opportunities=len(union),original_v4_selected_opportunities=len(original),
        net_per_common_raw_union_opportunity=total/len(union) if union else None,
        net_per_own_selected_plan=total/len(funnel) if funnel else None,
        matched_original_fills=len(matched),matched_original_net=sum(r['net'] for r in matched),
        matched_net_per_original_v4_plan=sum(r['net'] for r in matched)/len(original) if original else None,
        unmatched_fills=n-len(matched),unmatched_net=sum(r['net'] for r in rows if r['key'] not in original),
        denominator_note='Common union of strict and EMA-relaxed raw opportunity IDs, before liquidity/shortlist/native execution. Original V4 selected-plan subset reported separately; unmatched PnL is not assigned to those plans. PR12 is a separate playbook cohort.',
        submitted_orders=len(submitted),filled_orders=filled,unfilled_orders=len(submitted)-filled,fill_rate=filled/len(submitted) if submitted else None,
        execution_funnel=dict(Counter(r['execution_status'] for r in funnel)),
        native_rejected_signals=native.get('rejected_signals'),native_timedout_entry_orders=native.get('timedout_entry_orders'),
        native_canceled_entry_orders=native.get('canceled_entry_orders'),native_drawdown=native.get('max_drawdown_abs'),
        worst_losing_streak=worst,turnover=sum(r['turnover'] for r in rows),average_hold_minutes=float(np.mean([r['hold_minutes'] for r in rows])) if n else None,
        net_R_stop=[r['net_R_stop'] for r in rows],net_R_modeled=[r['net_R_modeled'] for r in rows],
        additional_friction_ledger={str(bp):total-sum(r['turnover'] for r in rows)*bp/10000 for bp in (5,10,20)},
        without_largest_winner=total-max(0,max(values,default=0)),without_three_largest_winners=total-sum(sorted(wins,reverse=True)[:3]),
        leave_one_market_out={pair:total-v['net'] for pair,v in groups['pair'].items()},
        chronological_weeks={k.isoformat():float(v) for k,v in weekly.items()},chronological_months={k.strftime('%Y-%m'):float(v) for k,v in months.items()},
        profitable_weeks=int((weekly>0).sum()),losing_weeks=int((weekly<0).sum()),flat_weeks=int((weekly==0).sum()),
        descriptive_week_block95_total=np.quantile(totals,[.025,.975]).tolist(),
        bootstrap_note='Inspected, dependent, small cohort; circular seven-day blocks, fixed seed, 2000 resamples. Not a calibrated forecast or independent validation. One-day extension has no useful uncertainty estimate.',
        same_candle_stop_target_trades=sum(bool(r['same_candle_stop_target']) for r in rows),groups=groups)

def execution_funnel(directory,p,rows):
    plans=read(WORK/p['cohort']/'plans'/(p['variant']+'.json'));start,end=bounds(p)
    audit=read(directory/'order-audit.json');contracts=read(PARENT/'contracts.json')
    orders={o['decision_id']:o for o in audit['orders'] if o['is_entry']};fills={r['decision_id']:r for r in rows}
    for o in orders.values():
        c=contracts[o['pair']];step=c['contract_size']*c['step_contracts'];tick=c['price_precision'];notional=o['amount']*o['price']
        assert notional<=25.0000001 and abs(o['amount']/step-round(o['amount']/step))<1e-5
        assert abs(o['price']/tick-round(o['price']/tick))<1e-4
        assert o['amount']+1e-12>=c['contract_size']*c['min_contracts'] and notional+1e-8>=c.get('min_notional',0)
    result=[]
    for pair,items in plans.items():
        for at,g in items.items():
            if not in_window(g,start,end):continue
            order=orders.get(g['decision_id']);fill=fills.get(g['decision_id'])
            events=[e for e in audit['observations'] if e['pair']==pair and pd.Timestamp(e['at'])==pd.Timestamp(at)]
            statuses=[e['verdict']['status'] for e in events if e['event']=='NATIVE_RISK_SIZE']
            if fill:status='FILLED_EXITED'
            elif order:status='UNFILLED_NATIVE_ENTRY'
            elif any(e['event']=='NATIVE_MAX_POSITION_REJECTION' for e in events):status='MAX_POSITIONS'
            elif any(e.get('existing_pair_position_at_loop_start') for e in events):status='EXISTING_PAIR_POSITION'
            elif any(s!='PASS' for s in statuses):status='NATIVE_RISK_SIZE_REJECTION'
            elif any(e['event']=='NATIVE_ENTER_ATTEMPT' for e in events):status='NATIVE_ORDER_MINIMUM_OR_MARGIN_REJECTION'
            else:status='UNRESOLVED_NATIVE_NON_SUBMISSION'
            result.append(dict(key=opportunity_key(pair,g),pair=pair,at=at,decision_id=g['decision_id'],plan=g,
                order_submitted=bool(order),order_filled=bool(fill),execution_status=status,order=order,ledger=fill,observations=events))
    write(directory/'execution-funnel.json',result)
    return result

def compare(base,other):
    a={r['key']:r for r in base};b={r['key']:r for r in other};shared=a.keys()&b.keys()
    return dict(shared_fills=len(shared),base_only=len(a.keys()-b.keys()),challenger_only=len(b.keys()-a.keys()),
        shared_net_delta=sum(b[k]['net']-a[k]['net'] for k in shared),
        base_only_net=sum(a[k]['net'] for k in a.keys()-b.keys()),challenger_only_net=sum(b[k]['net'] for k in b.keys()-a.keys()),
        net_delta=sum(r['net'] for r in other)-sum(r['net'] for r in base),
        changed_shared=[dict(key=k,base=a[k],challenger=b[k],delta=b[k]['net']-a[k]['net']) for k in sorted(shared) if abs(b[k]['net']-a[k]['net'])>1e-7 or b[k]['entry']!=a[k]['entry'] or b[k]['exit']!=a[k]['exit']])

def report():
    portfolios={};ledgers={};control_verification={};official={}
    for path in sorted((OUT/'native').glob('*/result.json')):
        directory=path.parent;p,native,rows=reconcile(directory);start,end=bounds(p)
        raw=read(OUT/('opportunities-'+p['cohort']+'.json'));union={x['key'] for x in raw if in_window(x['plan'],start,end)}
        original=read(WORK/p['cohort']/'plans/v4.json');keys={opportunity_key(pair,g) for pair,items in original.items() for g in items.values() if in_window(g,start,end)}
        funnel=execution_funnel(directory,p,rows);value=summarize(p,native,rows,funnel,union,keys)
        invalid=p['variant']=='passive-30m' and not directory.name.endswith('expiry-corrected')
        value.update(provenance=p,implementation_valid=not invalid,interpretation='INVALID_EXPIRY_PLUMBING_NATIVE_TIMEOUT_5MIN' if invalid else 'VALID_FIXED_EXPERIMENT',
            all_submitted_native_ticks_lots_minima_cap_verified=True)
        portfolios[directory.name]=value;ledgers[directory.name]=rows
        if not invalid and not p['short_window'] and not p['detail_5m'] and not p['trade_through'] and p['fee_per_side']==.00075 and not directory.name.endswith('lifecycle-audit'):
            official.setdefault(p['cohort'],{})[p['variant']]=directory.name
    for name,parent in [('v4','v4'),('pr12','pr12'),('passive','passive'),('structural','structural')]:
        directory=OUT/'native'/('development-'+name+'-touch-750')
        a=next(iter(read(directory/'result.json')['strategy'].values()))['trades']
        b=next(iter(read(PARENT/'native'/NATIVE_LABELS[parent]/'result.json')['strategy'].values()))['trades']
        control_verification[name]=dict(complete_native_trade_objects_equal=a==b,new=len(a),parent=len(b));assert a==b
    for name in ('v4','passive'):
        first=OUT/'native'/('development-'+name+'-touch-750');replay=OUT/'native'/('development-'+name+'-touch-750-lifecycle-audit')
        if (replay/'result.json').exists():
            equal=read(first/'result.json')['strategy'][next(iter(read(first/'result.json')['strategy']))]['trades']==next(iter(read(replay/'result.json')['strategy'].values()))['trades']
            control_verification[name+'_terminal_observer']=dict(complete_native_trade_objects_equal=equal);assert equal
    comparisons={}
    for cohort,variants in official.items():
        base=variants['v4'];comparisons[cohort]={v:compare(ledgers[base],ledgers[label]) for v,label in variants.items() if v!='v4'}
    dev=official['development'];factorial={v:portfolios[dev[v]]['net'] for v in ('v4','ema-eligibility-only','rank-only','ema-both','rank-qualified-only')}
    factorial.update(eligibility_effect_at_strict_rank=factorial['ema-eligibility-only']-factorial['v4'],rank_effect_at_strict_eligibility=factorial['rank-only']-factorial['v4'],
        interaction=factorial['ema-both']-factorial['ema-eligibility-only']-factorial['rank-only']+factorial['v4'])
    fidelity={}
    for variant in ('v4','passive','conditional-entry','passive-30m'):
        suffix='-expiry-corrected' if variant=='passive-30m' else ''
        a='development-'+variant+'-oct5-touch-750'+suffix;b='development-'+variant+'-oct5-detail5m-touch-750'+suffix
        if a in ledgers and b in ledgers:fidelity[variant]=dict(main_15m=a,detail_5m=b,comparison=compare(ledgers[a],ledgers[b]))
    expiry=[]
    for path in sorted((OUT/'native').glob('*/entry-lifecycle.json')):
        x=read(path)
        for event in x['terminal_events']:expiry.append(dict(run=path.parent.name,**event))
    write(OUT/'entry-expiry-audit.json',dict(events=expiry,interpretation='Actual removal clocks observed. Full candle range may be tested before its close; event clocks do not establish exchange touch or queue time. Original Order.status can remain open after native removal.'))
    validation=dict(independent_validation='NOT_COMPLETED',earlier='Distinct 17-day August cohort, already inspected by broader project; not independent',later='New fixed November3 one-day extension; inadequate sample for reliability',older_probe=read(OUT/'older-data-probe.json'))
    result=dict(at=now(),portfolios=portfolios,official=official,comparisons=comparisons,control_verification=control_verification,ema_factorial=factorial,
        fidelity=fidelity,validation=validation,native_result_records=len(portfolios),reconciled_trade_records=sum(map(len,ledgers.values())),
        preservation=verify_parent(),limitations=['INSPECTED_DEVELOPMENT','CURRENT_SURVIVOR_UNIVERSE','CURRENT_CONTRACT_SPECS_NOT_HISTORICAL',
        'UNKNOWN_HISTORICAL_SPREAD_QUEUE_AND_SIGNED_FLOW','PROFILE_ECONOMICS_NOT_TESTED','HOURLY_MARK_OPEN_NOT_EXACT_FUNDING_SETTLEMENT_MARK',
        'OHLCV_TOUCH_NOT_EXCHANGE_FILL','INCOMPLETE_ORIGINAL_5M_HISTORY','SMALL_DEPENDENT_SAMPLES','NO_FUTURE_HOLDOUT_ACCESSED'],
        decision='NO_PROMOTION_OR_ACTIVATION;NO_VARIANT_HAS_ESTABLISHED_RELIABLE_AFTER_COST_EDGE')
    write(OUT/'economic-report.json',result)
    lines=['| Cohort / native variant | Plans | Fills | Net USDT | Net/common raw opportunity | Extra10bp/side ledger |','|---|---:|---:|---:|---:|---:|']
    for cohort,variants in official.items():
        for v,label in variants.items():
            x=portfolios[label];lines.append(f"| {cohort} / {v} | {x['own_selected_plans']} | {x['fills']} | {x['net']:+.6f} | {x['net_per_common_raw_union_opportunity']:+.6f} | {x['additional_friction_ledger']['10']:+.6f} |")
    (OUT/'portfolio-table.md').write_text('\n'.join(lines)+'\n')
    print('Reconciled',len(portfolios),'native records;',result['reconciled_trade_records'],'overlapping trade records; all original controls exact',flush=True)

if __name__=='__main__':report()
