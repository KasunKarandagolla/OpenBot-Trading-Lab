"""Pinned casebook replay only. These observations cannot authorize orders.

The pins establish identity with the checked-in casebook, not live TLS or a fresh
download from Binance. The casebook records earlier archive verification; this
module does not independently reverify those archives.
"""
import hashlib
import json
import math
import re
from pathlib import Path

from trading_lab.watchlist import create, encode

ROOT = Path(__file__).resolve().parents[2]
PINS = Path(__file__).with_name('case_pins.json')
WIDTH = 300_000


def load_case(case_id):
    pins = json.loads(PINS.read_text())
    if not isinstance(case_id, str) or not re.fullmatch(r'B\d\d', case_id) or case_id not in pins:
        raise ValueError('UNKNOWN_PINNED_CASE')
    directory = ROOT / 'evidence/skills-v2/20261107/casebook/agent-inputs' / case_id
    raw = (directory / 'input.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != pins[case_id]:
        raise ValueError('CASE_INPUT_HASH_MISMATCH')
    case = json.loads(raw)
    if case.get('case_id') != case_id or case.get('venue') != 'BINANCE_PUBLIC_USDM':
        raise ValueError('CASE_IDENTITY_MISMATCH')
    record = case['numeric']['5m']
    bars = record['bars']
    if (record.get('timeframe') != '5m' or
            hashlib.sha256(encode(bars).encode()).hexdigest() != record['bars_sha256'] or
            not isinstance(bars, list) or len(bars) < 25):
        raise ValueError('CASE_BAR_HASH_OR_INTERVAL_MISMATCH')
    return case, digest


def available_bars(bars, as_of_ms):
    """Validate only the completed prefix; later data quality is not known yet."""
    result, previous = [], None
    for b in bars:
        if not isinstance(b, list) or not b or type(b[0]) is not int:
            raise ValueError('CASE_BAR_SHAPE')
        if b[0] + WIDTH > as_of_ms:
            break
        if (not isinstance(b, list) or len(b) != 12 or type(b[0]) is not int or
                type(b[6]) is not int or b[0] % WIDTH or b[6] != b[0] + WIDTH - 1 or
                (previous is not None and b[0] != previous + WIDTH)):
            raise ValueError('CASE_BAR_GAP_OR_TIME_MISMATCH')
        op, high, low, close = map(float, b[1:5])
        if not all(math.isfinite(v) and v > 0 for v in (op, high, low, close)) or high < max(op, low, close) or low > min(op, high, close):
            raise ValueError('CASE_INVALID_OHLC')
        previous = b[0]
        result.append(b)
    if not result or result[-1][6] + 1 != as_of_ms // WIDTH * WIDTH:
        raise ValueError('CASE_STALE_OR_INCOMPLETE_PREFIX')
    return result


def create_case_setup(db, definition, case_id):
    case, digest = load_case(case_id)
    rows = case['numeric']['5m']['bars']
    cutoff = definition.get('source_cutoff_ms')
    if (definition.get('symbol') != case['symbol'] or definition.get('venue') != case['venue'] or
            definition.get('source_sha256') != case['numeric']['5m']['bars_sha256'] or
            type(cutoff) is not int or cutoff % WIDTH or cutoff >= case['cutoff_ms']):
        raise ValueError('SETUP_SOURCE_IDENTITY_OR_CUTOFF_MISMATCH')
    if len(available_bars(rows, cutoff)) < 25:
        raise ValueError('INSUFFICIENT_PRE_DISCOVERY_BARS')
    return create(db, definition, _case_binding=(case_id, digest))


def expire(db, setup_id, as_of_ms):
    """Reconcile expiry by elapsed replay time, including when no new bar exists."""
    if type(as_of_ms) is not int:
        raise ValueError('INVALID_TIME')
    db.execute('BEGIN IMMEDIATE')
    try:
        row = db.execute('SELECT definition FROM setups WHERE id=?', (setup_id,)).fetchone()
        if not row:
            raise ValueError('UNKNOWN_SETUP')
        definition = json.loads(row[0])
        prior = db.execute('SELECT at_ms,state FROM events WHERE setup_id=? ORDER BY seq DESC LIMIT 1', (setup_id,)).fetchone()
        if as_of_ms < prior[0]:
            raise ValueError('TIME_MOVED_BACKWARDS')
        if as_of_ms >= definition['expires_ms'] and prior[1] not in ('EXPIRED', 'INVALIDATED'):
            db.execute('INSERT INTO events(setup_id,event_key,at_ms,state,body) VALUES(?,?,?,?,?)',
                       (setup_id, 'expiry', as_of_ms, 'EXPIRED', encode({'reason': 'ELAPSED_TIME', 'effective_expiry_ms': definition['expires_ms'], 'research_only': True})))
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK')
        raise


def observe_case(db, setup_id, *, as_of_ms):
    binding = db.execute('SELECT case_id,input_sha256 FROM case_bindings WHERE setup_id=?', (setup_id,)).fetchone()
    if not binding:
        raise ValueError('UNBOUND_LEGACY_SETUP')
    case, digest = load_case(binding[0])
    if digest != binding[1] or type(as_of_ms) is not int or as_of_ms > case['cutoff_ms']:
        raise ValueError('CASE_BINDING_OR_CUTOFF_MISMATCH')
    db.execute('BEGIN IMMEDIATE')
    try:
        definition = json.loads(db.execute('SELECT definition FROM setups WHERE id=?', (setup_id,)).fetchone()[0])
        if (definition['symbol'] != case['symbol'] or definition['venue'] != case['venue'] or
                definition['source_sha256'] != case['numeric']['5m']['bars_sha256']):
            raise ValueError('CASE_SOURCE_MISMATCH')
        last = db.execute('SELECT at_ms,state FROM events WHERE setup_id=? ORDER BY seq DESC LIMIT 1', (setup_id,)).fetchone()
        if as_of_ms < last[0]:
            raise ValueError('TIME_MOVED_BACKWARDS')
        if last[1] in ('EXPIRED', 'INVALIDATED'):
            db.execute('COMMIT')
            return
        rows = available_bars(case['numeric']['5m']['bars'], as_of_ms)
        history = [b for b in rows if b[6] + 1 <= definition['source_cutoff_ms']][-24:]
        if len(history) != 24 or history[-1][6] + 1 != definition['source_cutoff_ms']:
            raise ValueError('CASE_DISCOVERY_CUTOFF_MISMATCH')
        # A prior-range-derived observation distance, not a validated entry rule.
        approach_distance = sum(float(b[2]) - float(b[3]) for b in history) / len(history)
        subsequent = [b for b in rows if definition['source_cutoff_ms'] < b[6] + 1 <= as_of_ms]
        for i, bar in enumerate(subsequent):
            at = bar[6] + 1
            if at <= last[0]:
                continue
            if at != last[0] + WIDTH:
                raise ValueError('GAPPED_SETUP_HISTORY')
            if at >= definition['expires_ms']:
                break
            close, high, low = float(bar[4]), float(bar[2]), float(bar[3])
            level, invalidation = float(definition['level']), float(definition['invalidation'])
            long = definition['direction'] == 'LONG'
            invalid = close <= invalidation if long else close >= invalidation
            reclaim = low < level < close if long else high > level > close
            accepted = len(subsequent[:i]) >= 2 and all((float(x[4]) > level if long else float(x[4]) < level) for x in subsequent[i-2:i])
            retest = accepted and (low <= level < close if long else high >= level > close)
            family = definition['family']
            if invalid:
                state, reason = 'INVALIDATED', 'CLOSE_THROUGH_INVALIDATION'
            elif family == 'SWEEP_RECLAIM' and reclaim:
                state, reason = 'TRIGGER_CANDIDATE', 'EXCURSION_AND_RECLAIM_SAME_BAR'
            elif family == 'BREAKOUT_RETEST' and retest:
                state, reason = 'TRIGGER_CANDIDATE', 'TWO_CLOSE_ACCEPTANCE_AND_RETEST'
            elif family == 'HTF_REACTION' and (low <= level < close if long else high >= level > close):
                state, reason = 'REVIEW_REQUIRED', 'LEVEL_TOUCH_AND_CLOSE_REQUIRES_CONTEXT'
            elif abs(close - level) <= approach_distance:
                state, reason = 'APPROACHING', 'WITHIN_PRIOR_MEAN_BAR_RANGE'
            else:
                state, reason = 'WATCHING', 'NO_PLAYBOOK_EVENT'
            body = {'case_id': binding[0], 'input_sha256': digest,
                    'bar_sha256': hashlib.sha256(encode(bar).encode()).hexdigest(),
                    'reason': reason, 'close': close, 'feature_version': definition['feature_version'],
                    'research_only': True, 'execution_authority': 'NONE'}
            db.execute('INSERT INTO events(setup_id,event_key,at_ms,state,body) VALUES(?,?,?,?,?)',
                       (setup_id, 'bar:' + str(at), at, state, encode(body)))
            last = (at, state)
            if invalid:
                break
        if as_of_ms >= definition['expires_ms'] and last[1] != 'INVALIDATED':
            db.execute('INSERT OR IGNORE INTO events(setup_id,event_key,at_ms,state,body) VALUES(?,?,?,?,?)',
                       (setup_id, 'expiry', definition['expires_ms'], 'EXPIRED', encode({'reason': 'ELAPSED_TIME', 'research_only': True})))
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK')
        raise
