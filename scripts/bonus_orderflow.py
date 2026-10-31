"""Bounded public websocket capture through the configured HTTPS proxy, no keys."""
import asyncio
import inspect
import json
import os
import ssl
import time
import aiohttp
from bonus_common import *
sys.path[:0]=[str(ROOT/'research/bonus'),str(ROOT/'research/session3'),str(ROOT/'user_data/strategies')]
from orderflow import normalize,features,shadow


def paths(observation_id=None):
    import re
    if observation_id is not None and not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,60}',observation_id):
        raise ValueError('invalid observation ID')
    folder=OUT if observation_id is None else OUT/'forward'/observation_id
    folder.mkdir(parents=True,exist_ok=True)
    raw=ROOT/'user_data/data/bonus'/('orderflow-'+(observation_id or 'capture')+'.jsonl')
    return folder/'orderflow-observation.json',raw


def observed_setup(e,contract,observation,symbol='BTC/USDT:USDT'):
    """Real completed-candle opportunity at observation cutoff, with strict UNKNOWNs."""
    import pandas as pd
    from freqtrade.strategy import merge_informative_pair
    from freqtrade.enums import CandleType
    from OpportunityRouterV1 import RouterOnlyV1
    from advanced_features import qualifiers,plan
    from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
    from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
    asof=pd.Timestamp(observation['asof_ms'],unit='ms',tz='UTC')
    frames={}
    for tf,step in [('15m',pd.Timedelta(minutes=15)),('1h',pd.Timedelta(hours=1))]:
        rows=e.fetch_ohlcv(symbol,tf,limit=300)
        d=pd.DataFrame(rows,columns=['date','open','high','low','close','volume'])
        d['date']=pd.to_datetime(d.date,unit='ms',utc=True)
        frames[tf]=d.loc[d.date+step<=asof].reset_index(drop=True)
    cfg={'candle_type_def':CandleType.FUTURES};strategy=RouterOnlyV1(cfg)
    h=strategy.populate_indicators_1h(frames['1h'],{'pair':symbol})
    f=strategy.populate_indicators(merge_informative_pair(frames['15m'],h,'15m','1h',ffill=True),{'pair':symbol})
    row=f.iloc[-1];recipe='vwap' if row.adx_1h>=25 else 'sweep'
    parent=(VWAPTrendContinuationV1 if recipe=='vwap' else LiquiditySweepReversalV1)(cfg)
    signal=parent.populate_entry_trend(f.copy(),{'pair':symbol}).iloc[-1]
    side='long' if signal.enter_long else 'short' if signal.enter_short else None
    answer={'symbol':symbol,'contract':contract,'asof':asof.isoformat(),'recipe':recipe,
            'decision_id':symbol+'|'+asof.isoformat(),'signal_known_at':(row.date+pd.Timedelta(minutes=15)).isoformat(),
            'status':'NO_TRADE','reason':'NO_COMPLETED_CANDLE_SETUP','genuine_flow':observation['coverage_status'],
            'profile_fidelity':'OHLCV_PROXY','risk_review':'UNKNOWN_ACCOUNT_AND_TIERS','orders_created':False}
    if side:
        q=qualifiers(row,recipe,side);g=plan(row,recipe,side)
        if g and q['smc' if recipe=='vwap' else 'ict']:
            p={'decision_id':answer['decision_id'],'decision_ms':(row.date+pd.Timedelta(minutes=15)).timestamp()*1000,
               'expires_ms':(row.date+pd.Timedelta(minutes=20)).timestamp()*1000,'recipe':recipe,'side':side}
            answer.update(plan=g,orderflow_shadow=shadow(p,observation,observation['asof_ms']),
                          status='WATCH',reason='RESEARCH_SETUP_REQUIRES_SELECTION_AND_ACCOUNT_RISK')
    return answer


async def capture(seconds=95,observation_id=None,symbol='BTC/USDT:USDT'):
    check()
    import re
    if not re.fullmatch(r'[A-Z0-9]+/USDT:USDT',symbol):raise ValueError('USDT linear perpetual symbol required')
    target,raw=paths(observation_id)
    if target.exists():raise ValueError('preserve observed capture; create separate experiment')
    from public_exchange import public_exchange
    e=public_exchange();market=e.load_markets()[symbol]
    info=market['info']
    if not(market['active'] and market['swap'] and market['linear'] and market['settle']=='USDT'
           and market['quote']=='USDT' and info.get('contract_type')==''
           and info.get('in_delisting') is False and info.get('is_pre_market') is False):raise ValueError('invalid contract')
    contract=market['id'];multiplier=market['contractSize']
    scale=float(market['precision']['price'])*10
    if not scale>0:raise ValueError('price precision unavailable')
    coverage={'subscribed_ms':None,'connected_until_ms':0,'disconnects':0,'invalid_events':0,
              'out_of_order':0,'duplicate_ids':0,'received_batches':0}
    rows=[];seen=set();last=0;error=None
    raw.parent.mkdir(parents=True,exist_ok=True)
    proxy=os.environ.get('HTTPS_PROXY',os.environ.get('https_proxy'))
    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.ws_connect('wss://fx-ws.gateio.ws/v4/ws/usdt',proxy=proxy,
                                          ssl=ssl.create_default_context(),heartbeat=15,timeout=15,
                                          headers={'X-Gate-Size-Decimal':'1'}) as ws:
                await ws.send_json({'time':int(time.time()),'channel':'futures.trades','event':'subscribe','payload':[contract]})
                deadline=time.monotonic()+seconds
                with raw.open('x') as f:
                    while time.monotonic()<deadline:
                        try:msg=await asyncio.wait_for(ws.receive(),timeout=min(10,deadline-time.monotonic()))
                        except asyncio.TimeoutError:continue
                        now=time.time()*1000
                        if msg.type!=aiohttp.WSMsgType.TEXT:
                            if msg.type in (aiohttp.WSMsgType.CLOSE,aiohttp.WSMsgType.CLOSED,aiohttp.WSMsgType.ERROR):
                                coverage['disconnects']+=1;break
                            continue
                        event=json.loads(msg.data)
                        f.write(json.dumps({'received_ms':now,'message':event},sort_keys=True)+'\n')
                        if event.get('event')=='subscribe':
                            if event.get('result',{}).get('status')=='success':coverage['subscribed_ms']=now
                            else:raise ValueError('SUBSCRIPTION_REJECTED')
                        if event.get('channel')!='futures.trades' or event.get('event')!='update':continue
                        coverage['received_batches']+=1
                        for trade in event.get('result',[]):
                            try:r=normalize(trade,now,contract,multiplier)
                            except (ValueError,KeyError,TypeError):coverage['invalid_events']+=1;continue
                            if r['id'] in seen:coverage['duplicate_ids']+=1;continue
                            seen.add(r['id'])
                            if r['event_ms']<last:coverage['out_of_order']+=1
                            last=max(last,r['event_ms']);rows.append(r)
                        coverage['connected_until_ms']=now
                coverage['connected_until_ms']=time.time()*1000
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc);coverage['disconnects']+=1
    windows=[];shadow_rows=[]
    if coverage['subscribed_ms']:
        start=(int(coverage['subscribed_ms']/30000)+1)*30000
        for at in range(start,int(coverage['connected_until_ms'])-30000,30000):
            # Only events actually received by the window end+1s are eligible.
            observation=features(rows,at,at+30000,at+31000,coverage,scale=scale)
            windows.append(observation)
            for recipe in ('vwap','sweep'):
                for side in ('long','short'):
                    plan={'decision_id':f'plumbing-{at}-{recipe}-{side}','decision_ms':at+30000,
                          'expires_ms':at+330000,'recipe':recipe,'side':side}
                    shadow_rows.append(shadow(plan,observation,at+31000)|{'setup_fidelity':'PLUMBING_DEMONSTRATION_NOT_ACTUAL_CANDLE_SETUP'})
    # Persist only derived bounded output; raw prints stay local.
    from freqtrade.data.converter.orderflow import trades_to_volumeprofile_with_total_delta_bid_ask as native
    obj={'source':'Gate futures.trades public USDT websocket','contract':contract,'symbol':symbol,
         'footprint_scale_quote':scale,
         'decimal_size_header':True,
         'contract_size_base':multiplier,'coverage':coverage,'error':error,'observed_trades':len(rows),
         'normalized_base_volume':sum(r['amount'] for r in rows),'windows':windows,'shadow':shadow_rows,
         'raw_local_path':str(raw.relative_to(ROOT)),'raw_sha256':sha(raw) if raw.exists() else None,
         'native_aggregation_source_sha256':sha(Path(inspect.getfile(native))),
         'aggressor_semantics_reference':'https://www.gate.com/docs/developers/futures/ws/#trades-notification',
         'economic_impact':'UNMEASURED; bounded mechanics observation, no genuine historical trade cohort',
         'orders_created':False}
    if windows:
        try:obj['actual_completed_candle_shadow']=observed_setup(e,contract,windows[-1],symbol)
        except Exception as exc:obj['actual_completed_candle_shadow']={'status':'UNKNOWN','error':type(exc).__name__+': '+str(exc),'orders_created':False}
    write(target,obj)
    print(json.dumps({k:v for k,v in obj.items() if k not in ('windows','shadow')},indent=2))
    return obj


def replay(observation_id=None):
    target,_=paths(observation_id)
    obj=read(target);p=ROOT/obj['raw_local_path']
    if sha(p)!=obj['raw_sha256']:raise ValueError('raw capture changed')
    rows=[];seen=set()
    for line in p.read_text().splitlines():
        raw=json.loads(line);event=raw['message']
        if event.get('channel')!='futures.trades' or event.get('event')!='update':continue
        for trade in event['result']:
            try:r=normalize(trade,raw['received_ms'],obj['contract'],obj['contract_size_base'])
            except (ValueError,KeyError,TypeError):continue # same rejected-event policy as capture
            if r['id'] not in seen:rows.append(r);seen.add(r['id'])
    windows=[features(rows,w['start_ms'],w['end_ms'],w['asof_ms'],obj['coverage'],obj.get('footprint_scale_quote',10.)) for w in obj['windows']]
    if windows!=obj['windows']:raise ValueError('observed replay mismatch')
    result={'pass':True,'windows':len(windows),'trades':len(rows),'raw_sha256':sha(p)}
    write(target.parent/'orderflow-replay.json',result);return result
