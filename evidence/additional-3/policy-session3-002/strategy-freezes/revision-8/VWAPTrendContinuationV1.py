"""UTC session VWAP reclaim with completed-hour directional context."""
from PlaybookRiskV1 import PlaybookRiskV1


class VWAPTrendContinuationV1(PlaybookRiskV1):
    stop_buffer = .2
    hold_hours = 8

    def populate_entry_trend(self, d, metadata):
        valid = self.validity(d) & d.vwap_valid & (d.session_bars >= 8) & d.same_session & (d.rvol >= 1.) & (d.adx_1h >= 20)
        long = (valid & (d.ema20_1h > d.ema50_1h) & (d.ema20 > d.ema50)
          & (d.close.shift() <= d.vwap.shift()) & (d.close > d.vwap)
          & ((d.low-d.vwap).abs() <= .5*d.atr14))
        short = (valid & (d.ema20_1h < d.ema50_1h) & (d.ema20 < d.ema50)
          & (d.close.shift() >= d.vwap.shift()) & (d.close < d.vwap)
          & ((d.high-d.vwap).abs() <= .5*d.atr14))
        return self.finalize_signals(d,long,short)
