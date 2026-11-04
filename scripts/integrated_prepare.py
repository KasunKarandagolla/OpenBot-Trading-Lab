"""Freeze controlled variants using real sources and the existing feature stack."""
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
import copy
import numpy as np
import pandas as pd
from integrated_common import *
from market_reader import interpret, objective, reprice

def feature_job(pair):
    from setup_features import features
    from setup_map import four_hour_map
    from session4_features import indicators,hourly
    from freqtrade.strategy import merge_informative_pair
    root=DATA/'gate/futures'
    b=pd.read_feather(root/(slug(pair)+'-15m-futures.feather'))
    h=pd.read_feather(root/(slug(pair)+'-1h-futures.feather'))
    for kind in ('v4','new'):
        path=WORK/'features'/kind/(slug(pair)+'.pkl')
        if path.exists(): continue
        if kind=='v4': f=indicators(merge_informative_pair(b,hourly(h),'15m','1h',ffill=True))
        else:
            f=features(b,h)
            m=four_hour_map(h)[['known4h','struct_direction_4h']].rename(columns={'known4h':'parent_map_at','struct_direction_4h':'direction_4h'})
            f=pd.merge_asof(f,m,left_on='date',right_on='parent_map_at',direction='backward')
        path.parent.mkdir(parents=True,exist_ok=True); f.to_pickle(path)
    print('FEATURES',pair,flush=True)

def ema_context_candidates(frame):
    """All original non-EMA continuation conditions, with structural authority."""
    from session4_features import validity, structure_reason
    from policy_features import plan
    valid=validity(frame)
    common=valid & frame.vwap_valid & frame.session_bars.ge(8) & frame.same_session & frame.adx_1h.ge(20) & frame.rvol.ge(1)
    span=(frame.high-frame.low).replace(0,np.nan)
    records=[]
    for side,sign in [('long',1),('short',-1)]:
        mask=(common & frame['accepted_'+side] & frame['prior_touch_'+side]
            & (sign*(frame.close-frame['previous_high' if sign==1 else 'previous_low'])>0)
            & (sign*(frame.close-frame.open)>0)
            & (((frame.close-frame.low) if sign==1 else (frame.high-frame.close))/span>=.65)
            & (((frame.close-frame.pullback_low) if sign==1 else (frame.pullback_high-frame.close))/frame.atr14<=2.5)
            & frame.struct_direction_1h.eq('UP' if sign==1 else 'DOWN'))
        for i,r in frame.loc[mask].iterrows():
            g,why=plan(r,'continuation',side)
            if structure_reason(r,'continuation',side)!='MATCH': continue
            records.append(dict(index=int(i),at=(r.date+pd.Timedelta(minutes=15)).isoformat(),recipe='continuation',side=side,reason=why,plan=g))
    return records

def selected(pair,row,book,side,frames,strict=True):
    sign=1 if side=='long' else -1
    btc=frames['BTC/USDT:USDT'].loc[row.date,'return4h'];ranking=[]
    for p,f in frames.items():
        r=f.loc[row.date]
        if not r.eligible or not np.isfinite(r.return4h) or not np.isfinite(r.activity): continue
        if book=='continuation':
            if strict and sign*(r.ema20_1h-r.ema50_1h)<=0: continue
            score=sign*(r.return4h-(0 if p=='BTC/USDT:USDT' else btc))+.01*min(float(r.activity),3)
        else: score=sign*(r.close-(r.prior_low if sign==1 else r.prior_high))/r.atr14
        ranking.append((float(score),p))
    ranking.sort(key=lambda x:(-x[0],x[1]))
    return pair in [p for _,p in ranking[:3]], [p for _,p in ranking[:3]]

def prepare():
    from session4_features import candidates
    if (OUT/'plans.json').exists(): raise ValueError('completed plan registration is immutable')
    for row in read(OUT/'data.json')['files']:
        if sha(ROOT/row['path'])!=row['sha256']: raise ValueError('market source changed')
    with ProcessPoolExecutor(max_workers=3) as pool: list(pool.map(feature_job,pairs()))
    frames={p:pd.read_pickle(WORK/'features/v4'/(slug(p)+'.pkl')).set_index('date',drop=False) for p in pairs()}
    contexts={p:pd.read_pickle(WORK/'features/new'/(slug(p)+'.pkl')).set_index('date',drop=False) for p in pairs()}
    variants={v:{} for v in protocol()['variants']}; opportunities=[];decisions=[]
    start=pd.Timestamp(protocol()['evaluation_start'],tz='UTC');end=pd.Timestamp(protocol()['end_exclusive'],tz='UTC')
    for pair,f in frames.items():
        raw=candidates(f.reset_index(drop=True),'structure')
        for x in raw:
            if x['reason']!='TRADE' or not x['plan'] or not start<=pd.Timestamp(x['at'])<end: continue
            g=copy.deepcopy(x['plan']);g['decision_id']=pair+':'+g['decision_id']
            date=pd.Timestamp(x['at'])-pd.Timedelta(minutes=15);r=contexts[pair].loc[date]
            chosen,shortlist=selected(pair,f.loc[date],g['recipe'],g['side'],frames)
            relative=r.return4h-(0 if pair=='BTC/USDT:USDT' else contexts['BTC/USDT:USDT'].loc[date,'return4h'])
            context=interpret(r,g['side'],g['recipe'],g['reference'],g['stop'],relative)
            row=dict(pair=pair,at=x['at'],decision_id=g['decision_id'],shortlisted=chosen,shortlist=shortlist,plan=g,context=context)
            decisions.append(row)
            if not chosen: continue
            opportunities.append(row); variants['control-v4'].setdefault(pair,{})[x['at']]=g
            # New variants preserve the original decision identity and original hard stop.
            enriched=dict(g,boundary=float(r.prior_vwap) if g['recipe']=='continuation' else g['boundary'],
                reference_known_at=date.isoformat(),setup_armed_at=x['at'],market_read=context)
            if context['status']=='QUALIFIED_RESEARCH': variants['market-selector'].setdefault(pair,{})[x['at']]=copy.deepcopy(enriched)
            s=1 if g['side']=='long' else -1
            passive=reprice(enriched,g['reference']-s*.15*g['atr_at_signal'],'PASSIVE_0.15ATR_AFTER_COMPLETED_TRIGGER')
            if passive: variants['entry-passive'].setdefault(pair,{})[x['at']]=passive
            variants['thesis-exit'].setdefault(pair,{})[x['at']]=copy.deepcopy(enriched)
            first,why=objective(r,g['side'],g['reference'],g['stop'])
            objective_plan=None
            if why=='PASS':
                objective_plan=reprice(dict(enriched,target=first['price'],target_origin=first['source'],first_objective=first),g['reference'],'SIGNAL_CLOSE_LIMIT')
                if objective_plan: variants['take-profit'].setdefault(pair,{})[x['at']]=objective_plan
            if context['status']=='QUALIFIED_RESEARCH' and objective_plan:
                integrated=reprice(objective_plan,g['reference']-s*.15*g['atr_at_signal'],'PASSIVE_0.15ATR_AFTER_COMPLETED_TRIGGER')
                if integrated: variants['integrated'].setdefault(pair,{})[x['at']]=integrated
        relaxed=ema_context_candidates(f.reset_index(drop=True))
        for x in relaxed:
            if x['reason']!='TRADE' or not start<=pd.Timestamp(x['at'])<end: continue
            date=pd.Timestamp(x['at'])-pd.Timedelta(minutes=15)
            if selected(pair,f.loc[date],'continuation',x['side'],frames,strict=False)[0]:
                g=copy.deepcopy(x['plan']);g['decision_id']=pair+':ema-context:'+x['side']+':'+x['at']
                variants['ema-context'].setdefault(pair,{})[x['at']]=g
        for at,g in variants['control-v4'].get(pair,{}).items():
            if g['recipe']=='reversal': variants['ema-context'].setdefault(pair,{}).setdefault(at,copy.deepcopy(g))
    # All 14 PR12 READY decisions filled in the sealed control. Read their exact plans.
    for state in read(ROOT/'evidence/setup/run-003/native/setup-fixed-touch-750/states.json'):
        g=state['plan'];variants['control-pr12'].setdefault(state['pair'],{})[g['available_at']]=g
    write(OUT/'opportunities.json',opportunities);write(OUT/'selection-audit.json',decisions)
    from integrated_five import prepare_five
    five=prepare_five(contexts,frames,variants)
    registry={}
    for v,plans in variants.items():
        path=WORK/'plans'/(v+'.json');write(path,plans)
        registry[v]=dict(plans=sum(map(len,plans.values())),sha256=sha(path),features='new' if v=='control-pr12' else 'five' if v.startswith('five-') else 'v4',timeframe='5m' if v.startswith('five-') else '15m')
    write(OUT/'plans.json',registry)
    write(OUT/'preparation.json',dict(at=now(),original_v4_registered=len(opportunities),raw_v4_qualified=len(decisions),missed_shortlist=sum(not x['shortlisted'] for x in decisions),
        context_status=dict(Counter(x['context']['status'] for x in opportunities)),five_minute=five,variants=registry))
    frozen=[ROOT/'research/integrated/protocol.json']+list((ROOT/'research/integrated').glob('*.py'))+list((ROOT/'scripts').glob('integrated_*.py'))
    write(OUT/'decision-freeze.json',dict(at=now(),source_sha256=sha(OUT/'data.json'),
        decision_source_hashes={str(p.relative_to(ROOT)):sha(p) for p in frozen},
        feature_hashes={str(p.relative_to(ROOT)):sha(p) for p in (WORK/'features').rglob('*.pkl')},plans=registry))
    print(registry,flush=True)

if __name__=='__main__': prepare()
