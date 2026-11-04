"""Causal market interpretation and ordered setup events, version setup-v1.

Reuses native indicators and the confirmed-pivot state machine. No outcome,
exchange order, approximate profile, or LLM input participates in decisions.
"""
import hashlib
import math
import numpy as np
import pandas as pd
import talib.abstract as ta
from PlaybookRiskV1 import session_features
from causal_structure import structure, closed_merge
from session4_features import hourly, liquidity

COST=.0038
HOLDS={'continuation':8,'reversal':4,'breakout':8,'rotation':6}

def merge_candidate(existing,candidate):
    """Competing hypotheses on the same asset/decision time always abstain."""
    return candidate if existing is None else {'conflict':True}

def finite(x):
    try:return math.isfinite(float(x))
    except (ValueError,TypeError):return False

def features(base, hours):
    d=structure(session_features(base))
    h=hourly(hours)
    h['range_high']=h.high.shift().rolling(20).max()
    h['range_low']=h.low.shift().rolling(20).min()
    h['balance']=(h.adx<25)&((h.range_high-h.range_low)<=8*h.atr)
    d=closed_merge(d,h)
    # Resampling may produce a partial last4h bar. Its actual close timestamp
    # is used for the backward join, so it cannot affect an earlier decision.
    h4=hours.set_index('date').resample('4h').agg(
        open=('open','first'),high=('high','max'),low=('low','min'),
        close=('close','last'),volume=('volume','sum'),count=('close','count')).reset_index()
    h4['bias4h']=ta.EMA(h4,timeperiod=20)-ta.EMA(h4,timeperiod=50)
    h4['known4h']=h4.date+pd.Timedelta(hours=4)
    h4.loc[h4['count'].ne(4),'bias4h']=np.nan
    d['_at']=d.date+pd.Timedelta(minutes=15)
    d=pd.merge_asof(d,h4[['known4h','bias4h']],left_on='_at',right_on='known4h',direction='backward')
    for label,freq,n in [('day','D',96),('session','8h',32)]:
        group=d.date.dt.floor(freq)
        v=d.groupby(group).agg(high=('high','max'),low=('low','min'),count=('close','count'))
        v=v.reindex(pd.date_range(group.min(),group.max(),freq=freq,tz='UTC'))
        v.loc[v['count'].ne(n),['high','low']]=np.nan
        for side in ('high','low'):d['prior_'+label+'_'+side]=group.map(v[side].shift())
        d['prior_'+label+'_known_at']=group
    metrics=liquidity(d)
    for k in metrics:d[k]=metrics[k]
    d['prior_vwap']=d.vwap.shift();d['prior_vwap_known_at']=d.date
    d['previous_close']=d.close.shift();d['previous_high']=d.high.shift();d['previous_low']=d.low.shift()
    d['pull_low']=d.low.shift().rolling(6).min();d['pull_high']=d.high.shift().rolling(6).max()
    age=d._at-(d.date_1h+pd.Timedelta(hours=1))
    numeric=['open','high','low','close','volume','atr14','rvol','ema20_1h','ema50_1h','adx_1h','atr_1h','bias4h']
    clean=np.isfinite(d[numeric]).all(axis=1)&d.volume.gt(0)&d.atr_ratio.between(.001,.025)
    d['setup_valid']=clean&d.contiguous&d.context_valid_1h.eq(True)&age.between(pd.Timedelta(0),pd.Timedelta(minutes=45))
    d['setup_valid'] &= (d._at-d.known4h).between(pd.Timedelta(0),pd.Timedelta(hours=4)-pd.Timedelta(minutes=1))
    d['regime']=np.select([d.balance_1h.eq(True),d.adx_1h.ge(20)&d.struct_direction_1h.eq('UP'),d.adx_1h.ge(20)&d.struct_direction_1h.eq('DOWN')],['BALANCE','TREND_UP','TREND_DOWN'],default='TRANSITION')
    return d.drop(columns=['_at'])

def levels(r, side, include_inward=False):
    s=1 if side=='long' else -1
    result=[]
    for stem,clock in [('prior_swing','prior_swing_{edge}_known_at'),('swing_1h','swing_{edge}_known_at_1h'),('prior_day','prior_day_known_at'),('prior_session','prior_session_known_at')]:
        edge='high' if s==1 else 'low'
        key='swing_'+edge+'_1h' if stem=='swing_1h' else stem+'_'+edge
        stamp=clock.format(edge=edge)
        if finite(r.get(key)) and pd.notna(r.get(stamp)) and pd.Timestamp(r[stamp])<=pd.Timestamp(r.date):
            result.append(dict(price=float(r[key]),source=key,known_at=pd.Timestamp(r[stamp]).isoformat(),fidelity='CONFIRMED_CLOSED_BARS'))
    if include_inward:
        if finite(r.get('prior_vwap')) and bool(r.get('same_session',False)):
            result.append(dict(price=float(r.prior_vwap),source='SESSION_VWAP_FROZEN',known_at=r.date.isoformat(),fidelity='OHLCV_TYPICAL_PRICE_VWAP'))
        if finite(r.get('range_high_1h')) and finite(r.get('range_low_1h')) and bool(r.get('balance_1h',False)):
            result.append(dict(price=float((r.range_high_1h+r.range_low_1h)/2),source='COMPLETED_HOURLY_RANGE_MID',known_at=(r.date_1h+pd.Timedelta(hours=1)).isoformat(),fidelity='CONFIRMED_CLOSED_BARS'))
    return sorted([x for x in result if s*(x['price']-r.close)>0],key=lambda x:s*(x['price']-r.close))

def make_plan(r, armed, target_mode='objective'):
    side=armed['side'];s=1 if side=='long' else -1
    entry=float(r.close);atr=float(r.atr14)
    extreme=min(armed['extreme'],r.low) if s==1 else max(armed['extreme'],r.high)
    stop=float(extreme-s*.2*atr);risk=s*(entry-stop)/entry
    if not .003<=risk<=.025:return None,'LOGICAL_STOP_OUTSIDE_0.3_2.5_PERCENT'
    obstacles=levels(r,side,armed['playbook'] in ('reversal','rotation'))
    if armed['playbook']=='rotation':
        obstacles+=armed['profile_objectives']
        obstacles=sorted([x for x in obstacles if s*(x['price']-entry)>0],key=lambda x:s*(x['price']-entry))
    if not obstacles:return None,'NO_PREEXISTING_OBJECTIVE'
    first=obstacles[0];target=first['price'];origin=first['source']
    if target_mode=='fixed-r':target=entry+s*3*(s*(entry-stop));origin='REGISTERED_FIXED_3R_COMPARATOR'
    reward=s*(target-entry)/entry;rr=(reward-COST)/(risk+COST)
    if rr<1.25:return None,'FIRST_OBSTACLE_INSUFFICIENT_AFTER_COST_REWARD'
    at=r.date+pd.Timedelta(minutes=15)
    second=next((x for x in obstacles if s*(x['price']-first['price'])>.1*atr),None)
    ident=hashlib.sha256((armed['id']+':'+at.isoformat()).encode()).hexdigest()[:24]
    return dict(schema_version='setup.plan.v1',policy_id='setup-v1.0.0',decision_id=ident,setup_id=armed['id'],
        recipe=armed['playbook'],playbook_version='1.0.0',side=side,venue='gate',reference=entry,signal_close=entry,
        stop=stop,structural_stop=stop,target=target,first_objective=first,second_objective=second,
        target_origin=origin,obstacles=obstacles,risk_fraction=risk,modeled_loss_per_notional=risk+COST,
        after_cost_rr=rr,admission_cost_allowance=COST,available_at=at.isoformat(),
        expires_at=(at+pd.Timedelta(minutes=5)).isoformat(),max_hold_hours=HOLDS[armed['playbook']],
        deviation_fraction=min(.0015,.25*atr/entry),atr_at_signal=atr,boundary=armed['boundary'],
        boundary_source=armed['source'],reference_known_at=armed['reference_known_at'],
        setup_armed_at=armed['at'],confirmation_at=at.isoformat(),confirmation=armed['confirmation'],
        regime=r.regime,timeframes=['1d','4h','1h','15m'],state='CONFIRMED',
        invalidation='TWO_COMPLETED_ADVERSE_CLOSES_AT_FROZEN_BOUNDARY',
        management='FULL_FIRST_OBJECTIVE',flow={'status':'UNKNOWN','reason':'NO_HISTORICAL_EXECUTED_TAPE'},
        profile_fidelity='NOT_USED' if armed['playbook']!='rotation' else 'VERIFIED_TRADE_DERIVED',
        fill_model='NATIVE_LIMIT_RANGE_QUEUE_UNKNOWN'), 'TRADE'

def _arm(pair,r,playbook,side,boundary,source,stamp,extreme):
    ref=str(stamp);ident=':'.join([pair,playbook,side,source,ref,str(round(float(boundary),10))])
    return dict(id=ident,pair=pair,playbook=playbook,side=side,boundary=float(boundary),source=source,
                reference_known_at=ref,at=(r.date+pd.Timedelta(minutes=15)).isoformat(),extreme=float(extreme),bars=0)

def scan_pair(d,pair,mode='confirmed',profiles=None):
    """One attempt per immutable reference. Sequence state is local to this replay.

    All armed snapshots are frozen before confirmation. Missing authentic profile
    history emits UNKNOWN, never a candle proxy. Ranking is a separate stage.
    """
    active={};used=set();records=[]
    def record(r,a,state,reason,plan=None):
        records.append(dict(pair=pair,at=(r.date+pd.Timedelta(minutes=15)).isoformat(),setup_id=a['id'],
            playbook=a['playbook'],side=a['side'],state=state,reason=reason,plan=plan,
            boundary=a['boundary'],boundary_source=a['source'],reference_known_at=a['reference_known_at'],
            armed_at=a['at'],regime=r.regime,rvol=float(r.rvol),location_atr=abs(r.close-a['boundary'])/r.atr14))
        records[-1].update(entry_close=float(r.close),registered_extreme=a['extreme'],atr=float(r.atr14),
                           flow_status='UNKNOWN',profile_status='NOT_USED' if a['playbook']!='rotation' else 'VERIFIED_TRADE_DERIVED')
    def add(r,a):
        key=(a['playbook'],a['side'])
        # A VWAP anchor is one opportunity per session and side, rather than one
        # new trade for every small change of its cumulative numeric value.
        if a['source']=='SESSION_VWAP':a['id']=':'.join([pair,a['playbook'],a['side'],'VWAP',str(r.date.floor('D'))])
        if key not in active and a['id'] not in used:
            active[key]=a;record(r,a,'ARMED','WAIT_COMPLETED_CONFIRMATION')
    for _,r in d.iterrows():
        at=r.date+pd.Timedelta(minutes=15)
        if not bool(r.setup_valid):
            for a in active.values():
                record(r,a,'INVALIDATED','DATA_GAP_OR_UNAVAILABLE_CONTEXT');used.add(a['id'])
            active={};continue
        # First process earlier setups; a sweep/retest may not confirm on its
        # own formation candle. This is deliberately an ordered event sequence.
        for key,a in list(active.items()):
            s=1 if a['side']=='long' else -1;a['bars']+=1
            limit=8 if a['playbook']=='breakout' else 4
            if a['bars']>limit:
                record(r,a,'EXPIRED','CONFIRMATION_WINDOW_EXPIRED');used.add(a['id']);del active[key];continue
            extreme=r.low if s==1 else r.high
            if s*(r.close-a['boundary'])<-.5*r.atr14 or s*(extreme-a['extreme'])<-.2*r.atr14:
                record(r,a,'INVALIDATED','REGISTERED_BOUNDARY_OR_EXTREME_FAILED');used.add(a['id']);del active[key];continue
            a['extreme']=min(a['extreme'],r.low) if s==1 else max(a['extreme'],r.high)
            directional=s*(r.close-r.open)>0
            if a['playbook']=='continuation':
                aligned=r.struct_direction_1h==('UP' if s==1 else 'DOWN') and s*r.bias4h>0
                confirmed=aligned and directional and s*(r.close-(r.previous_high if s==1 else r.previous_low))>0 and r.rvol>=1 and s*(r.close-a['boundary'])>0 and abs(r.close-a['boundary'])<=2.5*r.atr14
                a['confirmation']='DEFENDED_ZONE_COMPLETED_PREVIOUS_BAR_BREAK'
            elif a['playbook']=='reversal':
                shift=finite(a.get('shift_level')) and s*(r.previous_close-a['shift_level'])<=0 and s*(r.close-a['shift_level'])>0
                displacement=s*(r.close-r.open)>=.8*r.atr14 and r.rvol>=1.2
                confirmed=s*(r.close-a['boundary'])>0 and directional and (shift or displacement)
                a['confirmation']='FROZEN_PRE_SWEEP_STRUCTURE_BREAK' if shift else 'LATER_PARTICIPATION_DISPLACEMENT'
            elif a['playbook']=='breakout':
                a['accepted']=a.get('accepted',0)+1 if s*(r.close-a['boundary'])>0 else 0
                retest=(r.low<=a['boundary']+.35*r.atr14 if s==1 else r.high>=a['boundary']-.35*r.atr14)
                confirmed=a['accepted']>=2 and retest and directional and r.rvol>=1 and 0<s*(r.close-a['boundary'])<=2.5*r.atr14
                a['confirmation']='TWO_CLOSE_ACCEPTANCE_AND_DEFENDED_RETEST'
            else:
                confirmed=directional and s*(r.close-a['boundary'])>0 and s*(r.close-r.previous_close)>0
                a['confirmation']='VALUE_REACCEPTANCE_AND_LATER_INWARD_CLOSE'
            if mode=='simple':confirmed=directional and s*(r.close-a['boundary'])>0
            if confirmed:
                p,reason=make_plan(r,a,'fixed-r' if mode=='fixed-r' else 'objective')
                record(r,a,'CONFIRMED' if p else 'REJECTED',reason,p);used.add(a['id']);del active[key]
        for side,s in [('long',1),('short',-1)]:
            edge='low' if s==1 else 'high';extreme=float(r[edge])
            direction='UP' if s==1 else 'DOWN'
            # Trend interpretation: coherent hourly structure and completed4h
            # bias, plus a real impulse preceding a controlled defended pullback.
            if r.struct_direction_1h==direction and r.adx_1h>=20 and s*r.bias4h>0 and r.session_bars>=8 and r.vwap_valid:
                zones=[]
                if bool(r.same_session) and finite(r.prior_vwap):zones.append((r.prior_vwap,'SESSION_VWAP',r.date))
                k='swing_'+edge+'_1h';stamp='swing_'+edge+'_known_at_1h'
                if finite(r.get(k)) and pd.notna(r.get(stamp)) and r[stamp]<=r.date:zones.append((r[k],k,r[stamp]))
                for boundary,source,known in zones:
                    impulse=s*(r.previous_close-(r.pull_low if s==1 else r.pull_high))>=r.atr14
                    touched=abs(extreme-boundary)<=.5*r.atr14 and s*(r.previous_close-boundary)>0 and s*(r.close-boundary)>=-.25*r.atr14
                    if impulse and touched:
                        protected=min(extreme,r.pull_low) if s==1 else max(extreme,r.pull_high)
                        add(r,_arm(pair,r,'continuation',side,boundary,source,known,protected));break
            # External references are known BEFORE the excursion, not arbitrary
            # rolling candle extremes or pivots backdated to their center bar.
            refs=[('prior_day_'+edge,'prior_day_known_at'),('prior_session_'+edge,'prior_session_known_at'),('swing_'+edge+'_1h','swing_'+edge+'_known_at_1h')]
            for k,stamp in refs:
                if not finite(r.get(k)) or pd.isna(r.get(stamp)) or r[stamp]>r.date:continue
                b=float(r[k]);excursion=s*(b-extreme)/r.atr14
                if .1<=excursion<=1 and s*(r.close-b)>0 and s*(r.previous_close-b)>=0:
                    a=_arm(pair,r,'reversal',side,b,k,r[stamp],extreme)
                    k='prior_swing_high' if s==1 else 'prior_swing_low';v=r.get(k)
                    a['shift_level']=float(v) if finite(v) and s*(v-r.close)>0 and bool(r.get(k+'_active',True)) else None
                    add(r,a);break
            # Independent breakout: freeze the prior hourly consolidation at
            # its first completed break, then wait for acceptance and a retest.
            b=r.get('range_high_1h' if s==1 else 'range_low_1h')
            if r.balance_1h and finite(b) and s*(r.previous_close-b)<=0 and s*(r.close-b)>=.1*r.atr14 and r.rvol>=1.2:
                a=_arm(pair,r,'breakout',side,b,'PRIOR20_COMPLETE_1H_RANGE',r.date_1h,extreme);a['accepted']=1;add(r,a)
            if profiles:
                profile=profiles.get(r.date.floor('D').isoformat())
                if profile and profile.get('status')=='READY' and profile.get('fidelity')=='OBSERVED_TRADES' and profile.get('pair')==pair and profile.get('venue')=='gate' and r.balance_1h and pd.Timestamp(profile['known_at'])<=r.date and r.date-pd.Timestamp(profile['anchor_end'])<pd.Timedelta(seconds=profile['anchor_seconds']):
                    b=profile['val' if s==1 else 'vah']
                    if s*(extreme-b)<-.1*r.atr14 and s*(r.close-b)>0:
                        a=_arm(pair,r,'rotation',side,b,'VERIFIED_TRADE_PROFILE_EDGE',profile['known_at'],extreme)
                        a['profile_objectives']=[dict(price=profile[k],source='VERIFIED_TRADE_PROFILE_'+k.upper(),known_at=profile['known_at'],fidelity='VERIFIED_TRADE_DERIVED') for k in ['poc','vah' if s==1 else 'val']];add(r,a)
    return records

def thesis_failed(g, rows):
    """Two completed adverse closes; hard stops work independently intrabar."""
    if len(rows)<2:return False
    s=1 if g['side']=='long' else -1;b=float(g['boundary']);buffer=.15*g['atr_at_signal']
    adverse=all(s*(float(r.close)-b)<-buffer for _,r in rows.tail(2).iterrows())
    if g['recipe']=='continuation':
        r=rows.iloc[-1]
        return adverse and r.get('struct_direction')==('DOWN' if s==1 else 'UP')
    return adverse
