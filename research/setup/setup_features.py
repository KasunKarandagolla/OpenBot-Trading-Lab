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
from setup_map import four_hour_map
from setup_profile import select_profile

COST=.0038
HOLDS={'continuation':8,'reversal':4,'breakout':8,'rotation':6}

def merge_candidate(existing,candidate):
    """Competing hypotheses on the same asset/decision time always abstain."""
    return candidate if existing is None else {'conflict':True}

def finite(x):
    try:return math.isfinite(float(x))
    except (ValueError,TypeError):return False

def features(base, hours, deep=True):
    d=session_features(base)
    if deep:d=structure(d)
    h=hourly(hours)
    h['range_high']=h.high.shift().rolling(20).max()
    h['range_low']=h.low.shift().rolling(20).min()
    h['balance']=(h.adx<25)&((h.range_high-h.range_low)<=8*h.atr)
    d=closed_merge(d,h)
    d['hour_context_known_at']=d.date_1h # prior20-hour range excludes that hour
    h4=four_hour_map(hours)
    d['_at']=d.date+pd.Timedelta(minutes=15)
    columns=['known4h','bias4h','map4h_ready','map4h_reason']+[c for c in h4 if c.startswith(('swing_','prior_swing_'))]
    # Obstacles must be known at the OPEN of the15m confirmation candle.
    d=pd.merge_asof(d,h4[columns],left_on='date',right_on='known4h',direction='backward')
    stale=~(d.date-d.known4h).between(pd.Timedelta(0),pd.Timedelta(hours=4)-pd.Timedelta(seconds=1))
    d.loc[stale,'map4h_ready']=False;d.loc[stale,'map4h_reason']='MISSING_OR_STALE_MAP'
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
    numeric=['open','high','low','close','volume','atr14','rvol','adx_1h','atr_1h']
    clean=np.isfinite(d[numeric]).all(axis=1)&d.volume.gt(0)&d.atr_ratio.between(.001,.025)
    d['setup_valid']=clean&d.contiguous&d.context_valid_1h.eq(True)&age.between(pd.Timedelta(0),pd.Timedelta(minutes=45))
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
            result.append(dict(price=float(r[key]),source=key,timeframe={'prior_swing':'15m','swing_1h':'1h','prior_day':'1d','prior_session':'8h'}[stem],known_at=pd.Timestamp(r[stamp]).isoformat(),fidelity='CONFIRMED_CLOSED_BARS'))
    edge='high' if s==1 else 'low'
    key='swing_'+edge+'_4h';stamp='swing_'+edge+'_known_at_4h'
    if finite(r.get(key)) and pd.notna(r.get(stamp)) and pd.Timestamp(r[stamp])<=pd.Timestamp(r.date):
        result.append(dict(price=float(r[key]),source=key,timeframe='4h',known_at=pd.Timestamp(r[stamp]).isoformat(),fidelity='CONFIRMED_CLOSED_BARS'))
    if include_inward:
        if finite(r.get('prior_vwap')) and bool(r.get('same_session',False)):
            result.append(dict(price=float(r.prior_vwap),source='SESSION_VWAP_FROZEN',timeframe='15m',known_at=r.date.isoformat(),fidelity='OHLCV_TYPICAL_PRICE_VWAP'))
        if finite(r.get('range_high_1h')) and finite(r.get('range_low_1h')) and bool(r.get('balance_1h',False)):
            result.append(dict(price=float((r.range_high_1h+r.range_low_1h)/2),source='COMPLETED_HOURLY_RANGE_MID',timeframe='1h',known_at=r.date_1h.isoformat(),fidelity='CONFIRMED_CLOSED_BARS'))
    return sorted([x for x in result if s*(x['price']-r.close)>0],key=lambda x:s*(x['price']-r.close))

def make_plan(r, armed, target_mode='objective'):
    side=armed['side'];s=1 if side=='long' else -1
    if pd.isna(r.get('map4h_ready')) or not bool(r.get('map4h_ready',False)):return None,'MAP4H_UNAVAILABLE:'+str(r.get('map4h_reason','MISSING'))
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
    # Restore the existing parent horizon safeguard. A structural level can be
    # real yet too distant for a bounded intraday hypothesis. Never move it
    # nearer merely to manufacture acceptable geometry.
    if s*(target-entry)>6*atr:return None,'FIRST_OBJECTIVE_BEYOND_EXISTING_6ATR_BOUND'
    reward=s*(target-entry)/entry;rr=(reward-COST)/(risk+COST)
    if rr<1.25:return None,'FIRST_OBSTACLE_INSUFFICIENT_AFTER_COST_REWARD'
    at=r.date+pd.Timedelta(minutes=15)
    second=next((x for x in obstacles if s*(x['price']-first['price'])>.1*atr),None)
    ident=hashlib.sha256((armed['id']+':'+at.isoformat()).encode()).hexdigest()[:24]
    return dict(schema_version='setup.plan.v1',policy_id='setup-v1.2.0',decision_id=ident,setup_id=armed['id'],
        recipe=armed['playbook'],playbook_version='1.2.0',side=side,venue='gate',reference=entry,signal_close=entry,
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
        profile_reference=armed.get('profile_reference'),
        fill_model='NATIVE_LIMIT_RANGE_QUEUE_UNKNOWN'), 'TRADE'

def _arm(pair,r,playbook,side,boundary,source,stamp,extreme):
    ref=str(stamp);ident=':'.join([pair,playbook,side,source,ref,str(round(float(boundary),10))])
    if playbook=='breakout':ident+=':BREAK_AT:'+(r.date+pd.Timedelta(minutes=15)).isoformat()
    return dict(id=ident,pair=pair,playbook=playbook,side=side,boundary=float(boundary),source=source,
                reference_known_at=ref,at=(r.date+pd.Timedelta(minutes=15)).isoformat(),extreme=float(extreme),bars=0)

def scan_pair(d,pair,mode='confirmed',profiles=None,state=None,allow_new=None):
    """One attempt per immutable reference. Sequence state is local to this replay.

    All armed snapshots are frozen before confirmation. Missing authentic profile
    history emits UNKNOWN, never a candle proxy. Ranking is a separate stage.
    """
    saved=state if state is not None else {}
    active=saved.setdefault('active',{});used=saved.setdefault('used',set());records=[]
    def record(r,a,state,reason,plan=None):
        records.append(dict(pair=pair,at=(r.date+pd.Timedelta(minutes=15)).isoformat(),setup_id=a['id'],
            playbook=a['playbook'],side=a['side'],state=state,reason=reason,plan=plan,
            boundary=a['boundary'],boundary_source=a['source'],reference_known_at=a['reference_known_at'],
            armed_at=a['at'],regime=r.regime,rvol=float(r.rvol),location_atr=abs(r.close-a['boundary'])/r.atr14))
        records[-1].update(entry_close=float(r.close),registered_extreme=a['extreme'],atr=float(r.atr14),
                           old_ema_would_veto=bool(a['playbook']=='continuation' and (not finite(r.get('bias4h')) or (1 if a['side']=='long' else -1)*r.get('bias4h',0)<=0 or not finite(r.get('ema20_1h')) or not finite(r.get('ema50_1h')) or (1 if a['side']=='long' else -1)*(r.get('ema20_1h',0)-r.get('ema50_1h',0))<=0)),flow_status='UNKNOWN',profile_status='NOT_USED' if a['playbook']!='rotation' else 'VERIFIED_TRADE_DERIVED')
        records[-1]['map4h']=dict(ready=bool(r.get('map4h_ready',False)),reason=str(r.get('map4h_reason','MISSING')),
            known_at=str(r.get('known4h')) if pd.notna(r.get('known4h')) else None)
        if state=='REJECTED' and plan is None:
            sign=1 if a['side']=='long' else -1
            obstacles=levels(r,a['side'],a['playbook'] in ('reversal','rotation'))
            if a['playbook']=='rotation':obstacles+=a['profile_objectives']
            obstacles=sorted([x for x in obstacles if sign*(x['price']-r.close)>0],key=lambda x:sign*(x['price']-r.close))
            records[-1]['candidate_geometry']=dict(available_at=(r.date+pd.Timedelta(minutes=15)).isoformat(),
                confirmation_at=(r.date+pd.Timedelta(minutes=15)).isoformat(),confirmation=a.get('confirmation'),
                reference=float(r.close),stop=float(a['extreme']-sign*.2*r.atr14),
                first_objective=obstacles[0] if obstacles else None,obstacles=obstacles,status='REJECTED_NOT_EXECUTABLE')
    def add(r,a):
        key=(a['playbook'],a['side'])
        if allow_new is not None and key not in allow_new:return
        # A VWAP anchor is one opportunity per session and side, rather than one
        # new trade for every small change of its cumulative numeric value.
        if a['source']=='SESSION_VWAP':a['id']=':'.join([pair,a['playbook'],a['side'],'VWAP',str(r.date.floor('D'))])
        if key not in active and a['id'] not in used:
            active[key]=a;record(r,a,'ARMED','WAIT_COMPLETED_CONFIRMATION')
    rows=enumerate(d) if isinstance(d,list) else d.iterrows()
    for _,r in rows:
        at=r.date+pd.Timedelta(minutes=15)
        if saved.get('last_at') is not None and at<=saved['last_at']:continue
        saved['last_at']=at
        if not bool(r.setup_valid):
            for a in active.values():
                record(r,a,'INVALIDATED','DATA_GAP_OR_UNAVAILABLE_CONTEXT');used.add(a['id'])
            active.clear();continue
        # First process earlier setups; a sweep/retest may not confirm on its
        # own formation candle. This is deliberately an ordered event sequence.
        for key,a in list(active.items()):
            s=1 if a['side']=='long' else -1;a['bars']+=1
            limit=8 if a['playbook']=='breakout' else 4
            if a['bars']>limit:
                record(r,a,'EXPIRED','CONFIRMATION_WINDOW_EXPIRED');used.add(a['id']);del active[key];continue
            extreme=r.low if s==1 else r.high
            if a['playbook']=='breakout' and s*(r.close-a['boundary'])<0:
                record(r,a,'INVALIDATED','BREAKOUT_CLOSE_BACK_INSIDE');used.add(a['id']);del active[key];continue
            if s*(r.close-a['boundary'])<-.5*r.atr14 or s*(extreme-a['extreme'])<-.2*r.atr14:
                record(r,a,'INVALIDATED','REGISTERED_BOUNDARY_OR_EXTREME_FAILED');used.add(a['id']);del active[key];continue
            a['extreme']=min(a['extreme'],r.low) if s==1 else max(a['extreme'],r.high)
            directional=s*(r.close-r.open)>0
            if a['playbook']=='continuation':
                aligned=r.struct_direction_1h==('UP' if s==1 else 'DOWN')
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
            if r.struct_direction_1h==direction and r.adx_1h>=20:
                zones=[]
                if r.session_bars>=8 and r.vwap_valid and bool(r.same_session) and finite(r.prior_vwap):zones.append((r.prior_vwap,'SESSION_VWAP',r.date))
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
                profile=select_profile(profiles,pair,r.date)
                if profile and profile.get('status')=='READY' and profile.get('fidelity')=='OBSERVED_TRADES' and profile.get('pair')==pair and profile.get('venue')=='gate' and r.balance_1h and pd.Timestamp(profile['known_at'])<=r.date and r.date-pd.Timestamp(profile['anchor_end'])<pd.Timedelta(seconds=profile['anchor_seconds']):
                    b=profile['val' if s==1 else 'vah']
                    if s*(extreme-b)<-.1*r.atr14 and s*(r.close-b)>0:
                        a=_arm(pair,r,'rotation',side,b,'VERIFIED_TRADE_PROFILE_EDGE',profile['known_at'],extreme)
                        a['profile_reference']={k:profile[k] for k in ['venue','pair','anchor_start','anchor_end','anchor_seconds','known_at','source','source_sha256','fidelity']}
                        a['profile_reference']['coverage']='COMPLETE_VERIFIED'
                        a['profile_reference']['receipt']=profile.get('source_receipt')
                        a['profile_objectives']=[dict(price=profile[k],source='VERIFIED_TRADE_PROFILE_'+k.upper(),timeframe='8h' if profile['anchor_seconds']==28800 else '1d',known_at=profile['known_at'],fidelity='VERIFIED_TRADE_DERIVED') for k in ['poc','vah' if s==1 else 'val']];add(r,a)
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
