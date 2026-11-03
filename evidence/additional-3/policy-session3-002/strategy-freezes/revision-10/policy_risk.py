"""Deterministic isolated linear-perpetual budgets. No exchange/order methods."""
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_FLOOR
import math

COST=.0038

@dataclass(frozen=True)
class Account:
    cash: float
    unrealized_net: float
    free_collateral: float
    posted_margin: float
    pending_margin: float
    open_risk: float
    pending_risk: float
    gross_notional: float
    correlated_notional: float
    positions: int
    day_start_equity: float
    peak_equity: float
    loss_streak: int=0
    cooldown_until: float=0
    asof: float=0
    complete: bool=True
    @property
    def equity(self): return self.cash+self.unrealized_net


def health(a,clock):
    if not a.complete or not all(math.isfinite(float(v)) for k,v in asdict(a).items() if k!='complete'): return 'ACCOUNT_STATE_UNAVAILABLE'
    if not 0<=clock-a.asof<=60: return 'ACCOUNT_SNAPSHOT_STALE'
    if min(a.equity,a.day_start_equity,a.peak_equity)<=0 or a.free_collateral<0: return 'MARGIN_EXHAUSTED'
    if a.equity<=a.day_start_equity*.99: return 'DAILY_MARK_TO_MARKET_LOSS'
    if a.equity<=a.peak_equity*.95: return 'PEAK_MARK_TO_MARKET_DRAWDOWN'
    if a.loss_streak>=3 and clock<a.cooldown_until: return 'LOSS_STREAK_COOLDOWN'
    if a.open_risk+a.pending_risk>=a.equity*.005: return 'PORTFOLIO_STOP_RISK_LIMIT'
    if a.gross_notional>=a.equity or a.correlated_notional>=a.equity*.5: return 'GROSS_OR_CORRELATED_EXPOSURE'
    return 'PASS'


def liquidation(entry,notional,leverage,side,tier,taker=.00075):
    """Gate documented isolated equation, tier selected by NOTIONAL, no guessed deduction.

    Only tiers explicitly recording deduction=0 support this venue equation.
    Conservative fee-inclusive formula uses current public specifications.
    """
    if not tier or tier.get('maintenance_deduction')!=0: return None
    mm=float(tier['maintenance_rate'])+taker
    if not 0<=mm<1: return None
    margin=notional/leverage; amount=notional/entry
    return (entry-margin/amount)/(1-mm) if side=='long' else (entry+margin/amount)/(1+mm)


def size(a,*,clock,side,entry,stop,leverage,contract,cap=250.,min_margin=0.):
    reason=health(a,clock)
    def reject(r): return dict(status='REJECT',reason=r,equity=a.equity)
    if reason!='PASS': return reject(reason)
    if a.positions>=2: return reject('SIMULTANEOUS_POSITION_LIMIT')
    if side not in ('long','short') or not all(math.isfinite(float(v)) and v>0 for v in [entry,stop,leverage,cap]): return reject('INVALID_PLAN')
    sign=1 if side=='long' else -1; distance=sign*(entry-stop)/entry
    if not .003-1e-12<=distance<=.025+1e-12: return reject('LOGICAL_STOP_OUTSIDE_POLICY')
    if not contract or not contract.get('verified'): return reject('CONTRACT_UNKNOWN')
    mult=contract.get('contract_size'); step=contract.get('step_contracts'); minimum=contract.get('min_contracts')
    if any(v is None or not math.isfinite(float(v)) or float(v)<=0 for v in [mult,step,minimum]): return reject('LOT_SPEC_UNKNOWN')
    if leverage>20: return reject('POLICY_LEVERAGE_CEILING')
    budget=min(a.equity*.0025,a.equity*.005-a.open_risk-a.pending_risk)
    free=max(0,a.free_collateral-a.pending_margin)
    notional=min(cap,budget/(distance+COST),free/(1/leverage+COST),a.equity-a.gross_notional,a.equity*.5-a.correlated_notional)
    contracts=float((Decimal(str(notional))/Decimal(str(entry*mult*step))).to_integral_value(rounding=ROUND_FLOOR)*Decimal(str(step)))
    amount=contracts*mult; notional=amount*entry; margin=notional/leverage
    if contracts<minimum or notional<contract.get('min_notional',0) or margin<min_margin: return reject('MINIMUM_ORDER_OR_MARGIN')
    if contract.get('max_contracts') is not None and contracts>contract['max_contracts']: return reject('MAXIMUM_CONTRACT_AMOUNT')
    tier=next((t for t in contract.get('tiers',[]) if t['min_notional']<=notional<t['max_notional']),None)
    if not tier:
        if leverage!=1 or free<notional*(1+COST): return reject('MARGIN_TIERS_UNAVAILABLE_LEVERAGE_UNSUPPORTED')
        liq=0. if sign==1 else 2*entry; clearance=sign*(stop-liq)/entry
        qualification='FULLY_COLLATERALIZED_1X_FALLBACK_NO_TIER_CLAIM'
    else:
        if leverage>tier['max_leverage']: return reject('CONTRACT_TIER_LEVERAGE_LIMIT')
        liq=liquidation(entry,notional,leverage,side,tier,contract.get('taker',.00075))
        if liq is None: return reject('LIQUIDATION_EQUATION_UNSUPPORTED')
        clearance=sign*(stop-liq)/entry; qualification='CURRENT_PUBLIC_GATE_TIER_NOT_HISTORICAL_TIER'
    if clearance<.01: return reject('STOP_LIQUIDATION_CLEARANCE_UNDER_1_PERCENT')
    return dict(status='PASS',reason=qualification,equity=a.equity,risk_budget=budget,contracts=contracts,
        amount=amount,notional=notional,margin=margin,leverage=leverage,planned_loss=notional*(distance+COST),
        liquidation_price=liq,stop_clearance=clearance,native_stop_ratio=-distance*leverage,
        free_collateral_after_reserves=free-margin-notional*COST,tier=tier)


def native_entry_margin(verdict,entry,leverage,contract,max_margin):
    """Represent an already-floored legal lot through native margin conversion.

    One-ULP upward adjustments repair binary roundoff only. Native reconversion
    must equal the original approved quantity; no extra contract or risk is added.
    """
    from freqtrade.exchange import amount_to_contract_precision
    from ccxt import TICK_SIZE
    desired=float(Decimal(str(verdict['contracts']))*Decimal(str(contract['contract_size'])))
    stake=desired*entry/leverage
    step=contract['contract_size']*contract['step_contracts']
    for _ in range(64):
        got=amount_to_contract_precision(stake/entry*leverage,contract['step_contracts'],TICK_SIZE,contract['contract_size'])
        if abs(got-desired)<step*1e-8:
            return stake if stake<=max_margin else 0.
        if got>desired:return 0.
        stake=math.nextafter(stake,math.inf)
    return 0.


def native_exit_reduction(quantity,trade):
    """Match Freqtrade's FtPrecise stake->base conversion before lot truncation."""
    from freqtrade.exchange import amount_to_contract_precision
    from freqtrade.util import FtPrecise
    stake=trade.stake_amount*quantity/trade.amount
    step=trade.contract_size*trade.amount_precision
    for _ in range(64):
        raw=abs(float(FtPrecise(-stake)*FtPrecise(trade.amount)/FtPrecise(trade.stake_amount)))
        got=amount_to_contract_precision(raw,trade.amount_precision,trade.precision_mode,trade.contract_size)
        if abs(got-quantity)<step*1e-8:return stake
        if got>quantity:return 0.
        stake=math.nextafter(stake,math.inf)
    return 0.
