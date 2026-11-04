"""Preregistered variants on common opportunities; never rewrite PR13 plans."""
import copy
from collections import Counter,defaultdict
import numpy as np
import pandas as pd
from diagnosis_common import *
from targeted_rules import conditional_entry,relaxed_candidates,compatible_thesis
from session4_features import candidates

VARIANTS=['v4','pr12','passive','structural','conditional-entry','passive-30m','ema-eligibility-only','rank-only','ema-both','rank-qualified-only','continuation-only','thesis-compatible']

def rank(rows,book,side,strict=True,qualified=None):
    sign=1 if side=='long' else -1;btc=rows['BTC/USDT:USDT'].return4h;ranked=[]
    for p,r in rows.items():
        if qualified is not None and p not in qualified:continue
        if not bool(r.eligible) or not np.isfinite(r.return4h) or not np.isfinite(r.activity):continue
        if book=='continuation':
            if strict and sign*(r.ema20_1h-r.ema50_1h)<=0:continue
            score=sign*(r.return4h-(0 if p=='BTC/USDT:USDT' else btc))+.01*min(float(r.activity),3)
        else:score=sign*(r.close-(r.prior_low if sign==1 else r.prior_high))/r.atr14
        ranked.append((float(score),p))
    ranked.sort(key=lambda x:(-x[0],x[1]))
    return [p for _,p in ranked[:3]]

def canonical(pair,x):
    g=copy.deepcopy(x['plan']);g.setdefault('methodology','structure')
    g['decision_id']=pair+':structure::'+g['recipe']+':'+g['side']+':'+g['available_at']
    return g

def construct(frames,contexts,start,end,contracts):
    start=pd.Timestamp(start,tz='UTC');end=pd.Timestamp(end,tz='UTC')
    strict=[];loose=[]
    for pair,f in frames.items():
        for x in candidates(f.reset_index(drop=True),'structure'):
            if x['reason']=='TRADE' and x['plan'] and start<=pd.Timestamp(x['at'])<end:strict.append(dict(pair=pair,**x))
        for x in relaxed_candidates(f.reset_index(drop=True)):
            if x['reason']=='TRADE' and x['plan'] and start<=pd.Timestamp(x['at'])<end:loose.append(dict(pair=pair,**x))
    # Reversals retain the exact frozen independent playbook in every eligibility arm.
    loose += [x for x in strict if x['recipe']=='reversal']
    qualified=defaultdict(set)
    for x in strict:
        date=pd.Timestamp(x['at'])-pd.Timedelta(minutes=15)
        if bool(frames[x['pair']].loc[date,'eligible']):qualified[(x['at'],x['recipe'],x['side'])].add(x['pair'])
    result={v:{} for v in VARIANTS};decisions=[]
    def put(v,pair,g):
        at=g['available_at'];existing=result[v].setdefault(pair,{}).get(at)
        if existing and existing['side']!=g['side']:
            result[v][pair].pop(at);return
        result[v][pair][at]=g
    for pool,raw in [('strict',strict),('relaxed',loose)]:
        for x in raw:
            pair=x['pair'];g=canonical(pair,x);date=pd.Timestamp(g['available_at'])-pd.Timedelta(minutes=15)
            rows={p:f.loc[date] for p,f in frames.items()};r=rows[pair]
            ranks={name:rank(rows,g['recipe'],g['side'],strict=name=='strict',qualified=qualified[(x['at'],g['recipe'],g['side'])] if name=='qualified' else None) for name in ('strict','relaxed','qualified')}
            decisions.append(dict(pool=pool,key=opportunity_key(pair,g),pair=pair,at=g['available_at'],plan=g,liquidity_eligible=bool(r.eligible),rank_choices=ranks))
            if pool=='strict':
                if pair in ranks['relaxed']:put('rank-only',pair,copy.deepcopy(g))
                if pair in ranks['qualified']:put('rank-qualified-only',pair,copy.deepcopy(g))
                if pair not in ranks['strict']:continue
                put('v4',pair,copy.deepcopy(g))
                passive=copy.deepcopy(g);sign=1 if g['side']=='long' else -1;passive['reference']-=sign*.15*g['atr_at_signal']
                from policy_features import execution_plan
                passive=execution_plan(passive,passive['reference'],pd.Timestamp(passive['available_at']))
                if passive:
                    put('passive',pair,copy.deepcopy(passive))
                    longer=copy.deepcopy(passive);longer['expires_at']=(pd.Timestamp(g['available_at'])+pd.Timedelta(minutes=30)).isoformat();put('passive-30m',pair,longer)
                conditional=conditional_entry(g,r)
                if conditional:put('conditional-entry',pair,conditional)
                if g['recipe']=='continuation':put('continuation-only',pair,copy.deepcopy(g))
                structural=copy.deepcopy(g)
                structural['boundary']=float(contexts[pair].loc[date,'prior_vwap']) if g['recipe']=='continuation' else g['boundary']
                structural['reference_known_at']=date.isoformat()
                put('structural',pair,copy.deepcopy(structural))
                structural['diagnosis_structural_compatible']=compatible_thesis(structural,contracts[pair]['price_precision'])
                put('thesis-compatible',pair,structural)
            else:
                if pair in ranks['strict']:put('ema-eligibility-only',pair,copy.deepcopy(g))
                if pair in ranks['relaxed']:put('ema-both',pair,copy.deepcopy(g))
    return result,decisions

def validation_features(cohort):
    from setup_features import features
    from setup_map import four_hour_map
    from session4_features import indicators,hourly
    from freqtrade.strategy import merge_informative_pair
    frames={};contexts={};root=ROOT/'user_data/data/diagnosis'/cohort/'gate/futures'
    for pair in pairs():
        b=pd.read_feather(root/(slug(pair)+'-15m-futures.feather'));h=pd.read_feather(root/(slug(pair)+'-1h-futures.feather'))
        for kind in ('v4','new'):
            target=WORK/cohort/'features'/kind/(slug(pair)+'.pkl')
            if not target.exists():
                if kind=='v4':f=indicators(merge_informative_pair(b,hourly(h),'15m','1h',ffill=True))
                else:
                    f=features(b,h);m=four_hour_map(h)[['known4h','struct_direction_4h']].rename(columns={'known4h':'parent_map_at','struct_direction_4h':'direction_4h'})
                    f=pd.merge_asof(f,m,left_on='date',right_on='parent_map_at',direction='backward')
                target.parent.mkdir(parents=True,exist_ok=True);f.to_pickle(target)
            f=pd.read_pickle(target).set_index('date',drop=False)
            (frames if kind=='v4' else contexts)[pair]=f
        print('FEATURES',cohort,pair,flush=True)
    return frames,contexts

def run(cohort='development'):
    verify_parent();spec=read(ROOT/'research/diagnosis/protocol.json')
    if sha(ROOT/'research/diagnosis/protocol.json')!=read(OUT/'preregistration.json')['sha256']:raise ValueError('preregistered protocol changed')
    registered=OUT/('plans-'+cohort+'.json')
    if registered.exists():raise ValueError('preserve completed plan registration')
    if cohort=='development':
        frames={p:pd.read_pickle(PWORK/'features/v4'/(slug(p)+'.pkl')).set_index('date',drop=False) for p in pairs()}
        contexts={p:pd.read_pickle(PWORK/'features/new'/(slug(p)+'.pkl')).set_index('date',drop=False) for p in pairs()}
    else:
        if not read(OUT/'data-validation.json')[cohort]['complete']:raise ValueError('incomplete validation data')
        frames,contexts=validation_features(cohort)
    contracts=read(PARENT/'contracts.json');window=spec['source_windows'][cohort]
    variants,decisions=construct(frames,contexts,window[1],window[2],contracts)
    if cohort=='development':
        frozen=read(PWORK/'plans/control-v4.json')
        if variants['v4']!=frozen:raise ValueError('frozen V4 reconstruction differs')
        # Preserve exact historical control objects and complete setup-specific management.
        variants['v4']=frozen;variants['pr12']=read(PWORK/'plans/control-pr12.json');variants['passive']=read(PWORK/'plans/entry-passive.json');variants['structural']=read(PWORK/'plans/thesis-exit.json')
    else:variants.pop('pr12',None)
    registry={}
    for v,plans in variants.items():
        path=WORK/cohort/'plans'/(v+'.json');write(path,plans)
        registry[v]=dict(plans=sum(map(len,plans.values())),sha256=sha(path),features='new' if v=='pr12' else 'v4')
    write(registered,registry);write(OUT/('opportunities-'+cohort+'.json'),decisions)
    sources=list((ROOT/'research/diagnosis').glob('*.*'))+[ROOT/'scripts/diagnosis_prepare.py',ROOT/'scripts/diagnosis_common.py']
    write(OUT/('plan-seal-'+cohort+'.json'),dict(at=now(),preregistration_sha256=sha(OUT/'preregistration.json'),source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources},
        plans=registry,validation_manifest_sha256=sha(OUT/'data-validation.json') if cohort!='development' else None,
        feature_hashes={str(p.relative_to(ROOT)):sha(p) for p in (WORK/cohort/'features').rglob('*.pkl')} if cohort!='development' else read(PARENT/'decision-freeze-v2.json')['feature_hashes']))
    print(cohort,registry,flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('cohort',nargs='?',default='development',choices=['development','earlier','later']);run(p.parse_args().cohort)
