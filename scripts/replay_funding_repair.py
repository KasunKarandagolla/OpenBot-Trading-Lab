"""Native replay of the audit's known partial-fill defect on exact old sources.

Separate from the recent cohort. Same old recipe, schedule, fees and candle
window in both arms; only native funding event ownership changes. No paper CLI.
"""
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from foundation_common import ROOT, paths, read, write, sha, now


def one(run_id, variant):
    if variant not in ('original', 'event-once'): raise ValueError('unknown funding control')
    from bonus_common import stage
    from master_native import native_config
    from freqtrade.commands import Arguments
    from freqtrade.commands.optimize_commands import setup_optimize_configuration
    from freqtrade.enums import RunMode
    from freqtrade.optimize.backtesting import Backtesting
    from research.foundation.funding import EventOnceFunding
    out, _ = paths(run_id)
    dest = out/'funding-replay'
    registration = read(dest/'registration.json')
    for path, digest in registration['source_hashes'].items():
        if sha(ROOT/path) != digest: raise ValueError('funding replay source changed')
    manifest = read(ROOT/'evidence/bonus/source-manifest.json')
    for row in manifest['files']:
        if sha(ROOT/row['path']) != row['sha256']: raise ValueError('old source identity differs')
    cfg = native_config('RouterOnlyV1')
    cfg.update(strategy='RouterOnlyM1V1', strategy_path=str(stage()), position_adjustment_enable=True)
    cfg_path = ROOT/'work/funding-replay'/run_id/(variant+'.json'); write(cfg_path, cfg)
    results = ROOT/'user_data/backtest_results/funding-replay'/run_id/variant
    results.mkdir(parents=True)
    args = ['backtesting', '--config', str(cfg_path), '--datadir', str(ROOT/'user_data/data/bonus/gate'),
        '--timerange', '20260805-20261030', '--fee', '0.0006', '--enable-protections', '--cache', 'none',
        '--export', 'trades', '--backtest-directory', str(results)]
    config = setup_optimize_configuration(Arguments(args).get_parsed_arg(), RunMode.BACKTEST)
    class Repaired(EventOnceFunding, Backtesting): pass
    runner = (Backtesting if variant == 'original' else Repaired)(config)
    runner.start()
    archive = results/read(results/'.last_result.json')['latest_backtest']
    with zipfile.ZipFile(archive) as bundle:
        member = next(n for n in bundle.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
        (dest/(variant+'.json')).write_bytes(bundle.read(member))


def run(run_id):
    import pandas as pd
    from bonus_funding_audit import event_bounds
    from bonus_data import frame
    from bonus_common import spec
    out, _ = paths(run_id); dest = out/'funding-replay'; dest.mkdir()
    write(dest/'registration.json', dict(registered_at=now(), cohort='EXACT_PRIOR_INSPECTED_DEVELOPMENT_REPLAY',
        sample_manifest_sha256=sha(ROOT/'evidence/bonus/source-manifest.json'),
        source_hashes={p: sha(ROOT/p) for p in ['scripts/replay_funding_repair.py', 'research/foundation/funding.py',
            'research/bonus/OpportunityRouterV1.py', 'research/bonus/advanced_features.py']},
        variants=['original', 'event-once'], fee_per_side=.0006,
        hypothesis='Repair duplicate funding without changing recipe, partial rules, historical sources, exits or fees',
        economic_status='NOT_NEW_HOLDOUT_OR_PROMOTION', persistent_qualification=False))
    for variant in ['original', 'event-once']:
        with (dest/(variant+'.txt')).open('x') as log:
            process = subprocess.run([sys.executable, __file__, 'one', run_id, variant], stdout=log, stderr=subprocess.STDOUT)
        if process.returncode: raise ValueError('funding replay failed: '+variant)
    events = {}
    for symbol in spec()['pairs']:
        f = frame(symbol, '1h', 'funding_rate'); m = frame(symbol, '1h', 'mark').set_index('date')
        events[symbol] = [dict(timestamp_ms=r.date.timestamp()*1000, rate=float(r.funding_rate), mark_open=float(m.loc[r.date, 'open'])) for _, r in f.iterrows()]
    controls = {}
    trade_lists = {}
    for variant in ['original', 'event-once']:
        trades = read(dest/(variant+'.json'))['strategy']['RouterOnlyM1V1']['trades']; trade_lists[variant] = trades
        rows = []
        for trade in trades:
            low, high, obs = event_bounds(trade, events[trade['pair']])
            actual = trade.get('funding_fees', 0) or 0
            rows.append(dict(pair=trade['pair'], open_date=trade['open_date'], native_funding=actual,
                source_min=low, source_max=high, outside_bounds_usdt=max(low-actual, actual-high, 0), events=obs))
        controls[variant] = dict(trades=len(trades), native_net_usdt=sum(t['profit_abs'] for t in trades),
            native_funding=sum(t.get('funding_fees', 0) or 0 for t in trades),
            partial_exits=sum(max(0, len([o for o in t['orders'] if not o['ft_is_entry']])-1) for t in trades),
            outside_source_bounds=sum(r['outside_bounds_usdt'] > 1e-8 for r in rows), funding_rows=rows)
    old = read(ROOT/'evidence/bonus/native-results/RouterOnlyM1V1.json')['strategy']['RouterOnlyM1V1']['trades']
    keys = lambda ts: sorted((t['pair'], t['open_timestamp'], t['is_short']) for t in ts)
    result = dict(schema_version=1, controls=controls,
        original_trade_fields_reproduce=old == trade_lists['original'],
        identical_entry_keys=keys(trade_lists['original']) == keys(trade_lists['event-once']),
        declared_priority='Event before an identical-clock exit; source bounds retain both venue priorities',
        fixed_source_audit_pass=controls['event-once']['outside_source_bounds'] == 0,
        persistent_lifecycle_qualified=False)
    write(dest/'comparison.json', result)
    assert result['original_trade_fields_reproduce']
    assert controls['original']['outside_source_bounds'] > 0
    assert result['fixed_source_audit_pass']
    print(json.dumps({k:v for k,v in result.items() if k != 'controls'}, indent=2))
    print(json.dumps({k:{f:v for f,v in r.items() if f != 'funding_rows'} for k,r in controls.items()}, indent=2))


if __name__ == '__main__':
    if sys.argv[1] == 'one': one(*sys.argv[2:])
    elif sys.argv[1] == 'run': run(*sys.argv[2:])
    else: raise ValueError('research replay only')
