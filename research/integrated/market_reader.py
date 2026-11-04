"""Small causal market reader. Facts and contradictions have separate authority."""
import math
import pandas as pd
from setup_features import levels, COST

def finite(value):
    try: return math.isfinite(float(value))
    except (ValueError, TypeError): return False

def objective(row, side, entry, stop):
    sign=1 if side=='long' else -1
    candidates=levels(row,side,False)
    # One numeric barrier can have several provenance labels; don't count votes.
    distinct=[]
    for item in candidates:
        if not any(abs(item['price']-x['price'])<=max(abs(item['price'])*1e-10,1e-15) for x in distinct): distinct.append(item)
    if not distinct: return None, 'NO_KNOWN_OBJECTIVE'
    first=distinct[0]
    risk=sign*(entry-stop)/entry; reward=sign*(first['price']-entry)/entry
    if not .003<=risk<=.025: return first, 'STRUCTURAL_STOP_OUTSIDE_BOUNDS'
    if sign*(first['price']-entry)>6*float(row.atr14): return first, 'OBJECTIVE_BEYOND_6ATR'
    if (reward-COST)/(risk+COST)<1.25: return first, 'FIRST_OBSTACLE_INSUFFICIENT_AFTER_COST_REWARD'
    return first, 'PASS'

def interpret(row, side, playbook, entry, stop, relative_btc=None):
    sign=1 if side=='long' else -1; direction='UP' if sign==1 else 'DOWN'
    at=pd.Timestamp(row.date)+pd.Timedelta(minutes=15)
    known_hour=pd.Timestamp(row.date_1h)+pd.Timedelta(hours=1) if pd.notna(row.get('date_1h')) else None
    known4h=row.get('known4h')
    facts=[];against=[]
    flags=all(pd.notna(row.get(k)) and bool(row.get(k)) for k in ('setup_valid','map4h_ready'))
    quality=(flags
        and known_hour is not None and known_hour<=at and pd.notna(known4h) and pd.Timestamp(known4h)<=pd.Timestamp(row.date))
    first,geometry=objective(row,side,entry,stop) if quality else (None,'CRITICAL_SOURCE_UNKNOWN')
    hdir=row.get('struct_direction_1h','UNKNOWN'); pdir=row.get('direction_4h','UNKNOWN')
    if hdir==direction: facts.append('CONFIRMED_1H_STRUCTURE_ALIGNED')
    else: against.append('1H_STRUCTURE_NOT_ALIGNED')
    if pdir in ('UP','DOWN') and pdir!=direction: against.append('4H_STRUCTURE_OPPOSED')
    ema=sign*(float(row.get('ema20_1h',float('nan')))-float(row.get('ema50_1h',float('nan'))))>0
    (facts if ema else against).append('HOURLY_EMA_ALIGNED' if ema else 'HOURLY_EMA_CONTRADICTS')
    zone=float(row.get('prior_vwap',float('nan')))
    extension=abs(entry-zone)/float(row.atr14) if finite(zone) else None
    if extension is None: against.append('DEFENDED_VWAP_UNKNOWN')
    elif extension>2.5: against.append('EXTENDED_FROM_DEFENDED_LOCATION')
    if finite(relative_btc): (facts if sign*relative_btc>=0 else against).append('BTC_RELATIVE_SUPPORT' if sign*relative_btc>=0 else 'BTC_RELATIVE_CONTRADICTION')
    allowed=quality and geometry=='PASS'
    if playbook=='continuation': allowed=allowed and hdir==direction and '4H_STRUCTURE_OPPOSED' not in against and extension is not None and extension<=2.5
    # Reversals retain an independent external-sweep recipe, not a continuation label.
    status='QUALIFIED_RESEARCH' if allowed else ('UNKNOWN' if not quality else 'NO_TRADE')
    return dict(as_of=at.isoformat(),status=status,primary_hypothesis=playbook,
        alternative='LOCAL_CORRECTION_IN_PARENT_TREND' if playbook=='reversal' else 'DEFENSE_FAILS_OR_RANGE_CONTINUES',
        structure_1h=hdir,structure_4h=pdir,hour_known_at=known_hour.isoformat() if known_hour is not None else None,
        map4h_known_at=pd.Timestamp(known4h).isoformat() if pd.notna(known4h) else None,
        trend=dict(adx=float(row.adx_1h) if finite(row.get('adx_1h')) else None,ema_aligned=bool(ema)),
        balance=bool(row.get('balance_1h',False)),volatility_atr_fraction=float(row.atr14/entry),
        extension_atr=extension,range_location=float((entry-row.range_low_1h)/(row.range_high_1h-row.range_low_1h)) if finite(row.get('range_high_1h')) and row.range_high_1h>row.range_low_1h else None,
        relative_btc=float(relative_btc) if finite(relative_btc) else None,relative_volume=float(row.rvol),
        supporting=facts,contradicting=against,first_objective=first,geometry_reason=geometry,
        next_required='COMPLETED_DEFENDED_REACTION_AND_NATIVE_RISK',structural_invalidation=stop,
        data_quality='COMPLETED_OHLCV' if quality else 'UNKNOWN',flow='UNKNOWN',profile='NOT_USED',execution_permission='NONE')

def reprice(plan, price, policy):
    """Frozen stop and target; price alternatives must pass original risk rules."""
    from policy_features import execution_plan
    g=dict(plan,reference=float(price),entry_policy=policy,policy_id='integrated-r1')
    return execution_plan(g,float(price),pd.Timestamp(g['available_at']))

def continuation_failure(plan, rows):
    """Completed original defended-zone failure with opposing local structure."""
    if len(rows)<2 or not finite(plan.get('boundary')): return False
    sign=1 if plan['side']=='long' else -1
    return (all(sign*(r.close-plan['boundary'])<-.15*plan['atr_at_signal'] for _,r in rows.tail(2).iterrows())
        and rows.iloc[-1].get('struct_direction')==('DOWN' if sign==1 else 'UP'))
