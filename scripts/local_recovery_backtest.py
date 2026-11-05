"""Run the registered five-minute contracts through network-disabled Freqtrade."""

import argparse
import json

import ccxt
import pandas as pd
from freqtrade.commands import Arguments
from freqtrade.commands.optimize_commands import setup_optimize_configuration
from freqtrade.enums import RunMode
from freqtrade.exchange import price_to_precision
from freqtrade.exchange.exchange import Exchange
from freqtrade.optimize.backtesting import Backtesting, DATE_IDX, ENTER_TAG_IDX, HIGH_IDX, LOW_IDX
from freqtrade.persistence import LocalTrade

from local_recovery_convert import load
from local_recovery_data import ROOT, WORK, protocol, write_json
from local_recovery_scan import frame_hash

IMAGE = "freqtradeorg/freqtrade@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7"
ADAPTER = "scripts/local_recovery_backtest.py"


def pair_name(symbol):
    return symbol.removesuffix("USDT") + "/USDT:USDT"


def freeze():
    files = [ROOT / "research/local_recovery/protocol.json",
             ROOT / "research/local_recovery/SetupFirst5mV1.py",
             *(ROOT / "scripts" / f"local_recovery_{name}.py" for name in ("data", "convert", "scan")),
             ROOT / "research/setup/setup_map.py", ROOT / "research/session3/causal_structure.py",
             WORK / "sources.json", WORK / "quality.json", WORK / "current-exchangeinfo.json",
             *sorted((WORK / "binance").rglob("*.feather"))]
    path = WORK / "research-freeze.json"
    value = {"image": IMAGE, "sha256": {str(p.relative_to(ROOT)): frame_hash(p) for p in files}}
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError("refusing to overwrite the existing research freeze")
        return
    write_json(path, value)


def validate_freeze(partition):
    path = WORK / "research-freeze.json"
    receipt = json.loads((WORK / partition / "scan-freeze.json").read_text())
    if receipt["freeze_sha256"] != frame_hash(path):
        raise ValueError("scan does not match the original protocol and code freeze")
    hashes = json.loads(path.read_text())["sha256"]
    for name, sha in hashes.items():
        candidate = ROOT / name
        if name == ADAPTER and frame_hash(candidate) != sha:
            # A pre-result transport repair retained the original exact bytes.
            # The strategy, scanner, protocol and input data still verify above.
            candidate = WORK / "pre-replay-adapter.py"
        if frame_hash(candidate) != sha:
            raise ValueError(f"frozen file changed: {name}")
    for name, sha in receipt["sha256"].items():
        if frame_hash(WORK / partition / name) != sha:
            raise ValueError(f"frozen scan output changed: {name}")


def install_snapshot(symbols):
    path = WORK / "current-exchangeinfo.json"
    info = json.loads(path.read_text())
    public_rows = [row for row in info["symbols"] if row["symbol"] in symbols
                   and row["contractType"] == "PERPETUAL" and row["status"] == "TRADING"]
    markets = {m["symbol"]: m for m in ccxt.binanceusdm().parse_markets(public_rows)}

    def load_markets(self, reload=False):
        if self.name.lower() != "binance" or self._config["runmode"] != RunMode.BACKTEST:
            raise ValueError("scenario market snapshot may only serve offline Binance backtests")
        self._api_async.set_markets(list(markets.values()))

    Exchange._load_async_markets = load_markets
    return markets


class RecoveryBacktest(Backtesting):
    """Keep native trade lifecycle and explicit point-in-time scenario boundaries."""

    def __init__(self, cfg, plans, date_range, markets, mode):
        self.plans = plans
        self.date_range = date_range
        self.mode = mode
        self.markets = markets
        self.entries = {}
        self.capacity = set()
        self.expired = set()
        super().__init__(cfg)

    def _load_bt_data_detail(self):
        super()._load_bt_data_detail()
        start, end = self.date_range
        for pair in self.pairlists.whitelist:
            symbol = self.markets[pair]["id"]
            funding = load(symbol, None, "fundingRate", sidecar=True)
            marks = load(symbol, "1h", "markPriceKlines")
            funding = funding.loc[funding.date.between(start, end, inclusive="left"), ["date", "funding_rate"]]
            funding = funding.rename(columns={"funding_rate": "open_fund"})
            funding["hour"] = funding.date.dt.floor("h")
            marks = marks[["date", "open"]].rename(columns={"date": "hour", "open": "open_mark"})
            exact = funding.merge(marks, on="hour", how="left", validate="many_to_one")
            if exact.open_mark.isna().any():
                raise ValueError(f"funding event mark hour unavailable in partition for {pair}")
            self.futures_data[pair] = Exchange._add_funding_columns(exact[["date", "open_mark", "open_fund"]])

    def _run_funding_fees(self, trade, current_time, force=False):
        fills = [o.order_filled_utc for o in trade.orders
                 if o.ft_order_side == trade.entry_side and o.filled and o.order_filled_utc]
        if not fills:
            return
        first = min(fills)
        frame = self.futures_data[trade.pair]
        clock = pd.Timestamp(current_time)
        start = pd.Timestamp(first)
        # Strict (entry, exit] assignment, using the source event milliseconds.
        dates = frame["_ff_date_ns"].to_numpy()
        cut = frame.iloc[dates.searchsorted(start.value, "right"):dates.searchsorted(clock.value, "right")]
        fee = self.exchange.calculate_funding_fees(cut, trade.amount, trade.is_short, first, current_time)
        # Native tracks the incremental amount since the last order snapshot.
        # With a single full entry and full exit there are no intervening resets.
        trade.set_funding_fees(fee)
        trade.set_custom_data("funding_events", [
            dict(at=row.date.isoformat(), rate=row.open_fund, mark_hour_open=row.open_mark)
            for row in cut.itertuples()
        ])

    def get_valid_entry_price_and_stake(self, pair, row, propose_rate, stake_amount,
                                        direction, current_time, entry_tag, trade, order_type,
                                        price_precision, precision_mode_price):
        plan = self.plans.get(entry_tag)
        if plan and order_type == "limit":
            # The pinned simulator clamps custom limits against the incoming
            # candle's high/low. Keep the frozen limit immutable when sizing.
            # Only the unmodified source row reaches the actual native fill check.
            limit = price_to_precision(plan["entry"], price_precision, precision_mode_price)
            values = list(row)
            values[HIGH_IDX] = max(values[HIGH_IDX], limit)
            values[LOW_IDX] = min(values[LOW_IDX], limit)
            row = tuple(values)
        return super().get_valid_entry_price_and_stake(
            pair, row, propose_rate, stake_amount, direction, current_time, entry_tag,
            trade, order_type, price_precision, precision_mode_price)

    def _enter_trade(self, pair, row, direction, *args, **kwargs):
        result = super()._enter_trade(pair, row, direction, *args, **kwargs)
        tag = row[ENTER_TAG_IDX]
        if tag in self.plans:
            self.entries[tag] = dict(at=row[DATE_IDX].isoformat(), trade=result)
        return result

    def _collate_rejected(self, pair, row):
        self.capacity.add(row[ENTER_TAG_IDX])
        return super()._collate_rejected(pair, row)

    def manage_open_orders(self, trade, current_time, row):
        pending = any(o.ft_order_side == trade.entry_side and o.ft_is_open for o in trade.orders)
        removed = super().manage_open_orders(trade, current_time, row)
        if pending and removed:
            self.expired.add(trade.enter_tag)
        return removed

    def _try_close_open_order(self, order, trade, current_date, row):
        if self.mode == "through" and order and order.ft_order_side == trade.entry_side:
            tick = float(self.markets[trade.pair]["precision"]["price"])
            crossed = (row[HIGH_IDX] >= order.ft_price + tick - tick * 1e-7 if trade.is_short
                       else row[LOW_IDX] <= order.ft_price - tick + tick * 1e-7)
            if not crossed:
                return False
        return super()._try_close_open_order(order, trade, current_date, row)


def run(partition, mode, playbook):
    validate_freeze(partition)
    adapter_sha = frame_hash(ROOT / ADAPTER)
    if partition != "development":
        runtime_lock = WORK / "runtime-freeze.json"
        if runtime_lock.exists() and json.loads(runtime_lock.read_text())["adapter_sha256"] != adapter_sha:
            raise ValueError("native adapter changed after the first validation attempt")
        if not runtime_lock.exists():
            write_json(runtime_lock, {"adapter_sha256": adapter_sha})
    spec = protocol()
    paths = WORK / partition
    plans = {p["decision_id"]: p for p in json.loads((paths / "plans.json").read_text())
             if playbook == "combined" or p["playbook"] == playbook}
    quality = json.loads((WORK / "quality.json").read_text())
    symbols = [s for s in spec["symbols"] if quality[s]["research_input_adequate"]
               and quality[s]["funding_inputs_present"]]
    markets = install_snapshot(symbols)
    dest = paths / f"native-{playbook}-{mode}"
    dest.mkdir(exist_ok=True)
    if (dest / "result.json").exists():
        raise ValueError("completed result is already preserved")
    plan_path = dest / "selected-plans.json"
    write_json(plan_path, list(plans.values()))
    cfg = json.loads((ROOT / "configs/research-vwap.json").read_text())
    cfg.update(
        strategy="SetupFirst5mV1", strategy_path=str(ROOT / "research/local_recovery"),
        user_data_dir=str(ROOT / "user_data"), timeframe="5m", fee=spec["fee_per_side"],
        dry_run=True, dry_run_wallet=spec["wallet_usdt"], max_open_trades=spec["positions_cap"],
        stake_amount=spec["notional_cap_usdt"], db_url="sqlite://", recovery_plans=str(plan_path),
        pairlists=[{"method": "StaticPairList"}], custom_price_max_distance_ratio=1.0,
        stoploss=-.025, minimal_roi={"0": 100.0}, position_adjustment_enable=False,
    )
    cfg["order_types"]["entry"] = "market" if mode == "market" else "limit"
    cfg["order_types"]["exit"] = "market"
    # Exchange validation expects a supported pricing configuration. Native
    # backtesting derives prices from the provided candles with no REST calls.
    cfg["entry_pricing"].update(use_order_book=True, price_side="other")
    cfg["exit_pricing"].update(use_order_book=True, price_side="other")
    cfg["exchange"] = dict(name="binance", pair_whitelist=list(markets), pair_blacklist=[],
                           ccxt_config={"has": {"fetchCurrencies": False}},
                           ccxt_async_config={"has": {"fetchCurrencies": False}})
    config_path = dest / "config.json"
    write_json(config_path, cfg)
    begin, end = spec["partitions_utc"][partition]
    args = ["backtesting", "--config", str(config_path), "--datadir", str(WORK / "binance"),
            "--timerange", begin.replace("-", "") + "-" + end.replace("-", ""),
            "--cache", "none", "--export", "trades", "--backtest-directory", str(dest)]
    parsed = setup_optimize_configuration(Arguments(args).get_parsed_arg(), RunMode.BACKTEST)
    date_range = [pd.Timestamp(d, tz="UTC") for d in (begin, end)]
    engine = RecoveryBacktest(parsed, plans, date_range, markets, mode)
    engine.start()
    orders, terminal = {}, {}
    closed = {t.enter_tag: t for t in LocalTrade.bt_trades if t.has_open_position or t.close_date}
    for tag, plan in plans.items():
        trade = engine.entries.get(tag, {}).get("trade")
        if trade is not None:
            orders[tag] = [dict(order_id=o.order_id, price=o.safe_price, amount=o.amount,
                                status=o.status, order_type=o.order_type, side=o.ft_order_side,
                                submitted_at=o.order_date_utc.isoformat(),
                                filled_at=o.order_filled_utc.isoformat() if o.order_filled_utc else None)
                           for o in trade.orders]
        if tag in closed:
            t = closed[tag]
            first_fill = min(o.order_filled_utc for o in t.orders if o.ft_order_side == t.entry_side and o.filled)
            terminal[tag] = dict(status="FILLED", exit_reason=t.exit_reason, entry_rate=t.open_rate,
                                 exit_rate=t.close_rate, profit=t.close_profit_abs, leverage=t.leverage,
                                 amount=t.amount, stake=t.stake_amount, funding=t.funding_fees,
                                 funding_events=t.get_custom_data("funding_events", []),
                                 filled_at=first_fill.isoformat(), closed_at=t.close_date_utc.isoformat())
        else:
            pair = pair_name(plan["symbol"])
            status = ("NO_SCENARIO_MARKET" if pair not in markets else
                      "EXPIRED_UNFILLED" if tag in engine.expired else
                      "CAPACITY_REJECT" if tag in engine.capacity else
                      "NATIVE_ENTRY_REJECT" if tag in engine.entries else
                      "PAIR_OCCUPIED_OR_NATIVE_SUPPRESSED")
            terminal[tag] = dict(status=status)
    native_archive = dest / json.loads((dest / ".last_result.json").read_text())["latest_backtest"]
    write_json(dest / "order-audit.json", orders)
    write_json(dest / "result.json", {
        "partition": partition, "playbook": playbook, "entry_mode": mode,
        "metadata_status": "EXECUTION_METADATA_UNQUALIFIED",
        "metadata": "Current public Binance filters and pinned Freqtrade dry-run leverage tiers",
        "archive": native_archive.name, "archive_sha256": frame_hash(native_archive),
        "engine": IMAGE, "adapter_sha256": adapter_sha, "args": args, "terminal": terminal,
    })
    print(partition, playbook, mode, "proposals", len(plans), "fills", len(closed), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("partition", choices=["freeze", *protocol()["partitions_utc"]])
    parser.add_argument("--mode", choices=["through", "touch", "market"], default="through")
    parser.add_argument("--playbook", choices=["combined", "continuation", "failed_auction"], default="combined")
    arguments = parser.parse_args()
    if arguments.partition == "freeze":
        freeze()
    else:
        run(arguments.partition, arguments.mode, arguments.playbook)
