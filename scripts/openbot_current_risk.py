"""Deterministic research validation for a proposed Binance Demo trade."""

import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import time

from openbot_current_market import CAP, MARKET, load, verify


ROLES = ('lead', 'market-researcher', 'chart-vision', 'researcher-rebuttal', 'risk-reviewer', 'director')
ENTRY = {'MARKET_ENTRY', 'LIMIT_ENTRY', 'CONDITIONAL_ENTRY'}


def evidence_errors(receipts, digest):
    errors = []
    ids = []
    for role in ROLES:
        receipt = receipts.get(role, {})
        if receipt.get('status') in ('permission.rejected', 'PERMISSION_REJECTED'):
            errors.append(f'PERMISSION_REJECTED:{role}')
        elif (not digest or receipt.get('packet_sha256') != digest
              or not all(receipt.get(k) for k in ('agent_id', 'message_id', 'session_id', 'observed_at'))):
            errors.append(f'MISSING_NATIVE_RECEIPT:{role}')
        elif role == 'chart-vision' and not receipt.get('image_transfer_id'):
            errors.append('MISSING_NATIVE_PNG_TRANSFER')
        elif role != 'researcher-rebuttal':
            ids.append(receipt['agent_id'])
    if len(ids) != len(set(ids)):
        errors.append('NATIVE_SPECIALIST_IDS_NOT_DISTINCT')
    if all(r in receipts for r in ('market-researcher', 'researcher-rebuttal')) and (
        receipts['market-researcher'].get('agent_id') != receipts['researcher-rebuttal'].get('agent_id')
    ):
        errors.append('REBUTTAL_RESEARCHER_ID_MISMATCH')
    return errors


def number(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('non-finite value')
    return result


def assess(plan, constraints, demo, now_ms, receipts=None, digest=None):
    def result(status, reasons, **metrics):
        return {'status': status, 'reasons': reasons, 'metrics': metrics, 'order_authorized': False}

    if plan is None:
        return result('UNKNOWN', ['NO_DIRECTOR_PROPOSAL'])
    if not digest or plan.get('packet_sha256') != digest:
        return result('VETO', ['PROPOSAL_PACKET_HASH_MISMATCH'])
    action = plan.get('decision')
    team_errors = evidence_errors(receipts or {}, digest)
    if action == 'NO_OPPORTUNITY':
        return result('UNKNOWN' if team_errors else 'PASS', team_errors or ['NO_ENTRY_PROPOSED'])
    if action not in ENTRY or plan.get('venue') != 'Binance USD-M Demo' or constraints.get('market_type') != MARKET:
        return result('VETO', ['WRONG_DECISION_OR_VENUE'])
    if plan.get('symbol') != constraints.get('symbol'):
        return result('VETO', ['SYMBOL_MISMATCH'])
    try:
        expires = plan['expires_at_ms']
        if type(expires) is not int or not now_ms < expires <= now_ms + 300_000:
            return result('VETO', ['EXPIRED_OR_INVALID_TTL'])
        if action == 'CONDITIONAL_ENTRY' and (not plan.get('trigger') or plan.get('revalidation_required') is not True):
            return result('VETO', ['MISSING_CONDITIONAL_TRIGGER_OR_REVALIDATION'])
        entry, stop, tp1, tp2, quantity, leverage = (
            number(plan[k]) for k in ('entry', 'stop', 'tp1', 'tp2', 'quantity', 'leverage')
        )
        if plan['side'] not in ('LONG', 'SHORT'):
            return result('VETO', ['WRONG_SIDE'])
        sign = Decimal(1 if plan['side'] == 'LONG' else -1)
        if min(entry, stop, tp1, tp2, quantity) <= 0 or not sign * stop < sign * entry < sign * tp1 < sign * tp2:
            return result('VETO', ['INVALID_STOP_OR_TARGET_GEOMETRY'])
        if not 10 <= leverage <= 25 or leverage % 1:
            return result('VETO', ['LEVERAGE_OUTSIDE_10_TO_25'])
        notional = entry * quantity
        if notional > CAP:
            return result('VETO', ['POSITION_NOTIONAL_ABOVE_25_USDT'])
        rules = constraints['public_filters']
        lot = rules['market' if action == 'MARKET_ENTRY' else 'limit']
        if any(x % number(rules['tick_size']) for x in (entry, stop, tp1, tp2)):
            return result('VETO', ['PRICE_TICK_MISMATCH'])
        if (quantity % number(lot['stepSize'])
                or not number(lot['minQty']) <= quantity <= number(lot['maxQty'])):
            return result('VETO', ['QUANTITY_FILTER_MISMATCH'])
        if notional < number(rules['minimum_notional']):
            return result('VETO', ['BELOW_PUBLIC_MINIMUM_NOTIONAL'])
        quote = constraints['public_quote']
        if not 0 <= now_ms - quote['quote_time_ms'] <= 120_000:
            return result('VETO', ['STALE_OR_FUTURE_QUOTE'])
        bid, ask = number(quote['bid']), number(quote['ask'])
        quote_reference = ask if sign > 0 else bid
        if abs(entry - quote_reference) / quote_reference > Decimal('0.0015'):
            return result('VETO', ['PRICE_DEVIATION_EXCEEDS_15_BPS'])
        if action == 'LIMIT_ENTRY' and (entry >= ask if sign > 0 else entry <= bid):
            return result('VETO', ['MARKETABLE_LIMIT_REQUIRES_REVIEW'])
        gap = sign * (entry - stop)
        if not Decimal('0.0025') <= gap / entry <= Decimal('0.025'):
            return result('VETO', ['OUTSIDE_BASELINE_STOP_RANGE'])
        metrics = {'notional_usdt': str(notional), 'initial_margin_before_cost_usdt': str(notional / leverage),
                   'gross_stop_loss_usdt': str(gap * quantity)}
        if not demo or demo.get('verification') != 'AUTHENTICATED_DEMO_WITH_SYMBOL_RULES':
            return result('UNKNOWN', [*team_errors, 'DEMO_RULES_COST_OR_ACCOUNT_UNQUALIFIED'], **metrics)
        if demo.get('symbol') != plan['symbol'] or demo.get('demo_filters') != rules:
            return result('UNKNOWN', ['DEMO_SYMBOL_OR_FILTERS_UNVERIFIED'], **metrics)
        if not 0 <= now_ms - demo['observed_at_ms'] <= 120_000:
            return result('UNKNOWN', ['DEMO_ACCOUNT_SNAPSHOT_STALE'], **metrics)
        positions, pending = demo['open_positions'], demo['pending_entry_slots']
        if type(positions) is not int or type(pending) is not int or min(positions, pending) < 0:
            return result('UNKNOWN', ['PORTFOLIO_EXPOSURE_UNQUALIFIED'], **metrics)
        if positions + pending >= 2:
            return result('VETO', ['PORTFOLIO_SLOT_CAP'], **metrics)
        if leverage > number(demo['max_leverage']):
            return result('VETO', ['DEMO_LEVERAGE_BRACKET'], **metrics)
        fee, slip, funding = (number(demo[k]) for k in ('fee_per_side', 'slippage_per_side', 'adverse_funding_rate'))
        if min(fee, slip, funding) < 0:
            return result('UNKNOWN', ['COST_ASSUMPTIONS_UNQUALIFIED'], **metrics)

        def costs(exit_price):
            return quantity * ((entry + exit_price) * (fee + slip) + entry * funding)

        loss = gap * quantity + costs(stop)
        rr1 = (sign * (tp1 - entry) * quantity - costs(tp1)) / loss
        rr2 = (sign * (tp2 - entry) * quantity - costs(tp2)) / loss
        metrics.update(net_stop_loss_usdt=str(loss), tp1_after_cost_rr=str(rr1), tp2_after_cost_rr=str(rr2),
                       exit_economics_basis='FULL_SIZE_ALTERNATIVE_EXITS')
        if rr1 < Decimal('1.25'):
            return result('VETO', ['TP1_AFTER_COST_RR_BELOW_1_25'], **metrics)
        margin = notional / leverage
        if margin + costs(stop) > number(demo['available_usdt']):
            return result('VETO', ['INSUFFICIENT_AVAILABLE_MARGIN'], **metrics)
        if demo.get('margin_model') != 'ISOLATED_ONE_WAY_SINGLE_TIER':
            return result('UNKNOWN', ['LIQUIDATION_MODEL_UNQUALIFIED'], **metrics)
        mmr, deduction = (number(demo[k]) for k in ('maintenance_ratio', 'maintenance_deduction_usdt'))
        if not 0 <= mmr < 1 or deduction < 0:
            return result('UNKNOWN', ['LIQUIDATION_BRACKET_UNQUALIFIED'], **metrics)
        buffer_margin = margin - notional * fee + deduction
        liquidation = (notional - sign * buffer_margin) / (quantity * (1 - sign * mmr))
        clearance = sign * (stop - liquidation)
        metrics.update(research_liquidation_usdt=str(liquidation), stop_to_liquidation_usdt=str(clearance))
        if clearance < max(entry * Decimal('0.005'), gap / 2):
            return result('VETO', ['INSUFFICIENT_LIQUIDATION_BUFFER'], **metrics)
        if team_errors:
            return result('UNKNOWN', team_errors, **metrics)
        return result('PASS', ['RESEARCH_CONSTRAINTS_SATISFIED'], **metrics)
    except (KeyError, TypeError, ValueError, InvalidOperation, ZeroDivisionError):
        return result('UNKNOWN', ['MISSING_OR_INVALID_NUMERICAL_INPUT'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('--proposal', type=Path)
    parser.add_argument('--demo-state', type=Path)
    parser.add_argument('--native-receipts', type=Path)
    args = parser.parse_args()
    seal = verify(args.packet)
    print(json.dumps(assess(
        load(args.proposal) if args.proposal else None,
        load(args.packet / 'execution-constraints.json'),
        load(args.demo_state) if args.demo_state else None,
        time.time_ns() // 1_000_000,
        load(args.native_receipts) if args.native_receipts else None,
        seal['packet_sha256'],
    ), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
