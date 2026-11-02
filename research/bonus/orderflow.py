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


def qualified_flow(trades, start_ms, end_ms, asof_ms, coverage, scale, boundary=None):
    """V2 flow/location interpretation; never infer absorption from delta alone.

    Events and receipt cutoffs are independent. REST pages without proven
    pagination coverage remain PARTIAL even when they contain many prints.
    """
    if not start_ms < end_ms <= asof_ms: raise ValueError('invalid observed window')
    selected=[r for r in trades if start_ms<=r['event_ms']<end_ms and r['received_ms']<=asof_ms]
    selected.sort(key=lambda r:(r['event_ms'],r['id']))
    if len({r['id'] for r in selected}) != len(selected): raise ValueError('DUPLICATE_TRADE_ID')
    good=(coverage.get('source')=='WEBSOCKET' and coverage.get('subscribed_ms',float('inf'))<=start_ms
        and coverage.get('connected_until_ms',0)>=asof_ms and coverage.get('disconnects',1)==0
        and coverage.get('invalid_events',1)==0 and coverage.get('out_of_order',1)==0
        and coverage.get('server_clock_offset_ms') is not None
        and abs(coverage.get('server_clock_offset_ms',float('inf')))<=1000)
    buy=sum(r['amount'] for r in selected if r['side']=='buy')
    sell=sum(r['amount'] for r in selected if r['side']=='sell'); total=buy+sell
    cvd=0.; path=[]
    for r in selected:
        cvd+=r['amount']*(1 if r['side']=='buy' else -1)
        path.append((r['event_ms'],r['price'],cvd))
    response=selected[-1]['price']/selected[0]['price']-1 if len(selected)>1 else None
    from advanced_features import volume_profile_v2
    profile=volume_profile_v2([r['price'] for r in selected],[r['amount'] for r in selected],'OBSERVED_TRADES')
    footprint=[]
    if selected:
        from freqtrade.data.converter.orderflow import trades_to_volumeprofile_with_total_delta_bid_ask
        f=trades_to_volumeprofile_with_total_delta_bid_ask(pd.DataFrame(selected),scale)
        footprint=[dict(price=float(p),buy_base=float(r.ask_amount),sell_base=float(r.bid_amount),delta_base=float(r.delta)) for p,r in f.iterrows()]
    divergence=None if response is None or not total else ('PRICE_UP_SELL_DELTA' if response>0 and cvd<0 else 'PRICE_DOWN_BUY_DELTA' if response<0 and cvd>0 else 'ALIGNED_OR_FLAT')
    location='UNKNOWN'; flow_at_boundary=None
    if boundary and selected:
        level=float(boundary['price']); direction=boundary['side']; sign=1 if direction=='long' else -1
        beyond=[r for r in selected if sign*(r['price']-level)<0]
        # Actual trades beyond a predeclared level followed by a return inside.
        rejected=bool(beyond and sign*(selected[-1]['price']-level)>0)
        location='OBSERVED_REJECTION' if rejected else 'BEYOND_BOUNDARY' if sign*(selected[-1]['price']-level)<0 else 'INSIDE_WITHOUT_OBSERVED_SWEEP'
        flow_at_boundary=dict(boundary=boundary,executed_beyond_base=sum(r['amount'] for r in beyond),
            beyond_delta_base=sum(r['amount']*(1 if r['side']=='buy' else -1) for r in beyond),
            absorption='POSSIBLE_FAILED_AGGRESSION_REQUIRES_REPLICATION' if good and rejected and any(sign*(1 if r['side']=='buy' else -1)<0 for r in beyond) else 'UNKNOWN')
    imbalance=cvd/total if total else None
    return dict(version=2,start_ms=start_ms,end_ms=end_ms,asof_ms=asof_ms,trade_count=len(selected),
        coverage_status='COMPLETE_OBSERVED_CONNECTION' if good else 'PARTIAL',venue_losslessness_proven=False,
        buy_base=buy,sell_base=sell,delta_base=cvd,cvd_base_window=cvd,cvd_resets_at=start_ms,
        imbalance=imbalance,price_return=response,divergence=divergence,location=location,flow_at_boundary=flow_at_boundary,
        profile=profile,profile_fidelity='OBSERVED_TRADES',footprint=footprint,
        cvd_checkpoints=[dict(event_ms=p[0],price=p[1],cvd_base=p[2]) for p in path[::max(1,len(path)//12)]],
        confirmation='UNKNOWN' if not good or len(selected)<2 else 'OBSERVED_PARTICIPATION_ONLY',
        max_latency_ms=max((r['latency_ms'] for r in selected),default=None),
        economic_uplift='UNMEASURED_NO_HISTORICAL_FLOW',orders_created=False)


def normalize_gate_rest(parsed, received_ms, contract, multiplier):
    """CCXT Gate REST amounts are contracts; mislabeled raw ms field is seconds.

    Cross-check the adapter's millisecond timestamp against the independent
    raw create_time seconds. WS keeps its original genuine millisecond field.
    """
    event=dict(parsed['info'])
    if event.get('contract')!=contract: raise ValueError('CONTRACT_IDENTITY')
    stamp=float(parsed['timestamp'])
    if abs(stamp-float(event['create_time'])*1000)>1.01: raise ValueError('REST_SOURCE_CLOCK_MISMATCH')
    event['create_time_ms']=stamp
    row=normalize(event,received_ms,contract,multiplier)
    expected=float(parsed['amount'])*multiplier
    if row['side']!=parsed['side'] or abs(row['amount']-expected)>max(1e-10,abs(expected)*1e-8):
        raise ValueError('REST_SIDE_OR_UNIT_MISMATCH')
    row['timestamp_semantics']='CCXT_MS_VERIFIED_AGAINST_RAW_CREATE_TIME_SECONDS'
    row['amount_semantics']='ABS_CONTRACTS_TIMES_VERIFIED_BASE_MULTIPLIER'
    return row
