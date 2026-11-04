"""Cheap lane ranking and demand-driven analysis. No orders or portfolio simulator."""
from collections import Counter
import math
import time
import pandas as pd
from causal_structure import structure
from setup_features import finite,scan_pair,merge_candidate
from setup_profile import select_profile

BOOKS=('continuation','reversal','breakout','rotation')
LANES=[(b,s) for b in BOOKS for s in ('long','short')]

class Snapshot(dict):
    """Scalar cached-bar transport; avoids pandas attribute/index overhead per gate."""
    __getattr__=dict.__getitem__
    def to_dict(self):return dict(self)

def locations(r,book,side,profiles,pair):
    s=1 if side=='long' else -1;edge='low' if s==1 else 'high';at=r.date
    levels=[]
    def add(key,stamp,proxy=False):
        if finite(r.get(key)) and pd.notna(r.get(stamp)) and pd.Timestamp(r[stamp])<=at:
            levels.append((float(r[key]),key,proxy))
    if book=='continuation':
        direction=r.get('struct_direction_1h')
        if direction in ('UP','DOWN') and direction!=('UP' if s==1 else 'DOWN'):return []
        add('swing_'+edge+'_1h','swing_'+edge+'_known_at_1h')
        if r.get('session_bars',0)>=8 and bool(r.get('vwap_valid',False)) and bool(r.get('same_session',False)):
            add('prior_vwap','prior_vwap_known_at')
        if not levels:
            add('range_'+edge+'_1h','hour_context_known_at',True)
    elif book=='reversal':
        for k,stamp in [('prior_day_'+edge,'prior_day_known_at'),('prior_session_'+edge,'prior_session_known_at'),('swing_'+edge+'_1h','swing_'+edge+'_known_at_1h')]:add(k,stamp)
    elif book=='breakout':
        if not bool(r.get('balance_1h',False)):return []
        add('range_'+('high' if s==1 else 'low')+'_1h','hour_context_known_at')
    else:
        p=select_profile(profiles,pair,at)
        if p:levels.append((p['val' if s==1 else 'vah'],'VERIFIED_PROFILE_EDGE',False))
    return levels

def shortlist(rows,profiles=(),budget=3,old=False):
    """Same cutoff/budget. Rank developing state, nearest location, activity, pair."""
    rows={p:Snapshot(r.to_dict()) if isinstance(r,pd.Series) else r for p,r in rows.items()}
    selected={};reasons={};counts=Counter(raw_pair_checks=len(rows))
    btc=rows.get('BTC/USDT:USDT');btc_return=btc.get('return4h',0) if btc is not None else 0
    for lane in LANES:
        book,side=lane;s=1 if side=='long' else -1;ranked=[]
        for pair,r in rows.items():
            if not bool(r.get('eligible',False)):continue
            if not bool(r.get('setup_valid',False)):continue
            if old:
                # The frozen PR11 selector ranked the entire eligible pool,
                # before setup suitability. Do not prefilter its pool using
                # the corrected structure/balance conditions.
                if book=='rotation' and select_profile(profiles,pair,r.date) is None:continue
                if book=='continuation':
                    if not all(finite(r.get(k)) for k in ['ema20_1h','ema50_1h','vwap']) or s*(r.ema20_1h-r.ema50_1h)<=0:continue
                    distance=abs(r.close-r.vwap)/r.atr14;source='SESSION_VWAP';level=r.vwap
                elif book=='reversal':
                    edge='low' if s==1 else 'high'
                    keys=['prior_day_'+edge,'prior_session_'+edge,'swing_'+edge+'_1h']
                    refs=[(float(r[k]),k,False) for k in keys if finite(r.get(k))]
                    if not refs:continue
                    level,source,_=min(refs,key=lambda z:abs(r.close-z[0]));distance=abs(r.close-level)/r.atr14
                else:
                    level=r.get('range_high_1h' if s==1 else 'range_low_1h');source='PRIOR20_COMPLETE_1H_RANGE'
                    if not finite(level):continue
                    distance=abs(r.close-level)/r.atr14
                score=-distance+.1*min(float(r.rvol),3)
                if not finite(score):continue
                ranked.append(((-score,pair),pair,dict(playbook=book,side=side,condition='FROZEN_PR11_SELECTOR',location_source=source,location_price=level,location_atr=distance)))
                continue
            refs=locations(r,book,side,profiles,pair)
            if not refs:continue
            closest=min(refs,key=lambda z:(abs(r.close-z[0]),z[1]))
            level,source,proxy=closest;distance=abs(r.close-level)/r.atr14
            extreme=r.low if s==1 else r.high
            developing=(abs(extreme-level)<=.5*r.atr14 if book=='continuation' else
                (s*(extreme-level)<0 and s*(r.close-level)>0) if book in ('reversal','rotation') else
                s*(r.close-level)>0 or s*(r.previous_close-level)>0)
            activity=float(r.get('activity',0));activity=activity if math.isfinite(activity) else 0
            key=(0 if developing else 1,distance,-activity,pair)
            ranked.append((key,pair,dict(playbook=book,side=side,condition='DEVELOPING' if developing else 'WATCH_LOCATION',
                location_source=source,location_price=level,location_atr=distance,proxy_requires_deep_verification=proxy,
                prior_day_quote=float(r.get('prior_day_quote',0)),prior7_quote=float(r.get('prior7_quote',0)),
                source_cutoff=(r.date+pd.Timedelta(minutes=15)).isoformat(),historical_spread='UNKNOWN',historical_market_status='UNKNOWN')))
        for _,pair,why in sorted(ranked,key=lambda z:z[0])[:budget]:
            selected.setdefault(pair,set()).add(lane);reasons.setdefault(pair,[]).append(why)
    counts['eligible_pair_checks']=sum(bool(r.get('eligible',False)) for r in rows.values())
    counts['unique_shortlisted_pairs']=len(selected);counts['shortlisted_lane_slots']=sum(map(len,selected.values()))
    counts['deduplicated_lane_slots']=counts['shortlisted_lane_slots']-len(selected)
    return selected,reasons,counts

class DeepProvider:
    """Cached archive transport; local pivot work occurs only on explicit demand."""
    def __init__(self,frames,warmup=960):
        self.frames=frames;self.warmup=warmup;self.states={};self.last={};self.cache={};self.materialized={p:{} for p in frames}
        self.counts=Counter();self.elapsed=0.
    def get(self,pair,r):
        at=r.date;key=(pair,at)
        if pair in self.cache and self.cache[pair][0]==at:self.counts['deep_cache_hits']+=1;return self.cache[pair][1]
        begin=time.perf_counter();self.counts['deep_calls']+=1
        previous=self.last.get(pair)
        if previous is None or at-previous!=pd.Timedelta(minutes=15):
            self.states[pair]={};f=self.frames[pair]
            warm=f.loc[f.date<at].tail(self.warmup)
            structure([Snapshot(x) for x in warm.to_dict('records')],state=self.states[pair],records_only=True)
            self.counts['deep_warmup_rows']+=len(warm);self.counts['deep_cache_misses']+=1
        else:self.counts['deep_state_cache_hits']+=1
        raw=Snapshot(r.to_dict())
        values=structure([raw],state=self.states[pair],records_only=True)[0]
        out=Snapshot({**raw,**values})
        self.last[pair]=at;self.cache[pair]=(at,out);self.materialized[pair][at]=values
        self.counts['deep_decision_rows']+=1;self.elapsed+=time.perf_counter()-begin
        return out
    def native_frames(self):
        result={}
        for pair,f in self.frames.items():
            d=f.copy();values=self.materialized[pair]
            keys={k for row in values.values() for k in row}
            for k in sorted(keys):
                d[k]=d.date.map({at:row.get(k) for at,row in values.items()})
                if k.endswith('_at'):d[k]=pd.to_datetime(d[k],utc=True)
            needed=['date','open','high','low','close','volume','atr14','rvol','eligible','setup_valid','regime',
                'struct_direction','swing_high','swing_low','swing_high_known_at','swing_low_known_at',
                'struct_direction_1h','adx_1h','map4h_ready','map4h_reason','known4h','swing_high_4h','swing_low_4h',
                'swing_high_known_at_4h','swing_low_known_at_4h','bias4h','ema20_1h','ema50_1h','prior_day_quote','prior7_quote']
            d=d[[k for k in needed if k in d]]
            result[pair]=d
        return result

class Workflow:
    def __init__(self,provider,profiles=(),mode='new'):
        self.provider=provider;self.profiles=profiles;self.mode=mode;self.states={};self.management_until={}
        self.plans={};self.events=[];self.trace=[];self.counts=Counter();self.selections={}
        self.gate_samples=[]
    def tick(self,rows,positions=()):
        selected,reasons,counts=shortlist(rows,self.profiles,old=self.mode=='old')
        self.counts.update(counts)
        at=next(iter(rows.values())).date+pd.Timedelta(minutes=15)
        self.selections[at.isoformat()]={p:sorted([b+':'+s for b,s in lanes]) for p,lanes in selected.items()}
        active={p for p,state in self.states.items() if state.get('active')}
        managed=set(positions)|{p for p,end in self.management_until.items() if at<=end}
        needed=set(selected)|active|managed
        for pair,r in rows.items():
            reason=('ILLIQUID_OR_NOT_WARM' if not bool(r.get('eligible',False)) else
                'REQUIRED_CLOSED_BAR_DATA_UNAVAILABLE' if not bool(r.get('setup_valid',False)) else
                'SHORTLISTED' if pair in selected else 'RETAINED_SETUP_OR_POSITION' if pair in active|managed else 'ELIGIBLE_NOT_SHORTLISTED')
            self.counts['gate_'+reason]+=1
            if len(self.gate_samples)<60 and (reason!='SHORTLISTED' or len(self.gate_samples)<10):
                self.gate_samples.append(dict(pair=pair,at=at.isoformat(),reason=reason,prior_day_quote=float(r.get('prior_day_quote',0)),prior7_quote=float(r.get('prior7_quote',0))))
            if bool(r.get('eligible',False)) and select_profile(self.profiles,pair,r.date) is None:self.counts['profile_unknown_pair_times']+=1
        if self.mode=='audit':needed={p for p,r in rows.items() if bool(r.get('eligible',False))}|active|managed
        complete={};new_events=[]
        for pair in sorted(needed):
            if pair not in rows:continue
            r=self.provider.get(pair,rows[pair]);lanes=selected.get(pair,set())
            if self.mode=='audit':lanes=set(LANES) if bool(r.get('eligible',False)) else set()
            elif not bool(r.get('eligible',False)):lanes=set()
            trace=dict(pair=pair,at=at.isoformat(),new_lanes=sorted([b+':'+s for b,s in lanes]),
                retained_setup=pair in active,position_or_reservation=pair in managed,shortlist=reasons.get(pair,[]))
            self.trace.append(trace)
            events=scan_pair([r],pair,profiles=self.profiles,state=self.states.setdefault(pair,{}),allow_new=lanes)
            for e in events:
                e['shortlist_at_event']=reasons.get(pair,[])
                if e['plan']:
                    if not bool(r.get('eligible',False)):
                        e.update(state='REJECTED',reason='ELIGIBILITY_LOST_BEFORE_ADMISSION')
                    else:
                        g=dict(e['plan'],pair=pair,decision_id=pair+':'+e['plan']['decision_id'],state='READY')
                        complete[pair]=merge_candidate(complete.get(pair),g)
                new_events.append(e)
        for pair,g in complete.items():
            if g.get('conflict'):
                for e in new_events:
                    if e['pair']==pair and e['plan']:e.update(state='REJECTED',reason='CONFLICTING_COMPLETE_PLANS')
                continue
            self.plans.setdefault(pair,{})[at.isoformat()]=g
            # Before native fills are known, conservatively reserve management
            # data for every executable plan through its possible first-fill hold.
            self.management_until[pair]=at+pd.Timedelta(hours=g['max_hold_hours'],minutes=20)
            for e in new_events:
                if e['pair']==pair and e['plan'] and e['plan']['setup_id']==g['setup_id']:
                    e.update(state='READY',reason='TRADE',plan=g)
        self.events.extend(new_events)
        self.counts.update({'event_'+k:v for k,v in Counter(e['state'] for e in new_events).items()})
        self.counts['deep_pair_updates']+=len(needed)
        self.counts['retained_setup_updates']+=len(active-set(selected))
        self.counts['management_updates_outside_shortlist']+=len(managed-set(selected))
        return new_events
