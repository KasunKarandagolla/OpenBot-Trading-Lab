"""Existing selection primitives, causal v3 lanes and complete opportunity ledger."""
from collections import Counter
import json
import numpy as np
import pandas as pd
from policy_common import *


def analyzed(b,h,symbol,cfg):
    from PolicyV3 import PolicyFixedV3
    from freqtrade.strategy import merge_informative_pair
    s=PolicyFixedV3(cfg)
    hourly=s.populate_indicators_1h(h,{'pair':symbol})
    return s.populate_indicators(merge_informative_pair(b,hourly,'15m','1h',ffill=True),{'pair':symbol})


def schedule(run_id):
    from bonus_pipeline import ranking
    from policy_features import raw_signals,suitability,plan
    from PolicyV3 import PolicyFixedV3
    from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
    from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
    from freqtrade.enums import CandleType
    out,data,spec=verify(run_id)
    if (out/'opportunity-ledger.json').exists():raise ValueError('preserve schedule')
    cfg=read(config(run_id,'PolicyFixedV3'))|{'candle_type_def':CandleType.FUTURES}
    bases={s:frame(data,s) for s in spec['pairs']}; _,absolute=ranking(bases)
    write(out/'absolute-schedule.json',dict(decisions=absolute))
    btc=bases['BTC/USDT:USDT'].set_index('date').close.pct_change(16)
    frames={}; pieces=[]; oldpieces=[];diagnosis=[]
    for symbol,b in bases.items():
        d=analyzed(b,frame(data,symbol,'1h'),symbol,cfg);frames[symbol]=d
        signals=raw_signals(d,PolicyFixedV3(cfg).validity(d))
        relative=d.close.pct_change(16).to_numpy()-btc.reindex(d.date).to_numpy()
        if symbol=='BTC/USDT:USDT':relative=d.close.pct_change(16).to_numpy()
        quote=d.volume*(d.high+d.low+d.close)/3
        activity=quote.rolling(16).sum()/quote.shift(16).rolling(16).sum();volume=quote.rolling(96).sum()
        for (recipe,side),mask in signals.items():
            sign=1 if side=='long' else -1;aligned=sign*(d.ema20_1h-d.ema50_1h)>0
            eligible=(volume>=1e7)&np.isfinite(relative)&d.contiguous&(aligned if recipe=='continuation' else mask)
            score=sign*relative+.01*activity.clip(upper=3) if recipe=='continuation' else sign*(d.close-(d.prior_low if sign==1 else d.prior_high))/d.atr14
            pieces.append(pd.DataFrame(dict(symbol=symbol,at=(d.date+pd.Timedelta(minutes=15)).astype(str),lane=recipe+':'+side,
                eligible=eligible,setup=mask,score=score,quote_volume24h=volume,relative_return4h=relative)))
        parents={recipe:cls(cfg).populate_entry_trend(d.copy(),{'pair':symbol}) for recipe,cls in [('vwap',VWAPTrendContinuationV1),('sweep',LiquiditySweepReversalV1)]}
        for recipe,p in parents.items():
            for side,sign in [('long',1),('short',-1)]:
                aligned=sign*(d.ema20_1h-d.ema50_1h)>0;failed=p['enter_'+side].eq(1)
                eligible=(volume>=1e7)&np.isfinite(relative)&d.contiguous&(aligned if recipe=='vwap' else failed)
                score=sign*relative+.01*activity.clip(upper=3) if recipe=='vwap' else sign*(d.close-(d.prior_low if sign==1 else d.prior_high))/d.atr14
                oldpieces.append(pd.DataFrame(dict(symbol=symbol,at=(d.date+pd.Timedelta(minutes=15)).astype(str),lane=recipe+':'+side,eligible=eligible,score=score)))
                if recipe=='vwap':
                    # Raw parent candidates BEFORE its favorable historical 2R
                    # geometry gate; exposes the full continuation bottleneck.
                    for _,r in p.loc[p['candidate_'+side].eq(1)].iterrows():
                        from intelligence_features import research_plan,COST
                        risk=sign*(r.close-(r.low-.2*r.atr14 if sign==1 else r.high+.2*r.atr14))/r.close
                        diagnosis.append(dict(symbol=symbol,at=(r.date+pd.Timedelta(minutes=15)).isoformat(),side=side,
                            risk_fraction=float(risk),fixed2r_net_rr=float((2*risk-COST)/(risk+COST)),
                            v2_plan_pass=research_plan(r,'vwap',side) is not None,
                            reason='NET_RR_REQUIRES_STOP_AT_LEAST_1.14_PERCENT' if risk<.0114 else 'CHECK_OTHER_GEOMETRY_OR_ROUTING',
                            atr_fraction=float(r.atr14/r.close)))
    def make_schedule(pieces,old=False):
        ranking=pd.concat(pieces,ignore_index=True); decisions={}
        for at,g in ranking.groupby('at',sort=True):
            stamp=pd.Timestamp(at).isoformat();slots={}
            for lane,part in g.groupby('lane'):
                slots[lane]=part.loc[part.eligible].sort_values(['score','symbol'],ascending=[False,True]).symbol.head(3).tolist()
            decisions[stamp]=dict(slots=slots) if old else slots
        return ranking,decisions
    ranks,decisions=make_schedule(pieces);_,old=make_schedule(oldpieces,True)
    write(out/'policy-schedule.json',dict(decisions=decisions,membership='FIXED_CURRENT_SURVIVORS_NOT_HISTORICAL_MEMBERSHIP'))
    write(out/'signed-schedule.json',dict(decisions=old))
    ranks.loc[ranks.setup|~ranks.eligible].to_csv(out/'selection-ledger.csv',index=False)
    records=[];start,end=[pd.to_datetime(x,format='%Y%m%d',utc=True) for x in spec['evaluation_timerange'].split('-')]
    import PolicyV3 as variants
    from IntelligenceRouterV2 import IntelligenceRegimeV2
    for symbol,d in frames.items():
        for name in [n for n in spec['variants'] if n.startswith('Policy')]+['IntelligenceRegimeV2']:
            s=getattr(variants,name)(cfg) if name.startswith('Policy') else IntelligenceRegimeV2(cfg)
            r=s.populate_entry_trend(d.copy(),{'pair':symbol})
            mask=r.parent_candidate.eq(1)&(r.date+pd.Timedelta(minutes=15)>=start)&(r.date+pd.Timedelta(minutes=15)<end)
            for _,row in r.loc[mask].iterrows():
                at=row.date+pd.Timedelta(minutes=15)
                details=json.loads(row.policy_details if name.startswith('Policy') else row.candidate_details)
                for item in details:
                    reason=item['reason'];side=item['side'];recipe=item['recipe']
                    contrary=['HISTORICAL_FLOW_NEWS_QUEUE_UNKNOWN']
                    if row.get('struct_direction_1h')==('UP' if side=='short' else 'DOWN'):contrary.append('OPPOSING_CONFIRMED_HOURLY_STRUCTURE_SHADOW')
                    if item['plan']:contrary+=item['plan'].get('cautions',[])
                    g=item['plan']
                    if g and reason=='TRADE':
                        g=g|dict(decision_id=f'{symbol}:{recipe}:{side}:{at.isoformat()}')
                    records.append(dict(schema_version=1,variant=name,decision_id=f'{run_id}:{name}:{symbol}:{recipe}:{side}:{at.isoformat()}',
                        environment='BACKTEST_RESEARCH',venue='gate',symbol=symbol,recipe=recipe,side=side,available_at=at.isoformat(),
                        expires_at=(at+pd.Timedelta(minutes=5)).isoformat(),observed_at=None,status='RESEARCH_CANDIDATE' if reason=='TRADE' else 'WATCH' if reason.startswith('WATCH') else 'REJECT',
                        reason=reason,geometry=g,regime='TREND' if row.adx_1h>=25 else 'WEAK_TREND_OR_RANGE',adx_1h=float(row.adx_1h),
                        orderflow=dict(status='UNKNOWN',reason='NO_GENUINE_HISTORICAL_SOURCE'),
                        profile=dict(fidelity='OHLCV_PROXY',poc=float(row.vp2_poc) if pd.notna(row.vp2_poc) else None),
                        opposing_evidence=[dict(evidence_id=f'{symbol}:{at.isoformat()}:{i}',reason=c) for i,c in enumerate(contrary)],
                        data_gaps=['PIT_MEMBERSHIP_UNKNOWN','ORIGINAL_RECEIPT_CLOCK_UNKNOWN','HISTORICAL_FLOW_NEWS_QUEUE_UNKNOWN'],orders_created=False))
    write(out/'opportunity-ledger.json',dict(records=records,by_variant={n:dict(Counter(r['reason'] for r in records if r['variant']==n)) for n in spec['variants']},
        selection=dict(market_time_rows=len(ranks),eligible=int(ranks.eligible.sum()),setup_lanes=int(ranks.setup.sum()))))
    write(out/'continuation-diagnosis.json',dict(raw_parent_signals=diagnosis,net_rr_required_risk=.0114,
        interpretation='2R with net RR1.25 and cost0.0038 requires risk >=0.0114. New3R requires >=0.004885714; thresholds/costs unchanged, target ambition explicitly increased and horizon bounded.'))
    print('V3 opportunity ledger',len(records),dict(Counter(r['reason'] for r in records)),flush=True)


def assess(run_id):
    from freqtrade.enums import CandleType
    from intelligence_features import executable_contract
    from policy_features import raw_signals,suitability,plan
    from PolicyV3 import PolicyFixedV3
    out,data,spec=verify(run_id);scan=read(out/'scan.json');ex=public();markets=ex.load_markets()
    asof=pd.Timestamp.now(tz='UTC');symbols=list(dict.fromkeys(['BTC/USDT:USDT']+[r['symbol'] for r in scan['shortlisted'][:20]]));cheap=[];bars={}
    for symbol in symbols:
        raw=ex.fetch_ohlcv(symbol,'15m',limit=120);f=pd.DataFrame(raw,columns=['date','open','high','low','close','volume']);f['date']=pd.to_datetime(f.date,unit='ms',utc=True)
        f=f.loc[f.date+pd.Timedelta(minutes=15)<=asof].reset_index(drop=True);bars[symbol]=f
        write(data.parent/'current'/(symbol.split('/')[0]+'-cheap.json'),dict(observed_at=now(),rows=raw))
    btcret=float(bars['BTC/USDT:USDT'].close.iloc[-1]/bars['BTC/USDT:USDT'].close.iloc[-17]-1)
    for symbol in symbols:
        if symbol not in [r['symbol'] for r in scan['shortlisted'][:20]]:continue
        f=bars[symbol];r=f.iloc[-1];ret=float(f.close.iloc[-1]/f.close.iloc[-17]-1);relative=ret-btcret if not symbol.startswith('BTC/') else ret
        side='long' if ret>=0 else 'short';sign=1 if side=='long' else -1
        failed=bool(r.low<f.low.iloc[-21:-1].min()<r.close or r.high>f.high.iloc[-21:-1].max()>r.close)
        activity=float(f.volume.iloc[-16:].sum()/max(f.volume.iloc[-32:-16].sum(),1e-12))
        cheap.append(dict(symbol=symbol,side=side,signed_score=sign*relative+.01*min(activity,3),boundary_failure=failed))
    cheap.sort(key=lambda r:(not r['boundary_failure'],-r['signed_score'],r['symbol']));deep=cheap[:5]
    write(out/'deep-shortlist.json',dict(cheap=cheap,deep=deep,budget=5))
    cfg=read(config(run_id,'PolicyManagedV3'))|{'candle_type_def':CandleType.FUTURES};records=[]
    for candidate in deep:
        symbol=candidate['symbol']
        try:
            frames={}
            for tf,step in [('15m',pd.Timedelta(minutes=15)),('1h',pd.Timedelta(hours=1))]:
                raw=ex.fetch_ohlcv(symbol,tf,limit=300);f=pd.DataFrame(raw,columns=['date','open','high','low','close','volume']);f['date']=pd.to_datetime(f.date,unit='ms',utc=True)
                frames[tf]=f.loc[f.date+step<=asof].reset_index(drop=True)
                write(data.parent/'current'/(symbol.split('/')[0]+'-'+tf+'.json'),dict(received_at=now(),rows=raw))
            d=analyzed(frames['15m'],frames['1h'],symbol,cfg);s=PolicyFixedV3(cfg);signals=raw_signals(d,s.validity(d));row=d.iloc[-1];at=row.date+pd.Timedelta(minutes=15)
            book=ex.fetch_order_book(symbol,limit=20,params={'with_id':True});received=pd.Timestamp.now(tz='UTC').timestamp()*1000
            quote=dict(source_timestamp_ms=book.get('timestamp'),received_ms=received,spread=1-book['bids'][0][0]/book['asks'][0][0])
            for (recipe,side),mask in signals.items():
                active=bool(mask.iloc[-1]);g,reason=plan(row,recipe,side) if active else (None,'WAIT_CLOSED_CONTROLLED_PULLBACK' if recipe=='continuation' else 'WAIT_FAILED_BOUNDARY_REJECTION')
                if active and suitability(row,recipe,side)!='MATCH':reason=suitability(row,recipe,side)
                records.append(dict(schema_version=1,decision_id=f'{run_id}:current:{symbol}:{recipe}:{side}:{at.isoformat()}',venue='gate',symbol=symbol,
                    environment='CURRENT_PUBLIC_RESEARCH',status='RESEARCH_CANDIDATE' if active and reason=='TRADE' else 'WATCH',reason=reason,
                    recipe=recipe,side=side,available_at=at.isoformat(),expires_at=(at+pd.Timedelta(minutes=5)).isoformat(),observed_at=now(),geometry=g,
                    structure=dict(prior_boundary_low=float(row.prior_low),prior_boundary_high=float(row.prior_high),boundary_known_at=str(row.date)),
                    profile=dict(fidelity='OHLCV_PROXY',poc=float(row.vp2_poc)),quote=quote,
                    execution_feasibility=executable_contract(markets[symbol],float(row.close),25),
                    opposing_evidence=[dict(evidence_id=f'contrary:{symbol}:{recipe}:{side}',reason='EXECUTION_ACCOUNT_NEWS_AND_QUEUE_REQUIRE_QUALIFICATION')],
                    execution_status='NO_TRADE',risk_verdict='CURRENT_ACCOUNT_UNAVAILABLE_RESEARCH_ONLY',data_gaps=['CURRENT_ACCOUNT_UNKNOWN','NEWS_UNKNOWN','QUEUE_UNKNOWN'],orders_created=False))
        except Exception as e:
            records.append(dict(schema_version=1,decision_id=run_id+':'+symbol+':error',venue='gate',symbol=symbol,environment='CURRENT_PUBLIC_RESEARCH',status='NO_TRADE',reason='SOURCE_ASSESSMENT_FAILED',error=str(e)[:300],orders_created=False))
    write(out/'opportunities.json',dict(records=records,orders_created=False))
    print('Current deep checks',len(deep),dict(Counter(r['status'] for r in records)),flush=True)
