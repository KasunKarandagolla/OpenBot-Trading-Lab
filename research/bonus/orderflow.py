"""Verified Gate USDT futures WS signed contracts, observed-time windows.

Signed size is aggressive *executed* volume, never passive book liquidity.
Coverage means connection-observed, not a venue sequence/packet-loss guarantee.
"""
import math
import pandas as pd


def normalize(event,received_ms,contract,multiplier):
    if event.get('is_internal') is True:
        raise ValueError('INTERNAL_NONMATCHED_TRADE')
    if event.get('contract')!=contract or not contract.endswith('_USDT'):
        raise ValueError('CONTRACT_IDENTITY')
    stamp=event.get('create_time_ms')
    if stamp is None:stamp=float(event['create_time'])*1000
    at=float(stamp); size=float(event['size']);price=float(event['price'])
    if not all(math.isfinite(v) for v in (at,size,price,multiplier,received_ms)) or min(price,multiplier)<=0 or size==0:
        raise ValueError('INVALID_TRADE')
    if at>received_ms+1000:raise ValueError('FUTURE_EVENT')
    base=abs(size)*multiplier
    return {'id':str(event['id']),'contract':contract,'event_ms':at,'received_ms':received_ms,
            'latency_ms':received_ms-at,'signed_contracts':size,'amount':base,
            'quote_usdt':base*price,'price':price,'side':'buy' if size>0 else 'sell'}


def features(trades,start_ms,end_ms,asof_ms,coverage,scale):
    if end_ms>asof_ms:raise ValueError('UNOBSERVED_WINDOW')
    rows=[r for r in trades if start_ms<=r['event_ms']<end_ms and r['received_ms']<=asof_ms]
    ids=[r['id'] for r in rows]
    if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_TRADE_ID')
    complete=(coverage.get('subscribed_ms',float('inf'))<=start_ms
              and coverage.get('connected_until_ms',0)>=end_ms
              and coverage.get('disconnects',1)==0 and coverage.get('invalid_events',1)==0
              and coverage.get('out_of_order',1)==0)
    buy=sum(r['amount'] for r in rows if r['side']=='buy')
    sell=sum(r['amount'] for r in rows if r['side']=='sell');total=buy+sell
    footprint=[];profile=None
    if rows:
        from freqtrade.data.converter.orderflow import trades_to_volumeprofile_with_total_delta_bid_ask
        f=trades_to_volumeprofile_with_total_delta_bid_ask(pd.DataFrame(rows),scale)
        footprint=[{'price':float(i),'buy_base':float(r.ask_amount),'sell_base':float(r.bid_amount),
                    'delta_base':float(r.delta),'imbalance':float(r.delta/r.total_volume) if r.total_volume else None}
                   for i,r in f.iterrows()]
        from advanced_features import volume_profile
        profile=volume_profile([r['price'] for r in rows],[r['amount'] for r in rows])
    ordered=sorted(rows,key=lambda r:(r['event_ms'],r['id']))
    price_return=ordered[-1]['price']/ordered[0]['price']-1 if len(ordered)>1 else None
    return {'start_ms':start_ms,'end_ms':end_ms,'asof_ms':asof_ms,'trade_count':len(rows),
            'coverage_status':'COMPLETE_OBSERVED_CONNECTION' if complete else 'PARTIAL',
            'venue_losslessness_proven':False,'buy_base':buy,'sell_base':sell,'delta_base':buy-sell,
            'cvd_base_window':buy-sell,'imbalance':(buy-sell)/total if total else None,
            'quote_volume_usdt':sum(r['quote_usdt'] for r in rows),'price_return':price_return,
            'footprint':footprint,'profile':profile,'profile_fidelity':'OBSERVED_TRADED_BASE_VOLUME_AT_PRICE',
            'max_latency_ms':max((r['latency_ms'] for r in rows),default=None)}


def confirmation(observation,recipe,side):
    if observation['coverage_status']!='COMPLETE_OBSERVED_CONNECTION' or observation['trade_count']<2:
        return 'UNKNOWN'
    imbalance=observation['imbalance'];response=observation['price_return'];sign=1 if side=='long' else -1
    if imbalance is None or response is None:return 'UNKNOWN'
    # A reversal tests failed prior aggression in the *opposite* direction.
    condition=(sign*imbalance>=.2 if recipe=='vwap' else sign*imbalance<=-.2)
    return 'CONFIRM' if condition and sign*response>0 else 'CONTRADICT'


def shadow(plan,observation,asof_ms):
    """Stateless versioned shadow admission; cannot place orders or label outcomes."""
    valid=plan['decision_ms']<=asof_ms<plan['expires_ms']
    if observation['end_ms']>asof_ms:raise ValueError('FUTURE_ORDERFLOW')
    if observation['end_ms']<plan['decision_ms']-60000:valid=False
    outcome=confirmation(observation,plan['recipe'],plan['side']) if valid else 'EXPIRED'
    return {'decision_id':plan['decision_id'],'policy':'genuine-of-shadow-v1','asof_ms':asof_ms,
            'recipe':plan['recipe'],'side':plan['side'],'confirmation':outcome,
            'strict_shadow_action':'TRADE' if valid and outcome=='CONFIRM' else 'NO_TRADE',
            'economic_outcome':'UNMEASURED','orders_created':False}
