"""Bounded real executed-trade observations using the existing normalizer/native footprint."""
import asyncio
import inspect
import json
import os
import ssl
import time
import aiohttp
from foundation_common import *
from orderflow import normalize
from intelligence_orderflow import normalize_gate_rest,qualified_flow


async def capture(run_id,seconds=45):
    out,data,spec=verify(run_id)
    if (out/'orderflow.json').exists(): raise ValueError('preserve flow observation')
    source_dir=data.parent/'flow'/('attempt-'+str(len(list((data.parent/'flow').glob('attempt-*')))+1).zfill(3))
    source_dir.mkdir(parents=True)
    shortlist=read(out/'deep-shortlist.json')['deep'][:3]
    candidates=read(out/'opportunities.json')['records']
    ex=public(); markets=ex.load_markets(); contexts={}; results=[]
    t0=time.time()*1000
    try: venue=ex.fetch_time(); t1=time.time()*1000; offset=float(venue)-(t0+t1)/2
    except Exception: offset=None; t1=time.time()*1000
    # Retain the adapter implementing the venue's signed-size mapping by hash.
    import ccxt
    adapter=inspect.getsource(ccxt.gate.parse_trade)
    adapter_path=source_dir/'gate-parse-trade-source.txt'; adapter_path.write_text(adapter)
    documentation='https://www.gate.com/docs/developers/futures/ws/#trades-notification'
    for candidate in shortlist:
        symbol=candidate['symbol']; market=markets[symbol]; contract=market['id']; multiplier=market['contractSize']
        if not multiplier or not market['linear'] or market['settle']!='USDT': raise ValueError('unverified linear base multiplier')
        raw=ex.fetch_trades(symbol,limit=1000); received=time.time()*1000; normalized=[]; seen=set(); duplicates=0; invalid=0; side_mismatches=0
        for trade in raw:
            try:
                r=normalize_gate_rest(trade,received,contract,multiplier)
                if r['id'] in seen: duplicates+=1; continue
                seen.add(r['id']); normalized.append(r)
            except (KeyError,ValueError,TypeError) as error:
                invalid+=1
                if 'MISMATCH' in str(error): side_mismatches+=1
        path=source_dir/(contract+'-public-trades.json'); write(path,dict(received_ms=received,trades=raw))
        scale=float(market['precision']['price'])*10
        coverage=dict(source='REST',pagination_continuity='UNKNOWN_BOUNDED_PAGE',disconnects=0,invalid_events=invalid,
            duplicate_ids=duplicates,side_unit_mismatches=side_mismatches,server_clock_offset_ms=offset)
        start=min((r['event_ms'] for r in normalized),default=received-1)
        end=min(received,max((r['event_ms']+1 for r in normalized),default=received))
        obs=qualified_flow(normalized,start,end,received,coverage,scale) if start<end else None
        results.append(dict(symbol=symbol,contract=contract,contract_size_base=multiplier,source='GATE_PUBLIC_EXECUTED_TRADES_REST',
            side_semantics='SIGNED_SIZE_POSITIVE_AGGRESSIVE_BUY_NEGATIVE_AGGRESSIVE_SELL',ccxt_side_unit_mismatches=side_mismatches,
            verified_adapter_sha256=sha(adapter_path),semantics_reference=documentation,coverage=coverage,
            observation=obs,source_sha256=sha(path),raw_source_local_path=str(path.relative_to(ROOT)),orders_created=False))
        context=next((r.get('structure',{}) for r in candidates if r['symbol']==symbol and r.get('structure')), {})
        boundaries=[dict(price=context['prior_boundary_low'],side='long',known_at=context['boundary_known_at']),
                    dict(price=context['prior_boundary_high'],side='short',known_at=context['boundary_known_at'])] if 'prior_boundary_low' in context else []
        contexts[contract]=dict(symbol=symbol,multiplier=multiplier,scale=scale,rows=[],seen=set(),last=0,boundaries=boundaries,
            coverage=dict(source='WEBSOCKET',subscribed_ms=None,connected_until_ms=0,disconnects=0,invalid_events=0,out_of_order=0,duplicate_ids=0,server_clock_offset_ms=offset))
    rawpath=source_dir/'flow-websocket.jsonl'; error=None
    proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.ws_connect('wss://fx-ws.gateio.ws/v4/ws/usdt',proxy=proxy,ssl=ssl.create_default_context(),heartbeat=10,timeout=15,headers={'X-Gate-Size-Decimal':'1'}) as ws:
                for contract in contexts:
                    await ws.send_json(dict(time=int(time.time()),channel='futures.trades',event='subscribe',payload=[contract]))
                deadline=time.monotonic()+seconds
                with rawpath.open('x') as file:
                    while time.monotonic()<deadline:
                        try: message=await asyncio.wait_for(ws.receive(),timeout=min(5,max(.001,deadline-time.monotonic())))
                        except asyncio.TimeoutError: continue
                        received=time.time()*1000
                        if message.type!=aiohttp.WSMsgType.TEXT:
                            if message.type in (aiohttp.WSMsgType.CLOSED,aiohttp.WSMsgType.CLOSE,aiohttp.WSMsgType.ERROR): raise ValueError('WS_DISCONNECTED')
                            continue
                        event=json.loads(message.data); file.write(json.dumps(dict(received_ms=received,message=event))+'\n')
                        if event.get('event')=='subscribe' and event.get('channel')=='futures.trades':
                            if event.get('result',{}).get('status')!='success': raise ValueError('SUBSCRIPTION_FAILED')
                            # Server acknowledgement does not echo all payloads;
                            # every requested stream starts no earlier than ack.
                            for ctx in contexts.values(): ctx['coverage']['subscribed_ms']=received
                        if event.get('channel')!='futures.trades' or event.get('event')!='update': continue
                        for trade in event.get('result',[]):
                            ctx=contexts.get(trade.get('contract'))
                            if ctx is None: continue
                            try: r=normalize(trade,received,trade['contract'],ctx['multiplier'])
                            except (ValueError,KeyError,TypeError): ctx['coverage']['invalid_events']+=1; continue
                            if r['id'] in ctx['seen']: ctx['coverage']['duplicate_ids']+=1; continue
                            ctx['seen'].add(r['id'])
                            if r['event_ms']<ctx['last']: ctx['coverage']['out_of_order']+=1
                            ctx['last']=max(ctx['last'],r['event_ms']); ctx['rows'].append(r)
                ended=time.time()*1000
                for ctx in contexts.values(): ctx['coverage']['connected_until_ms']=ended
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc)[:1000]
        for ctx in contexts.values(): ctx['coverage']['disconnects']+=1;ctx['coverage']['connected_until_ms']=time.time()*1000
    streams=[]
    for contract,ctx in contexts.items():
        coverage=ctx['coverage']; windows=[]
        if coverage['subscribed_ms']:
            start=(int(coverage['subscribed_ms']//10000)+1)*10000
            end=int((coverage['connected_until_ms']-1000)//10000)*10000
            for at in range(start,end,10000):
                observation=qualified_flow(ctx['rows'],at,at+10000,at+11000,coverage,ctx['scale'])
                observation['location_assessments']=[]
                for boundary in ctx['boundaries']:
                    if __import__('datetime').datetime.fromisoformat(boundary['known_at']).timestamp()*1000>at:
                        raise ValueError('boundary not known before flow window')
                    located=qualified_flow(ctx['rows'],at,at+10000,at+11000,coverage,ctx['scale'],boundary)
                    observation['location_assessments'].append(dict(side=boundary['side'],location=located['location'],flow_at_boundary=located['flow_at_boundary']))
                windows.append(observation)
        streams.append(dict(symbol=ctx['symbol'],contract=contract,observed_trades=len(ctx['rows']),coverage=coverage,windows=windows))
    write(out/'orderflow.json',dict(version=2,observed_at=now(),venue='gate',rest=results,websocket=streams,
        websocket_error=error,websocket_source_sha256=sha(rawpath) if rawpath.exists() else None,
        websocket_source_local_path=str(rawpath.relative_to(ROOT)),
        server_clock=dict(offset_ms=offset,round_trip_ms=t1-t0),duration_budget_seconds=seconds,
        historical_flow='UNKNOWN_NO_GENUINE_HISTORICAL_COVERAGE',economic_uplift='UNMEASURED',orders_created=False))
    print('Real flow:',sum(r['observation']['trade_count'] if r['observation'] else 0 for r in results),'REST prints;',sum(s['observed_trades'] for s in streams),'WS prints;',sum(len(s['windows']) for s in streams),'qualified-window attempts; error',error,flush=True)
