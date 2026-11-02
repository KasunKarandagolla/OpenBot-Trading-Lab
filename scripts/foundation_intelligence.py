"""Session 2 extension of the existing native research workflow and scanner."""
import csv
import json
import math
import time
from collections import Counter
import pandas as pd
import numpy as np
from foundation_common import *


def analyzed(bars,hourly,symbol,cfg):
    from IntelligenceRouterV2 import IntelligenceRegimeV2
    from freqtrade.strategy import merge_informative_pair
    s=IntelligenceRegimeV2(cfg)
    h=s.populate_indicators_1h(hourly,{'pair':symbol})
    return s.populate_indicators(merge_informative_pair(bars,h,'15m','1h',ffill=True),{'pair':symbol})


def schedule(run_id):
    from foundation_native import schedule as original
    from IntelligenceRouterV2 import IntelligenceCostV2
    from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
    from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
    from freqtrade.enums import CandleType
    original(run_id)  # Preserve actual legacy ranking and parent candidate ledger.
    out,data,spec=verify(run_id)
    cfg=read(config(run_id,'IntelligenceRegimeV2'))|{'candle_type_def':CandleType.FUTURES}
    bases={s:frame(data,s) for s in spec['pairs']}; features={}; parents={}; rows=[]
    btc=bases['BTC/USDT:USDT'].set_index('date').close.pct_change(16)
    for symbol,b in bases.items():
        d=analyzed(b,frame(data,symbol,'1h'),symbol,cfg); features[symbol]=d
        relative=d.close.pct_change(16).to_numpy()-btc.reindex(d.date).to_numpy()
        if symbol=='BTC/USDT:USDT': relative=d.close.pct_change(16).to_numpy()
        quote=d.volume*(d.high+d.low+d.close)/3
        activity=quote.rolling(16).sum()/quote.shift(16).rolling(16).sum()
        volume=quote.rolling(96).sum()
        parents[symbol]={recipe:cls(cfg).populate_entry_trend(d.copy(),{'pair':symbol}) for recipe,cls in
            [('vwap',VWAPTrendContinuationV1),('sweep',LiquiditySweepReversalV1)]}
        for i,r in d.iterrows():
            at=r.date+pd.Timedelta(minutes=15)
            for side,sign in [('long',1),('short',-1)]:
                aligned=sign*(r.ema20_1h-r.ema50_1h)>0
                for recipe in ('vwap','sweep'):
                    failed=bool(parents[symbol][recipe].at[i,'enter_'+side]==1)
                    eligible=bool(volume.iloc[i]>=1e7 and np.isfinite(relative[i]) and r.contiguous and (aligned if recipe=='vwap' else failed))
                    score=float(sign*relative[i]+.01*min(float(activity.iloc[i]),3)) if eligible and recipe=='vwap' else float(sign*(r.close-(r.prior_low if sign==1 else r.prior_high))/r.atr14) if eligible else None
                    rows.append(dict(symbol=symbol,decision_at=at.isoformat(),recipe=recipe,side=side,eligible=eligible,
                        score=score,relative_return4h=float(relative[i]) if np.isfinite(relative[i]) else None,
                        failed_boundary_confirmed=failed if recipe=='sweep' else None))
    ranking=pd.DataFrame(rows); decisions={}
    for at,group in ranking.groupby('decision_at',sort=True):
        slots={}
        for (recipe,side),lane in group.groupby(['recipe','side']):
            slots[recipe+':'+side]=lane.loc[lane.eligible].sort_values(['score','symbol'],ascending=[False,True]).symbol.head(3).tolist()
        decisions[at]=dict(slots=slots,selected=sorted({s for values in slots.values() for s in values}),
            expensive_market_budget=5,status='ANALYZE' if any(slots.values()) else 'NO_TRADE')
    ranking.to_csv(out/'signed-market-ranking.csv',index=False)
    write(out/'signed-schedule.json',dict(version=2,decisions=decisions,membership=spec['membership'],
        recipe='SIDE_SIGNED_CONTINUATION; OBSERVED_FAILED_BOUNDARY_REVERSAL; TOP3_PER_LANE_MAX5_MARKETS'))
    start,end=[pd.to_datetime(x,format='%Y%m%d',utc=True) for x in spec['evaluation_timerange'].split('-')]
    records=[]
    import IntelligenceRouterV2 as variants
    for symbol,d in features.items():
        for name in [n for n in spec['strategies'] if n.startswith('Intelligence')]:
            s=getattr(variants,name)(cfg); result=s.populate_entry_trend(d.copy(),{'pair':symbol})
            mask=result.parent_candidate.eq(1)&(result.date+pd.Timedelta(minutes=15)>=start)&(result.date+pd.Timedelta(minutes=15)<end)
            for _,r in result.loc[mask].iterrows():
                at=r.date+pd.Timedelta(minutes=15)
                for item in json.loads(r.candidate_details):
                    reason=item['reason']; side=item['side']; recipe=item['recipe']
                    contrary=[]; opposite='DOWN' if side=='long' else 'UP'
                    if r.get('struct_direction_1h')==opposite: contrary.append('OPPOSING_CONFIRMED_HOURLY_STRUCTURE')
                    if recipe=='sweep' and r.adx_1h>=25: contrary.append('STRONG_OPPOSING_CONTINUATION_POSSIBLE')
                    if item['plan']: contrary+=item['plan']['cautions']
                    if not contrary: contrary=['HISTORICAL_EXECUTION_AND_FLOW_UNOBSERVED']
                    records.append(dict(schema_version=1,variant=name,decision_id=f'{run_id}:{name}:{symbol}:{recipe}:{side}:{at.isoformat()}',
                        environment='BACKTEST_RESEARCH',venue='gate',symbol=symbol,available_at=at.isoformat(),expires_at=(at+pd.Timedelta(minutes=5)).isoformat(),
                        observed_at=None,recipe=recipe,side=side,regime='TREND' if r.adx_1h>=25 else 'RANGE_OR_WEAK_TREND',adx_1h=float(r.adx_1h),
                        status='RESEARCH_CANDIDATE' if reason=='TRADE' else 'WATCH' if reason.startswith('WATCH') else 'REJECT',reason=reason,
                        geometry=item['plan'],structure=dict(hourly_direction=r.get('struct_direction_1h'),local_direction=r.struct_direction,known_at=str(r.struct_known_at)),
                        profile=dict(fidelity='OHLCV_PROXY',poc=None if pd.isna(r.vp2_poc) else float(r.vp2_poc),val=None if pd.isna(r.vp2_val) else float(r.vp2_val),vah=None if pd.isna(r.vp2_vah) else float(r.vp2_vah),known_at=str(r.vp2_known_at)),
                        orderflow=dict(status='UNKNOWN',reason='NO_GENUINE_HISTORICAL_TRADES'),
                        opposing_evidence=[dict(evidence_id=f'{symbol}:{at.isoformat()}:{c}',reason=c,assessment='CAUTION_REQUIRES_REVIEW') for c in contrary],
                        data_gaps=['PIT_MEMBERSHIP_UNKNOWN','HISTORICAL_FLOW_NEWS_DEPTH_QUEUE_UNKNOWN','ORIGINAL_RECEIPT_CLOCK_UNKNOWN'],orders_created=False))
    write(out/'intelligent-opportunities.json',dict(version=2,records=records,by_variant={n:dict(Counter(r['reason'] for r in records if r['variant']==n)) for n in spec['strategies'] if n.startswith('Intelligence')}))
    print('Signed schedule:',len(decisions),'closes;',len(records),'candidate-arm records',flush=True)


def assess(run_id):
    from freqtrade.enums import CandleType
    from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
    from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
    from intelligence_features import match,research_plan
    out,data,spec=verify(run_id); scan=read(out/'scan.json'); ex=public(); markets=ex.load_markets()
    asof=pd.Timestamp.now(tz='UTC'); cheap=[]; bars={}
    # Cheap OHLCV context on the capped native shortlist. No structure/profile
    # calculations or hourly requests until the five-market deep budget is set.
    symbols=list(dict.fromkeys(['BTC/USDT:USDT']+[r['symbol'] for r in scan['shortlisted'][:20]]))
    for symbol in symbols:
        raw=ex.fetch_ohlcv(symbol,'15m',limit=120)
        f=pd.DataFrame(raw,columns=['date','open','high','low','close','volume']); f['date']=pd.to_datetime(f.date,unit='ms',utc=True)
        f=f.loc[f.date+pd.Timedelta(minutes=15)<=asof].reset_index(drop=True); bars[symbol]=f
        write(data.parent/'current'/(symbol.split('/')[0]+'-cheap.json'),dict(observed_at=now(),rows=raw))
    btc=bars['BTC/USDT:USDT']; btcret=float(btc.close.iloc[-1]/btc.close.iloc[-17]-1)
    for symbol in [r['symbol'] for r in scan['shortlisted'][:20]]:
        f=bars[symbol]; r=f.iloc[-1]; ret=float(f.close.iloc[-1]/f.close.iloc[-17]-1); relative=ret-btcret if symbol!='BTC/USDT:USDT' else ret
        direction='long' if ret>=0 else 'short'; sign=1 if direction=='long' else -1
        boundary_low=float(f.low.iloc[-21:-1].min()); boundary_high=float(f.high.iloc[-21:-1].max())
        failed_long=r.low<boundary_low<r.close; failed_short=r.high>boundary_high>r.close
        activity=float(f.volume.iloc[-16:].sum()/max(f.volume.iloc[-32:-16].sum(),1e-12))
        cheap.append(dict(symbol=symbol,return4h=ret,btc_relative4h=relative,continuation_side=direction,
            continuation_score=sign*relative+.01*min(activity,3),
            reversal_side='long' if failed_long else 'short' if failed_short else None,
            reason='OBSERVED_BOUNDARY_FAILURE_REQUIRES_DEEP_CONFIRMATION' if failed_long or failed_short else 'SIGNED_CONTINUATION_CONTEXT',
            closed_at=(r.date+pd.Timedelta(minutes=15)).isoformat()))
    cheap.sort(key=lambda r:(r['reversal_side'] is None,-r['continuation_score'],r['symbol']))
    deep=cheap[:5]; write(out/'deep-shortlist.json',dict(cheap=cheap,deep=deep,budget=5,selection='Failed-boundary candidates first, then side-signed BTC-relative continuation activity; five serious checks maximum'))
    cfg=read(config(run_id,'IntelligenceRegimeV2'))|{'candle_type_def':CandleType.FUTURES}; records=[]
    for candidate in deep:
        symbol=candidate['symbol']
        try:
            # 300 bars for EMA/structure warm-up; cheap stage only had 120.
            frames={}
            for tf,step in [('15m',pd.Timedelta(minutes=15)),('1h',pd.Timedelta(hours=1))]:
                raw=ex.fetch_ohlcv(symbol,tf,limit=300)
                f=pd.DataFrame(raw,columns=['date','open','high','low','close','volume']); f['date']=pd.to_datetime(f.date,unit='ms',utc=True)
                frames[tf]=f.loc[f.date+step<=asof].reset_index(drop=True)
                write(data.parent/'current'/(symbol.split('/')[0]+'-deep-'+tf+'.json'),dict(received_at=now(),rows=raw))
            d=analyzed(frames['15m'],frames['1h'],symbol,cfg); row=d.iloc[-1]
            quote=ex.fetch_order_book(symbol,limit=20,params={'with_id':True}); received=time.time()*1000; source=quote.get('timestamp')
            bid=quote['bids'][0][0]; ask=quote['asks'][0][0]; spread=1-bid/ask
            fresh=source is not None and 0<=received-source<=5000 and 0<=spread<=.002
            write(data.parent/'current'/(symbol.split('/')[0]+'-quote-v2.json'),dict(quote=quote,received_ms=received))
            for recipe,cls in [('vwap',VWAPTrendContinuationV1),('sweep',LiquiditySweepReversalV1)]:
                p=cls(cfg).populate_entry_trend(d.copy(),{'pair':symbol}).iloc[-1]
                for side in ('long','short'):
                    active=p['enter_'+side]==1; reason=match(row,recipe,side); g=research_plan(row,recipe,side,'target') if active else None
                    status='RESEARCH_CANDIDATE' if active and reason=='MATCH' and g else 'WATCH'
                    if not active: reason='WAIT_CLOSED_VWAP_RECLAIM' if recipe=='vwap' else 'WAIT_ACTUAL_BOUNDARY_FAILURE_REJECTION'
                    elif g is None: status='REJECT'; reason='INSUFFICIENT_NET_TARGET_OR_STOP_GEOMETRY'
                    at=row.date+pd.Timedelta(minutes=15); expires=at+pd.Timedelta(minutes=5)
                    gaps=['ACCOUNT_MTM_PENDING_EXPOSURE_UNQUALIFIED','NEWS_CLEARANCE_UNKNOWN','QUEUE_AND_SEQUENCE_UNKNOWN']
                    if not fresh: gaps.append('QUOTE_UNVERIFIED_OR_STALE')
                    if asof>=expires: gaps.append('SIGNAL_EXPIRED')
                    contradiction='NO_CLOSED_ENTRY_CONFIRMATION' if not active else reason if reason!='MATCH' else 'REST_DEPTH_CANNOT_ESTABLISH_QUEUE_OR_EXECUTION'
                    records.append(dict(schema_version=1,decision_id=f'{run_id}:current:{symbol}:{recipe}:{side}:{at.isoformat()}',
                        venue='gate',symbol=symbol,contract_id=markets[symbol]['id'],environment='CURRENT_PUBLIC_RESEARCH',status=status,reason=reason,
                        recipe=recipe,side=side,available_at=at.isoformat(),expires_at=expires.isoformat(),observed_at=now(),
                        regime='TREND' if row.adx_1h>=25 else 'RANGE_OR_WEAK_TREND',adx_1h=float(row.adx_1h),
                        geometry=g,signed_suitability=(1 if side=='long' else -1)*candidate['btc_relative4h'],
                        structure=dict(hourly_direction=row.get('struct_direction_1h'),local_direction=row.struct_direction,known_at=str(row.struct_known_at)),
                        profile=dict(fidelity='OHLCV_PROXY',poc=float(row.vp2_poc),val=float(row.vp2_val),vah=float(row.vp2_vah),anchor=str(row.vp2_anchor),known_at=str(row.vp2_known_at),
                            location='ABOVE_VALUE' if row.close>row.vp2_vah else 'BELOW_VALUE' if row.close<row.vp2_val else 'INSIDE_VALUE',acceptance='UNKNOWN_REQUIRES_REPEATED_TIME_AND_FLOW'),
                        orderflow=dict(status='UNKNOWN',reason='SEE_SEPARATELY_TIMESTAMPED_BOUNDED_FLOW_OBSERVATION'),
                        opposing_evidence=[dict(evidence_id='contrary:'+contradiction,reason=contradiction,assessment='INVALIDATES_ENTRY' if not active else 'CAUTION')],
                        quote=dict(venue_timestamp_ms=source,received_ms=received,spread_ratio=spread,freshness='CHECKED' if fresh else 'UNKNOWN_OR_STALE',sequence_continuity='UNVERIFIED_SINGLE_REST_SNAPSHOT'),
                        data_gaps=gaps,execution_status='NO_TRADE',execution_reason='RESEARCH_ONLY_NO_ORDER_AUTHORITY',orders_created=False))
        except Exception as error:
            records.append(dict(schema_version=1,decision_id=f'{run_id}:current:{symbol}:error',venue='gate',symbol=symbol,environment='CURRENT_PUBLIC_RESEARCH',status='NO_TRADE',reason='SOURCE_ASSESSMENT_FAILED',error=str(error)[:500],orders_created=False))
    write(out/'opportunities.json',dict(version=2,records=records,status='NO_TRADE',orders_created=False))
    print('Current deep checks',len(deep),dict(Counter(r['status'] for r in records)),flush=True)


def flow(run_id):
    from foundation_intelligence_flow import capture
    import asyncio
    asyncio.run(capture(run_id))


def compare(run_id):
    from foundation_intelligence_report import compare as implementation
    implementation(run_id)


def export(run_id):
    from foundation_intelligence_report import export as implementation
    implementation(run_id)


def lookahead(run_id):
    import subprocess
    out,_,_=verify(run_id); checks=[]
    for name in ['IntelligenceRegimeV2','IntelligenceTargetV2','IntelligenceEntryV2']:
        log=out/(name+'-lookahead.txt')
        with log.open('x') as f:
            r=subprocess.run([sys.executable,str(ROOT/'scripts/foundation.py'),'native-lookahead',run_id,name],stdout=f,stderr=subprocess.STDOUT)
        path=out/(name+'-lookahead.csv')
        rows=pd.read_csv(path).to_dict('records') if path.exists() else []
        checks.append(dict(strategy=name,exit_code=r.returncode,csv_rows=rows,
            interpretation='INSPECT_TEXT_TABLE_AND_SAMPLE_SIZE; HEADER_ONLY_CSV_IS_NOT_PROOF_OF_NO_BIAS',log_sha256=sha(log)))
        print('Native lookahead',name,'exit',r.returncode,flush=True)
    write(out/'intelligence-lookahead.json',dict(checks=checks))
    if any(c['exit_code'] for c in checks): raise ValueError('lookahead command failed; inspect retained logs')
