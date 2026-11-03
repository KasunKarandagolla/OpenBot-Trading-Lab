"""Event-once native valuation, explicitly before exit at an identical clock.

Scoped to a disposable native Backtesting subclass. No installed Freqtrade
module, operational Trade, exchange API or persistent database is modified.
"""
import pandas as pd
from freqtrade.enums import TradingMode


class EventOnceFunding:
    def _run_funding_fees(self, trade, current_time, force=False):
        if self.trading_mode != TradingMode.FUTURES:
            return
        if not (force or current_time.timestamp() % self.funding_fee_timeframe_secs == 0):
            return
        frame = self.futures_data[trade.pair]
        if not frame.date.is_monotonic_increasing or frame.date.duplicated().any():
            raise ValueError('funding source must have ordered unique event clocks')
        first = pd.Timestamp(trade.open_date_utc)
        # A cursor on this native trade object cannot leak through reused Python
        # object IDs or a subsequent portfolio. It is intentionally not persistent.
        cursor = getattr(trade, '_foundation_funding_cursor', None)
        eligible = frame.loc[(frame.date >= first) & (frame.date <= pd.Timestamp(current_time))]
        if cursor is not None:
            eligible = eligible.loc[eligible.date > cursor]
        fee = 0.
        if not eligible.empty:
            fee = self.exchange.calculate_funding_fees(
                eligible, amount=trade.amount, is_short=trade.is_short,
                open_date=first.to_pydatetime(), close_date=current_time)
            trade._foundation_funding_cursor = eligible.date.iloc[-1]
        trade.set_funding_fees((trade.funding_fee_running or 0.) + fee)
