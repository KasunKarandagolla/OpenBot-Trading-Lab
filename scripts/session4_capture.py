"""Bounded prospective book/tape evidence, never order or historical flow inference."""
from pathlib import Path
import time
from session4_common import *


def capture():
    from intelligence_orderflow import normalize_gate_rest,qualified_flow
    ex=public();source=read(DATA.parent/'contract-source.json');ex.set_markets([r['market'] for r in source.values()])
    records=[]
    for pair in ['BTC/USDT:USDT','ETH/USDT:USDT','SOL/USDT:USDT']:
        record=dict(pair=pair,venue='gate',observed_at=now(),books=[],flow_fidelity='UNKNOWN',orders_created=False)
        for _ in range(2):
            try:
                begin=time.time()*1000;book=ex.fetch_order_book(pair,limit=20);end=time.time()*1000
                record['books'].append(dict(request_ms=begin,received_ms=end,source_timestamp=book.get('timestamp'),
                    bids=book['bids'],asks=book['asks'],spread_fraction=1-book['bids'][0][0]/book['asks'][0][0],
                    queue_priority='UNKNOWN',actual_exchange_fill='NOT_OBSERVED'))
            except Exception as e:record['books'].append(dict(error=type(e).__name__+': '+str(e)[:300],received_at=now()))
        try:
            trades=ex.fetch_trades(pair,limit=300);received=time.time()*1000
            rows=[normalize_gate_rest(t,received,source[pair]['market']['id'],source[pair]['market']['contractSize']) for t in trades]
            rows=list({r['id']:r for r in rows}.values())
            write(DATA.parent/'prospective'/(pair.split('/')[0]+'-trades.json'),rows)
            record['flow']=qualified_flow(rows,min(r['event_ms'] for r in rows),received,received,
                dict(source='REST',disconnects=0),scale=float(source[pair]['market']['precision']['price'])*10)
            record['flow_fidelity']='OBSERVED_GATE_EXECUTED_TRADES_PARTIAL_REST_WINDOW'
            record['economic_increment']='UNMEASURED_PROSPECTIVE_ONLY_NO_HISTORICAL_INPUT'
        except Exception as e:record['flow_error']=type(e).__name__+': '+str(e)[:300]
        records.append(record)
    directory=OUT/'prospective';write(directory/f'capture-{len(list(directory.glob("*.json")))+1:03}.json',dict(at=now(),records=records,
        historical_orderflow_profitability='UNTESTABLE_WITHOUT_GENUINE_HISTORICAL_GATE_TAPE',cross_venue_blending=False))
    print([(r['pair'],r['flow_fidelity']) for r in records],flush=True)


if __name__=='__main__':capture()
