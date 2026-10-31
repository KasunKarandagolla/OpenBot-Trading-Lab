"""20-second public Gate sequence probe; no trading or persistent collector.

Run in the pinned native image (aiohttp dependency). Snapshot limit and WS depth
are both 20. Subscribe and buffer before requesting the REST base snapshot.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
import time
import aiohttp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research'))
from master_audit.data_checks import validate_book


async def main(run_id):
    import re
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,40}',run_id):
        raise ValueError('invalid ID')
    out=ROOT/'evidence/master-audit'/run_id
    out.mkdir()
    coverage=json.loads((ROOT/'evidence/master-audit/source-001/coverage.json').read_text())
    shortlist=coverage['gate_scan']['shortlisted']
    # First eligible shortlisted contract, declared by turnover before book checks.
    symbol=shortlist[0] if shortlist else None
    obj=dict(symbol=symbol,status='BLOCKED',updates=[],messages=[],
             official_sequence_reference='https://www.gate.com/docs/developers/futures/ws/#order-book-api',
             no_orders=True,no_persistent_collection=True)
    try:
        if not symbol:
            raise ValueError('NO_SHORTLIST')
        async with aiohttp.ClientSession(trust_env=True,timeout=aiohttp.ClientTimeout(total=20)) as session:
            async with session.ws_connect('wss://fx-ws.gateio.ws/v4/ws/usdt',
                    proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'),
                    headers={'X-Gate-Size-Decimal':'1'},heartbeat=5) as ws:
                await ws.send_json(dict(time=int(time.time()),channel='futures.order_book_update',
                                        event='subscribe',payload=[symbol,'100ms','20']))
                updates=[]
                async def receive():
                    async for message in ws:
                        if message.type != aiohttp.WSMsgType.TEXT:
                            raise ValueError('WEBSOCKET_DISCONNECT')
                        item=json.loads(message.data)
                        if item.get('error'):
                            raise ValueError(str(item['error']))
                        if item.get('event')=='update' and item.get('channel')=='futures.order_book_update':
                            result=item['result']
                            if result.get('s')!=symbol:
                                raise ValueError('CONTRACT_MISMATCH')
                            updates.append(result|{'received_ms':time.time()*1000})
                        elif len(obj['messages'])<3:
                            obj['messages'].append(item)
                receiver=asyncio.create_task(receive())
                try:
                    await asyncio.sleep(0.5)
                    requested=time.time()
                    async with session.get('https://api.gateio.ws/api/v4/futures/usdt/order_book',
                            params=dict(contract=symbol,limit=20,with_id='true')) as response:
                        response.raise_for_status()
                        snapshot=await response.json()
                    received=time.time()
                    await asyncio.sleep(2)
                    if receiver.done():
                        receiver.result()
                    obj.update(snapshot=snapshot,updates=updates,
                               validation=validate_book(snapshot,requested,received,updates))
                    obj['status']=obj['validation']['status']
                finally:
                    receiver.cancel()
                    try:
                        await receiver
                    except asyncio.CancelledError:
                        pass
    except Exception as error:
        obj['error']=type(error).__name__+':'+str(error)
    (out/'book.json').write_text(json.dumps(obj,indent=2)+'\n')
    print(json.dumps({k:v for k,v in obj.items() if k not in ('snapshot','updates','messages')}))


if __name__=='__main__':
    asyncio.run(asyncio.wait_for(main(sys.argv[1]),timeout=25))
