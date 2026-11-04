"""Genuine 5m signal path on shared, prospectively frozen 15m opportunities."""
import copy
import hashlib
import numpy as np
import pandas as pd
from integrated_common import *
from market_reader import objective,reprice

def first_response(candles,opportunity,minutes=5):
    """No response on the arming bar; stop/expiry failures consume this attempt."""
    arm=pd.Timestamp(opportunity['setup_armed_at']);expiry=arm+pd.Timedelta(minutes=60)
    sign=1 if opportunity['side']=='long' else -1
    q=candles.loc[(candles.date>=arm)&(candles.date+pd.Timedelta(minutes=minutes)<=expiry)]
    previous=arm-pd.Timedelta(minutes=minutes)
    for _,r in q.iterrows():
        if previous is not None and r.date-previous!=pd.Timedelta(minutes=minutes): return None,'SOURCE_GAP'
        previous=r.date
        if sign*((r.low if sign==1 else r.high)-opportunity['stop'])<=0: return None,'PROTECTED_EXTREME_FAILED'
        if sign*(r.close-opportunity['boundary'])<-.5*opportunity['atr_at_signal']: return None,'DEFENSE_FAILED'
        prior=r.get('previous_high' if sign==1 else 'previous_low')
        if pd.notna(prior) and sign*(r.close-r.open)>0 and sign*(r.close-prior)>0 and sign*(r.close-opportunity['boundary'])>0:
            if abs(r.close-opportunity['boundary'])>2.5*opportunity['atr_at_signal']: return None,'TRIGGER_EXTENDED'
            g=copy.deepcopy(opportunity)
            at=r.date+pd.Timedelta(minutes=minutes)
            g.update(available_at=at.isoformat(),confirmation_at=at.isoformat(),expires_at=(at+pd.Timedelta(minutes=5)).isoformat(),signal_close=float(r.close),reference=float(r.close))
            g['decision_id']=opportunity['setup_id']+':'+str(minutes)+':'+at.isoformat()
            result=reprice(g,float(r.close),'FIRST_COMPLETED_'+str(minutes)+'M_RESPONSE')
            return result,'QUALIFIED' if result else 'TRIGGER_GEOMETRY_REJECTED'
    return None,'NO_COMPLETED_RESPONSE_BEFORE_EXPIRY'

def prepare_five(contexts,frames,variants):
    paths=[DATA/'gate/futures'/(slug(p)+'-5m-futures.feather') for p in pairs()]
    if not all(p.exists() for p in paths): return dict(status='NOT_TESTED_MISSING_QUALIFIED_5M',missing=[str(p) for p in paths if not p.exists()])
    from integrated_prepare import selected
    for v in ('five-15m-response','five-early','five-passive'): variants[v]={}
    start=pd.Timestamp(read(OUT/'data.json')['five_minute_start'],tz='UTC')
    end=pd.Timestamp(protocol()['end_exclusive'],tz='UTC');records=[]
    for pair,f in contexts.items():
        five=pd.read_feather(DATA/'gate/futures'/(slug(pair)+'-5m-futures.feather'))
        five['previous_high']=five.high.shift();five['previous_low']=five.low.shift()
        # Native cache keeps actual 5m OHLCV and only context available at its OPEN.
        context=f.reset_index(drop=True).copy()
        context['source15_closed_at']=context.date+pd.Timedelta(minutes=15)
        context=context.rename(columns={k:'source15_'+k for k in ('date','open','high','low','close','volume','previous_high','previous_low')})
        native=pd.merge_asof(five,context,left_on='date',right_on='source15_closed_at',direction='backward')
        stale=(native.date-native.source15_closed_at)>=pd.Timedelta(minutes=15)
        native.loc[stale,'setup_valid']=False
        path=WORK/'features/five'/(slug(pair)+'.pkl');path.parent.mkdir(parents=True,exist_ok=True);native.to_pickle(path)
        used=set()
        for _,r in f.iterrows():
            arm=r.date+pd.Timedelta(minutes=15)
            if not start<=arm<end or not bool(r.setup_valid) or not bool(r.eligible) or not bool(r.map4h_ready): continue
            if not bool(r.same_session) or not bool(r.vwap_valid) or r.session_bars<8: continue
            for side,sign in [('long',1),('short',-1)]:
                key=(arm.floor('D'),side)
                if key in used or r.struct_direction_1h!=('UP' if sign==1 else 'DOWN') or r.adx_1h<20: continue
                b=float(r.prior_vwap);extreme=float(r.low if sign==1 else r.high)
                if not np.isfinite(b) or not (abs(extreme-b)<=.5*r.atr14 and sign*(r.previous_close-b)>0 and sign*(r.close-b)>=-.25*r.atr14): continue
                if sign*(r.previous_close-(r.pull_low if sign==1 else r.pull_high))<r.atr14: continue
                used.add(key)
                protected=min(float(r.pull_low),extreme) if sign==1 else max(float(r.pull_high),extreme)
                stop=protected-sign*.2*float(r.atr14)
                first,why=objective(r,side,float(r.close),stop)
                ident=hashlib.sha256(f'{pair}:{side}:{arm}:VWAP'.encode()).hexdigest()[:24]
                ranked,shortlist=selected(pair,frames[pair].loc[r.date],'continuation',side,frames)
                record=dict(setup_id=ident,pair=pair,side=side,armed_at=arm.isoformat(),boundary=b,reference_known_at=r.date.isoformat(),stop=stop,first_objective=first,shortlisted=ranked,shortlist=shortlist)
                if first is None:
                    record['status']='NO_KNOWN_OBJECTIVE';records.append(record);continue
                if why in ('STRUCTURAL_STOP_OUTSIDE_BOUNDS','OBJECTIVE_BEYOND_6ATR'):
                    record['status']=why;records.append(record);continue
                g=dict(policy_id='integrated-five-r1',recipe='continuation',side=side,setup_id=ident,decision_id=ident,
                    setup_armed_at=arm.isoformat(),boundary=b,reference_known_at=r.date.isoformat(),reference=float(r.close),signal_close=float(r.close),
                    stop=stop,structural_stop=stop,target=first['price'],first_objective=first,target_origin=first['source'],
                    atr_at_signal=float(r.atr14),available_at=arm.isoformat(),expires_at=(arm+pd.Timedelta(minutes=5)).isoformat(),
                    max_hold_hours=8,deviation_fraction=min(.0015,.25*r.atr14/r.close),admission_cost_allowance=.0038,
                    fill_model='NATIVE_5M_LIMIT_RANGE_QUEUE_UNKNOWN',flow={'status':'UNKNOWN'},profile_fidelity='NOT_USED')
                record['opportunity']=g;record['variants']={}
                for v,minutes in [('five-15m-response',15),('five-early',5)]:
                    p,reason=first_response(five if minutes==5 else f,g,minutes)
                    record['variants'][v]=dict(reason=reason,plan=p)
                    if p and ranked: variants[v].setdefault(pair,{})[p['available_at']]=p
                    if v=='five-early':
                        passive=reprice(p,p['reference']-sign*.15*p['atr_at_signal'],'PASSIVE_0.15ATR_AFTER_5M_TRIGGER') if p else None
                        record['variants']['five-passive']=dict(reason='QUALIFIED' if passive else reason if p is None else 'PASSIVE_GEOMETRY_REJECTED',plan=passive)
                        if passive and ranked: variants['five-passive'].setdefault(pair,{})[passive['available_at']]=passive
                record['status']='REGISTERED';records.append(record)
        print('FIVE',pair,flush=True)
    write(OUT/'five-opportunities.json',records)
    return dict(status='GENUINE_5M_PRIMARY_SIGNAL_PATH',start=start.isoformat(),end_exclusive=end.isoformat(),registered=len(records),
        selected=sum(x['shortlisted'] for x in records),missed_shortlist=sum(not x['shortlisted'] for x in records),
        limitation='Separate shared prospective opportunity cohort; not identical to archived V4 fills. Context frozen on 15m; immediate vs passive share first completed 5m trigger.')
