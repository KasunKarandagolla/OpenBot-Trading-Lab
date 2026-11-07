"""Reproduce a bounded casebook replay; development evidence, no trade simulation."""
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, 'scripts')
from trading_lab.case_monitor import create_case_setup, load_case, observe_case
from trading_lab.watchlist import connect

results = []
with tempfile.TemporaryDirectory() as root:
    db = connect(root)
    for case_id in ('B01', 'B02', 'B03'):
        case, input_digest = load_case(case_id)
        bars = case['numeric']['5m']['bars']
        past = bars[276:300]
        cutoff = past[-1][6] + 1
        high = max(float(b[2]) for b in past)
        low = min(float(b[3]) for b in past)
        setups = (('SWEEP_RECLAIM', 'LONG', low, low - (high-low)),
                  ('SWEEP_RECLAIM', 'SHORT', high, high + (high-low)),
                  ('BREAKOUT_RETEST', 'LONG', high, low),
                  ('BREAKOUT_RETEST', 'SHORT', low, high))
        for family, direction, level, invalidation in setups:
            definition = dict(symbol=case['symbol'], venue=case['venue'], direction=direction,
                family=family, source_cutoff_ms=cutoff,
                source_sha256=case['numeric']['5m']['bars_sha256'], level=level,
                invalidation=invalidation, expires_ms=cutoff+49*300000,
                hypothesis='Price may react at a prior 24-bar extreme.',
                opposition='Price may move through the reference without a usable reaction.',
                confirmation=('Excursion and close back through level.' if family == 'SWEEP_RECLAIM'
                              else 'Two closes beyond level followed by retest and close beyond.'),
                feature_version='case-monitor-v1')
            sid = create_case_setup(db, definition, case_id)
            # Advance one completed bar at a time; no bar beyond the requested as-of is used.
            for bar in bars[300:348]:
                observe_case(db, sid, as_of_ms=bar[6]+1)
            events = [dict(at_ms=r[0], state=r[1], reason=json.loads(r[2]).get('reason'))
                      for r in db.execute('SELECT at_ms,state,body FROM events WHERE setup_id=? ORDER BY seq', (sid,))]
            results.append(dict(case_id=case_id, input_sha256=input_digest, symbol=case['symbol'],
                                direction=direction, family=family, setup_id=sid, cutoff_ms=cutoff,
                                level=level, invalidation=invalidation, events=events,
                                counts=dict(Counter(e['state'] for e in events))))
    db.close()
    db = connect(root)
    recovered = db.execute('SELECT COUNT(*) FROM setups').fetchone()[0]
    db.close()
summary = {'status': 'PARTIAL_HISTORICAL_RESEARCH_ONLY', 'setups_recovered_after_restart': recovered,
           'limitations': ['Not broad discovery or an unseen holdout', 'Previously studied, pinned casebook exports',
               'Case hashes establish repository identity; original Binance archive verification was inherited',
               'Historical eligibility, spread, fill, funding and account information remain unknown',
               'Trigger candidates are research observations, not trade plans or execution authorization'],
           'setups': results}
out = Path('evidence/session2-partial/case-replay.json')
out.write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
print(json.dumps([{'symbol': x['symbol'], 'family': x['family'], 'direction': x['direction'], 'counts': x['counts']} for x in results], indent=2))
