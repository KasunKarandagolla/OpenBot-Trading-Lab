"""Authentic profile input boundary; existing contiguous profile implementation.

No reconstruction from candle color or OHLCV. Coverage is an explicit source
receipt claim that must be backed by a verified capture, not an inferred field.
"""
import hashlib
import json
import math
import pandas as pd
from intelligence_profile import volume_profile_v2

def verified_profile(trades,receipt,asof):
    if receipt.get('fidelity')!='EXECUTED_TRADES' or receipt.get('coverage')!='COMPLETE_VERIFIED':
        return {'status':'UNKNOWN','reason':'AUTHENTIC_COMPLETE_TAPE_REQUIRED'}
    required=['id','event_ms','received_ms','price','amount']
    if not all(k in t for t in trades for k in required) or not trades:
        return {'status':'UNKNOWN','reason':'MISSING_TRADE_FIELDS'}
    if not receipt.get('source') or receipt.get('venue')!='gate' or not receipt.get('pair'):
        return {'status':'UNKNOWN','reason':'SOURCE_IDENTITY_REQUIRED'}
    ids=[t['id'] for t in trades]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate trade ids')
    end=pd.Timestamp(receipt['end']);start=pd.Timestamp(receipt['start']);known=pd.Timestamp(receipt['known_at'])
    if not start<end<=known<=pd.Timestamp(asof):raise ValueError('profile availability')
    seconds=(end-start).total_seconds()
    if seconds not in (28800,86400) or end!=end.floor('8h' if seconds==28800 else 'D'):
        raise ValueError('complete UTC8h or UTCday reference required')
    previous=-float('inf')
    for t in trades:
        if not all(math.isfinite(float(t[k])) for k in required[1:]):raise ValueError('nonfinite trade')
        if min(t['price'],t['amount'])<=0:raise ValueError('invalid executed volume')
        if not start.timestamp()*1000<=t['event_ms']<end.timestamp()*1000:raise ValueError('outside anchor')
        if not t['event_ms']<=t['received_ms']<=known.timestamp()*1000:raise ValueError('unavailable trade')
        if t['event_ms']<previous:raise ValueError('out of order')
        previous=t['event_ms']
    seal=hashlib.sha256(json.dumps(trades,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if receipt.get('sha256')!=seal:raise ValueError('source receipt differs')
    p=volume_profile_v2([t['price'] for t in trades],[t['amount'] for t in trades],'OBSERVED_TRADES')
    return dict(status='READY',known_at=known.isoformat(),anchor_start=start.isoformat(),anchor_end=end.isoformat(),anchor_seconds=seconds,source=receipt['source'],venue=receipt['venue'],pair=receipt['pair'],source_sha256=seal,**p)
