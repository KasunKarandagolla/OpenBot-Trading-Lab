"""Shared Session 2 callbacks. Candle research, never an exchange execution engine."""
from datetime import timedelta
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import talib.abstract as ta
from freqtrade.strategy import IStrategy, informative, stoploss_from_absolute
from freqtrade.persistence import Trade

COST_ALLOWANCE = .0012 + .002 + .0003  # fees + assumed friction + adverse funding


def session_features(df):
    d = df.copy()
    day = pd.to_datetime(d.date, utc=True).dt.floor('D')
    typical = (d.high + d.low + d.close) / 3
    volume = d.volume.where(d.volume > 0, 0.)
    d['vwap'] = (typical * volume).groupby(day).cumsum() / volume.groupby(day).cumsum().replace(0, np.nan)
    d['session_bars'] = d.groupby(day).cumcount() + 1
    d['same_session'] = day.eq(day.shift())
    clean = pd.Series(np.isfinite(d[['open','high','low','close','volume']].to_numpy(dtype=float)).all(axis=1),index=d.index) & (d.volume >= 0)
    continuity = d.date.diff().eq(pd.Timedelta(minutes=15)) | d.date.eq(day)
    d['vwap_valid'] = (clean & continuity).groupby(day).cummin()
    d['rvol'] = d.volume / d.volume.shift(1).rolling(20, min_periods=20).mean().replace(0, np.nan)
    d['prior_low'] = d.low.shift(1).rolling(20, min_periods=20).min()
    d['prior_high'] = d.high.shift(1).rolling(20, min_periods=20).max()
    d['contiguous'] = d.date.diff().eq(pd.Timedelta(minutes=15)).rolling(21, min_periods=21).sum().eq(21)
    d['ema20'] = ta.EMA(d, timeperiod=20)
    d['ema50'] = ta.EMA(d, timeperiod=50)
    d['atr14'] = ta.ATR(d, timeperiod=14)
    d['atr_ratio'] = d.atr14 / d.close
    return d


def geometry(row, side, rate, buffer):
    """All prices in quote units. Return None rather than fabricate missing risk."""
    try:
        atr = float(row['atr14']); ref = float(row['close'])
        stop = float(row['high']) + buffer*atr if side == 'short' else float(row['low']) - buffer*atr
        sign = -1 if side == 'short' else 1
        fraction = sign*(rate-stop)/rate
        if not all(math.isfinite(x) and x > 0 for x in (atr, ref, rate, stop)):
            return None
        deviation = min(.0015, .25*atr/ref)
        if abs(rate/ref-1) > deviation + 1e-12 or not .003 <= fraction <= .025:
            return None
        # Target is a native net ROI request. Conservative denominator includes costs.
        if 2*fraction / (fraction+COST_ALLOWANCE) < 1.25:
            return None
        return {'reference':ref, 'stop':stop, 'risk_fraction':fraction,
                'deviation_fraction':deviation, 'target_roi':2*fraction,
                'modeled_loss_per_notional':fraction+COST_ALLOWANCE}
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        return None


def stake_for(g, min_stake, max_stake):
    if not g or not math.isfinite(max_stake) or max_stake <= 0:
        return 0.
    stake = min(25., max_stake, 2.5/g['modeled_loss_per_notional'])
    if not math.isfinite(stake) or stake <= 0 or (min_stake is not None and stake < min_stake):
        return 0.
    return stake


class PlaybookRiskV1(IStrategy):
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = '15m'
    startup_candle_count = 240
    process_only_new_candles = True
    stoploss = -.03  # emergency bound if a callback is unavailable
    minimal_roi = {'0': 100.}
    use_custom_stoploss = True
    use_custom_roi = True
    trailing_stop = False
    position_adjustment_enable = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    stop_buffer = .2
    hold_hours = 8
    order_time_in_force = {'entry':'GTC', 'exit':'GTC'}

    def version(self):
        return '1.0.0'

    @property
    def protections(self):
        return [{'method':'CooldownPeriod', 'stop_duration_candles':2}]

    @informative('1h')
    def populate_indicators_1h(self, dataframe, metadata):
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['context_valid'] = (np.isfinite(dataframe[['open','high','low','close','volume']]).all(axis=1)
          & (dataframe.volume > 0) & dataframe.date.diff().eq(pd.Timedelta(hours=1)))
        return dataframe

    def populate_indicators(self, dataframe, metadata):
        return session_features(dataframe)

    def validity(self, d):
        columns = ['open','high','low','close','volume','atr14','ema20','ema50','rvol','ema20_1h','ema50_1h','adx_1h']
        finite = pd.Series(np.isfinite(d[columns].to_numpy(dtype=float)).all(axis=1), index=d.index)
        # Native merge dates are hourly OPEN times. Hour close must precede signal availability.
        age = d.date + pd.Timedelta(minutes=15) - (d.date_1h + pd.Timedelta(hours=1))
        return (finite & (d.volume > 0) & (d.close > 0) & d.contiguous
          & d.atr_ratio.between(.001,.025) & d.context_valid_1h.eq(True)
          & age.between(pd.Timedelta(0),pd.Timedelta(minutes=45)))

    def finalize_signals(self, d, long, short):
        d['candidate_long'] = long.astype(int)
        d['candidate_short'] = short.astype(int)
        # Geometry gating is vectorized, using the exact callback formula at reference close.
        lr = (d.close - (d.low-self.stop_buffer*d.atr14))/d.close
        sr = ((d.high+self.stop_buffer*d.atr14)-d.close)/d.close
        lg = lr.between(.003,.025) & ((2*lr/(lr+COST_ALLOWANCE)) >= 1.25)
        sg = sr.between(.003,.025) & ((2*sr/(sr+COST_ALLOWANCE)) >= 1.25)
        d['enter_long'] = (long & lg).astype(int)
        d['enter_short'] = (short & sg).astype(int)
        d['reason'] = np.select([~self.validity(d), (long&~lg)|(short&~sg), (long&lg)|(short&sg)],
                               ['INVALID_OR_STALE_DATA','COST_OR_STOP_GEOMETRY','CANDIDATE'], default='NO_SETUP')
        d.loc[(d.enter_long == 1)|(d.enter_short == 1),'enter_tag'] = self.__class__.__name__+':v1'
        return d

    def populate_exit_trend(self, dataframe, metadata):
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe

    def signal_row(self, pair, current_time, side=None):
        try:
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if df.empty:
                return None
            row = df.iloc[-1]
            available = row['date'].to_pydatetime() + timedelta(minutes=15)
            if not timedelta(0) <= current_time-available < timedelta(minutes=5):
                return None
            if side and int(row.get('enter_'+side,0)) != 1:
                return None
            return row
        except (AttributeError, KeyError, ValueError, TypeError):
            return None

    def event(self, pair, now, side, reason, g=None, amount=None, rate=None):
        # Bounded local diagnostics. No API, credentials or raw source candles.
        if not self.config.get('lab_audit',False):
            return
        p = Path('/lab/user_data/logs/s2-events.jsonl')
        if p.exists() and p.stat().st_size > 4_000_000:
            return
        row = self.signal_row(pair,now,side)
        item = {'schema_version':1,'strategy':self.__class__.__name__,'pair':pair,'side':side,
                'decision_utc':now.isoformat(),'reason':reason,'geometry':g,'amount':amount,'rate':rate,
                'signal_open_utc':None if row is None else row['date'].isoformat(),
                'timeframe':'15m','expiry_seconds':300,'fee_round_trip':.0012,
                'assumed_extra_friction':.002,'adverse_funding_allowance':.0003}
        with p.open('a') as f:
            f.write(json.dumps(item,allow_nan=False)+'\n')

    def custom_entry_price(self, pair, trade, current_time, proposed_rate, entry_tag, side, **kwargs):
        row = self.signal_row(pair,current_time,side)
        return float(row['close']) if row is not None else proposed_rate

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake,
                            min_stake, max_stake, leverage, entry_tag, side, **kwargs):
        row = self.signal_row(pair,current_time,side)
        if row is None or leverage != 1:
            return 0.
        return stake_for(geometry(row,side,current_rate,self.stop_buffer),min_stake,max_stake)

    def daily_allowed(self, current_time):
        """UTC realized net loss only; explicitly not a mark-to-market account-loss halt."""
        start = current_time.replace(hour=0,minute=0,second=0,microsecond=0)
        try:
            closed = Trade.get_trades_proxy(is_open=False)
            pnl = sum(float(t.close_profit_abs or 0) for t in closed
              if t.close_date_utc is not None and start <= t.close_date_utc <= current_time)
            return math.isfinite(pnl) and pnl > -10.
        except Exception:
            return False

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force,
                            current_time, entry_tag, side, **kwargs):
        row = self.signal_row(pair,current_time,side)
        g = geometry(row,side,rate,self.stop_buffer) if row is not None else None
        reason = 'ACCEPTED'
        try:
            open_trades = Trade.get_open_trades()
            notional = amount*rate
            # Reserve the 3% emergency stop + costs for every admitted 25 USDT position.
            if g is None:
                reason = 'STALE_PRICE_OR_GEOMETRY'
            elif not math.isfinite(notional) or not 0 < notional <= 25.+1e-7:
                reason = 'INVALID_NOTIONAL'
            elif len(open_trades) >= 2 or any(t.pair == pair for t in open_trades):
                reason = 'CAPACITY_OR_SYMBOL'
            elif notional*(.03+COST_ALLOWANCE) > 2.5 or (sum(t.stake_amount for t in open_trades)+notional)*(.03+COST_ALLOWANCE) > 5.:
                reason = 'INTENDED_RISK'
            elif not self.daily_allowed(current_time):
                reason = 'UTC_REALIZED_LOSS_OR_UNAVAILABLE'
        except Exception:
            reason = 'RISK_STATE_UNAVAILABLE'
        self.event(pair,current_time,side,reason,g,amount,rate)
        return reason == 'ACCEPTED'

    def check_entry_timeout(self, pair, trade, order, current_time, **kwargs):
        # Never replace/reprice an expired setup. The native timeout is also five minutes.
        opened = order.order_date_utc
        expired = current_time-opened >= timedelta(minutes=5)
        row = self.signal_row(pair,current_time,'short' if trade.is_short else 'long')
        cancelled = expired or row is None
        mode = self.config.get('runmode')
        if row is not None and getattr(mode,'value',mode) == 'dry_run':
            try:
                quote = self.dp.ticker(pair)
                rate = float(quote['bid' if trade.is_short else 'ask'])
                cancelled = cancelled or geometry(row,'short' if trade.is_short else 'long',rate,self.stop_buffer) is None
            except Exception:
                cancelled = True
        if cancelled:
            self.event(pair,current_time,'short' if trade.is_short else 'long','EXPIRED_OR_INVALIDATED')
        return cancelled

    def adjust_entry_price(self, trade, order, pair, current_time, proposed_rate,
                           current_order_rate, entry_tag, side, **kwargs):
        # Keeping original rate cannot chase; timeout handles cancellation.
        return current_order_rate

    def order_filled(self, pair, trade, order, current_time, **kwargs):
        if order.ft_order_side != trade.entry_side or trade.get_custom_data('initial_geometry') is not None:
            return
        row = self.signal_row(pair,current_time,'short' if trade.is_short else 'long')
        g = geometry(row,'short' if trade.is_short else 'long',trade.open_rate,self.stop_buffer) if row is not None else None
        if g:
            g['initial_risk_usdt'] = trade.stake_amount*g['modeled_loss_per_notional']
            g['signal_open_utc'] = row['date'].isoformat()
            trade.set_custom_data('initial_geometry',g)

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit,
                        after_fill=False, **kwargs):
        g = trade.get_custom_data('initial_geometry')
        if not g:
            return None  # native emergency stop remains, never zero-risk
        return stoploss_from_absolute(g['stop'],current_rate,is_short=trade.is_short,leverage=1.)

    def custom_roi(self, pair, trade, current_time, trade_duration, entry_tag, side, **kwargs):
        g = trade.get_custom_data('initial_geometry')
        return g['target_roi'] if g else None

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        if trade.get_custom_data('initial_geometry') is None:
            return 'geometry_unavailable'
        if current_time-trade.open_date_utc >= timedelta(hours=self.hold_hours):
            return 'max_hold_'+str(self.hold_hours)+'h'
        return None

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        return 1.
