"""Existing scanner -> causal cross-sectional schedule -> native recipes -> ledger."""
import csv
import json
import shutil
import subprocess
import sys
import zipfile
import pandas as pd
import numpy as np
from bonus_common import *
from bonus_data import verify,frame
sys.path[:0]=[str(ROOT/'research/bonus'),str(ROOT/'research/session3'),str(ROOT/'user_data/strategies')]
from OpportunityRouterV1 import RouterOnlyV1,RouterSMCV1,RouterICTV1,RouterProfileV1,IntegratedM0V1,IntegratedM1V1,RouterOnlyM1V1
from freqtrade.strategy import merge_informative_pair
from freqtrade.enums import CandleType

CLASSES=[RouterOnlyV1,RouterSMCV1,RouterICTV1,RouterProfileV1,IntegratedM0V1,IntegratedM1V1,RouterOnlyM1V1]


def ranking(bases):
    pieces=[]
    btc=bases['BTC/USDT:USDT'].set_index('date').close.pct_change(16)
    for symbol,b in bases.items():
        d=b.copy().set_index('date')
        relative=d.close.pct_change(16)-btc.reindex(d.index)
        # BTC still has a directional activity score rather than zero by construction.
        if symbol=='BTC/USDT:USDT':relative=d.close.pct_change(16)
        quote=d.volume*(d.high+d.low+d.close)/3
        activity=quote.rolling(16,min_periods=16).sum()/quote.shift(16).rolling(16,min_periods=16).sum()
        volume=quote.rolling(96,min_periods=96).sum()
        score=relative.abs()+.01*activity.clip(0,3)
        valid=(volume>=1e7)&np.isfinite(score)&d.date.diff().eq(pd.Timedelta(minutes=15)) if 'date' in d else (volume>=1e7)&np.isfinite(score)
        pieces.append(pd.DataFrame({'symbol':symbol,'decision_at':d.index+pd.Timedelta(minutes=15),
                                   'relative_return4h':relative,'quote_volume24h_proxy':volume,
                                   'activity_ratio':activity,'score':score,'cheap_pass':valid}).reset_index(drop=True))
    allrows=pd.concat(pieces,ignore_index=True)
    allrows=allrows.sort_values(['decision_at','score','symbol'],ascending=[True,False,True])
    allrows['rank']=allrows.where(allrows.cheap_pass).groupby('decision_at').cumcount()+1
    allrows.loc[~allrows.cheap_pass,'rank']=np.nan
    decisions={}
    for at,d in allrows.groupby('decision_at',sort=True):
        ordered=d.loc[d.cheap_pass].sort_values(['score','symbol'],ascending=[False,True])
        selected=ordered.symbol.iloc[:3].tolist()
        decisions[at.isoformat()]={'selected':selected,'eligible_sample':len(ordered),
                                  'status':'ANALYZE' if selected else 'NO_TRADE'}
    return allrows,decisions


def schedule():
    check();verify()
    if (OUT/'schedule.json').exists():raise ValueError('schedule exists; preserve')
    bases={s:frame(s) for s in spec()['pairs']}
    rows,decisions=ranking(bases)
    rows.to_csv(OUT/'market-ranking.csv',index=False)
    obj={'policy':'causal-top3-v1','membership':spec()['membership'],
         'historical_spread':'UNOBSERVED; common cost assumption, no actual spread eligibility claim',
         'decisions':decisions}
    (OUT/'schedule.json').write_text(json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n')
    summary={'observed_sample_markets':5,'market_time_rows':len(rows),'cheap_pass':int(rows.cheap_pass.sum()),
             'selected_market_time_rows':sum(len(r['selected']) for r in decisions.values()),
             'no_trade_screen_times':sum(not r['selected'] for r in decisions.values()),
             'schedule_sha256':sha(OUT/'schedule.json'),'ranking_sha256':sha(OUT/'market-ranking.csv')}
    write(OUT/'selection-summary.json',summary);print(json.dumps(summary,indent=2))
    candidates()


def analyzed(symbol):
    s=RouterOnlyV1(config('RouterOnlyV1')|{'candle_type_def':CandleType.FUTURES})
    h=s.populate_indicators_1h(frame(symbol,'1h'),{'pair':symbol})
    merged=merge_informative_pair(frame(symbol),h,'15m','1h',ffill=True)
    return s.populate_indicators(merged,{'pair':symbol})


def candidates():
    counts={};examples=[]
    start,end=[pd.to_datetime(x,format='%Y%m%d',utc=True) for x in spec()['timerange'].split('-')]
    records=[]
    for symbol in spec()['pairs']:
        d=analyzed(symbol)
        for cls in CLASSES:
            s=cls(config(cls.__name__)|{'candle_type_def':CandleType.FUTURES})
            result=s.populate_entry_trend(d.copy(),{'pair':symbol})
            ev=result.loc[(result.parent_candidate==1)&(result.date+pd.Timedelta(minutes=15)>=start)&(result.date+pd.Timedelta(minutes=15)<end)]
            for _,r in ev.iterrows():
                record={'variant':cls.__name__,'symbol':symbol,'decision_at':(r.date+pd.Timedelta(minutes=15)).isoformat(),
                        'recipe':r.bonus_recipe,'decision':'TRADE' if r.bonus_reason=='TRADE' else 'REJECT',
                        'reason':r.bonus_reason,'side':'long' if r.enter_long else 'short' if r.enter_short else 'PARENT_REJECTED',
                        'smc_ok':bool(r.smc_ok),'ict_ok':bool(r.ict_ok),'profile_ok':bool(r.profile_ok),
                        'regime':'TREND' if r.adx_1h>=25 else 'BALANCE',
                        'reference':r.close,'plan':r.bonus_plan}
                records.append(record)
                if r.bonus_reason=='TRADE' and len(examples)<24:
                    g=json.loads(r.bonus_plan);at=r.date+pd.Timedelta(minutes=15)
                    examples.append({'decision_id':cls.__name__+'|'+symbol+'|'+at.isoformat(),'variant':cls.__name__,'symbol':symbol,'decision':'TRADE',
                                     'decision_at':at.isoformat(),'asof':at.isoformat(),'expires':(at+pd.Timedelta(minutes=5)).isoformat(),
                                     'recipe_version':'bonus-recipes-v1','plan':g,
                                     'opposing_evidence':[k.upper()+'_NOT_CONFIRMED' for k in ('smc','ict','profile') if not r[k+'_ok']],
                                     'orderflow':{'status':'UNKNOWN','reason':'NO_HISTORICAL_TRADE_COVERAGE'},
                                     'data_coverage':{'15m':'COMPLETE_VALIDATED','1h':'COMPLETE_VALIDATED','profile':'OHLCV_PROXY','news':'UNKNOWN'},
                                     'risk':{'leverage':1,'notional_cap':25,'margin_cap':25,'illustrative_budget':True},
                                     'features':{k:None if pd.isna(r.get(k)) else str(r.get(k)) for k in
                                                 ['struct_direction','struct_event','struct_direction_1h','prior_swing_high',
                                                  'prior_swing_low','prior_day_high','prior_day_low','recent_fvg_up',
                                                  'recent_fvg_down','dealing_location','vp_poc','vp_val','vp_vah',
                                                  'vp_anchor','vp_known_at','struct_known_at_1h']},
                                     'source_manifest_sha256':sha(OUT/'source-manifest.json')})
    df=pd.DataFrame(records);df.to_csv(OUT/'opportunity-ledger.csv',index=False)
    for name,group in df.groupby('variant'):
        counts[name]={'parent_candidates':len(group),'decisions':group.reason.value_counts().to_dict(),
                      'by_recipe':group.loc[group.decision=='TRADE'].recipe.value_counts().to_dict()}
    write(OUT/'opportunity-summary.json',counts);write(OUT/'trade-plans.json',examples)
    print(json.dumps(counts,indent=2))


def scan():
    """Reuse native scanner/exporter in a new isolated output tree."""
    mirror=ROOT/'work/bonus-scanner'
    for folder in ['user_data/logs','configs','evidence/session-1']:(mirror/folder).mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'configs/scan-rules.json',mirror/'configs/scan-rules.json')
    args=[sys.executable,str(ROOT/'scripts/guard.py'),'test-pairlist','--config',str(ROOT/'configs/scanner.json'),'--print-json']
    if (ROOT/'user_data/runtime/cloud.json').exists():args+=['--config',str(ROOT/'user_data/runtime/cloud.json')]
    with (OUT/'scanner-native-output.txt').open('x') as f:
        r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=sanitized_env())
    if r.returncode:raise ValueError('native scanner failed')
    shutil.copyfile(OUT/'scanner-native-output.txt',mirror/'user_data/logs/scan-native.log')
    import scan_export
    scan_export.ROOT=mirror;scan_export.main()
    shutil.copyfile(mirror/'evidence/session-1/scan-snapshot.json',OUT/'scanner-snapshot.json')
    # Serious current analysis is bounded to five. Unknown ticker source time vetoes entry.
    snapshot=read(OUT/'scanner-snapshot.json')
    from public_exchange import public_exchange
    from advanced_features import qualifiers
    e=public_exchange();results=[]
    for r in snapshot['shortlisted'][:5]:
        symbol=r['symbol'];candles={}
        for tf in ['15m','1h']:
            raw=e.fetch_ohlcv(symbol,tf,limit=300)
            d=pd.DataFrame(raw,columns=['date','open','high','low','close','volume'])
            d['date']=pd.to_datetime(d.date,unit='ms',utc=True)
            step=pd.Timedelta(minutes=15) if tf=='15m' else pd.Timedelta(hours=1)
            candles[tf]=d.loc[d.date+step<=pd.Timestamp.now(tz='UTC')].reset_index(drop=True)
        s=RouterOnlyV1(config('RouterOnlyV1')|{'candle_type_def':CandleType.FUTURES})
        h=s.populate_indicators_1h(candles['1h'],{'pair':symbol})
        d=s.populate_indicators(merge_informative_pair(candles['15m'],h,'15m','1h',ffill=True),{'pair':symbol})
        row=d.iloc[-1];at=row.date+pd.Timedelta(minutes=15)
        results.append({'symbol':symbol,'asof':pd.Timestamp.now(tz='UTC').isoformat(),
                        'last_candle_known_at':at.isoformat(),'recipe':'vwap' if row.adx_1h>=25 else 'sweep',
                        'regime':'TREND' if row.adx_1h>=25 else 'BALANCE','profile_poc_proxy':float(row.vp_poc),
                        'structure':row.struct_direction,'decision':'REJECT' if r['freshness_status']=='UNKNOWN' else 'WATCH',
                        'reason':'TICKER_SOURCE_FRESHNESS_UNKNOWN' if r['freshness_status']=='UNKNOWN' else 'NO_EXECUTION_FROM_SNAPSHOT',
                        'orderflow':'UNKNOWN','orders_created':False})
    write(OUT/'current-assessments.json',results)
    print(json.dumps({'eligible':snapshot['eligible_universe_count'],'shortlist':len(snapshot['shortlisted']),
                      'detailed':len(results),'decisions':pd.Series([r['decision'] for r in results]).value_counts().to_dict()},indent=2))


def extract(name,directory,destination):
    archive=directory/read(directory/'.last_result.json')['latest_backtest']
    with zipfile.ZipFile(archive) as z:
        member=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
        destination.write_bytes(z.read(member))
    return archive


def run():
    check();verify()
    for name in spec()['variants']:
        dest=OUT/'native-results';dest.mkdir(exist_ok=True)
        result=dest/(name+'.json')
        if result.exists():continue # immutable completed variants; explicit retry only missing run
        log=dest/(name+'-output.txt')
        if log.exists():raise ValueError('failed run retained; version a correction before retry')
        started=pd.Timestamp.now(tz='UTC')
        with log.open('x') as f:
            r=subprocess.run([sys.executable,str(ROOT/'scripts/bonus_common.py'),'backtesting',name],
                             stdout=f,stderr=subprocess.STDOUT,env=sanitized_env())
        if r.returncode:raise ValueError('native run failed: '+name)
        directory=ROOT/'user_data/backtest_results/bonus'/name
        archive=extract(name,directory,result)
        if archive.stat().st_mtime<started.timestamp():raise ValueError('stale native result')
        write(dest/(name+'-provenance.json'),{'started':started.isoformat(),'completed':pd.Timestamp.now(tz='UTC').isoformat(),
                                           'result_sha256':sha(result),'archive_sha256':sha(archive),
                                           'source_manifest_sha256':sha(OUT/'source-manifest.json'),
                                           'schedule_sha256':sha(OUT/'schedule.json'),'freeze_sha256':sha(OUT/'freeze.sha256'),
                                           'protocol_sha256':sha(PROTOCOL),'config_sha256':sha(ROOT/'work/bonus-configs'/(name+'.json')),
                                           'engine':'Freqtrade2026.10','ccxt':'4.5.90','exit_code':r.returncode})
        native=read(result)['strategy'][name]
        print(name,len(native['trades']),sum(t['profit_abs'] for t in native['trades']),flush=True)


def lookahead():
    # Integrated policy has no entries; sample an actionable frozen router policy.
    name='RouterOnlyV1'
    with (OUT/'lookahead-output.txt').open('x') as f:
        r=subprocess.run([sys.executable,str(ROOT/'scripts/bonus_common.py'),'lookahead-analysis',name],
                         stdout=f,stderr=subprocess.STDOUT,env=sanitized_env())
    if r.returncode:raise ValueError('native lookahead failed')


def replay_native():
    name='RouterOnlyV1';result=OUT/'native-router-replay.json'
    if result.exists():raise ValueError('preserve native replay')
    with (OUT/'native-replay-output.txt').open('x') as f:
        r=subprocess.run([sys.executable,str(ROOT/'scripts/bonus_common.py'),'native-replay',name],
                         stdout=f,stderr=subprocess.STDOUT,env=sanitized_env())
    if r.returncode:raise ValueError('native replay failed')
    directory=ROOT/'user_data/backtest_results/bonus'/('replay-'+name)
    archive=extract(name,directory,result)
    previous=read(OUT/'native-results'/(name+'.json'))['strategy'][name]['trades']
    current=read(result)['strategy'][name]['trades']
    if previous!=current:raise ValueError('native trade-field replay mismatch')
    write(OUT/'native-replay-verification.json',{'pass':True,'trades':len(current),'comparison':'every field of every native trade',
                                              'result_sha256':sha(result),'archive_sha256':sha(archive),
                                              'freeze_sha256':sha(OUT/'freeze.sha256')})
