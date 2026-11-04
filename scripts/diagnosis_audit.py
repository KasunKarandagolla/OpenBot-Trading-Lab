"""Forensic joins and bounded path diagnostics, never a replacement fill simulator."""
from collections import Counter
from decimal import Decimal as D
import inspect
import numpy as np
import pandas as pd
from diagnosis_common import *
from market_reader import objective,continuation_failure
from setup_features import levels

CACHE={}
def feature(pair,kind='v4'):
    key=(pair,kind)
    if key not in CACHE:CACHE[key]=pd.read_pickle(PWORK/'features'/kind/(slug(pair)+'.pkl')).set_index('date',drop=False)
    return CACHE[key]
def candles(pair,tf='15m'):
    key=(pair,tf)
    if key not in CACHE:CACHE[key]=pd.read_feather(DATA/'gate/futures'/(slug(pair)+'-'+tf+'-futures.feather'))
    return CACHE[key]
def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,(pd.Timestamp,)):return value.isoformat()
    if value is None:return None
    if isinstance(value,(float,np.floating)) and not np.isfinite(value):return None
    if isinstance(value,np.generic):return value.item()
    if value is pd.NaT:return None
    return value

def load_portfolio(name):
    directory=PARENT/'native'/NATIVE_LABELS[name]
    native=next(iter(read(directory/'result.json')['strategy'].values()))
    states={(s['pair'],pd.Timestamp(s['open_date'])):s for s in read(directory/'states.json')}
    ledger={r['decision_id']:r for r in read(directory/'ledger.json')}
    rows=[]
    for t in native['trades']:
        s=states[(t['pair'],pd.Timestamp(t['open_date']))];g=s['plan']
        rows.append(dict(source_strategy=name,key=opportunity_key(t['pair'],g),plan=g,trade=t,ledger=ledger[g['decision_id']],state=s))
    return rows,native,read(directory/'order-audit.json')

def state_at(pair,g):
    at=pd.Timestamp(g['available_at']);date=at-pd.Timedelta(minutes=15)
    r=feature(pair,'v4').loc[date];d=feature(pair,'new').loc[date];sign=1 if g['side']=='long' else -1
    hdir=d.struct_direction_1h;expected='UP' if sign==1 else 'DOWN'
    span=float(r.high-r.low)
    return clean(dict(as_of=at,source_bar_open=date,hour_available_at=d.date_1h+pd.Timedelta(hours=1),map4h_known_at=d.known4h,
        parent_direction=d.direction_4h,hour_direction=hdir,hour_aligned=hdir==expected,regime=d.regime,
        ema_1h_aligned=bool(sign*(r.ema20_1h-r.ema50_1h)>0),ema_15m_aligned=bool(sign*(r.ema20-r.ema50)>0),ema_slope_aligned=bool(sign*r.ema20_slope>0),
        ema_15m_slope_atr=sign*r.ema20_slope/r.atr14,adx=float(r.adx_1h),rvol=float(r.rvol),
        vwap=float(r.vwap),frozen_prior_vwap=float(d.prior_vwap),vwap_anchor='UTC_MIDNIGHT_HLC3_VOLUME_PROXY',
        signed_distance_vwap_atr=sign*(r.close-d.prior_vwap)/r.atr14,extension_from_pullback_atr=sign*(r.close-(r.pullback_low if sign==1 else r.pullback_high))/r.atr14,
        signal_body_atr=sign*(r.close-r.open)/r.atr14,signal_range_atr=span/r.atr14,
        directional_close_location=(r.close-r.low)/span if sign==1 and span else (r.high-r.close)/span if span else None,
        atr=float(r.atr14),atr_fraction=float(r.atr14/r.close),return4h=float(r.return4h),
        signed_relative_btc=sign*(r.return4h-(0 if pair=='BTC/USDT:USDT' else feature('BTC/USDT:USDT','v4').loc[date,'return4h'])),
        struct_event=r.struct_event,local_direction=r.struct_direction,local_known_at=r.struct_known_at,
        fvg_up=bool(r.get('fvg_up',False)),fvg_down=bool(r.get('fvg_down',False)),
        fvg_retest_up=bool(r.get('fvg_retest_up',False)),fvg_retest_down=bool(r.get('fvg_retest_down',False)),
        liquidity_eligible=bool(r.eligible),prior_day_quote=float(r.prior_day_quote),prior7_quote=float(r.prior7_quote),
        range_low_1h=d.range_low_1h,range_high_1h=d.range_high_1h,
        range_location=(r.close-d.range_low_1h)/(d.range_high_1h-d.range_low_1h) if d.range_high_1h>d.range_low_1h else None,
        flow='UNKNOWN_NO_HISTORICAL_SIGNED_TAPE',profile='NOT_TESTED_NO_TIMESTAMP_ELIGIBLE_COMPLETE_PROFILE',historical_spread='UNKNOWN'))

def rank_at(pair,g,strict=True):
    date=pd.Timestamp(g['available_at'])-pd.Timedelta(minutes=15);sign=1 if g['side']=='long' else -1
    btc=feature('BTC/USDT:USDT').loc[date,'return4h'];ranks=[]
    for p in pairs():
        r=feature(p).loc[date]
        if not bool(r.eligible) or not np.isfinite(r.return4h) or not np.isfinite(r.activity):continue
        if g['recipe']=='continuation':
            if strict and sign*(r.ema20_1h-r.ema50_1h)<=0:continue
            score=sign*(r.return4h-(0 if p=='BTC/USDT:USDT' else btc))+.01*min(float(r.activity),3)
        else:score=sign*(r.close-(r.prior_low if sign==1 else r.prior_high))/r.atr14
        ranks.append(dict(pair=p,score=float(score)))
    ranks.sort(key=lambda x:(-x['score'],x['pair']))
    return dict(rank=next((i+1 for i,x in enumerate(ranks) if x['pair']==pair),None),top3=ranks[:3],pool=ranks,eligible_by_rank=pair in [x['pair'] for x in ranks[:3]])

def path_summary(pair,g,t):
    start=pd.Timestamp(t['open_date']);end=pd.Timestamp(t['close_date']);sign=1 if g['side']=='long' else -1;entry=t['open_rate'];risk=abs(entry-g['stop'])
    result={}
    for tf,step in [('15m',15),('5m',5)]:
        c=candles(pair,tf)
        if start<c.date.min():result[tf]=dict(status='NOT_TESTABLE_WITH_AVAILABLE_DATA');continue
        held=c.loc[(c.date>=start)&(c.date<end)]
        including_exit=c.loc[(c.date>=start)&(c.date<=end)]
        milestones={}
        for multiple in (.5,1,2,3):
            target=entry+sign*multiple*risk
            hits=held.loc[held.high.ge(target) if sign==1 else held.low.le(target)]
            milestones[str(multiple)]=dict(first_bar_open=hits.date.iloc[0].isoformat(),known_bar_close=(hits.date.iloc[0]+pd.Timedelta(minutes=step)).isoformat(),minutes_lower_bound=(hits.date.iloc[0]-start).total_seconds()/60,status='TOUCH_DIAGNOSTIC_NOT_NATIVE_FILL') if len(hits) else None
        horizons={}
        for minutes in (5,15,30,60):
            if minutes<step:continue
            q=c.loc[(c.date>=start)&(c.date<min(start+pd.Timedelta(minutes=minutes),end))]
            if len(q):horizons[str(minutes)]=dict(favorable_bp=sign*((q.high.max() if sign==1 else q.low.min())/entry-1)*10000,
                adverse_bp=sign*((q.low.min() if sign==1 else q.high.max())/entry-1)*10000,end_close_bp=sign*(q.close.iloc[-1]/entry-1)*10000,bars=len(q))
        collision=[];first_stop=None;first_target=None
        for _,r in including_exit.iterrows():
            stop=r.low<=g['stop'] if sign==1 else r.high>=g['stop'];tp=r.high>=g['target'] if sign==1 else r.low<=g['target']
            if stop and first_stop is None:first_stop=r.date.isoformat()
            if tp and first_target is None:first_target=r.date.isoformat()
            if stop and tp:collision.append(r.date.isoformat())
        after=c.loc[(c.date>end)&(c.date<end+pd.Timedelta(hours=1))]
        result[tf]=dict(status='OBSERVED_OHLCV_BOUNDS',horizons=horizons,time_to_R=milestones,
            favorable_held_excluding_exit_bp=sign*((held.high.max() if sign==1 else held.low.min())/entry-1)*10000 if len(held) else None,
            favorable_including_exit_candle_bp=sign*((including_exit.high.max() if sign==1 else including_exit.low.min())/entry-1)*10000 if len(including_exit) else None,
            stop_touch_bar=first_stop,target_touch_bar=first_target,ordering='INTRABAR_AMBIGUOUS' if collision else 'NO_SAME_BAR_COLLISION_OBSERVED',collisions=collision,
            post_exit_1h_favorable_bp=sign*((after.high.max() if sign==1 else after.low.min())/entry-1)*10000 if len(after) else None,
            post_exit_classification='HINDSIGHT_DIAGNOSTIC_NOT_AVAILABLE_PROFIT')
    return clean(result)

def thesis_timeline(pair,g,t):
    first=pd.Timestamp(t['open_date']);end=pd.Timestamp(t['close_date'])
    f=feature(pair).loc[lambda f:(f.date+pd.Timedelta(minutes=15)>first)&(f.date+pd.Timedelta(minutes=15)<=end)]
    boundary=g.get('boundary')
    if g['recipe']=='continuation' and boundary is None:
        boundary=feature(pair,'new').loc[pd.Timestamp(g['available_at'])-pd.Timedelta(minutes=15),'prior_vwap']
    frozen=dict(g,boundary=boundary);observations=[]
    for i,(_,r) in enumerate(f.iterrows()):
        fast=bool(r.get('thesis_lost_'+g['side'],False))
        structural=continuation_failure(frozen,f.iloc[:i+1]) if g['recipe']=='continuation' else None
        if fast or structural:
            observations.append(dict(available_at=(r.date+pd.Timedelta(minutes=15)).isoformat(),fast_v4=fast,structural=structural,close=float(r.close),vwap=float(r.vwap),ema20=float(r.ema20),local_direction=r.struct_direction,boundary=boundary))
    return observations

def obstacle_status(pair,g,selected=True):
    date=pd.Timestamp(g['available_at'])-pd.Timedelta(minutes=15);r=feature(pair,'new').loc[date];sign=1 if g['side']=='long' else -1
    obstacles=levels(r,g['side']);details=[]
    end=pd.Timestamp(g['available_at'])+pd.Timedelta(hours=g['max_hold_hours'])
    future=candles(pair).loc[lambda f:(f.date>=pd.Timestamp(g['available_at']))&(f.date<end)]
    for x in obstacles:
        source=x['source']
        active_key=source+'_active'
        if source.endswith('_1h'):active_key=source[:-3]+'_active_1h'
        elif source.endswith('_4h'):active_key=source[:-3]+'_active_4h'
        active=r.get(active_key)
        age=(pd.Timestamp(g['available_at'])-pd.Timestamp(x['known_at'])).total_seconds()/3600
        history=candles(pair).loc[lambda f:(f.date>=pd.Timestamp(x['known_at']))&(f.date<date)]
        crossed=bool((history.close>x['price']).any()) if sign==1 else bool((history.close<x['price']).any())
        # Timeframe/active/age annotations use only pre-entry observations; no empirical success label.
        relevance='CONSUMED_CONFIRMED_SWING' if active is not None and pd.notna(active) and not bool(active) else 'LOCAL_INTERNAL_15M' if x['timeframe']=='15m' else 'PREKNOWN_PARENT_OR_SESSION_LEVEL'
        touch=future.loc[future.high.ge(x['price']) if sign==1 else future.low.le(x['price'])]
        acceptance=future.loc[sign*(future.close-x['price'])>.15*g['atr_at_signal']]
        rr=(sign*(x['price']-g['reference'])/g['reference']-.0038)/(sign*(g['reference']-g['stop'])/g['reference']+.0038)
        details.append(dict(**x,active=bool(active) if active is not None and pd.notna(active) else None,known_age_hours=age,prior_close_crossed=crossed,relevance_status=relevance,
            distance_atr=sign*(x['price']-g['reference'])/g['atr_at_signal'],after_cost_rr=rr,
            hindsight_interaction=dict(first_touch_bar=touch.date.iloc[0].isoformat() if len(touch) else None,
                first_close_beyond_buffer=acceptance.date.iloc[0].isoformat() if len(acceptance) else None,
                status='HINDSIGHT_ONLY;TOUCH_AND_ACCEPTANCE_DO_NOT_PROVE_EXECUTABLE_PROFIT')))
    first,why=objective(r,g['side'],g['reference'],g['stop'])
    return dict(key=opportunity_key(pair,g),pair=pair,side=g['side'],at=g['available_at'],selected=selected,
        entry=g['reference'],stop=g['stop'],fixed_target=g['target'],parent_direction=r.direction_4h,hour_direction=r.struct_direction_1h,
        obstacles=clean(details),first_objective=first,original_reason=why,ranking=rank_at(pair,g))

def passive_touch(pair,g,original,order):
    at=pd.Timestamp(g['available_at']);expiry=pd.Timestamp(g['expires_at']);sign=1 if g['side']=='long' else -1
    result={}
    for tf,step in [('5m',5),('15m',15)]:
        f=candles(pair,tf)
        if at<f.date.min():result[tf]=dict(status='NOT_TESTABLE_WITH_AVAILABLE_DATA');continue
        q=f.loc[(f.date>=at)&(f.date<at+pd.Timedelta(minutes=60))]
        touched=(q.low<=g['reference']) if sign==1 else (q.high>=g['reference'])
        hits=q.loc[touched]
        first=hits.iloc[0] if len(hits) else None
        legal=q.loc[(q.date>=at)&(q.date+pd.Timedelta(minutes=step)<=expiry)]
        legal_touch=bool(((legal.low<=g['reference']) if sign==1 else (legal.high>=g['reference'])).any())
        result[tf]=dict(status='COARSE_BAR_OVERLAPS_EXPIRY' if step>5 else 'REAL_5M_CANDLE_RANGE_DIAGNOSTIC',
            legal_complete_bar_touch=legal_touch if step<=5 else None,first_touch_bar=first.date.isoformat() if first is not None else None,
            first_touch_bar_end=(first.date+pd.Timedelta(minutes=step)).isoformat() if first is not None else None,
            after_expiry=bool(first.date>=expiry) if first is not None else None,
            first_candle_directional_bp=sign*(q.close.iloc[0]/original['trade']['open_rate']-1)*10000 if len(q) else None)
    return dict(available_at=g['available_at'],expires_at=g['expires_at'],planned_price=g['reference'],native_order=order,
        original_v4_net=original['ledger']['net'],touch_diagnostics=result,
        conclusion='NO_LEGAL_FIRST_15M_TOUCH_IMPLIES_NO_5M_FILL' if result.get('15m',{}).get('first_touch_bar') is None else 'SEE_TIMEFRAME_SPECIFIC_BOUNDS;QUEUE_UNKNOWN')

def run():
    preservation=verify_parent();portfolios={};natives={};orders={}
    for v in NATIVE_LABELS:portfolios[v],natives[v],orders[v]=load_portfolio(v)
    maps={v:{x['key']:x for x in z} for v,z in portfolios.items()};rows=[]
    for name,items in portfolios.items():
        order_map={o['decision_id']:o for o in orders[name]['orders'] if o['is_entry']}
        for x in items:
            pair=x['trade']['pair'];g=x['plan'];t=x['trade'];l=x['ledger'];state=state_at(pair,g)
            mechanism=[]
            if l['gross']>0 and l['net']<0:mechanism.append(dict(category='COST_OR_EXECUTION',grade='OBSERVED_MECHANISM',evidence='Native fees/funding turn positive gross into net loss'))
            if 'stop' in l['exit_reason']:mechanism.append(dict(category='STOP_GEOMETRY',grade='INSUFFICIENT_EVIDENCE',evidence='Protective exit occurred; suitability of its original structural boundary is not established by loss'))
            if not state['hour_aligned']:mechanism.append(dict(category='WRONG_OPPORTUNITY',grade='PLAUSIBLE_HYPOTHESIS',evidence='Confirmed hourly structure opposed/unknown; local structure exception can still authorize original playbook'))
            if not all(state[k] for k in ('ema_1h_aligned','ema_15m_aligned','ema_slope_aligned')):mechanism.append(dict(category='WRONG_OPPORTUNITY',grade='PLAUSIBLE_HYPOTHESIS',evidence='One or more original EMA predicates contradict; isolated replay required'))
            if not mechanism:mechanism.append(dict(category='UNDETERMINED',grade='INSUFFICIENT_EVIDENCE',evidence='Outcome does not identify a unique entry/stop/target cause'))
            original=maps['v4'].get(x['key'])
            row=dict(**x,decision_time=state,original_strategy_inputs='Frozen V4 price/structure predicates and rank' if name!='pr12' else 'PR12 frozen setup lifecycle and first objective',
                descriptive_features='4h context, range and obstacle relevance are retrospective AS-OF feature enrichment unless present in original plan',
                native_entry_order=order_map.get(g['decision_id']),rank=rank_at(pair,g,strict=name!='relaxed'),path=path_summary(pair,g,t),
                thesis_observations=thesis_timeline(pair,g,t),failure_mechanisms=mechanism,
                matched_v4_net_delta=l['net']-original['ledger']['net'] if original else None,
                unresolved=['REAL_QUEUE_AND_SPREAD','HIDDEN_ORDER_FLOW_AND_AUTHENTIC_PROFILE','CAUSAL_STOP_OR_TARGET_SUPERIORITY'])
            rows.append(row)
    write(OUT/'trade-forensics.json',clean(rows))
    pd.DataFrame([dict(strategy=x['source_strategy'],key=x['key'],pair=x['trade']['pair'],side=x['plan']['side'],playbook=x['plan']['recipe'],at=x['plan']['available_at'],
        net=x['ledger']['net'],entry=x['trade']['open_rate'],exit=x['trade']['close_rate'],exit_at=x['trade']['close_date'],exit_reason=x['trade']['exit_reason'],
        mechanisms=';'.join(y['category']+':'+y['grade'] for y in x['failure_mechanisms'])) for x in rows]).to_csv(OUT/'trade-forensics.csv',index=False)
    passive=[];missed=[]
    plans=read(PWORK/'plans/entry-passive.json');porders={o['decision_id']:o for o in orders['passive']['orders'] if o['is_entry']}
    for key,original in maps['v4'].items():
        pair=original['trade']['pair'];g=plans[pair][original['plan']['available_at']]
        match=maps['passive'].get(key)
        if match:
            sign=1 if g['side']=='long' else -1;c=read(PARENT/'contracts.json')[pair];a=original['trade'];b=match['trade']
            passive.append(dict(key=key,pair=pair,at=g['available_at'],v4=original,passive=match,
                price_improvement_ticks=sign*(a['open_rate']-b['open_rate'])/c['price_precision'],price_improvement_bp=sign*(a['open_rate']-b['open_rate'])/a['open_rate']*10000,
                price_improvement_atr=sign*(a['open_rate']-b['open_rate'])/g['atr_at_signal'],quantity_equal=a['amount']==b['amount'],
                exit_price_equal=a['close_rate']==b['close_rate'],exit_time_equal=a['close_date']==b['close_date'],
                net_delta=match['ledger']['net']-original['ledger']['net'],gross_delta=match['ledger']['gross']-original['ledger']['gross'],
                grade='CAUSAL_MATCHED_DIFFERENCE_WITH_POSSIBLE_SIZE_AND_EXIT_INTERACTION'))
        else:missed.append(dict(key=key,pair=pair,original=original,signal_state=state_at(pair,g),**passive_touch(pair,g,original,porders.get(g['decision_id']))))
    write(OUT/'passive-matched.json',clean(passive));write(OUT/'passive-missed.json',clean(missed))
    changed=[]
    for key,x in maps['v4'].items():
        y=maps['structural'].get(key)
        if y and abs(y['ledger']['net']-x['ledger']['net'])>1e-7:
            pair=x['trade']['pair'];latest=max(pd.Timestamp(x['trade']['close_date']),pd.Timestamp(y['trade']['close_date']))
            both=dict(y['trade'],close_date=latest.isoformat())
            changed.append(dict(key=key,pair=pair,v4=x,structural=y,delta=y['ledger']['net']-x['ledger']['net'],
                alternative_later=pd.Timestamp(y['trade']['close_date'])>pd.Timestamp(x['trade']['close_date']),
                timeline=thesis_timeline(pair,y['plan'],both),grade='CAUSAL_MATCHED_DIFFERENCE',
                protection_note='Native trailing_stop_loss label can mean fixed geometric stop tightened from emergency bound; it does not prove a dynamic trailing rule'))
    write(OUT/'structural-changes.json',clean(changed))
    extra=[x for k,x in maps['relaxed'].items() if k not in maps['v4']]
    displaced=[x for k,x in maps['v4'].items() if k not in maps['relaxed']]
    shared=[dict(key=k,v4=x,relaxed=maps['relaxed'][k],delta=maps['relaxed'][k]['ledger']['net']-x['ledger']['net']) for k,x in maps['v4'].items() if k in maps['relaxed']]
    write(OUT/'ema-membership.json',clean(dict(additional=[dict(**x,asof=state_at(x['trade']['pair'],x['plan'])) for x in extra],displaced=displaced,shared=shared)))
    obstacles=[obstacle_status(x['pair'],x['plan'],x['shortlisted']) for x in read(PARENT/'selection-audit.json')]
    write(OUT/'obstacle-audit.json',clean(obstacles))
    five=read(PARENT/'five-opportunities.json');funnel={}
    for variant in ['five-15m-response','five-early','five-passive']:
        counts=Counter();qualified=[]
        for x in five:
            counts['LOCATION']+=1
            if 'opportunity' not in x:counts[x['status']]+=1;continue
            counts['REGISTERED']+=1;y=x['variants'][variant];counts[y['reason']]+=1
            if y.get('plan'):
                counts['GEOMETRY_QUALIFIED']+=1;qualified.append(dict(candidate=x,ranking=rank_at(x['pair'],dict(y['plan'],available_at=x['armed_at']))))
                counts['SHORTLIST_PASS' if x['shortlisted'] else 'SHORTLIST_REJECT']+=1
        funnel[variant]=dict(counts=dict(counts),qualified=qualified)
    write(OUT/'five-funnel.json',clean(funnel))
    segments={}
    for variant,items in portfolios.items():
        segments[variant]={}
        for field in ('playbook','side','exit_reason','pair'):
            vals={x['trade']['pair'] if field=='pair' else x['plan']['recipe'] if field=='playbook' else x['plan']['side'] if field=='side' else x['trade']['exit_reason'] for x in items}
            def get(x):return x['trade']['pair'] if field=='pair' else x['plan']['recipe'] if field=='playbook' else x['plan']['side'] if field=='side' else x['trade']['exit_reason']
            segments[variant][field]={v:dict(n=sum(get(x)==v for x in items),net=sum(x['ledger']['net'] for x in items if get(x)==v)) for v in sorted(vals)}
    distributions={}
    v4rows=[r for r in rows if r['source_strategy']=='v4']
    for name in ('adx','rvol','signed_distance_vwap_atr','extension_from_pullback_atr','signal_body_atr','signed_relative_btc','atr_fraction'):
        distributions[name]={}
        for group,predicate in [('winner',lambda r:r['ledger']['net']>0),('loser',lambda r:r['ledger']['net']<=0),('september_winner',lambda r:r['ledger']['net']>0 and r['plan']['available_at'].startswith('2026-09')),('october_winner',lambda r:r['ledger']['net']>0 and r['plan']['available_at'].startswith('2026-10'))]:
            values=[r['decision_time'][name] for r in v4rows if predicate(r) and r['decision_time'][name] is not None]
            distributions[name][group]=dict(n=len(values),q25_median_q75=np.quantile(values,[.25,.5,.75]).tolist() if values else None)
    write(OUT/'winner-loser-distributions.json',distributions)
    from freqtrade.optimize.backtesting import Backtesting
    import freqtrade,ccxt,sys
    semantics=dict(python=sys.version,freqtrade=freqtrade.__version__,ccxt=ccxt.__version__,
        engine_source_sha256=sha(Path(inspect.getfile(Backtesting))),
        limit_fill_source=inspect.getsource(Backtesting._try_close_open_order),
        capacity_source=inspect.getsource(Backtesting.trade_slot_available),
        callback_clocks='Main15m rows shifted to next candle; analyzed dataframe excludes current main candle. Configured5m expiry cannot recover within15m ordering.')
    write(OUT/'native-semantics.json',semantics)
    summary=dict(at=now(),preservation=preservation,portfolio_fills={k:len(v) for k,v in portfolios.items()},
        total_overlapping_trade_records=len(rows),unique_filled_opportunities=len({x['key'] for x in rows}),
        passive=dict(matched=len(passive),matched_net_delta=sum(x['net_delta'] for x in passive),missed=len(missed),missed_v4_net=sum(x['original']['ledger']['net'] for x in missed)),
        structural=dict(changed=len(changed),worse=sum(x['delta']<0 for x in changed),improved=sum(x['delta']>0 for x in changed),delta=sum(x['delta'] for x in changed)),
        ema=dict(shared=len(shared),additional=len(extra),additional_winners=sum(x['ledger']['net']>0 for x in extra),additional_net=sum(x['ledger']['net'] for x in extra),displaced=len(displaced),displaced_v4_net=sum(x['ledger']['net'] for x in displaced)),
        obstacles=dict(raw=len(obstacles),selected=sum(x['selected'] for x in obstacles),raw_reasons=dict(Counter(x['original_reason'] for x in obstacles)),first_relevance=dict(Counter(x['obstacles'][0]['relevance_status'] if x['obstacles'] else 'MISSING' for x in obstacles if x['selected']))),
        native_capacity_rejects={k:n['rejected_signals'] for k,n in natives.items()},segments=segments,
        evidence_policy='Post-entry paths are descriptive hindsight; no candle-path cash counterfactual or universal loss cause',flow='UNKNOWN',profile='NOT_TESTED')
    write(OUT/'diagnosis-summary.json',clean(summary));print(summary,flush=True)

if __name__=='__main__':run()
