"""Authentic cutoff exports and a separate later-path evaluator; no agent claims.

Selection is deterministic from pretrade plans plus fixed clock samples, never P&L.
The source archives stay owner-local; only bounded, hashed cutoff exports are shared.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from binance_research_data import DataError
import openbot_current_market as market
from trading_lab.skills import sha
from trading_lab.public import write_new


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def register(history, out):
    """Call before exporting/evaluating paths; preserve all zero-setup cutoffs."""
    import pandas as pd
    history, out = Path(history), Path(out)
    plans = market.load(history / 'development/plans.json')
    # Six earliest registered pretrade decisions, independent of subsequent paths.
    chosen = sorted(plans, key=lambda p: (p['decision_at'], p['symbol']))[:6]
    cases = [dict(symbol=p['symbol'], cutoff_ms=int(pd.Timestamp(p['decision_at']).value // 1000000),
                  plan=p, selection='EARLIEST_PRETRADE_PLAN') for p in chosen]
    for symbol in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']:
        for hour in ['00', '12']:
            cases.append(dict(symbol=symbol, cutoff_ms=int(pd.Timestamp('2026-08-07T' + hour + ':00Z').value // 1000000),
                              plan=None, selection='SYSTEMATIC_CLOCK_SAMPLE'))
    for i, case in enumerate(cases): case['case_id'] = 'B%02d' % (i + 1)
    registration = dict(schema='openbot.blind-case-registration.v2', cases=cases,
                        selection='Six earliest pretrade plans plus six fixed symbol/clock cutoffs; no outcome selection',
                        outcome_access='NOT_READ_BY_REGISTRATION', planned_arms=['N', 'N+V'],
                        native_paired_trials='NOT_RUN', source_plans_sha256=sha(history / 'development/plans.json'),
                        frozen_recipe_sha256=sha(market.PROTOCOL),
                        recipe='FROZEN_LOCAL_RECOVERY_V1_HISTORICAL_1X',
                        limitation='Previously studied development data; not a pristine independent holdout or prospective trial')
    write_new(out / 'registration.json', registration)
    return dict(status='REGISTERED', cases=len(cases), registration_sha256=sha(out / 'registration.json'))


def load_frame(history, symbol, timeframe, funding=False):
    import pandas as pd
    name = symbol.removesuffix('USDT') + '_USDT_USDT-' + timeframe + ('-funding_rate' if funding else '-futures') + '.feather'
    return pd.read_feather(Path(history) / 'binance/research' / name)


def verify_archives(history, frame):
    import csv, io, math, zipfile
    sources = market.load(Path(history) / 'sources.json')['sources']
    result = []
    for digest in sorted(set(frame.source_sha256)):
        receipt = next((s for s in sources if s.get('sha256') == digest), None)
        if receipt is None or receipt.get('official_sha256') != digest:
            raise DataError('CASE_ARCHIVE_OFFICIAL_HASH_MISSING')
        # Source manifest paths are repository-relative; resolve only the archives suffix.
        relative = Path(receipt['cache_path'])
        parts = relative.parts
        if 'archives' not in parts: raise DataError('CASE_ARCHIVE_PATH')
        path = Path(history).joinpath(*parts[parts.index('archives'):])
        if sha(path) != digest: raise DataError('CASE_ARCHIVE_HASH_MISMATCH')
        # A source_sha column alone does not prove a converted row came from it.
        # Compare actual selected rows to their checksum-verified CSV archive.
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != 1: raise DataError('CASE_ARCHIVE_MEMBER_COUNT')
            records = list(csv.DictReader(io.StringIO(archive.read(names[0]).decode())))
        selected = frame.loc[frame.source_sha256 == digest]
        if 'open_time_ms' in selected:
            raw = {int(r['open_time']): r for r in records}
            for row in selected.itertuples():
                original = raw.get(int(row.open_time_ms))
                if original is None or int(original['close_time']) != int(row.close_time_ms):
                    raise DataError('CASE_ARCHIVE_ROW_CLOCK')
                for target, source in [('open','open'),('high','high'),('low','low'),('close','close'),
                                       ('base_volume','volume'),('quote_volume','quote_volume'),
                                       ('taker_buy_base_volume','taker_buy_volume'),('taker_buy_quote_volume','taker_buy_quote_volume')]:
                    if not math.isclose(float(original[source]), float(getattr(row, target)), rel_tol=1e-12, abs_tol=1e-12):
                        raise DataError('CASE_ARCHIVE_ROW_VALUE')
        elif len(selected):
            raw = {int(r['calc_time']): r for r in records}
            for row in selected.itertuples():
                original = raw.get(int(row.source_event_time_ms))
                if original is None or not math.isclose(float(original['last_funding_rate']), float(row.funding_rate), rel_tol=1e-12, abs_tol=1e-12):
                    raise DataError('CASE_ARCHIVE_FUNDING_VALUE')
        result.append(dict(url=receipt['url'], sha256=digest, official_checksum_verified=True))
    return result


def validate_outcome_window(path, start, end):
    if (path.empty or len(path) != (end-start)//300000
            or int(path.open_time_ms.iloc[0]) != start or int(path.available_at_ms.iloc[-1]) != end
            or not path.open_time_ms.diff().iloc[1:].eq(300000).all()
            or not (path.available_at_ms == path.open_time_ms+300000).all()):
        raise DataError('OUTCOME_WINDOW_INCOMPLETE_OR_GAPPED')


def export(history, out):
    import pandas as pd
    from local_recovery_scan import cheap_frame, candidate_rows, entry_features, examine, protocol
    history, out = Path(history), Path(out)
    registration = market.load(out / 'registration.json')
    if sha(history / 'development/plans.json') != registration['source_plans_sha256']:
        raise DataError('CASE_PLAN_SOURCE_CHANGED')
    exported = []
    for case in registration['cases']:
        cutoff = case['cutoff_ms']; symbol = case['symbol']; frames = {}; evidence = {}
        for tf, count in [('1h', 721), ('15m', 289), ('5m', 865)]:
            full = load_frame(history, symbol, tf)
            partial = full.loc[full.available_at_ms <= cutoff].tail(count).copy()
            if (len(partial) != count or partial.source_symbol.ne(symbol).any()
                    or partial.source_venue.ne('binance').any()
                    or partial.available_at_ms.iloc[-1] != cutoff // market.INTERVAL_MS[tf] * market.INTERVAL_MS[tf]):
                raise DataError('CASE_SOURCE_CLOCK_OR_COVERAGE')
            sources = verify_archives(history, partial)
            bars = [[int(r.open_time_ms), str(r.open), str(r.high), str(r.low), str(r.close), str(r.base_volume),
                     int(r.close_time_ms), str(r.quote_volume), int(r.trade_count), str(r.taker_buy_base_volume),
                     str(r.taker_buy_quote_volume), '0'] for r in partial.itertuples()]
            from trading_lab.public import validate_bars
            validate_bars(bars, tf, cutoff, count)
            evidence[tf] = dict(timeframe=tf, sources=sources, bars=bars,
                                bars_sha256=hashlib.sha256(encoded(bars)).hexdigest())
            frames[tf] = partial.rename(columns={'base_volume':'volume'})
        plan = case['plan']
        q = cheap_frame(frames['1h'], frames['15m'])
        if plan is None:
            at = pd.Timestamp(cutoff, unit='ms', tz='UTC')
            candidates = candidate_rows(q, symbol, at - pd.Timedelta(minutes=30), at + pd.Timedelta(milliseconds=1),
                                        {}, {}, protocol()['gates'])
            for c in candidates:
                if c['status'] == 'RESEARCHABLE':
                    examine(c, entry_features(frames['5m']), protocol()['gates'], at + pd.Timedelta(hours=16))
            active = [c['plan'] for c in candidates if 'plan' in c
                      and pd.Timestamp(c['plan']['decision_at']) <= at < pd.Timestamp(c['plan']['expires_at'])]
            plan = active[0] if active else None
        past_only = dict(case_id=case['case_id'], symbol=symbol, venue='BINANCE_PUBLIC_USDM', cutoff_ms=cutoff,
                         numeric=evidence, recipe=registration['recipe'], recipe_sha256=registration['frozen_recipe_sha256'],
                         regime_1h=str(q.iloc[-1].struct_direction), regime_4h=str(q.iloc[-1].struct_direction_4h),
                         baseline=dict(kind='DETERMINISTIC_FROZEN_RECIPE_NOT_AGENT_N',
                                       recommendation='TRADE' if plan else 'NO_TRADE', plan=plan),
                         execution_authority='NONE', later_bars='EXCLUDED',
                         source_limit='Historical perpetual eligibility/spread/account metadata UNQUALIFIED')
        folder = out / 'agent-inputs' / case['case_id'];write_new(folder / 'input.json', past_only)
        write_new(folder / 'decision-seal.json', dict(input_sha256=sha(folder / 'input.json'),
                   decision_sha256=hashlib.sha256(encoded(past_only['baseline'])).hexdigest(), sealed_before_evaluation=True))
        exported.append(dict(case_id=case['case_id'], input_sha256=sha(folder / 'input.json'),
                             recommendation=past_only['baseline']['recommendation'],
                             regime_1h=past_only['regime_1h'], regime_4h=past_only['regime_4h']))
    write_new(out / 'decision-index.json', dict(registration_sha256=sha(out / 'registration.json'), cases=exported,
               native_N='NOT_RUN', native_N_plus_V='NOT_RUN', paired_agent_cases=0))
    return dict(status='EXPORTED_AND_SEALED', cases=len(exported), decisions=dict(Counter(c['recommendation'] for c in exported)))


def evaluate(history, out):
    """Separate process after seals: conservative candle-touch replay, not exchange fills."""
    history, out = Path(history), Path(out)
    index = market.load(out / 'decision-index.json'); results = []
    if index['registration_sha256'] != sha(out / 'registration.json'): raise DataError('REGISTRATION_CHANGED')
    for item in index['cases']:
        folder = out / 'agent-inputs' / item['case_id'];case = market.load(folder / 'input.json')
        seal = market.load(folder / 'decision-seal.json')
        if (sha(folder / 'input.json') != item['input_sha256'] or seal['input_sha256'] != item['input_sha256']
                or seal['decision_sha256'] != hashlib.sha256(encoded(case['baseline'])).hexdigest()):
            raise DataError('CASE_DECISION_CHANGED')
        plan = case['baseline']['plan']
        result = dict(case_id=case['case_id'], symbol=case['symbol'], cutoff_ms=case['cutoff_ms'],
                      recommendation=case['baseline']['recommendation'], input_sha256=item['input_sha256'],
                      native_N_vs_N_plus_V='NOT_MEASURED', order_authorized=False)
        if plan is None:
            result.update(outcome='ABSTAIN', missed_winner='NOT_IDENTIFIABLE_WITHOUT_ALTERNATE_FROZEN_PLAN')
        else:
            import pandas as pd
            start = case['cutoff_ms']; end = start + int(plan['max_hold_minutes']) * 60000
            frame = load_frame(history, case['symbol'], '5m')
            path = frame.loc[(frame.open_time_ms >= start) & (frame.available_at_ms <= end)]
            verify_archives(history, path)
            validate_outcome_window(path, start, end)
            entry, stop, target = (float(plan[k]) for k in ['entry', 'stop', 'target'])
            # One 5m expiry: a range touch is a hypothetical assumption, not queue proof.
            first = path.iloc[0]
            if not first.low <= entry <= first.high:
                result.update(outcome='NONFILL', hypothetical_net_usdt=0, fill_assumption='FIRST_NEXT_BAR_RANGE_TOUCH')
            else:
                sign = 1 if plan['side'] == 'long' else -1
                price = float(path.close.iloc[-1]); exit_at = int(path.available_at_ms.iloc[-1]); tag='TIME_EXIT'; ambiguous=False
                for row in path.itertuples():
                    stopped = row.low <= stop if sign > 0 else row.high >= stop
                    targeted = row.high >= target if sign > 0 else row.low <= target
                    if stopped or targeted:
                        price = stop if stopped else target; exit_at = int(row.available_at_ms)
                        tag = 'STOP' if stopped else 'TARGET'; ambiguous = stopped and targeted;break
                qty = 25 / entry
                fees = qty * (entry + price) * .0005
                slip = qty * (entry + price) * .001
                funding = load_frame(history, case['symbol'], '1h', funding=True)
                events = funding.loc[(funding.source_event_time_ms > start) & (funding.source_event_time_ms <= exit_at)]
                verify_archives(history, events)
                funding_cost = 25 * sign * float(events.funding_rate.sum())
                net = sign * (price - entry) * qty - fees - slip - funding_cost
                result.update(outcome=tag, side=plan['side'], hypothetical_net_usdt=net, fees_usdt=fees,
                              slippage_usdt=slip, funding_usdt=funding_cost, funding_events=len(events),
                              exit_available_ms=exit_at, ambiguous_same_bar=ambiguous,
                              fill_assumption='FIRST_NEXT_BAR_RANGE_TOUCH; STOP_FIRST_IF_AMBIGUOUS',
                              economics='UNQUALIFIED: modeled costs/queue/metadata; no real fill',
                              avoided_loser_if_vetoed=net < 0, missed_winner_if_vetoed=net > 0)
        results.append(result)
    summary = dict(schema='openbot.blind-case-outcomes.v2', cases=len(results),
                   outcomes=dict(Counter(r['outcome'] for r in results)),
                   hypothetical_net_usdt=sum(r.get('hypothetical_net_usdt', 0) for r in results),
                   paired_agent_cases=0, native_N_vs_N_plus_V='NOT_MEASURED',
                   economic_verdict='UNQUALIFIED', blind_agent_intelligence='NOT_TESTED',
                   separation='Exporter excludes future bars; evaluator is a separate command. No OS isolation claim.',
                   results=results)
    write_new(out / 'evaluator-only' / 'outcomes.json', summary)
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action', choices=['register','export','evaluate'])
    p.add_argument('history', type=Path);p.add_argument('out', type=Path);args=p.parse_args()
    print(json.dumps(globals()[args.action](args.history,args.out),indent=2,allow_nan=False));return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (DataError,OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'status':'BLOCKED','reason':str(error) if isinstance(error,DataError) else type(error).__name__}));sys.exit(1)
