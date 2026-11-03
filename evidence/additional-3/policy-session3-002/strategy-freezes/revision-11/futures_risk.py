"""Illustrative, fail-closed linear-futures risk calculation, never an order API."""
import math


def evaluate(*, side, price, stop, equity, day_start_equity, available_margin,
             unrealized_pnl, leverage, contract_size, min_contracts, step_contracts,
             tiers, open_risk=0., pending_risk=0., correlated_notional=0.,
             requested_notional=25., costs=.0035):
    values=[price,stop,equity,day_start_equity,available_margin,unrealized_pnl,
            leverage,contract_size,min_contracts,step_contracts,open_risk,
            pending_risk,correlated_notional,requested_notional,costs]
    if side not in ('long','short') or not all(math.isfinite(float(x)) for x in values):
        return {'status':'REJECT','reason':'MISSING_OR_INVALID_ACCOUNT_STATE'}
    mtm=equity+unrealized_pnl
    if min(price,stop,mtm,day_start_equity,leverage,contract_size,step_contracts)<=0 or min(available_margin,min_contracts,open_risk,pending_risk,correlated_notional,costs)<0:
        return {'status':'REJECT','reason':'INVALID_RISK_INPUT'}
    if mtm<=day_start_equity*.99:
        return {'status':'REJECT','reason':'MARK_TO_MARKET_DAILY_LOSS'}
    sign=1 if side=='long' else -1
    distance=sign*(price-stop)/price
    if not 0<distance<1:
        return {'status':'REJECT','reason':'INVALID_STRUCTURAL_STOP'}
    budget=min(mtm*.0025,mtm*.005-open_risk-pending_risk)
    notional=min(requested_notional,budget/(distance+costs),available_margin*leverage)
    if notional<=0:return {'status':'REJECT','reason':'PORTFOLIO_OR_PENDING_RISK'}
    contracts=math.floor((notional/(price*contract_size))/step_contracts)*step_contracts
    notional=contracts*contract_size*price
    if contracts<min_contracts or notional<=0:
        return {'status':'REJECT','reason':'MINIMUM_SIZE'}
    tier=next((t for t in (tiers or []) if t['min_notional']<=notional<t['max_notional']),None)
    if not tier:return {'status':'REJECT','reason':'MARGIN_TIER_UNKNOWN'}
    if leverage>tier['max_leverage']:
        return {'status':'REJECT','reason':'LEVERAGE_LIMIT'}
    mmr=tier['maintenance_rate'];deduction=tier.get('maintenance_deduction',0.)
    if not 0<=mmr<1:return {'status':'REJECT','reason':'INVALID_MARGIN_TIER'}
    margin=notional/leverage
    # Isolated linear approximation; entry/close fee reserve is explicitly held aside.
    base=contracts*contract_size
    usable=margin-notional*.0012
    liq=(notional-usable-deduction)/(base*(1-mmr)) if sign==1 else (notional+usable+deduction)/(base*(1+mmr))
    clearance=sign*(stop-liq)/price
    status='PASS';reason='ILLUSTRATIVE_BUDGET_AND_CLEARANCE'
    if clearance<.01:status='REJECT';reason='BUFFERED_LIQUIDATION_CLEARANCE'
    if correlated_notional+notional>mtm*.5:status='REJECT';reason='CORRELATED_EXPOSURE'
    return {'status':status,'reason':reason,'owner_approved':False,'version':'illustrative-risk-v1',
            'equity_mark_to_market':mtm,'price_risk_fraction':distance,'contracts':contracts,
            'base_amount':base,'notional':notional,'margin':margin,'leverage':leverage,
            'planned_risk':notional*(distance+costs),'native_stop_ratio':-distance*leverage,
            'liquidation_price_approx':liq,'buffered_clearance_fraction':clearance-.01,
            'cost_allowance':notional*costs,'tier':tier,
            'limitations':'Isolated algebra, no cross-margin/gap/outage guarantee. Requires current validated tier and account inputs. Research only.'}
