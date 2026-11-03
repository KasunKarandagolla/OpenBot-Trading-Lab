"""V2 flow fidelity, reusing the frozen signed-trade normalizer."""
import pandas as pd
from orderflow import normalize

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
    from intelligence_profile import volume_profile_v2
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
