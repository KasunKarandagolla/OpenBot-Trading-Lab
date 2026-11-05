"""Native Freqtrade adapter for frozen, completed five-minute research signals."""

import json
from pathlib import Path

import pandas as pd
from freqtrade.enums import RunMode
from freqtrade.strategy import IStrategy, stoploss_from_absolute


class SetupFirst5mV1(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = True
    startup_candle_count = 0
    stoploss = -.025
    trailing_stop = False
    use_custom_stoploss = True
    use_custom_roi = True
    use_exit_signal = True
    position_adjustment_enable = False
    minimal_roi = {"0": 100.0}
    order_types = {
        "entry": "limit", "exit": "market", "stoploss": "market", "stoploss_on_exchange": False,
    }

    def bot_start(self, **kwargs):
        if self.config["runmode"] != RunMode.BACKTEST or self.config["dry_run"] is not True:
            raise ValueError("SetupFirst5mV1 requires offline historical backtesting")
        self.plans = {x["decision_id"]: x for x in json.loads(Path(self.config["recovery_plans"]).read_text())}

    def populate_indicators(self, dataframe, metadata):
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        symbol = metadata["pair"].split("/")[0] + "USDT"
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""
        for plan in self.plans.values():
            if plan["symbol"] != symbol:
                continue
            # Freqtrade shifts signals by one candle. The signal row opens
            # five minutes before the frozen close-time decision.
            at = pd.Timestamp(plan["decision_at"]) - pd.Timedelta(minutes=5)
            mask = dataframe.date.eq(at)
            dataframe.loc[mask, ["enter_" + plan["side"], "enter_tag"]] = [1, plan["decision_id"]]
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        return dataframe

    def leverage(self, **kwargs):
        return 1.0

    def custom_entry_price(self, pair, trade, current_time, proposed_rate, entry_tag, side, **kwargs):
        plan = self.plans.get(entry_tag)
        if plan is None:
            return proposed_rate
        return plan["entry"]

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force,
                            current_time, entry_tag, side, **kwargs):
        plan = self.plans.get(entry_tag)
        if plan is None or side != plan["side"] or amount * rate > 25 + 1e-9:
            return False
        if pd.Timestamp(current_time) != pd.Timestamp(plan["earliest_order_at"]):
            return False
        sign = 1 if side == "long" else -1
        risk = sign * (rate - plan["stop"]) / rate
        reward = sign * (plan["target"] - rate) / rate
        allowance = plan["admission_cost_allowance"]
        return (abs(rate / plan["entry"] - 1) <= plan["max_deviation"]
                and 0 < risk <= .025 and (reward - allowance) / (risk + allowance) >= 1.25)

    def check_entry_timeout(self, pair, trade, order, current_time, **kwargs):
        return pd.Timestamp(current_time) >= pd.Timestamp(self.plans[trade.enter_tag]["expires_at"])

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit,
                        after_fill=False, **kwargs):
        plan = self.plans[trade.enter_tag]
        return stoploss_from_absolute(plan["stop"], current_rate, is_short=trade.is_short,
                                      leverage=trade.leverage)

    def custom_roi(self, pair, trade, current_time, trade_duration, entry_tag, side, **kwargs):
        return max(0, trade.calc_profit_ratio(self.plans[entry_tag]["target"]))

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        plan = self.plans[trade.enter_tag]
        minutes = min(plan["max_hold_minutes"], 900)
        if pd.Timestamp(current_time) >= pd.Timestamp(trade.open_date_utc) + pd.Timedelta(minutes=minutes):
            return "TIME_CAP"
        frame, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        closed = frame.loc[frame.date + pd.Timedelta(minutes=5) <= current_time, "close"].tail(2)
        sign = -1 if trade.is_short else 1
        if len(closed) == 2 and (sign * (closed - plan["boundary"]) < -.15 * plan["atr15"]).all():
            return "THESIS_INVALIDATION"
        return None
