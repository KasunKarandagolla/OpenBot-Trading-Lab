"""Frozen Session 1 benchmark. No economic qualification is implied."""
from datetime import datetime, timedelta
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade


class TrendPullbackBaselineV1(IStrategy):
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = '15m'
    startup_candle_count = 200
    process_only_new_candles = True
    minimal_roi = {'0': 0.03}
    stoploss = -0.02
    trailing_stop = False
    position_adjustment_enable = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    @property
    def protections(self):
        return [{'method': 'CooldownPeriod', 'stop_duration_candles': 2}]

    def version(self) -> str:
        return '1.0.0'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['atr14'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_ratio'] = dataframe['atr14'] / dataframe['close']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Freqtrade supplies completed signal bars; fills occur on a later bar in backtesting.
        valid = ((dataframe['volume'] > 0) & (dataframe['close'] > 0)
                 & dataframe['atr_ratio'].between(0.001, 0.03, inclusive='both'))
        long = (valid & (dataframe['ema20'] > dataframe['ema50'])
                & (dataframe['close'].shift(1) <= dataframe['ema20'].shift(1))
                & (dataframe['close'] > dataframe['ema20']))
        short = (valid & (dataframe['ema20'] < dataframe['ema50'])
                 & (dataframe['close'].shift(1) >= dataframe['ema20'].shift(1))
                 & (dataframe['close'] < dataframe['ema20']))
        dataframe['enter_long'] = long.astype(int)
        dataframe['enter_short'] = short.astype(int)
        dataframe.loc[long, 'enter_tag'] = 'ema20_reclaim_v1'
        dataframe.loc[short, 'enter_tag'] = 'ema20_rejection_v1'
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = (dataframe['ema20'] < dataframe['ema50']).astype(int)
        dataframe['exit_short'] = (dataframe['ema20'] > dataframe['ema50']).astype(int)
        return dataframe

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs):
        if current_time - trade.open_date_utc >= timedelta(hours=12):
            return 'max_hold_12h'
        return None

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None,
                 side: str, **kwargs) -> float:
        return 1.0
