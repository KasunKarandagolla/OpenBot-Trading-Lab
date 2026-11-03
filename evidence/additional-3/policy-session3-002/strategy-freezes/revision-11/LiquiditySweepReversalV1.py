"""Candle failed-breakout reversal; no claim of visible stop orders or liquidations."""
import numpy as np
from PlaybookRiskV1 import PlaybookRiskV1


class LiquiditySweepReversalV1(PlaybookRiskV1):
    stop_buffer = .15
    hold_hours = 4

    def populate_entry_trend(self, d, metadata):
        valid = self.validity(d) & (d.rvol >= 1.2) & (d.adx_1h <= 30)
        body = np.maximum((d.close-d.open).abs(), .1*d.atr14)
        lower = d[['open','close']].min(axis=1)-d.low
        upper = d.high-d[['open','close']].max(axis=1)
        long = (valid & ((d.prior_low-d.low)/d.atr14).between(.1,1.)
          & (d.close > d.prior_low) & (lower >= 1.5*body))
        short = (valid & ((d.high-d.prior_high)/d.atr14).between(.1,1.)
          & (d.close < d.prior_high) & (upper >= 1.5*body))
        return self.finalize_signals(d,long,short)
