"""Stage cheap playbook-specific shortlist, causal setups, then deterministic plans."""
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
import numpy as np
import pandas as pd
from setup_common import *

def feature_job(pair):
    from setup_features import features
    from session4_features import indicators,hourly
    from freqtrade.strategy import merge_informative_pair
    root=DATA/'development/gate/futures'
    b=pd.read_feather(root/(slug(pair)+'-15m-futures.feather'))
    h=pd.read_feather(root/(slug(pair)+'-1h-futures.feather'))
    p=WORK/'features/new'/(slug(pair)+'.pkl');p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():features(b,h).to_pickle(p)
    p=WORK/'features/v4'/(slug(pair)+'.pkl');p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():indicators(merge_informative_pair(b,hourly(h),'15m','1h',ffill=True)).to_pickle(p)
    return pair

def prepare():
    from setup_features import scan_pair,merge_candidate
    from session4_features import candidates
    if (OUT/'plans.json').exists():raise ValueError('refuse overwrite completed plan registration')
    with ProcessPoolExecutor(max_workers=4) as pool:list(pool.map(feature_job,pairs()))
    frames={p:pd.read_pickle(WORK/'features/new'/(slug(p)+'.pkl')) for p in pairs()}
    old_frames={p:pd.read_pickle(WORK/'features/v4'/(slug(p)+'.pkl')) for p in pairs()}
    columns=['date','eligible','setup_valid','return4h','activity','close','vwap','atr14','rvol','range_high_1h','range_low_1h','prior_day_high','prior_day_low','prior_session_high','prior_session_low','swing_low_1h','swing_high_1h','ema20_1h','ema50_1h']
    wide=pd.concat([d[columns].assign(pair=p) for p,d in frames.items()],ignore_index=True)
    btc=frames['BTC/USDT:USDT'].set_index('date').return4h
    slots={v:{} for v in ['setup','old-ranking','null-ranking-1','null-ranking-2','null-ranking-3']}
    funnel=Counter()
    if (WORK/'shortlist.json').exists():
        slots=read(WORK/'shortlist.json')
    else:
        for date,g in wide.groupby('date',sort=True):
            at=(date+pd.Timedelta(minutes=15)).isoformat()
            if not protocol()['evaluation_start']<=at<protocol()['end_exclusive']:continue
            funnel['raw_market_checks']+=len(g)
            q=g.loc[g.eligible & g.setup_valid].copy();funnel['eligible_market_checks']+=len(q)
            if q.empty:continue
            q['relative']=q.return4h-float(btc.loc[date]);q.loc[q.pair.eq('BTC/USDT:USDT'),'relative']=q.return4h
            for book in ['continuation','reversal','breakout','rotation']:
                for side,s in [('long',1),('short',-1)]:
                    lane=book+':'+side
                    z=q.copy()
                    if book=='continuation':
                        z=z.loc[s*(z.ema20_1h-z.ema50_1h)>0].copy()
                        z['score']=-(z.close-z.vwap).abs()/z.atr14+.1*z.rvol.clip(upper=3)
                    elif book=='reversal':
                        keys=['prior_day_low','prior_session_low','swing_low_1h'] if s==1 else ['prior_day_high','prior_session_high','swing_high_1h']
                        z['score']=-pd.concat([(z.close-z[k]).abs()/z.atr14 for k in keys],axis=1).min(axis=1)+.1*z.rvol.clip(upper=3)
                    else:
                        boundary=z.range_high_1h if s==1 else z.range_low_1h
                        z['score']=-(z.close-boundary).abs()/z.atr14+.1*z.rvol.clip(upper=3)
                    z=z.loc[np.isfinite(z.score)]
                    slots['setup'].setdefault(at,{})[lane]=z.sort_values(['score','pair'],ascending=[False,True]).pair.head(3).tolist()
                    old=q.copy()
                    if book=='continuation':old=old.loc[s*(old.ema20_1h-old.ema50_1h)>0].copy()
                    old['score']=s*old.relative+.01*old.activity.clip(upper=3)
                    slots['old-ranking'].setdefault(at,{})[lane]=old.sort_values(['score','pair'],ascending=[False,True]).pair.head(3).tolist()
                    for seed in [1,2,3]:
                        null=q.copy();null['order']=[__import__('hashlib').sha256(f'{seed}:{at}:{lane}:{p}'.encode()).hexdigest() for p in null.pair]
                        slots['null-ranking-'+str(seed)].setdefault(at,{})[lane]=null.sort_values('order').pair.head(3).tolist()
    variants=protocol()['variants'];plans={v:{} for v in variants};ledger=[]
    def route(items,mode):
        for item in items:
            if not protocol()['evaluation_start']<=item['at']<protocol()['end_exclusive']:continue
            if mode=='confirmed':ledger.append(item)
            if item['reason']!='TRADE' or not item['plan']:continue
            p=item['plan'];pair=item['pair'];at=item['at'];lane=p['recipe']+':'+p['side']
            choices=['setup','old-ranking','null-ranking-1','null-ranking-2','null-ranking-3'] if mode=='confirmed' else ['simple-trigger' if mode=='simple' else 'fixed-r']
            for v in choices:
                rank=v if v in slots else 'setup'
                if pair not in slots[rank].get(at,{}).get(lane,[]):continue
                old=plans[v].setdefault(pair,{}).get(at)
                candidate=dict(p,decision_id=pair+':'+p['decision_id'],pair=pair,state='ADMITTED',
                    source_data_refs=[dict(path=x['path'],sha256=x['sha256']) for x in read(OUT/'data-development.json')['files'] if slug(pair)+'-' in Path(x['path']).name])
                plans[v][pair][at]=merge_candidate(old,candidate)
    for pair,d in frames.items():
        route(scan_pair(d,pair),'confirmed');route(scan_pair(d,pair,'simple'),'simple')
        # Fixed-R changes targets only on the EXACT confirmed opportunities;
        # geometry admission effects remain visible in same-entry diagnostics.
        old=old_frames[pair]
        for item in candidates(old,'reference'):
            at=item['at'];p=item['plan'];r=old.iloc[item['index']]
            if not protocol()['evaluation_start']<=at<protocol()['end_exclusive'] or item['reason']!='TRADE' or not p:continue
            lane=item['recipe']+':'+item['side']
            # Frozen V4 selection formula, with its distinct reversal location
            # score, reconstructed on this separate source cohort.
            group=wide.loc[wide.date.eq(r.date)&wide.eligible].copy()
            s=1 if item['side']=='long' else -1
            if item['recipe']=='continuation':
                group=group.loc[s*(group.ema20_1h-group.ema50_1h)>0].copy()
                group['score']=s*(group.return4h-float(btc.loc[r.date]))+.01*group.activity.clip(upper=3)
                group.loc[group.pair.eq('BTC/USDT:USDT'),'score']=s*group.return4h+.01*group.activity.clip(upper=3)
            else:
                # Parent uses prior20 15m candle boundary. Obtain exact frozen
                # columns from each parent feature cache, never new definitions.
                group['score']=[s*(old_frames[pair2].loc[lambda f:f.date.eq(r.date),'close'].iloc[0]-old_frames[pair2].loc[lambda f:f.date.eq(r.date),'prior_low' if s==1 else 'prior_high'].iloc[0])/old_frames[pair2].loc[lambda f:f.date.eq(r.date),'atr14'].iloc[0] for pair2 in group.pair]
            if pair in group.sort_values(['score','pair'],ascending=[False,True]).pair.head(3).tolist():
                plans['v4-reference'].setdefault(pair,{})[at]=dict(p,decision_id=pair+':'+p['decision_id'])
    conflicts={}
    for v in plans:
        conflicts[v]=sum(1 for z in plans[v].values() for p in z.values() if p.get('conflict'))
        for pair in plans[v]:plans[v][pair]={at:p for at,p in plans[v][pair].items() if not p.get('conflict')}
    plans['management']=__import__('copy').deepcopy(plans['setup'])
    for book in ['continuation','reversal','breakout']:
        plans[book]={p:{at:g for at,g in z.items() if g['recipe']==book} for p,z in plans['setup'].items()}
    # The fixed-R same-entry comparator uses the SAME objective-admitted plans.
    # This isolates target/portfolio effects without sneaking through obstacles.
    plans['fixed-r']=__import__('copy').deepcopy(plans['setup'])
    for z in plans['fixed-r'].values():
        for p in z.values():
            s=1 if p['side']=='long' else -1;p['target']=p['reference']+s*3*abs(p['reference']-p['stop']);p['target_origin']='SAME_ENTRY_FIXED_3R'
            p['objective_admission_rr']=p['after_cost_rr'];p['after_cost_rr']=(3*p['risk_fraction']-.0038)/(p['risk_fraction']+.0038)
    for item in ledger:
        if item['plan']:
            approved=plans['setup'].get(item['pair'],{}).get(item['at'])
            item['setup_confirmation_reason']=item['reason']
            item['state']='ADMITTED' if approved and approved['setup_id']==item['setup_id'] else 'REJECTED'
            item['reason']='TRADE' if item['state']=='ADMITTED' else 'CAUSAL_SHORTLIST_OR_PLAYBOOK_CONFLICT'
    summary={}
    for v,z in plans.items():
        path=WORK/'plans'/(v+'.json');write(path,z)
        summary[v]=dict(plans=sum(map(len,z.values())),sha256=sha(path),conflicts=conflicts.get(v,0))
    write(OUT/'plans.json',summary);write(OUT/'decisions.json',ledger)
    write(WORK/'shortlist.json',slots)
    write(OUT/'funnel.json',dict(**funnel,states=dict(Counter(x['state'] for x in ledger)),reasons=dict(Counter(x['reason'] for x in ledger)),distinct_setups=len({x['setup_id'] for x in ledger}),profile={'status':'NOT_TESTED','reason':'NO_COMPLETE_VERIFIED_HISTORICAL_TAPE'}))
    write(OUT/'features.json',{kind:{p:sha(WORK/'features'/kind/(slug(p)+'.pkl')) for p in pairs()} for kind in ['new','v4']})
    print(summary,flush=True)
if __name__=='__main__':
    if RUN_ID=='run-003':
        import argparse
        from setup_candidate import prepare as corrected_prepare
        p=argparse.ArgumentParser();p.add_argument('--audit',action='store_true');corrected_prepare(p.parse_args().audit)
    else:prepare()
