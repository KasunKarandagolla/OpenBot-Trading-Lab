"""Experimental native-backtest funding repair, never an operational patch.

Delegate event valuation to Freqtrade Exchange.calculate_funding_fees, but own
each observed funding timestamp once. Native trade/order accounting is retained.
Assumption: a same-clock event applies BEFORE an exit. Exchange priority remains
unobserved and source-event bounds must still be reported. In-memory cursor is
not restart-safe; M1 stays disabled in the research runner and operational guard.
"""
import pandas as pd
from freqtrade.enums import TradingMode


class EventOnceFundingMixin:
    def _run_funding_fees(self,trade,current_time,force=False):
        if self.trading_mode!=TradingMode.FUTURES:
            return
        if not (force or current_time.timestamp()%self.funding_fee_timeframe_secs==0):
            return
        frame=self.futures_data[trade.pair]
        if not frame.date.is_monotonic_increasing or frame.date.duplicated().any():
            raise ValueError('funding source order/uniqueness unknown')
        cursors=getattr(self,'_master_funding_cursors',{})
        cursor=cursors.get(id(trade))
        first=pd.Timestamp(trade.open_date_utc)
        eligible=frame.loc[(frame.date>=first)&(frame.date<=pd.Timestamp(current_time))]
        if cursor is not None:
            eligible=eligible.loc[eligible.date>pd.Timestamp(cursor)]
        fee=0.
        if not eligible.empty:
            fee=self.exchange.calculate_funding_fees(eligible,amount=trade.amount,
                  is_short=trade.is_short,open_date=first.to_pydatetime(),close_date=current_time)
            cursors[id(trade)]=eligible.date.iloc[-1].isoformat()
            self._master_funding_cursors=cursors
        trade.set_funding_fees((trade.funding_fee_running or 0.)+fee)
