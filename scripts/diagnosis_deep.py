"""Detailed mechanism tests and retrospective distributions; no executable target rewrite."""
from collections import Counter
import numpy as np
import pandas as pd
from diagnosis_common import *
from diagnosis_audit import feature,candles,clean,load_portfolio,state_at,rank_at
from targeted_rules import compatible_thesis

def auc(values,labels):
    a=np.array(values,dtype=float);y=np.array(labels,dtype=bool)
    if not y.any() or y.all():return None
    ranks=pd.Series(a).rank(method='average').to_numpy()
    return float((ranks[y].sum()-y.sum()*(y.sum()+1)/2)/(y.sum()*(~y).sum()))

def run():
    verify_parent();matched=read(OUT/'passive-matched.json');decomposed=[]
    for x in matched:
        a=x['v4'];b=x['passive'];sign=1 if a['plan']['side']=='long' else -1
        qa=a['trade']['amount'];qb=b['trade']['amount'];ea=a['trade']['open_rate'];eb=b['trade']['open_rate'];xa=a['trade']['close_rate'];xb=b['trade']['close_rate']
        pieces=dict(entry_price=sign*qa*(ea-eb),exit_price=sign*qa*(xb-xa),quantity_interaction=sign*(qb-qa)*(xb-eb),fees=a['ledger']['fees']-b['ledger']['fees'],funding=b['ledger']['funding']-a['ledger']['funding'])
        if abs(sum(pieces.values())-x['net_delta'])>1e-7:raise ValueError('paired PnL decomposition mismatch')
        decomposed.append(dict(key=x['key'],pair=x['pair'],available_at=x['at'],pieces=pieces,net_delta=x['net_delta'],price_improvement_ticks=x['price_improvement_ticks'],
            price_improvement_bp=x['price_improvement_bp'],price_improvement_atr=x['price_improvement_atr'],quantity_equal=x['quantity_equal'],exit_time_equal=x['exit_time_equal'],exit_price_equal=x['exit_price_equal'],
            label='ARITHMETIC_ATTRIBUTION_OF_TWO_NATIVE_RESULTS;NOT_A_RECONSTRUCTED_PORTFOLIO'))
    write(OUT/'passive-pnl-decomposition.json',decomposed)
    barriers=[]
    for x in read(OUT/'obstacle-audit.json'):
        at=pd.Timestamp(x['at']);sign=1 if x['side']=='long' else -1;date=at-pd.Timedelta(minutes=15);r=feature(x['pair'],'new').loc[date];items=[]
        for level in x['obstacles']:
            past=candles(x['pair']).loc[lambda f:(f.date>=pd.Timestamp(level['known_at']))&(f.date+pd.Timedelta(minutes=15)<=date)]
            reaction=sign*(level['price']-(past.low.min() if sign==1 else past.high.max()))/r.atr14 if len(past) else None
            has_reaction=reaction is not None and reaction>=1.
            usable=level['active'] is not False and (level['timeframe']!='15m' or has_reaction)
            items.append(dict(**level,pre_entry_opposing_reaction_atr=reaction,
                diagnostic_relevance='CREDIBLE_PARENT_OR_PRIOR_1ATR_REACTION' if usable else 'CONSUMED_OR_LOCAL_WITHOUT_PRIOR_1ATR_REACTION',
                consumer='DIAGNOSTIC_ONLY;ORIGINAL_TARGET_ADMISSION_UNCHANGED'))
        relevant=[z for z in items if z['diagnostic_relevance']=='CREDIBLE_PARENT_OR_PRIOR_1ATR_REACTION']
        first=relevant[0] if relevant else None
        barriers.append(dict(**{k:v for k,v in x.items() if k!='obstacles'},obstacles=clean(items),diagnostic_first_relevant=first,
            significance_caveat='One1ATR prior reaction is a frozen descriptive hypothesis, not validated resistance or permission to skip actual obstacles.'))
    write(OUT/'obstacle-relevance.json',clean(barriers))
    structural=[];contracts=read(PARENT/'contracts.json')
    for r in read(OUT/'trade-forensics.json'):
        g=r['plan'];pair=r['trade']['pair'];sign=1 if g['side']=='long' else -1
        if r['source_strategy']=='structural' and g['recipe']=='continuation':
            line=g['boundary']-sign*.15*g['atr_at_signal']
            structural.append(dict(key=r['key'],pair=pair,side=g['side'],entry=g['reference'],hard_stop=g['stop'],frozen_zone=g['boundary'],failure_close_line=line,
                directional_line_to_stop_atr=sign*(line-g['stop'])/g['atr_at_signal'],compatible_before_stop=compatible_thesis(g,contracts[pair]['price_precision']),
                grade='OBSERVED_MECHANISM',reason='Buffered failure boundary is geometrically reachable before stop' if compatible_thesis(g,contracts[pair]['price_precision']) else 'Hard stop reached before required adverse close; structural rule cannot provide earlier protection',
                original_exit=r['trade']['exit_reason']))
    write(OUT/'thesis-compatibility.json',structural)
    records=read(OUT/'trade-forensics.json');entry=[]
    for x in records:
        g=x['plan'];pair=x['trade']['pair'];at=pd.Timestamp(g['available_at']);sign=1 if g['side']=='long' else -1
        f=feature(pair);signal=at-pd.Timedelta(minutes=15)
        prior=f.loc[(f.date<signal)&(f.date>=signal-pd.Timedelta(hours=1))];touches=[]
        for _,r in prior.iterrows():
            touched=(r.low<=max(r.ema20,r.vwap)+.35*r.atr14 and r.close>=r.ema50-r.atr14) if sign==1 else (r.high>=min(r.ema20,r.vwap)-.35*r.atr14 and r.close<=r.ema50+r.atr14)
            if touched:touches.append(dict(observed_at=(r.date+pd.Timedelta(minutes=15)).isoformat(),ema20=float(r.ema20),vwap=float(r.vwap),low=float(r.low),high=float(r.high),
                reference_fidelity='COMPLETED_TOUCH_BAR_REFERENCE;NOT_A_PRE_REGISTERED_V4_ZONE'))
        entry.append(dict(key=x['key'],strategy=x['source_strategy'],pair=pair,opportunity_valid_at=g.get('setup_armed_at',g['available_at']),confirmation_at=g['available_at'],
            previous_observed_touch_events=touches,time_from_earliest_observed_touch_minutes=(at-pd.Timestamp(touches[0]['observed_at'])).total_seconds()/60 if touches else None,
            stop_distance_atr=sign*(x['trade']['open_rate']-g['stop'])/g['atr_at_signal'],target_distance_atr=sign*(g['target']-x['trade']['open_rate'])/g['atr_at_signal'],
            native_order=x['native_entry_order'],known_at_caveat='Actual V4 opportunity is the completed signal; earlier touches are reconstructed observations, not originally registered setup IDs'))
    write(OUT/'entry-context.json',entry)
    discriminator={}
    v4=[x for x in records if x['source_strategy']=='v4']
    for field,orientation in [('adx',1),('rvol',1),('signal_body_atr',1),('extension_from_pullback_atr',-1),('signed_distance_vwap_atr',-1),('signed_relative_btc',1)]:
        discriminator[field]={}
        for label,month in [('september','2026-09'),('october_november',None)]:
            q=[x for x in v4 if (x['plan']['available_at'].startswith(month) if month else not x['plan']['available_at'].startswith('2026-09')) and x['decision_time'][field] is not None]
            discriminator[field][label]=dict(fills=len(q),winners=sum(x['ledger']['net']>0 for x in q),auc=auc([orientation*x['decision_time'][field] for x in q],[x['ledger']['net']>0 for x in q]))
    write(OUT/'chronological-feature-separability.json',dict(features=discriminator,orientation='Fixed natural direction: largerADX/volume/body/relative strength, lowerextension/distance',
        interpretation='DESCRIPTIVE_REPEATEDLY_INSPECTED_DEVELOPMENT;NO_FITTED_FILTER_OR_INDEPENDENT_OUT_OF_SAMPLE_EDGE_CLAIM'))
    summary=dict(passive_arithmetic_parts={k:sum(x['pieces'][k] for x in decomposed) for k in decomposed[0]['pieces']},
        passive_exit_prices_changed=sum(not x['exit_price_equal'] for x in decomposed),passive_quantities_changed=sum(not x['quantity_equal'] for x in decomposed),
        unreachable_structural_failures=sum(not x['compatible_before_stop'] for x in structural),continuation_structural_fills=len(structural),
        selected_obstacle_relevance=dict(Counter(x['obstacles'][0]['diagnostic_relevance'] if x['obstacles'] else 'MISSING' for x in barriers if x['selected'])),
        geometry_pass_shortlist_exclusions=[dict(key=x['key'],pair=x['pair'],side=x['side'],at=x['at'],rank=x['ranking']['rank'],top3=x['ranking']['top3'],
            source_liquidity_eligible=state_at(x['pair'],dict(available_at=x['at'],side=x['side']))['liquidity_eligible']) for x in barriers if x['original_reason']=='PASS'],
        stops='No stop widening is supported by these outcomes; post-exit bounces are hindsight diagnostics',
        target_findings='Fixed3R sometimes traverses local levels; neither a touched local swing nor a distant3R establishes expected executable profit',
        statistical_edge='Winner/loser feature distributions overlap; independent discriminatory ability remains unestablished')
    write(OUT/'deep-summary.json',clean(summary));print(summary,flush=True)

if __name__=='__main__':run()
