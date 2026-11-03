"""Completed-candle state machine. Candle dates are opens, decisions are closes.

Strict pivots require left/right distinct lower highs or higher lows. A confirmed
level is never backfilled to its pivot row. Breaks inspect levels available before
this candle, consume each level once, and use close (wick excursions are separate).
An initial break establishes direction without inventing a preceding trend.
"""
import numpy as np
import pandas as pd


def structure(frame, timeframe='15m', left=2, right=2):
    if timeframe not in ('15m', '1h') or left < 1 or right < 1:
        raise ValueError('unsupported structure window/timeframe')
    step = pd.Timedelta(minutes=15) if timeframe == '15m' else pd.Timedelta(hours=1)
    d = frame.copy().reset_index(drop=True)
    state = 'UNKNOWN'; levels = {}; consumed = set(); history = []; records = []
    last_bos = last_choch = None; previous = None
    for i, row in d.iterrows():
        at = pd.Timestamp(row.date); known = at + step
        vals = np.array([row.open, row.high, row.low, row.close, row.volume], dtype=float)
        clean = (not pd.isna(at) and np.isfinite(vals).all() and (vals[:4] > 0).all()
                 and vals[4] >= 0 and row.high >= max(row.open, row.close, row.low)
                 and row.low <= min(row.open, row.close, row.high))
        gap = previous is not None and at - previous != step
        if gap or not clean:
            state = 'UNKNOWN'; levels = {}; consumed = set(); history = []
            last_bos = last_choch = None
        prior = dict(levels)
        event = None; broken = None
        up = clean and 'high' in prior and prior['high']['known_at'] <= at and 'high' not in consumed and row.close > prior['high']['price']
        down = clean and 'low' in prior and prior['low']['known_at'] <= at and 'low' not in consumed and row.close < prior['low']['price']
        if up != down:
            direction = 'UP' if up else 'DOWN'; side = 'high' if up else 'low'
            event = 'INITIAL_BREAK' if state == 'UNKNOWN' else ('BOS' if state == direction else 'CHOCH')
            broken = prior[side]; consumed.add(side); state = direction
            if event == 'BOS': last_bos = known
            if event == 'CHOCH': last_choch = known
        elif up and down:
            state = 'UNKNOWN'; consumed.update(('high', 'low')); event = 'AMBIGUOUS_BREAK'
        pivot_event = None
        if clean:
            history.append((i, row))
            history = history[-(left+right+1):]
            if len(history) == left+right+1:
                _, pivot = history[left]
                others = [r for j, (_, r) in enumerate(history) if j != left]
                for side, qualifies in [('high', all(pivot.high > r.high for r in others)),
                                        ('low', all(pivot.low < r.low for r in others))]:
                    if qualifies:
                        p = {'pivot_at':pd.Timestamp(pivot.date), 'known_at':known,
                             'first_eligible_decision_at':known, 'price':float(pivot[side]),
                             'direction':side.upper(), 'confirmation_bars':right, 'source_timeframe':timeframe}
                        levels[side] = p; consumed.discard(side); pivot_event = p
        r = {'struct_direction':state, 'struct_known_at':known, 'struct_event':event,
             'struct_broken_level_known_at':None if broken is None else broken['known_at'],
             'struct_last_bos_at':last_bos, 'struct_last_choch_at':last_choch,
             'struct_valid':clean and not gap, 'struct_pivot_event':pivot_event,
             'struct_wick_high':bool(clean and 'high' in prior and row.high > prior['high']['price'] and not up),
             'struct_wick_low':bool(clean and 'low' in prior and row.low < prior['low']['price'] and not down)}
        for side in ('high', 'low'):
            for label, value in [('swing', levels.get(side)), ('prior_swing', prior.get(side))]:
                prefix = f'{label}_{side}'
                r[prefix] = None if value is None else value['price']
                r[prefix+'_pivot_at'] = None if value is None else value['pivot_at']
                r[prefix+'_known_at'] = None if value is None else value['known_at']
                r[prefix+'_active'] = value is not None and side not in consumed
        records.append(r); previous = at
    features = pd.DataFrame(records, index=d.index)
    for col in features:
        if col.endswith('_at'):
            features[col] = pd.to_datetime(features[col], utc=True).dt.as_unit('ns')
        elif col in ('swing_high','swing_low','prior_swing_high','prior_swing_low'):
            features[col] = pd.to_numeric(features[col]).astype(float)
        elif col == 'struct_event':
            features[col] = features[col].astype(object)
    return pd.concat([d, features], axis=1)


def closed_merge(base, hourly):
    """Same availability as native informative merge: 00h known at01h close.

    Explicit backward join on close times prevents partial-hour use even when
    input is truncated at an arbitrary as-of timestamp. Caller validates gaps.
    """
    b = base.copy(); h = hourly.copy()
    b['_decision'] = b.date + pd.Timedelta(minutes=15)
    h['_hour_known'] = h.date + pd.Timedelta(hours=1)
    h = h.rename(columns={c:c+'_1h' for c in h if c != '_hour_known'})
    return pd.merge_asof(b.sort_values('_decision'), h.sort_values('_hour_known'),
                         left_on='_decision', right_on='_hour_known', direction='backward').drop(columns=['_decision','_hour_known'])
