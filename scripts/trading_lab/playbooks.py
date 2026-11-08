"""One causal setup/plan kernel for archive scanning, monitoring and native research.

Input dates are candle opens; decisions occur at close. No outcome/fill simulation.
HTF structure reuses the existing strict 2L/2R implementation.
"""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from trading_lab.watchlist import encode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/session3'))
from causal_structure import structure
from local_recovery_convert import aggregate

VERSION = 'multi-playbook-v3.0.2'
FIVE = pd.Timedelta(minutes=5)
COST = .001 + .002 + .0003  # 5bp/side fees, 10bp/side friction + adverse funding allowance


def ms(at):
    return int(pd.Timestamp(at).value // 1_000_000)


def stamp(at):
    return pd.Timestamp(at).isoformat()


def active_levels(frame):
    """Causal seven-day unconsumed pivot map; broken levels are not target walls.

    A close through resistance/support consumes that role. A later role-flip is
    a separate hypothesis, not automatically inferred from a historical price.
    """
    resistance=[];support=[];up=[];down=[]
    for row in frame.to_dict('records'):
        at=pd.Timestamp(row['struct_known_at']);close=float(row['close'])
        resistance=[p for p in resistance if close<=p['price'] and at-pd.Timestamp(p['known_at'])<=pd.Timedelta(days=7)]
        support=[p for p in support if close>=p['price'] and at-pd.Timestamp(p['known_at'])<=pd.Timedelta(days=7)]
        for side,levels,kind in [('high',resistance,'resistance'),('low',support,'support')]:
            known=row.get('swing_'+side+'_known_at')
            if pd.notna(known) and pd.Timestamp(known)==at:
                levels.append(dict(price=float(row['swing_'+side]),known_at=stamp(at),kind=kind,
                                   basis='confirmed_'+side+'_2L2R',pivot_at=stamp(row['swing_'+side+'_pivot_at'])))
        up.append([dict(p) for p in resistance]);down.append([dict(p) for p in support])
    result=frame.copy();result['active_resistances']=up;result['active_supports']=down
    return result


def prepare(five, hours):
    """O(n) causal feature cache, retaining explicit availability on every HTF row."""
    d = five.copy().reset_index(drop=True)
    h = hours.copy().reset_index(drop=True)
    for f, step in [(d, FIVE), (h, pd.Timedelta(hours=1))]:
        if (f.empty or f.date.duplicated().any() or not f.date.is_monotonic_increasing
                or not f.date.diff().iloc[1:].eq(step).all()):
            raise ValueError('GAPPED_OR_UNORDERED_FEATURE_SOURCE')
        if not np.isfinite(f[['open','high','low','close','volume']]).all().all():
            raise ValueError('NONFINITE_FEATURE_SOURCE')
    prev = d.close.shift()
    tr = pd.concat([d.high-d.low, (d.high-prev).abs(), (d.low-prev).abs()], axis=1).max(axis=1)
    d['atr5'] = tr.rolling(14, min_periods=14).mean()
    d['rvol'] = d.volume / d.volume.shift().rolling(20, min_periods=20).mean().replace(0, np.nan)
    d['at'] = d.date + FIVE
    d['prior_high5'] = d.high.shift().rolling(3).max()
    d['prior_low5'] = d.low.shift().rolling(3).min()
    h['ema20'] = h.close.ewm(span=20, adjust=False, min_periods=20).mean()
    h['ema50'] = h.close.ewm(span=50, adjust=False, min_periods=50).mean()
    hp = h.close.shift()
    h['atr'] = pd.concat([h.high-h.low, (h.high-hp).abs(), (h.low-hp).abs()], axis=1).max(axis=1).rolling(14).mean()
    # Pre-existing 24h range, excluding the arming-hour candle.
    h['range_high'] = h.high.shift().rolling(24).max()
    h['range_low'] = h.low.shift().rolling(24).min()
    for lookback in (72,168):
        h[f'high{lookback}'] = h.high.shift().rolling(lookback).max()
        h[f'low{lookback}'] = h.low.shift().rolling(lookback).min()
    h['range_known_at'] = h.date  # previous hour closed at this open
    h = active_levels(structure(h, '1h'))
    h['at'] = h.date + pd.Timedelta(hours=1)
    q = aggregate(hours, '4h')
    q = q.loc[q.components.eq(4)].drop(columns='components').reset_index(drop=True)
    q = active_levels(structure(q, '4h'))
    q['at4'] = q.date + pd.Timedelta(hours=4)
    q['ema20_4'] = q.close.ewm(span=20, adjust=False, min_periods=20).mean()
    q['ema50_4'] = q.close.ewm(span=50, adjust=False, min_periods=50).mean()
    h = pd.merge_asof(h.sort_values('at'), q[['at4','struct_direction','ema20_4','ema50_4','swing_high','swing_low','swing_high_known_at','swing_low_known_at','active_resistances','active_supports']].rename(columns={'struct_direction':'structure4h','swing_high':'swing_high4h','swing_low':'swing_low4h','swing_high_known_at':'swing_high4h_known_at','swing_low_known_at':'swing_low4h_known_at','active_resistances':'active_resistances4h','active_supports':'active_supports4h'}).sort_values('at4'), left_on='at', right_on='at4', direction='backward')
    h['trend1h'] = np.select([h.ema20 > h.ema50, h.ema20 < h.ema50], ['UP','DOWN'], default='UNKNOWN')
    h['trend4h'] = np.select([h.ema20_4 > h.ema50_4, h.ema20_4 < h.ema50_4], ['UP','DOWN'], default='UNKNOWN')
    h['regime'] = np.select([(h.ema20-h.ema50).abs() < .5*h.atr,
                            (h.trend1h=='UP') & (h.struct_direction=='UP'),
                            (h.trend1h=='DOWN') & (h.struct_direction=='DOWN')],
                           ['BALANCE','TREND_UP','TREND_DOWN'], default='TRANSITION')
    return d, h


def discover(symbol, d, h, at, source_id, *, quote_volume_24h=None, btc=None):
    """Reason-coded broad-panel screen; execution metadata remains explicitly unknown."""
    at = pd.Timestamp(at)
    if at.tzinfo is None:
        raise ValueError('UTC_CUTOFF_REQUIRED')
    past = d.loc[d['at'] <= at]
    context = h.loc[h['at'] <= at]
    row = dict(symbol=symbol, as_of=stamp(at), source_id=source_id, feature_version=VERSION,
               historical_membership='PRESELECTED_ARCHIVE_PANEL_NOT_LISTING_CENSUS',
               spread='UNKNOWN', execution_eligibility='UNVERIFIED', reasons=[], setups=[])
    if len(context) < 60 or len(past) < 288 or past['at'].iloc[-1] != at or context['at'].iloc[-1] != at.floor('h'):
        row.update(status='REJECT', reasons=['DATA_GAP_STALE_OR_WARMUP'])
        return row
    c = context.iloc[-1]
    if quote_volume_24h is None:
        # No close*volume approximation is passed as published quote volume.
        row.update(status='REJECT', reasons=['QUOTE_VOLUME_UNAVAILABLE'])
        return row
    atr = float(c.atr); price = float(past.close.iloc[-1])
    row.update(quote_volume_24h=float(quote_volume_24h), price=price, atr1h=atr,
               regime=c.regime, trend1h=c.trend1h, trend4h=c.trend4h,
               structure1h=c.struct_direction, structure4h=c.structure4h,
               htf_known_at=stamp(c['at']), btc_alignment=btc or 'UNAVAILABLE',
               participation=float(past.rvol.iloc[-1]), flow='OHLCV_PARTICIPATION_ONLY')
    if 'activity14d' in c and (not np.isfinite(c.activity14d) or c.activity14d<5_000_000 or c.map4h_ready!=True):
        row.update(status='REJECT',reasons=['INHERITED_SCANNER_ACTIVITY_OR_4H_READINESS'])
        return row
    if 'activity14d' in c:
        row['median_daily_quote_14d']=float(c.activity14d)
        row['screen_known_at']=stamp(c.screen_known_at)
    if quote_volume_24h < 5_000_000:
        row.update(status='REJECT', reasons=['LOW_ROLLING_QUOTE_VOLUME'])
        return row
    if not .001 <= atr/price <= .08:
        row.update(status='REJECT', reasons=['VOLATILITY_OUTSIDE_RESEARCH_RANGE'])
        return row
    high, low = float(c.range_high), float(c.range_low)
    known = c.range_known_at
    row.update(range_high=high, range_low=low, range_known_at=stamp(known),
               distance_to_boundary_atr=min(abs(price-high),abs(price-low))/atr)
    # Far from meaningful location is retained as INTERESTING; no invented watch level.
    if row['distance_to_boundary_atr'] > 2.0:
        row.update(status='INTERESTING', reasons=['MIDRANGE_OR_FAR_FROM_BOUNDARY_NO_QUALIFIED_SETUP'])
        return row
    obstacles=[]
    for name,timeframe in [('active_resistances','1h'),('active_supports','1h'),
                           ('active_resistances4h','4h'),('active_supports4h','4h')]:
        for level in c[name]:
            if pd.Timestamp(level['known_at'])<=at:
                obstacles.append(dict(level,basis=timeframe+'_'+level['basis']))
    for n in (72,168):
        for side in ('high','low'):
            if pd.notna(c[f'{side}{n}']):
                obstacles.append(dict(price=float(c[f'{side}{n}']),known_at=stamp(known),basis=f'prior{n}h_{side}',kind='resistance' if side=='high' else 'support'))
    # The prior 24h high/low and midpoint were all known before discovery.
    obstacles += [dict(price=v,known_at=stamp(known),basis=b,kind='resistance' if b.endswith('high') else 'support' if b.endswith('low') else 'both') for v,b in [(high,'prior24h_high'),(low,'prior24h_low'),((high+low)/2,'prior24h_midpoint')]]
    for side in ('long','short'):
        for family in ('BREAKOUT_RETEST','SWEEP_RECLAIM'):
            boundary = (high if side=='long' else low) if family=='BREAKOUT_RETEST' else (low if side=='long' else high)
            # Near a different edge does not justify every family; keep independent feasible hypotheses.
            if abs(price-boundary) > 2*atr:
                continue
            opposing = 'DOWN' if side=='long' else 'UP'
            fresh_opposition = c.trend1h==opposing and c.trend4h==opposing and c.struct_direction==opposing
            setup = dict(symbol=symbol, side=side, family=family, boundary=boundary,
                         boundary_known_at=stamp(known), armed_at=stamp(at), expires_at=stamp(at+pd.Timedelta(hours=3)),
                         atr1h=atr, obstacles=obstacles, regime=c.regime, trend1h=c.trend1h,
                         trend4h=c.trend4h, source_id=source_id, feature_version=VERSION,
                         htf_reaction_context='PREKNOWN_RANGE_BOUNDARY', fresh_opposition=bool(fresh_opposition),
                         hypothesis=('Acceptance then retest holds outside boundary' if family=='BREAKOUT_RETEST' else 'Excursion reclaims boundary; later confirmation'),
                         opposition=('Failed breakout closes back inside' if family=='BREAKOUT_RETEST' else 'Genuine continuation accepts beyond boundary'),
                         confirmation='Completed 5m playbook event; then geometry/cost diagnostics')
            setup['setup_key']=hashlib.sha256(encode(setup).encode()).hexdigest()
            row['setups'].append(setup)
    row.update(status='DEVELOPING_WATCH' if row['setups'] else 'INTERESTING',
               reasons=['KNOWN_LEVEL_PROXIMITY','TRIGGER_NOT_REQUIRED_FOR_WATCH'] if row['setups'] else ['NO_QUALIFIED_SETUP'])
    return row


def initial_state():
    return dict(phase='WATCH', accepted=0, excursion=None, event_at=None, last_at=None,
                acceptance_extreme=None, rejection_extreme=None)


def advance(setup, state, bar, *, variant='retest'):
    """Pure single-completed-bar transition; caller validates source/cutoff/continuity."""
    state=dict(state); at=pd.Timestamp(bar['at']); armed=pd.Timestamp(setup['armed_at'])
    if at <= armed:
        raise ValueError('TRIGGER_MUST_FOLLOW_ARMING')
    if state['last_at'] and at != pd.Timestamp(state['last_at'])+FIVE:
        raise ValueError('GAPPED_SETUP_HISTORY')
    if state['phase'] in ('TRIGGER_CANDIDATE','INVALIDATED','EXPIRED'):
        return state, None
    state['last_at']=stamp(at)
    if at >= pd.Timestamp(setup['expires_at']):
        state['phase']='EXPIRED';return state,dict(state='EXPIRED',reason='SETUP_TIME_EXPIRY',at=stamp(at))
    sign=1 if setup['side']=='long' else -1
    boundary=setup['boundary']; atr=setup['atr1h']; close=float(bar['close'])
    low,high=float(bar['low']),float(bar['high'])
    good=sign*(close-boundary)>0
    extreme=low if sign==1 else high
    trigger=False;reason='WAITING_FOR_PLAYBOOK_TRIGGER'
    if setup['family']=='BREAKOUT_RETEST':
        if good:
            state['accepted']+=1
            if state['acceptance_extreme'] is None:
                state['acceptance_extreme']=extreme
            else:
                state['acceptance_extreme']=min(state['acceptance_extreme'],low) if sign==1 else max(state['acceptance_extreme'],high)
            if state['phase']=='WATCH' and state['accepted']>=2:
                state.update(phase='ACCEPTED',event_at=stamp(at));reason='TWO_CLOSE_ACCEPTANCE'
                trigger=variant=='immediate'
            elif state['phase']=='ACCEPTED' and at>pd.Timestamp(state['event_at']):
                touch=low<=boundary+.10*atr if sign==1 else high>=boundary-.10*atr
                if touch and sign*(close-boundary)<=.75*atr and float(bar['rvol'])>=1.0:
                    trigger=True;reason='LATER_RETEST_DEFENSE'
        else:
            state['accepted']=0
            if state['phase']=='ACCEPTED':
                state['phase']='INVALIDATED';reason='ACCEPTANCE_FAILED_BACK_INSIDE'
        if good and sign*(close-boundary)>1.25*atr:
            trigger=False;reason='TOO_LATE_NO_CHASE'
    else:
        excursion=(boundary-low) if sign==1 else (high-boundary)
        if state['phase']=='WATCH' and .05*atr <= excursion <= 1.5*atr and good:
            state.update(phase='RECLAIMED',excursion=extreme,event_at=stamp(at),rejection_extreme=high if sign==1 else low)
            reason='EXCURSION_AND_COMPLETED_RECLAIM'
            trigger=variant=='early'
        elif state['phase']=='RECLAIMED':
            if not good or sign*(extreme-state['excursion'])<-.2*atr:
                state['phase']='INVALIDATED';reason='RECLAIM_FAILED_OR_NEW_EXTREME'
            elif at>pd.Timestamp(state['event_at']):
                confirmed=close>state['rejection_extreme'] if sign==1 else close<state['rejection_extreme']
                if confirmed and float(bar['rvol'])>=1.0:
                    trigger=True;reason='LATER_5M_RECLAIM_CONFIRMATION'
        if setup['fresh_opposition']:
            trigger=False
            if state['phase']=='RECLAIMED':reason='FRESH_OPPOSING_HTF_IMPULSE_REQUIRES_STRUCTURE_SHIFT'
    if trigger:
        state['phase']='TRIGGER_CANDIDATE'
    event=dict(state=state['phase'],reason=reason,at=stamp(at))
    return state,event


def plan_for(setup, state, bar, variant='retest'):
    at=pd.Timestamp(bar['at']); sign=1 if setup['side']=='long' else -1
    entry=float(bar['close']);atr=setup['atr1h']
    if setup['family']=='SWEEP_RECLAIM':
        anchor=state['excursion']
    else:
        anchor=min(float(bar['low']),setup['boundary']) if sign==1 else max(float(bar['high']),setup['boundary'])
    stop=anchor-sign*.15*atr
    risk=sign*(entry-stop)/entry
    levels=[o for o in setup['obstacles'] if o.get('kind','both') in ('both','resistance' if sign==1 else 'support') and sign*(o['price']-entry)>0 and pd.Timestamp(o['known_at'])<=pd.Timestamp(setup['armed_at'])]
    levels.sort(key=lambda o: sign*(o['price']-entry))
    reasons=[]
    if not .0025<=risk<=.025:
        reasons.append('STRUCTURAL_STOP_POLICY_CONFLICT' if risk>.025 else 'STOP_TOO_TIGHT_OR_INVERTED')
    if not levels:
        reasons.append('NO_PREKNOWN_OBJECTIVE');target=None;rr=None
    else:
        objective=levels[0]
        # Exit before first known obstacle; never delete nearer structure to get preferred R.
        target=objective['price']-sign*.05*atr
        reward=sign*(target-entry)/entry
        rr=(reward-COST)/(risk+COST) if risk+COST>0 else None
        if rr is None or rr<1.25:reasons.append('NEARBY_OBSTACLE_OR_COST_ECONOMICS')
        if abs(target-entry)>6*atr:reasons.append('OBJECTIVE_TOO_FAR_FOR_HOLD_RESEARCH_POLICY')
    result=dict(decision_id=hashlib.sha256((setup['setup_key']+stamp(at)+variant).encode()).hexdigest(),
                setup_key=setup['setup_key'],symbol=setup['symbol'],family=setup['family'],variant=variant,
                side=setup['side'],armed_at=setup['armed_at'],decision_at=stamp(at),earliest_order_at=stamp(at),
                expires_at=stamp(at+FIVE),entry=entry,stop=stop,target=target,
                boundary=setup['boundary'],boundary_known_at=setup['boundary_known_at'],atr15=atr,atr1h=atr,atr_reference_timeframe='1h',
                next_obstacles=levels[:3],
                stop_anchor=anchor,stop_buffer=.15*atr,risk_fraction=risk,net_rr=rr,
                objective=levels[0] if levels else None,source_id=setup['source_id'],
                admission_cost_allowance=COST,max_deviation=.0015,max_hold_minutes=480 if setup['family']=='BREAKOUT_RETEST' else 240,
                notional_cap=25,leverage=1,execution_authority='NONE',
                native_risk='AGENT_NOT_VERIFIED',risk_qualification='NO_ACTION',
                diagnostics='REJECT' if reasons else 'GEOMETRY_PASS_RESEARCH_ONLY',reasons=reasons,
                feature_version=VERSION)
    return result


def research_symbol(symbol, d, h, quote, start, end, source_id, variant='retest', btc=None):
    """Hourly cross-section inputs and chronological 5m same-kernel updates."""
    start,end=pd.Timestamp(start),pd.Timestamp(end)
    if start.tzinfo is None:start=start.tz_localize('UTC')
    if end.tzinfo is None:end=end.tz_localize('UTC')
    d=d.loc[(d['at']>=start-pd.Timedelta(days=2)) & (d['at']<=end)].reset_index(drop=True)
    q=quote.set_index('at')['quote24']
    hidx=h.set_index('at'); active={}; scans=[];events=[];plans=[]
    for bar in d.to_dict('records'):
        at=bar['at']
        if at<start:continue
        # Update earlier hypotheses before adding new ones at this boundary.
        for key,(setup,state) in list(active.items()):
            state,event=advance(setup,state,bar,variant=variant)
            active[key]=(setup,state)
            if event and (event['state']!='WATCH' or event['reason']!='WAITING_FOR_PLAYBOOK_TRIGGER'):
                events.append(dict(setup_key=key,**event))
            if state['phase']=='TRIGGER_CANDIDATE':
                plans.append(plan_for(setup,state,bar,variant))
            if state['phase'] in ('TRIGGER_CANDIDATE','INVALIDATED','EXPIRED'):
                del active[key]
        if at.minute==0 and at<=end-pd.Timedelta(hours=16):
            volume=float(q.get(at,np.nan))
            alignment=None
            if btc is not None:
                b=btc.loc[btc['at']<=at]
                alignment=None if b.empty else {'trend1h':b.iloc[-1].trend1h,'known_at':stamp(b.iloc[-1]['at'])}
            scan=discover(symbol,d,h,at,source_id,quote_volume_24h=volume,btc=alignment)
            scans.append(scan)
            for setup in scan['setups']:
                active[setup['setup_key']]=(setup,initial_state())
    return scans,events,plans
