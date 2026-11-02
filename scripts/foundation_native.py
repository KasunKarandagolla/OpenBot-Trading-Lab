"""One native Freqtrade backtester, with scoped funding lifecycle repair."""
import json
import subprocess
import sys
import zipfile
import pandas as pd
from foundation_common import *


def schedule(run_id):
    from bonus_pipeline import ranking
    from OpportunityRouterV1 import RouterOnlyV1
    from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
    from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
    from freqtrade.strategy import merge_informative_pair
    from freqtrade.enums import CandleType
    from foundation_market import validate
    out, data, spec = verify(run_id)
    if (out/'schedule.json').exists(): raise ValueError('preserve completed schedule')
    validate(run_id)
    bases = {s: frame(data, s) for s in spec['pairs']}
    rows, decisions = ranking(bases)
    # Published rank is conditional on eligibility, like the existing selection.
    rows.loc[rows.cheap_pass, 'rank'] = rows.loc[rows.cheap_pass].groupby('decision_at').cumcount()+1
    rows.to_csv(out/'market-ranking.csv', index=False)
    write(out/'schedule.json', dict(schema_version=1, policy='EXISTING_CAUSAL_TOP3_V1',
          membership=spec['membership'], venue='gate', decisions=decisions,
          historical_spread='UNKNOWN; common explicit cost scenario'))
    start, end = [pd.to_datetime(x, format='%Y%m%d', utc=True) for x in spec['evaluation_timerange'].split('-')]
    records = []
    cfg = read(config(run_id, 'RouterOnlyV1')) | {'candle_type_def': CandleType.FUTURES}
    for symbol in spec['pairs']:
        strategy = RouterOnlyV1(cfg)
        hourly = strategy.populate_indicators_1h(frame(data, symbol, '1h'), {'pair': symbol})
        merged = merge_informative_pair(bases[symbol], hourly, '15m', '1h', ffill=True)
        d = strategy.populate_indicators(merged, {'pair': symbol})
        parents = {key: cls(cfg).populate_entry_trend(d.copy(), {'pair': symbol}) for key, cls in
                   [('vwap', VWAPTrendContinuationV1), ('sweep', LiquiditySweepReversalV1)]}
        result = strategy.populate_entry_trend(d, {'pair': symbol})
        mask = result.parent_candidate.eq(1) & (result.date+pd.Timedelta(minutes=15) >= start) & (result.date+pd.Timedelta(minutes=15) < end)
        for idx, row in result.loc[mask].iterrows():
            at = row.date+pd.Timedelta(minutes=15)
            parent = parents[row.bonus_recipe].loc[idx]
            side = 'long' if parent.enter_long else 'short'
            opposite = 'DOWN' if side == 'long' else 'UP'
            opposing = []
            if row.get('struct_direction_1h') == opposite: opposing.append('OPPOSING_HOURLY_STRUCTURE')
            if row.bonus_recipe == 'sweep' and row.get('adx_1h', 0) >= 20: opposing.append('OPPOSING_IMPULSE_MAY_CONTINUE')
            for key in ('smc', 'ict', 'profile'):
                if not bool(row[key+'_ok']): opposing.append(key.upper()+'_NOT_CONFIRMED')
            records.append(dict(schema_version=1, decision_id=f'{run_id}:{symbol}:{at.isoformat()}',
                environment='BACKTEST_RESEARCH', venue='gate', symbol=symbol,
                available_at=at.isoformat(), expires_at=(at+pd.Timedelta(minutes=5)).isoformat(),
                observed_at=None, observation_reason='Historical venue bars; original researcher receipt time UNKNOWN',
                recipe=row.bonus_recipe, side=side, regime='TREND' if row.adx_1h >= 25 else 'RANGE_OR_WEAK_TREND',
                status='RESEARCH_CANDIDATE' if row.bonus_reason == 'TRADE' else 'REJECT', reason=row.bonus_reason,
                geometry=json.loads(row.bonus_plan) if isinstance(row.bonus_plan, str) else None,
                opposing_evidence=[dict(evidence_id=f'{symbol}:{at.isoformat()}:{r}', reason=r,
                    assessment='CAUTION_NONBINDING_RESEARCH_CHECKPOINT') for r in opposing],
                data_gaps=['HISTORICAL_NEWS_UNKNOWN', 'HISTORICAL_SPREAD_DEPTH_QUEUE_UNKNOWN', 'PIT_MEMBERSHIP_UNKNOWN', 'ORIGINAL_RECEIPT_TIME_UNKNOWN'],
                source_manifest_sha256=sha(out/'data-manifest.json'), orders_created=False))
    write(out/'historical-opportunities.json', dict(schema_version=1, records=records,
          status_counts={s: sum(r['status'] == s for r in records) for s in ['RESEARCH_CANDIDATE', 'REJECT']},
          recipe='Existing router, fixed 2R, parent parameters unchanged; M0 repairs management only.'))
    print('Historical opportunities:', len(records), 'plans', sum(r['status'] == 'RESEARCH_CANDIDATE' for r in records))


def native(run_id, name, lookahead=False):
    from foundation_market import validate
    out, data, spec = verify(run_id)
    validate(run_id)
    cfg_path = config(run_id, name)
    directory = ROOT/'user_data/backtest_results/foundation'/run_id/name
    if not lookahead:
        directory.mkdir(parents=True)  # refuse overwrite/implicit cached replay
    args = ['lookahead-analysis' if lookahead else 'backtesting', '--config', str(cfg_path),
            '--datadir', str(data), '--timerange', spec['evaluation_timerange'], '--fee', str(spec['fee_per_side'])]
    if lookahead:
        if name == 'FoundationRouterM1V1': raise ValueError('M1 lookahead not supported by this runner')
        args += ['--minimum-trade-amount', '1', '--targeted-trade-amount', '20',
                 '--lookahead-analysis-exportfilename', str(out/(name+'-lookahead.csv'))]
        from freqtrade.main import main
        return main(args)
    args += ['--enable-protections', '--cache', 'none', '--export', 'trades', '--backtest-directory', str(directory)]
    from freqtrade.commands import Arguments
    from freqtrade.commands.optimize_commands import setup_optimize_configuration
    from freqtrade.enums import RunMode
    from freqtrade.optimize.backtesting import Backtesting
    from foundation.funding import EventOnceFunding
    class RepairedBacktesting(EventOnceFunding, Backtesting):
        pass
    parsed = Arguments(args).get_parsed_arg()
    cfg = setup_optimize_configuration(parsed, RunMode.BACKTEST)
    # The original router is retained as the audit control. All other portfolios
    # use the repaired event-once lifecycle; M0 has no partial reductions.
    engine = Backtesting if name == 'RouterOnlyV1' else RepairedBacktesting
    backtest = engine(cfg)
    backtest.start()
    latest = read(directory/'.last_result.json')['latest_backtest']
    archive = directory/latest
    with zipfile.ZipFile(archive) as bundle:
        member = next(n for n in bundle.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
        result = bundle.read(member)
    dest = out/'native-results'/(name+'.json')
    dest.parent.mkdir(exist_ok=True)
    if dest.exists(): raise ValueError('preserve native result')
    dest.write_bytes(result)
    write(out/'native-provenance'/(name+'.json'), dict(schema_version=1, strategy=name, observed_at=now(),
        argv=args, engine='Freqtrade 2026.10 native Backtesting',
        funding='ORIGINAL_NATIVE_CONTROL' if name == 'RouterOnlyV1' else 'EVENT_ONCE_BEFORE_EXIT_RESEARCH_SUBCLASS',
        configuration_sha256=sha(cfg_path), dataset_manifest_sha256=sha(out/'data-manifest.json'),
        source_registration_sha256=sha(out/'registration.json'), result_sha256=sha(dest), archive_sha256=sha(archive),
        partial_fill_priority='UNKNOWN venue priority; before-exit at identical native timestamps is a declared scenario',
        persistent_lifecycle_qualified=False))
    return 0


def backtest(run_id):
    out, _, spec = verify(run_id)
    for name in spec['strategies']:
        if (out/'native-results'/(name+'.json')).exists():
            print('Preserving completed native portfolio:', name)
            continue
        log = out/(name+'-native.txt')
        # Failed attempts remain; a fresh name is needed for an intentional retry.
        if log.exists(): raise ValueError('preserve failed native attempt; inspect before retry')
        with log.open('x') as file:
            result = subprocess.run([sys.executable, str(ROOT/'scripts/foundation.py'), 'native', run_id, name], stdout=file, stderr=subprocess.STDOUT)
        if result.returncode: raise ValueError('native run failed: '+name+'; see '+log.name)
        r = read(out/'native-results'/(name+'.json'))['strategy'][name]
        print(f'{name}: {r["total_trades"]} trades; native net {sum(t["profit_abs"] for t in r["trades"]):.8f} USDT', flush=True)


def lookahead(run_id):
    out, _, _ = verify(run_id)
    records = []
    for name in ['VWAPTrendContinuationV1', 'LiquiditySweepReversalV1', 'FoundationRouterM0V1']:
        log = out/(name+'-lookahead.txt')
        with log.open('x') as file:
            result = subprocess.run([sys.executable, str(ROOT/'scripts/foundation.py'), 'native-lookahead', run_id, name], stdout=file, stderr=subprocess.STDOUT)
        records.append(dict(strategy=name, exit_code=result.returncode, log_sha256=sha(log),
              csv_exists=(out/(name+'-lookahead.csv')).exists()))
        print('Native lookahead', name, 'exit', result.returncode, flush=True)
    write(out/'lookahead-checks.json', dict(checks=records, limits='Diagnostic on inspected development signals; zero trades/insufficient signals never establish universal absence of lookahead.'))
