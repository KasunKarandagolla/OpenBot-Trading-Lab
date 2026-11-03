"""Trade economics and matched opportunity paths; these are diagnostics, not portfolios."""
from collections import defaultdict,Counter
import math
import numpy as np
import pandas as pd
import talib.abstract as ta
from recovery_common import *

def interval(x, draws=2000):
    x=np.asarray(x,float); n=len(x)
    if not n:return [None,None]
    rng=np.random.default_rng(4103)
    idx=(rng.integers(0,n,(draws,math.ceil(n/7),1))+np.arange(7))%n
    return np.quantile(x[idx.reshape(draws,-1)[:,:n]].sum(axis=1),[.025,.975]).tolist()

def ledger_diagnosis():
    result={}
    for label in ['reference','structure','reference-risk','structure-risk','structure-open','structure-through','structure-market','hour']:
        d=pd.DataFrame(read(ROOT/'evidence/session4/run-001/trade-ledgers'/(label+'.json')))
        w=d.loc[d.net_usdt>0,'net_usdt'];l=d.loc[d.net_usdt<=0,'net_usdt']
        groups={k:{str(s):dict(n=len(q),net=float(q.net_usdt.sum()),mean_bp=float(q.net_entry_bp.mean()),
                     stress10=float(sum(r['10'] for r in q.stresses))) for s,q in d.groupby(k)}
                for k in ['recipe','side','regime','hour_structure','exit_reason']}
        result[label]=dict(n=len(d),gross=float(d.gross_usdt.sum()),fees=float(d.fees_usdt.sum()),funding=float(d.funding_usdt.sum()),
            net=float(d.net_usdt.sum()),stress10=float(sum(r['10'] for r in d.stresses)),mean_trade_bp=float(d.net_entry_bp.mean()),
            sum_net_stop_R=float(d.net_stop_R.sum()),mean_risk_fraction=float((d.stop_risk_usdt/d.entry_notional).mean()),
            net_bp_vs_stop_risk_correlation=float(d.net_entry_bp.corr(d.stop_risk_usdt/d.entry_notional)),
            cost_to_gross=float(d.fees_usdt.sum()/d.gross_usdt.sum()),extra_break_even_bp_per_side=float(d.net_usdt.sum()/(d.entry_notional.sum()+d.exit_notional.sum())*1e4),
            without_top3=float(d.net_usdt.sum()-d.net_usdt.nlargest(3).sum()),positive_top3_share=float(w.nlargest(3).sum()/w.sum()),
            win_rate=len(w)/len(d),mean_win=float(w.mean()),mean_loss=float(l.mean()),median_hold_minutes=float(d.hold_minutes.median()),groups=groups)
    # Reweight the SAME structure fills before allowing native sizing to change feasibility/cooldowns.
    d=pd.DataFrame(read(ROOT/'evidence/session4/run-001/trade-ledgers/structure.json'))
    risk=d.stop_risk_usdt/d.entry_notional+.0038
    weights=np.minimum(50.,.25/risk)/d.entry_notional
    result['same_fills_reweighted_structure']=dict(native=d.net_usdt.sum(),constant_modeled_risk_net=float((d.net_usdt*weights).sum()),
        equal_entry_notional_25_net=float((d.net_usdt*25/d.entry_notional).sum()),
        warning='Reweighting attribution only; official risk portfolio has different lot eligibility and sequence.')
    result['selection_funnel']=read(ROOT/'evidence/session4/run-001/selection-summary.json')
    write(OUT/'ledger-diagnosis.json',result)
    return result

def load_lite():
    frames={}
    for pair in pairs():
        base=DATA/'development/gate/futures'/slug(pair)
        d=pd.read_feather(str(base)+'-15m-futures.feather')
        h=pd.read_feather(str(base)+'-1h-futures.feather')
        h['bias']=np.sign(ta.EMA(h,timeperiod=20)-ta.EMA(h,timeperiod=50));h['adx']=ta.ADX(h,timeperiod=14)
        h['known']=h.date+pd.Timedelta(hours=1)
        d['known']=d.date+pd.Timedelta(minutes=15)
        d=pd.merge_asof(d.sort_values('known'),h[['known','bias','adx']],on='known',direction='backward')
        d['atr']=ta.ATR(d,timeperiod=14);d['atr_ratio']=d.atr/d.close
        # Broad, causal volatility bins avoid outcome-derived breakpoints.
        d['volbin']=pd.cut(d.atr_ratio,[0,.002,.004,.008,np.inf],labels=False)
        q=d.volume*(d.high+d.low+d.close)/3;day=d.date.dt.floor('D')
        daily=q.groupby(day).sum();counts=d.groupby(day).size();v=daily.where(counts==96).shift()
        d['eligible']=day.map(v).ge(1e7)&day.map(v.rolling(7,min_periods=7).mean()).ge(1e7)&(d.date>=d.date.iloc[0]+pd.Timedelta(days=10))
        d['ret24']=d.close.pct_change(96);d['ret4']=d.close.pct_change(16)
        frames[pair]=d
    return frames

def path(d,i,sign,risk,reward,hours):
    n=int(hours*4)
    if i<0 or i+n>=len(d):return None
    # Decision is at this candle OPEN. Only subsequent observed OHLC determines outcomes.
    e=float(d.open.iloc[i]);q=d.iloc[i:i+n]
    hi=sign*(q.high.to_numpy()/e-1);lo=sign*(q.low.to_numpy()/e-1)
    favorable=np.maximum(hi,lo);adverse=np.minimum(hi,lo)
    stop=adverse<=-risk;target=favorable>=reward
    s=int(np.flatnonzero(stop)[0]) if stop.any() else n
    t=int(np.flatnonzero(target)[0]) if target.any() else n
    hit='AMBIGUOUS_STOP_FIRST' if s==t and s<n else 'STOP_FIRST' if s<t else 'TARGET_FIRST' if t<s else 'NEITHER'
    cost=np.flatnonzero(favorable>=.0035)
    return dict(return_bp=float(sign*(d.close.iloc[i+n-1]/e-1)*1e4),mfe_bp=float(favorable.max()*1e4),
        mae_bp=float(adverse.min()*1e4),barrier=hit,first_favorable_35bp_minutes=int(cost[0]*15) if len(cost) else None,
        endpoint_after35bp_bp=float(sign*(d.close.iloc[i+n-1]/e-1)*1e4-35),
        barrier_payoff_bp=float((reward if hit=='TARGET_FIRST' else -risk if 'STOP' in hit else sign*(d.close.iloc[i+n-1]/e-1))*1e4-35))

def summarize(rows):
    if not rows:return dict(n=0)
    d=pd.DataFrame(rows); out=dict(n=len(d))
    for k in ['return_bp','mfe_bp','mae_bp','endpoint_after35bp_bp','barrier_payoff_bp']:
        out[k]=dict(mean=float(d[k].mean()),median=float(d[k].median()),p10=float(d[k].quantile(.1)),p90=float(d[k].quantile(.9)))
    out['barrier_probabilities']=d.barrier.value_counts(normalize=True).to_dict()
    out['favorable35bp_probability']=float(d.first_favorable_35bp_minutes.notna().mean())
    out['median_minutes_to35bp_conditional']=float(d.first_favorable_35bp_minutes.median()) if d.first_favorable_35bp_minutes.notna().any() else None
    # Jeffreys shrinkage; setup-level uncertainty also depends on shared weeks.
    k=int(d.barrier.eq('TARGET_FIRST').sum());n=len(d)
    from scipy.stats import beta
    out['target_first_shrunk']=(k+.5)/(n+1);out['target_first_beta95']=beta.ppf([.025,.975],k+.5,n-k+.5).tolist()
    success=d.loc[d.barrier.eq('TARGET_FIRST'),'barrier_payoff_bp']
    failure=d.loc[~d.barrier.eq('TARGET_FIRST'),'barrier_payoff_bp']
    out['mean_net_payoff_if_target_first_bp']=float(success.mean()) if len(success) else None
    out['mean_net_payoff_otherwise_bp']=float(failure.mean()) if len(failure) else None
    out['transaction_cost_assumption_bp']=35
    if 'risk_fraction' in d:
        out['mean_geometry_binary_break_even_target_probability']=float(((d.risk_fraction+.0035)/(d.risk_fraction+d.reward_fraction)).mean())
        out['break_even_caveat']='Binary target/stop comparison only;NEITHER observations use actual endpoint payoff in empirical expectancy.'
    out['probability_warning']='Descriptive marginal estimate; overlapping opportunities and market dependence invalidate iid qualification.'
    return out

def opportunities():
    frames=load_lite(); records=[]; nulls=defaultdict(lambda:np.zeros(199)); rng=np.random.default_rng(4103);coverage=Counter()
    # All four mechanisms use pre-decision inputs. Outcomes remain diagnostic.
    pools={}
    for pair,d in frames.items():
        # Match on the completed SIGNAL row; entry is the following candle open.
        for key,g in d.loc[d.eligible & (d.date>=pd.Timestamp('2026-08-05',tz='UTC'))].groupby([d.date.dt.month,d.date.dt.hour,'bias','volbin']):pools[(pair,*key)]=g.index.to_numpy()+1
    for o in read(ROOT/'evidence/session4/run-001/opportunities.json'):
        if o['variant'] not in ('reference','structure'):continue
        population=o['variant']+':'+o['recipe']+':'+str(o['reason']=='TRADE')
        coverage[population+':raw_records']+=1
        if not o['plan']:coverage[population+':no_valid_geometry']+=1;continue
        pair=o['symbol'];d=frames[pair];at=pd.Timestamp(o['at']);ix=d.index[d.date.eq(at)]
        if not len(ix):coverage[population+':no_following_source_bar']+=1;continue
        i=int(ix[0]);r=d.iloc[i-1];g=o['plan'];sign=1 if o['side']=='long' else -1
        risk=g['risk_fraction'];reward=sign*(g['target']-g['reference'])/g['reference'];hours=g['max_hold_hours']
        actual=path(d,i,sign,risk,reward,hours)
        if actual is None:coverage[population+':incomplete_outcome_horizon']+=1;continue
        key=(pair,r.date.month,r.date.hour,r.bias,r.volbin)
        pool=pools.get(key,np.array([],int));pool=pool[(pool+hours*4<len(d))&(np.abs(pool-i)>=32)]
        if len(pool)<8:coverage[population+':fewer_than8_matched_control_times']+=1;continue
        coverage[population+':included']+=1
        draws=rng.choice(pool,199,replace=True)
        control_returns=sign*(d.close.to_numpy()[draws+int(hours*4)-1]/d.open.to_numpy()[draws]-1)*1e4
        control_mean=float(control_returns.mean())
        btc=frames['BTC/USDT:USDT'].iloc[i-1]
        row=dict(variant=o['variant'],pair=pair,at=o['at'],recipe=o['recipe'],side=o['side'],selected=o['reason']=='TRADE',reason=o['reason'],
            risk_fraction=risk,reward_fraction=reward,hours=hours,regime=o['regime'],hour_structure=o['hour_structure'],fvg_retest=o['fvg_retest'],
            btc_aligned=bool(sign*btc.ret4>0),relative_aligned=bool(sign*(r.ret4-btc.ret4)>0),volbin=int(r.volbin),
            next_open_gap_bp=float(sign*(d.open.iloc[i]/g['reference']-1)*1e4),**actual,
            matched_time_return_bp=control_mean,timing_lift_bp=actual['return_bp']-control_mean,
            direction_flip_return_bp=-actual['return_bp'])
        for h in [1,2,4,8]:
            p=path(d,i,sign,risk,reward,h)
            if p:row['return_'+str(h)+'h_bp']=p['return_bp']
        records.append(row)
        group=o['variant']+':'+o['recipe']+':'+str(row['selected'])
        nulls[group]+=control_returns
    write(OUT/'opportunity-paths.json',records)
    result={};df=pd.DataFrame(records)
    for keys,g in df.groupby(['variant','recipe','selected']):
        label=keys[0]+':'+keys[1]+':'+str(keys[2]);n=len(g)
        item=summarize(g.to_dict('records'));item['time_control_mean_bp']=float(g.matched_time_return_bp.mean())
        item['timing_lift_bp']=float(g.timing_lift_bp.mean());item['direction_flip_mean_bp']=float(g.direction_flip_return_bp.mean())
        s=nulls[label]/n;item['matched_time_null_199']=dict(seeds=199,p_resolution=1/200,upper_p=float((1+(s>=g.return_bp.mean()).sum())/200),p5_p95=np.quantile(s,[.05,.95]).tolist())
        daily=g.groupby(pd.to_datetime(g['at']).dt.floor('D')).timing_lift_bp.sum().reindex(pd.date_range('2026-08-05','2026-11-02',tz='UTC'),fill_value=0)
        item['week_block95_lift_mean_bp']=[x/n for x in interval(daily)]
        item['subgroups']={key:{str(k):summarize(q.to_dict('records')) for k,q in g.groupby(key)} for key in ['btc_aligned','relative_aligned','regime','fvg_retest','volbin']}
        result[label]=item
    write(OUT/'opportunity-diagnosis.json',dict(populations=result,coverage=dict(coverage),matched_control='Same asset, month, UTC hour, completed-hour EMA bias and fixed ATR-ratio bin; exclude +-8hours; causal eligible bars;199 seeded matched draws per opportunity',
        execution='NEXT_OPEN_PATH_DIAGNOSTICS; OHLC ordering ambiguous => stop-first; not official portfolios or five-minute fill estimates',
        limitations=['Matched controls do not establish causality','Historical flow UNKNOWN; profiles are OHLCV_PROXY','Old opportunity sampling is inspected development','Time matching does not force identical signal count per calendar day','Conditional planned-opportunity population;invalid geometry is in the funnel but excluded from barrier tests','First favorable movement time is the START of the first qualifying15m bar,not an observed tick time']))
    print(df.groupby(['variant','recipe','selected']).agg(n=('return_bp','size'),mean_bp=('return_bp','mean'),timing_lift=('timing_lift_bp','mean'),barrier_net35=('barrier_payoff_bp','mean')).to_string(),flush=True)

if __name__=='__main__':
    ledger_diagnosis()
    if len(sys.argv)>1 and sys.argv[1]=='paths':opportunities()
