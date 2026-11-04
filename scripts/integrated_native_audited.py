"""Observe native Order objects, including canceled nonfills; no decision changes."""
from integrated_common import *

def run(variant,fee=.00075,execution='touch',replay_id=None):
    from freqtrade.optimize.backtesting import Backtesting,DATE_IDX
    from integrated_native import native
    original=Backtesting._enter_trade
    trades={};orders={};attempts=[]
    def observed(self,pair,row,direction,*args,**kwargs):
        result=original(self,pair,row,direction,*args,**kwargs)
        attempts.append(dict(pair=pair,at=row[DATE_IDX].isoformat(),side=direction,returned_trade_id=result.id if result else None))
        if result:
            trades[result.id]=result
            for o in result.orders: orders[(result.id,o.order_id)]=(result,o)
        return result
    Backtesting._enter_trade=observed
    try: native(variant,fee,execution,replay_id)
    finally: Backtesting._enter_trade=original
    for t in trades.values():
        for o in t.orders: orders[(t.id,o.order_id)]=(t,o)
    rows=[];plans=read(WORK/'plans'/(variant+'.json'))
    for t,o in orders.values():
        g=t.get_custom_data('policy_plan')
        if not g:
            g=plans.get(t.pair,{}).get(t.open_date_utc.isoformat())
        rows.append(dict(trade_id=t.id,pair=t.pair,order_id=o.order_id,is_entry=o.ft_order_side==t.entry_side,
            order_type=o.order_type,status=o.status,created_at=o.order_date_utc.isoformat(),
            filled_at=o.order_filled_utc.isoformat() if o.filled and o.order_filled_utc else None,
            update_at=o.order_update_date.isoformat() if o.order_update_date else None,
            native_price=float(o.safe_price),amount=float(o.amount),filled=float(o.filled or 0),remaining=float(o.remaining or 0),
            decision_id=g['decision_id'] if g else None,requested_reference=g['reference'] if g else None,
            plan_expires_at=g['expires_at'] if g else None,setup_id=g.get('setup_id') if g else None,
            entry_notional=float(o.amount)*float(o.safe_price) if o.ft_order_side==t.entry_side else None))
    label=f'{variant}-{execution}-{round(fee*1e6)}'+('-'+replay_id if replay_id else '')
    write(OUT/'native'/label/'order-audit.json',dict(instrumentation_sha256=sha(Path(__file__)),
        mechanism='Observer wraps native Backtesting._enter_trade, returns original object unchanged and retains native order references through cancellation',
        attempts=attempts,orders=rows))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('variant');p.add_argument('--fee',type=float,default=.00075)
    p.add_argument('--execution',choices=['touch','through'],default='touch');p.add_argument('--replay-id')
    a=p.parse_args();run(a.variant,a.fee,a.execution,a.replay_id)
