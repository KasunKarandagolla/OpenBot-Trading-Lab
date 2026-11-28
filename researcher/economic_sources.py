"""Small native public depth/OI reads and declared research friction assumptions.

Depth is displayed liquidity, not execution or absorption. A fixed USDT probe
notional measures book walking, not account position sizing or an order plan.
"""
from decimal import Decimal as D, ROUND_CEILING
from .contracts import ContractError,number,utc,digest
from .inventory import json_document
from .market import milliseconds

DOCS='https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data'


def depth_snapshot(api,instrument):
    if instrument.identity_status!='EXCHANGE_VERIFIED':raise ContractError('KLINES_REQUIRE_VERIFIED_IDENTITY')
    response=api.http.request('binance_depth',query={'symbol':instrument.native_symbol,'limit':100})
    return normalize_depth(json_document(response.body),instrument,response.receipt)


def normalize_depth(data,instrument,receipt):
    if instrument.identity_status!='EXCHANGE_VERIFIED':raise ContractError('KLINES_REQUIRE_VERIFIED_IDENTITY')
    if receipt.get('requested_query',{}).get('symbol')!=instrument.native_symbol:
        raise ContractError('NOMINATION_EVIDENCE_SCOPE')
    at=milliseconds(data['T']);received=receipt['received_at_utc']
    if not 0<=(utc(received)-utc(at)).total_seconds()<=30:raise ContractError('STALE_OR_FUTURE_MARKET_SNAPSHOT')
    sides={}
    for name,reverse in (('bids',True),('asks',False)):
        rows=data.get(name)
        if not isinstance(rows,list) or not 1<=len(rows)<=100:raise ContractError('MARKET_ROW_SCHEMA')
        levels=[(number(r[0],positive=True),number(r[1],positive=True)) for r in rows if isinstance(r,list) and len(r)==2]
        if len(levels)!=len(rows) or len({p for p,q in levels})!=len(levels) or levels!=sorted(levels,reverse=reverse):
            raise ContractError('MARKET_ROW_SCHEMA')
        sides[name]=levels
    if sides['bids'][0][0]>=sides['asks'][0][0]:raise ContractError('CROSSED_BOOK')
    return {'native_symbol':instrument.native_symbol,'venue':instrument.venue,'time':at,'received':received,
        'source_hash':receipt['response_sha256'],'source':DOCS,'receipt':receipt,'levels':sides,
        'units':'PRICE_USDT_PER_BASE; QUANTITY_NATIVE_BASE','coverage':'FIRST_100_DISPLAYED_LEVELS; NOT_FULL_BOOK_OR_EXECUTED_FLOW'}


def book_cost(snapshot,instrument,*,notional,obstacle=None,direction=1):
    """Both-side round trip at snapshot; future liquidity remains conditional."""
    notional=number(notional,positive=True);s=snapshot['levels'];mid=(s['asks'][0][0]+s['bids'][0][0])/2
    rules=instrument.quantity_rules.get('MARKET_LOT_SIZE') or instrument.quantity_rules.get('LOT_SIZE')
    if not rules:raise ContractError('INSTRUMENT_FILTER_SCHEMA')
    step=number(rules['stepSize'],positive=True);qty=(notional/mid/step).to_integral_value(rounding=ROUND_CEILING)*step
    filters={r['filterType']:r for r in instrument.exchange_rules}
    minimum=filters.get('MIN_NOTIONAL',{}).get('notional')
    if minimum is None:return {'status':'UNKNOWN','reason':'MIN_NOTIONAL_UNSOURCED'}
    if not number(rules['minQty'])<=qty<=number(rules['maxQty']) or qty*mid<number(minimum):
        return {'status':'RESTRICTED','reason':'PROBE_NOTIONAL_FAILS_NATIVE_LOT_OR_MIN_NOTIONAL','rules':rules,'minimum_notional':minimum}
    prices={}
    for side,levels in s.items():
        left=qty;value=D(0)
        for p,q in levels:
            used=min(q,left);value+=used*p;left-=used
            if left==0:break
        if left:return {'status':'UNKNOWN','reason':'FIRST_100_LEVELS_INSUFFICIENT_FOR_PROBE'}
        prices[side]=value/qty
    spread=10000*(s['asks'][0][0]-s['bids'][0][0])/mid
    walk=10000*(prices['asks']-prices['bids'])/mid
    levels=s['asks'] if direction==1 else s['bids']
    within=sum((p*q for p,q in levels if obstacle is not None and direction*(p-obstacle)<=0),D(0))
    return {'status':'OBSERVED','probe_notional_usdt':notional,'spread_bps':spread,
        'round_trip_book_walk_bps':walk,'slippage_excluding_spread_bps':max(D(0),walk-spread),
        'depth_usdt_within_room':within if obstacle is not None else None,
        'scope':'SNAPSHOT_DISPLAYED_ONLY; NOT_GUARANTEED_FUTURE_FILL','native_filters':instrument.exchange_rules}


def oi_observation(api,instrument):
    if instrument.identity_status!='EXCHANGE_VERIFIED':raise ContractError('KLINES_REQUIRE_VERIFIED_IDENTITY')
    response=api.http.request('binance_oi_history',query={'symbol':instrument.native_symbol,'period':'5m','limit':12})
    data=json_document(response.body)
    if not isinstance(data,list) or len(data)!=12:raise ContractError('INSUFFICIENT_HISTORY')
    times=[];native=[];usd=[]
    for row in data:
        if row.get('symbol')!=instrument.native_symbol:raise ContractError('NOMINATION_EVIDENCE_SCOPE')
        times.append(row['timestamp']);native.append(number(row['sumOpenInterest'],positive=True));usd.append(number(row['sumOpenInterestValue'],positive=True))
    if any(type(t)is not int for t in times) or any(b-a!=300000 for a,b in zip(times,times[1:])):
        raise ContractError('MISSING_OR_MISALIGNED_BARS')
    at=milliseconds(times[-1]);received=response.receipt['received_at_utc']
    if not 0<=(utc(received)-utc(at)).total_seconds()<=600:raise ContractError('STALE_OR_FUTURE_MARKET_SNAPSHOT')
    change=native[-1]/native[0]-1
    return {'native_symbol':instrument.native_symbol,'venue':instrument.venue,'time':at,'received':received,
        'native_oi':native,'oi_value_usdt':usd,'times_ms':times,'native_change_fraction':change,
        'nomination':abs(change)>=D('.05'),'threshold':'PREDECLARED_ABS_55MIN_NATIVE_OI_CHANGE_5_PERCENT; NOT_OPTIMIZED',
        'source_hash':digest(response.body),'receipt':response.receipt,'source':DOCS,
        'fidelity':'NATIVE_AGGREGATE_OI; NO_LONG_SHORT_DIRECTION_OR_LIQUIDATION_ASSERTION',
        'rights':'PUBLIC_DOCUMENTED_NO_KEY_API; SUSTAINED_ENTITLEMENT_NOT_ATTESTED'}
