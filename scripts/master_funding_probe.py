"""Actual pinned native lifecycle reproduction with an explicitly synthetic event."""
import functools
import hashlib
import inspect
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pandas as pd
from freqtrade.enums import TradingMode
from freqtrade.exchange import Exchange
from freqtrade.optimize.backtesting import Backtesting
from freqtrade.persistence import LocalTrade,Order

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research'))
from master_audit.funding_once import EventOnceFundingMixin


class ResearchFundingBacktest(EventOnceFundingMixin,Backtesting):
    pass


def fixture(engine,short=False):
    start=pd.Timestamp('2026-08-20T07:00:00Z')
    event=start+pd.Timedelta(hours=1)
    finish=event+pd.Timedelta(hours=1)
    quantity=.01;price=2278.794;rate=.00005
    trade=LocalTrade(pair='ETH/USDT:USDT',open_rate=price,amount=quantity,
        stake_amount=quantity*price,open_date=start.to_pydatetime().replace(tzinfo=None),
        fee_open=.0006,fee_close=.0006,is_short=short,leverage=1.,
        trading_mode=TradingMode.FUTURES,precision_mode=4,amount_precision=.001,
        precision_mode_price=4,price_precision=.001)
    def order(identifier,entry,amount,at,status):
        return Order(order_id=identifier,ft_order_side=trade.entry_side if entry else trade.exit_side,
                     side=trade.entry_side if entry else trade.exit_side,order_type='limit',
                     ft_pair=trade.pair,ft_is_open=status=='open',status=status,
                     price=price,average=price,amount=amount,filled=amount if status=='closed' else 0.,
                     remaining=0 if status=='closed' else amount,
                     order_filled_date=at.to_pydatetime().replace(tzinfo=None) if status=='closed' else None,
                     funding_fee=0. if entry else None)
    entry=order('entry',True,quantity,start,'closed')
    trade.orders=[entry]
    trade.recalc_trade_from_orders()
    runner=engine.__new__(engine)
    runner.trading_mode=TradingMode.FUTURES
    runner.funding_fee_timeframe_secs=3600
    runner.futures_data={trade.pair:pd.DataFrame(dict(date=[event],
        _ff_date_ns=[event.value],_ff_fee_per_unit=[price*rate]))}
    runner.exchange=SimpleNamespace(calculate_funding_fees=functools.partial(Exchange.calculate_funding_fees,None))
    runner._run_funding_fees(trade,event.to_pydatetime())
    partial=order('partial',False,quantity*.5,event,'open');trade.orders.append(partial)
    partial.close_bt_order(event.to_pydatetime().replace(tzinfo=None),trade)
    runner._run_funding_fees(trade,event.to_pydatetime(),force=True)
    trade.recalc_trade_from_orders()
    final=order('final',False,quantity*.5,finish,'open');trade.orders.append(final)
    final.close_bt_order(finish.to_pydatetime().replace(tzinfo=None),trade)
    runner._run_funding_fees(trade,finish.to_pydatetime(),force=True)
    trade.recalc_trade_from_orders()
    expected=(1 if short else -1)*quantity*price*rate
    return dict(short=short,synthetic_event=True,expected_before_exit_priority=expected,
                after_exit_priority_bound=expected*.5,native_funding=trade.funding_fees,
                order_funding=[o.funding_fee for o in trade.orders],
                residual_vs_before_priority=trade.funding_fees-expected,
                reconciles=abs(trade.funding_fees-expected)<1e-12)


def main():
    path=ROOT/'evidence/master-audit/native-funding-lifecycle.json'
    if path.exists():
        raise ValueError('preserve funding probe')
    result=dict(engine='Freqtrade 2026.10',
                original=[fixture(Backtesting,x) for x in (False,True)],
                experimental_repair=[fixture(ResearchFundingBacktest,x) for x in (False,True)],
                original_method_sha256=hashlib.sha256(inspect.getsource(Backtesting._run_funding_fees).encode()).hexdigest(),
                M1_enabled=False,
                limits=['Synthetic lifecycle reproduction is not a new market result',
                        'No full repaired M1 economic replay, exchange partial-fill or restart qualification',
                        'Same-clock exchange priority unknown; explicit before-exit assumption only'])
    path.write_text(json.dumps(result,indent=2)+'\n')
    assert all(not x['reconciles'] for x in result['original'])
    assert all(x['reconciles'] for x in result['experimental_repair'])
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
