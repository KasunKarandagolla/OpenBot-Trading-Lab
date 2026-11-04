"""Audit every archived fill and rejected setup without rewriting sealed evidence."""
from collections import Counter
from decimal import Decimal as D
from datetime import datetime
from integrated_common import *

CONTROLS = {
    'V4': ROOT / 'evidence/setup/run-002/native/v4-structure-fixed-touch-750',
    'PR12': ROOT / 'evidence/setup/run-003/native/setup-fixed-touch-750',
}

def audit():
    records = []
    for label, directory in CONTROLS.items():
        result = next(iter(read(directory / 'result.json')['strategy'].values()))
        states = {(x['pair'], datetime.fromisoformat(x['open_date'])): x for x in read(directory / 'states.json')}
        ledgers = {x['decision_id']: x for x in read(directory / 'ledger.json')}
        for trade in result['trades']:
            state = states[(trade['pair'], datetime.fromisoformat(trade['open_date']))]
            g = state['plan']; old = ledgers[g['decision_id']]
            sign = -1 if trade['is_short'] else 1
            entries = [o for o in trade['orders'] if o['ft_is_entry']]
            exits = [o for o in trade['orders'] if not o['ft_is_entry']]
            amount = sum(D(str(o['amount'])) for o in entries)
            assert amount == sum(D(str(o['amount'])) for o in exits)
            a = sum(D(str(o['amount'])) * D(str(o['safe_price'])) for o in entries)
            b = sum(D(str(o['amount'])) * D(str(o['safe_price'])) for o in exits)
            gross = sign * (b-a)
            fees = a*D(str(trade['fee_open'])) + b*D(str(trade['fee_close']))
            funding = D(str(trade.get('funding_fees') or 0))
            net = gross-fees+funding
            assert abs(net-D(str(trade['profit_abs']))) < D('0.00000011')
            independent_funding = sum(-sign*D(str(e['quantity']))*D(str(e['mark']))*D(str(e['rate'])) for e in state['funding'])
            assert abs(independent_funding-funding) < D('0.00000011')
            entry = trade['open_rate']; stop = g['stop']; atr = g['atr_at_signal']
            levels = [x for x in g.get('obstacles', []) if x.get('fidelity') != 'OHLCV_PROXY' and sign*(x['price']-entry)>0]
            first = min(levels, key=lambda x: sign*(x['price']-entry)) if levels else None
            reward = sign*(first['price']-entry)/entry if first else None
            rr = (reward-.0038)/(sign*(entry-stop)/entry+.0038) if reward is not None else None
            contributors = []
            if first and rr < 1.25:
                contributors.append({'category': 'TARGET_GEOMETRY', 'evidence': 'Nearest recorded nonproxy obstacle offers RR<1.25; causal timestamp absent on old V4 obstacle records', 'causal_cause': 'UNKNOWN'})
            if gross > 0 and net < 0:
                contributors.append({'category': 'EXECUTION_COST', 'evidence': 'Fees/funding turn positive gross into net loss', 'causal_cause': 'ARITHMETIC_VERIFIED'})
            if 'stop' in trade['exit_reason'] or 'protective' in trade['exit_reason']:
                contributors.append({'category': 'STOP_GEOMETRY', 'evidence': 'Native protective exit observed; suitability of initial stop UNKNOWN', 'causal_cause': 'UNKNOWN'})
            if 'thesis' in trade['exit_reason']:
                contributors.append({'category': 'MANAGEMENT', 'evidence': 'Native thesis-exit callback fired; alternative-exit value requires native ablation', 'causal_cause': 'UNKNOWN'})
            if not contributors:
                contributors.append({'category': 'UNKNOWN', 'evidence': 'Outcome alone does not isolate opportunity, entry or exit causality', 'causal_cause': 'UNKNOWN'})
            native_mfe = sign*((trade['min_rate'] if sign == -1 else trade['max_rate'])/entry-1)*10000
            native_mae = sign*((trade['max_rate'] if sign == -1 else trade['min_rate'])/entry-1)*10000
            realized = sign*(trade['close_rate']/entry-1)*10000
            records.append(dict(control=label, pair=trade['pair'], side=g['side'], playbook=g['recipe'], decision_id=g['decision_id'],
                decision_at=g['available_at'], original_plan=g, native_trade=trade, funding_events=state['funding'],
                gross=float(gross), fees=float(fees), funding=float(funding), net=float(net),
                stop_distance_atr=sign*(entry-stop)/atr, first_recorded_obstacle=first, obstacle_net_rr=rr,
                entry_distance_boundary_atr=abs(entry-g['boundary'])/atr if g.get('boundary') else None,
                native_extremes_bp=dict(favorable=native_mfe, adverse=native_mae, status='NATIVE_BOOKKEEPING_WINDOW; NOT_EXECUTABLE_PROFIT'),
                archived_auxiliary_extremes_bp=dict(favorable=old['mfe_bp_bar_upper_bound'], adverse=old['mae_bp_bar_lower_bound'], status='CANDLES_OPEN_AT_OR_AFTER_FILL_AND_STRICTLY_BEFORE_EXIT;EXCLUDES_EXIT_CANDLE'),
                realized_move_bp=realized, auxiliary_mfe_below_realized=old['mfe_bp_bar_upper_bound'] is not None and old['mfe_bp_bar_upper_bound']+1e-7<realized,
                contributors=contributors, unresolved=['EARLIEST_5M_TRIGGER_UNKNOWN_WITHOUT_SOURCE', 'HISTORICAL_QUEUE_SPREAD_UNKNOWN'],
                independent_quantity_fee_funding_net_verified=True))
    write(OUT/'forensics-trades.json', records)
    decisions = read(ROOT/'evidence/setup/run-003/decisions.json')
    rejected = [x for x in decisions if x.get('candidate_geometry') or x['state'] in ('REJECTED', 'INVALIDATED', 'EXPIRED')]
    write(OUT/'forensics-rejected.json', rejected)
    summary = {}
    for name in CONTROLS:
        rows = [x for x in records if x['control']==name]
        summary[name] = dict(fills=len(rows), gross=sum(x['gross'] for x in rows), fees=sum(x['fees'] for x in rows), funding=sum(x['funding'] for x in rows), net=sum(x['net'] for x in rows),
            exit_reasons=dict(Counter(x['native_trade']['exit_reason'] for x in rows)),
            loss_contributors=dict(Counter(y['category'] for x in rows if x['net']<0 for y in x['contributors'])),
            auxiliary_mfe_below_realized=sum(x['auxiliary_mfe_below_realized'] for x in rows))
    write(OUT/'forensics-summary.json', dict(controls=summary, rejected_records=len(rejected),
        rejected_reasons=dict(Counter(x['reason'] for x in rejected)),
        interpretation='Exit-candle exclusion explains why auxiliary MFE can be below realized return. Native extreme can include post-exit path in exit candle. Neither is accessible peak profit. Full-candle remeasurement, if available, is only a bound.',
        funding_check='Recomputed from archived event quantities/rates/marks; source-event completeness awaits recovered market files'))
    print(summary)

if __name__ == '__main__':
    audit()
