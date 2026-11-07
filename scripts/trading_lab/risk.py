"""Versioned deterministic real-input gate; PASS never grants order authority."""
from decimal import Decimal, InvalidOperation
import hashlib
import json
from datetime import datetime

from openbot_current_risk import assess, number

DECISIONS = {'MARKET': 'MARKET_ENTRY', 'LIMIT': 'LIMIT_ENTRY', 'CONDITIONAL': 'CONDITIONAL_ENTRY'}
DEMO = 'demo-fapi.binance.com'


def historical_geometry(plan, evidence):
    """Supplemental original-contract geometry, never a current/executable proposal."""
    result=response('UNKNOWN',['HISTORICAL_EXECUTION_METADATA_UNQUALIFIED'])
    result.update(mode='HISTORICAL_FIXED_CUTOFF_RESEARCH',historical_protocol_leverage=1,
                  geometry_status='NOT_EVALUATED')
    try:
        cutoff=int(datetime.fromisoformat(plan['decision_at']).timestamp()*1000)
        if evidence['cutoff_ms']!=cutoff or evidence['symbol']!=plan['symbol']:
            raise ValueError('HISTORICAL_IDENTITY')
        bars=evidence['completed_5m_bars']
        if (not bars or any(b['available_ms']!=b['open_ms']+300000 or b['available_ms']>cutoff for b in bars)
                or any(b['open_ms']-a['open_ms']!=300000 for a,b in zip(bars,bars[1:]))
                or bars[-1]['available_ms']!=cutoff or number(bars[-1]['close'])!=number(plan['entry'])
                or not evidence.get('archive_sha256_verified')):
            raise ValueError('HISTORICAL_BAR_AVAILABILITY_OR_SOURCE')
        objective=plan['objective']
        if (int(datetime.fromisoformat(objective['known_at']).timestamp()*1000)>cutoff
                or int(datetime.fromisoformat(plan['earliest_order_at']).timestamp()*1000)<cutoff
                or int(datetime.fromisoformat(plan['expires_at']).timestamp()*1000)<=cutoff):
            raise ValueError('HISTORICAL_LOOKAHEAD_OR_ORDER_TIMING')
        sign=Decimal(1 if plan['side']=='long' else -1 if plan['side']=='short' else 0)
        entry,stop,target,cost=(number(plan[k]) for k in ['entry','stop','target','admission_cost_allowance'])
        if not sign or min(entry,stop,target)<=0 or not sign*stop<sign*entry<sign*target or cost<0:
            raise ValueError('HISTORICAL_PRICE_GEOMETRY')
        rr=(sign*(target-entry)/entry-cost)/(sign*(entry-stop)/entry+cost)
        if abs(rr-number(plan['net_rr']))>Decimal('.000000001'):
            raise ValueError('HISTORICAL_RR_MISMATCH')
        result.update(geometry_status='PASS',cutoff_ms=cutoff,source_sha256=evidence['source_sha256'])
        result['metrics']={'entry':str(entry),'stop':str(stop),'target':str(target),
                           'net_reward_risk_original_cost_model':str(rr),
                           'original_cost_allowance':str(cost),'quantity_and_demo_filters':'UNVERIFIED'}
    except (KeyError,ValueError,TypeError,InvalidOperation,ZeroDivisionError) as error:
        result.update(status='VETO',geometry_status='FAIL',reasons=[str(error) if isinstance(error,ValueError) else 'HISTORICAL_INPUT_INCOMPLETE'])
    return result


def response(status, reasons, metrics=None):
    return {'schema': 'openbot.validate-market-plan.v2', 'status': status, 'reasons': reasons,
            'metrics': metrics or {}, 'order_authorized': False,
            'execution_readiness': 'EXECUTION_BLOCKED_CREDENTIAL_BOUNDARY'}


def validate_market_plan(plan, constraints, account, now_ms, receipts=None, digest=None):
    if plan is None or isinstance(plan, dict) and plan.get('decision') == 'NO_OPPORTUNITY':
        return response('SKIPPED_NO_PROPOSAL', ['NO_DIRECTOR_TRADE_PROPOSAL'])
    if not isinstance(plan, dict) or not isinstance(constraints, dict):
        return response('VETO', ['MALFORMED_PROPOSAL_OR_CONSTRAINTS'])
    if plan.get('decision') not in DECISIONS:
        return response('VETO', ['INVALID_DECISION_WATCH_IS_NOT_ACTIONABLE'])
    try:
        cutoff = constraints['as_of_ms']
        if type(cutoff) is not int or not 0 <= now_ms-cutoff <= 180_000:
            return response('VETO', ['STALE_OR_FUTURE_CANDLES'])
        quote = constraints['public_quote']
        if quote['quote_time_ms'] > cutoff:
            return response('VETO', ['TICKER_AFTER_RESEARCH_CUTOFF'])
        if constraints['public_symbol_status'] != 'TRADING':
            return response('VETO', ['INSTRUMENT_NOT_TRADING'])
        if (plan.get('stop_working_type') != 'MARK_PRICE'
                or plan.get('margin_type') != 'ISOLATED' or plan.get('position_side') != 'BOTH'
                or plan.get('engine_mode') != 'DEMO_READ_ONLY'):
            return response('VETO', ['UNSUPPORTED_MODE_MARGIN_OR_STOP_TRIGGER'])
        if type(plan.get('hold_seconds')) is not int or not 0 < plan['hold_seconds'] <= 15*3600:
            return response('VETO', ['HOLD_LIMIT_15_HOURS'])
        structural = plan['invalidation']
        if (not isinstance(structural, dict) or not structural.get('reason')
                or structural.get('source_sha256') not in constraints['closed_bar_source_sha256']
                or type(structural.get('available_at_ms')) is not int
                or structural['available_at_ms'] > cutoff):
            return response('VETO', ['STOP_STRUCTURAL_EVIDENCE_MISSING_OR_LOOKAHEAD'])
        anchor=next((a for a in constraints['structural_anchors']
                     if a['source_sha256']==structural['source_sha256']
                     and a['available_at_ms']==structural['available_at_ms']),None)
        if (anchor is None or plan['side'] not in {'LONG','SHORT'}
                or number(structural['anchor_price'])!=number(anchor['low' if plan['side']=='LONG' else 'high'])
                or (number(plan['stop'])>number(structural['anchor_price']) if plan['side']=='LONG'
                    else number(plan['stop'])<number(structural['anchor_price']))):
            return response('VETO',['STOP_NOT_OUTSIDE_CITED_BAR_STRUCTURE'])
        qty = number(plan['quantity'])
        if plan['decision'] == 'CONDITIONAL':
            trigger = plan.get('trigger', {})
            if (trigger.get('kind') not in {'CLOSED_5M_ABOVE', 'CLOSED_5M_BELOW'}
                    or trigger.get('order_after_confirmation') is not True
                    or type(trigger.get('not_before_ms')) is not int
                    or not cutoff <= trigger['not_before_ms'] < plan['expires_at_ms']
                    or number(trigger['price']) <= 0):
                return response('VETO', ['CONDITIONAL_TRIGGER_OR_ORDER_TIMING_INVALID'])
        translated = {**plan, 'decision': DECISIONS[plan['decision']]}
        result = assess(translated, constraints, account, now_ms, receipts, digest)
        if result['status'] == 'VETO':
            return response('VETO', result['reasons'], result['metrics'])
        # Geometry remains visible when real account / native receipts are unavailable.
        metrics = result['metrics']
        if not account:
            return response('UNKNOWN', [*result['reasons'], 'AUTHENTICATED_ACCOUNT_AND_DEMO_QUOTE_REQUIRED'], metrics)
        if (account.get('host') != DEMO or account.get('engine_mode') != 'DEMO_READ_ONLY'
                or account.get('authenticated') is not True
                or account.get('credential_boundary_verified') is not True):
            return response('VETO', ['ACCOUNT_VENUE_MODE_OR_CREDENTIAL_BOUNDARY'], metrics)
        if account.get('symbol_has_position') or account.get('symbol_has_open_orders') or account.get('symbol_has_algo_orders'):
            return response('VETO', ['EXISTING_OR_CONFLICTING_SYMBOL_EXPOSURE'], metrics)
        if (account.get('position_mode') != 'ONE_WAY' or account.get('margin_type') != 'ISOLATED'
                or account.get('multi_assets') is not False):
            return response('VETO', ['ACCOUNT_MODE_UNSUPPORTED'], metrics)
        venue_quote = account['demo_quote']
        if (venue_quote['host'] != DEMO or not 0 <= now_ms-venue_quote['observed_at_ms'] <= 10_000
                or not 0 < number(venue_quote['bid']) <= number(venue_quote['ask'])
                or number(venue_quote['mark']) <= 0):
            return response('VETO', ['DEMO_QUOTE_MISSING_STALE_OR_WRONG_VENUE'], metrics)
        reference = number(venue_quote['ask'] if plan['side'] == 'LONG' else venue_quote['bid'])
        if abs(reference-number(plan['entry']))/reference > Decimal('.0015'):
            return response('VETO', ['RESEARCH_DEMO_PRICE_DIVERGENCE'], metrics)
        direction = 1 if plan['side'] == 'LONG' else -1
        if direction*(number(venue_quote['mark'])-number(plan['stop'])) <= 0:
            return response('VETO', ['STOP_ALREADY_TRIGGERED_AT_DEMO_MARK'], metrics)
        bracket = account['bracket']
        notional = qty * number(plan['entry'])
        if (not number(bracket['notional_floor']) <= notional < number(bracket['notional_cap'])
                or number(plan['leverage']) > number(bracket['initial_leverage'])
                or number(account['configured_leverage']) != number(plan['leverage'])
                or number(bracket['maintenance_ratio']) != number(account['maintenance_ratio'])
                or number(bracket['maintenance_deduction_usdt']) != number(account['maintenance_deduction_usdt'])):
            return response('VETO', ['LEVERAGE_OR_MAINTENANCE_BRACKET_MISMATCH'], metrics)
        exits = plan['exits']
        if not isinstance(exits, list) or not 1 <= len(exits) <= 2:
            return response('VETO', ['EXIT_ALLOCATION_REQUIRED'], metrics)
        lot = account['demo_filters']['market']
        if sum(number(e['quantity']) for e in exits) != qty:
            return response('VETO', ['EXIT_SIZE_MISMATCH'], metrics)
        for exit in exits:
            amount, price = number(exit['quantity']), number(exit['price'])
            if (amount <= 0 or amount % number(lot['stepSize']) or amount < number(lot['minQty'])
                    or amount > number(lot['maxQty']) or exit.get('reduce_only') is not True
                    or price not in [number(plan['tp1']), number(plan['tp2'])]
                    or amount*price < number(account['demo_filters']['minimum_notional'])):
                return response('VETO', ['EXIT_BELOW_FILTER_OR_NOT_CLOSE_ONLY'], metrics)
        loss = number(metrics['net_stop_loss_usdt'])
        if loss > number(account['remaining_daily_loss_budget_usdt']):
            return response('VETO', ['DAILY_LOSS_BUDGET'], metrics)
        if loss+number(account['correlated_stop_risk_usdt']) > number(account['portfolio_stop_risk_budget_usdt']):
            return response('VETO', ['CORRELATED_PORTFOLIO_RISK'], metrics)
        if (notional/number(plan['leverage']) + loss > number(account['available_after_reservations_usdt'])
                or number(account['equity_usdt']) <= 0):
            return response('VETO', ['INSUFFICIENT_WALLET_AFTER_RESERVES_AND_COSTS'], metrics)
        if type(account['next_funding_ms']) is not int or account['next_funding_ms'] <= now_ms:
            return response('UNKNOWN', ['FUNDING_SCHEDULE_UNVERIFIED'], metrics)
        interval=account['funding_interval_ms']
        if type(interval) is not int or not 3600_000<=interval<=24*3600_000:
            return response('UNKNOWN',['FUNDING_INTERVAL_UNVERIFIED'],metrics)
        hold_end=now_ms+plan['hold_seconds']*1000
        funding_events=max(0,(hold_end-account['next_funding_ms'])//interval+1)
        per_event=number(account['adverse_funding_rate_per_event'])
        if per_event<0 or number(account['adverse_funding_rate'])<funding_events*per_event:
            return response('VETO',['FUNDING_STRESS_DOES_NOT_COVER_HOLD'],metrics)
        # Funding can deplete isolated margin before a stop triggers. Checking
        # P&L costs alone does not establish stop-to-liquidation clearance.
        leverage=number(plan['leverage'])
        stressed_margin=(notional/leverage
            -notional*(number(account['fee_per_side'])+number(account['adverse_funding_rate']))
            +number(account['maintenance_deduction_usdt']))
        liquidation=(notional-direction*stressed_margin)/(qty*(1-direction*number(account['maintenance_ratio'])))
        clearance=direction*(number(plan['stop'])-liquidation)
        metrics.update(funding_stressed_liquidation_usdt=str(liquidation),
                       funding_stressed_stop_clearance_usdt=str(clearance))
        if clearance<max(number(plan['entry'])*Decimal('.005'),abs(number(plan['entry'])-number(plan['stop']))/2):
            return response('VETO',['LIQUIDATION_BUFFER_AFTER_FUNDING_STRESS'],metrics)
        # Fee/funding stress in assess is already charged in net-stop and target economics.
        metrics.update(account_risk_percent=str(loss/number(account['equity_usdt'])*100),
                       gross_pnl_tp1_usdt=str(direction*(number(plan['tp1'])-number(plan['entry']))*qty),
                       net_pnl_tp1_usdt=str(number(metrics['tp1_after_cost_rr'])*loss),
                       net_pnl_tp2_usdt=str(number(metrics['tp2_after_cost_rr'])*loss),
                       fee_per_side=str(number(account['fee_per_side'])),
                       slippage_per_side=str(number(account['slippage_per_side'])),
                       adverse_funding_events=funding_events,
                       return_on_notional_stop_percent=str(-loss/notional*100),
                       return_on_margin_stop_percent=str(-loss/(notional/number(plan['leverage']))*100),
                       adverse_excursion='NOT_OBSERVED_PRETRADE',
                       funding_fee_basis='ADVERSE_RATE_COVERS_ALL_FUNDING_EVENTS_WITHIN_HOLD',
                       proposal_sha256=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest())
        return response(result['status'], result['reasons'], metrics)
    except (KeyError, TypeError, ValueError, InvalidOperation, ZeroDivisionError):
        return response('UNKNOWN', ['MISSING_INVALID_OR_NONFINITE_INPUT'])
