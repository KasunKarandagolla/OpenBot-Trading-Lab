"""Reconcile native scenario results to all original opportunities and cost stresses."""

import gzip
import json
from collections import Counter

import numpy as np
import pandas as pd

from local_recovery_convert import load
from local_recovery_data import WORK, protocol, write_json
from local_recovery_scan import FIVE, entry_features, examine, frame_hash


def candidate_path(plan, bars, include_order_bar):
    """Descriptive post-cutoff OHLC only; an ambiguous bar stays ambiguous."""
    sign = 1 if plan["side"] == "long" else -1
    decision = pd.Timestamp(plan["decision_at"])
    after = decision if include_order_bar else pd.Timestamp(plan["expires_at"])
    end = decision + pd.Timedelta(minutes=plan["max_hold_minutes"])
    path = bars.loc[bars.date.between(after, end, inclusive="left")]
    for row in path.itertuples():
        upside = row.high if sign == 1 else row.low
        downside = row.low if sign == 1 else row.high
        target = sign * (upside - plan["target"]) >= 0
        stop = sign * (downside - plan["stop"]) <= 0
        if target or stop:
            return "AMBIGUOUS_SAME_BAR" if target and stop else "TARGET_FIRST" if target else "STOP_FIRST"
    return "NEITHER_REACHED"


def stats(trades, population, spec):
    trades.sort(key=lambda t: t["closed_at"])
    profits = [x["profit"] for x in trades]
    wallet = np.cumsum([0, *profits])
    losses = -sum(p for p in profits if p < 0)
    winners = sorted((p for p in profits if p > 0), reverse=True)
    r = [x["profit"] / (abs(x["entry_rate"] - x["plan"]["stop"]) * x["amount"]) for x in trades]
    streak = worst = 0
    for value in profits:
        streak = streak + 1 if value < 0 else 0
        worst = max(streak, worst)
    costs = {"native": sum(profits)}
    for bp in spec["additional_bps_per_side"]:
        costs[f"extra_{bp}bp_per_side"] = sum(
            x["profit"] - bp / 10_000 * x["amount"] * (x["entry_rate"] + x["exit_rate"]) for x in trades)
    return dict(
        fills=len(trades), wins=len(winners), losses=sum(p < 0 for p in profits),
        profit_factor=sum(winners) / losses if losses else None,
        average_win_usdt=sum(winners) / len(winners) if winners else None,
        average_loss_usdt=-losses / sum(p < 0 for p in profits) if losses else None,
        winner_top_third_share=sum(winners[:(len(winners) + 2) // 3]) / sum(winners) if winners else None,
        max_closed_trade_drawdown_usdt=float((np.maximum.accumulate(wallet) - wallet).max()),
        worst_losing_streak=worst, filled_r=r, pnl_usdt=costs,
        pnl_per_registered_opportunity_usdt={k: v / population if population else None for k, v in costs.items()},
        exit_reasons=dict(Counter(x["exit_reason"] for x in trades)),
        funding_usdt=sum(x["funding"] for x in trades),
    )


def audit_trade(trade, orders, mode, snapshot):
    p = trade["plan"]
    fills = pd.Timestamp(trade["filled_at"])
    close = pd.Timestamp(trade["closed_at"])
    decision = pd.Timestamp(p["decision_at"])
    tick = float(next(f["tickSize"] for f in snapshot["filters"] if f["filterType"] == "PRICE_FILTER"))
    step = float(next(f["stepSize"] for f in snapshot["filters"] if f["filterType"] == "LOT_SIZE"))
    minimum = float(next(f["notional"] for f in snapshot["filters"] if f["filterType"] == "MIN_NOTIONAL"))
    ordered = trade["entry_rate"]
    fees = trade["amount"] * (ordered + trade["exit_rate"]) * protocol()["fee_per_side"]
    sign = 1 if p["side"] == "long" else -1
    reconstructed = sign * (trade["exit_rate"] - ordered) * trade["amount"] - fees + trade["funding"]
    clocks = [pd.Timestamp(f["at"]) for f in trade["funding_events"]]
    modeled_funding = sum(-sign * f["rate"] * f["mark_hour_open"] * trade["amount"]
                          for f in trade["funding_events"])
    held = close - fills
    return dict(
        causal_order_clock=bool(pd.Timestamp(orders[0]["submitted_at"]) == decision == fills
                                and fills < pd.Timestamp(p["expires_at"])),
        position_limits=bool(trade["leverage"] == 1 and trade["stake"] <= 25 + 1e-8
                             and len(orders) == 2 and pd.Timedelta(0) <= held
                             <= pd.Timedelta(minutes=min(900, p["max_hold_minutes"]))),
        scenario_lot=bool(ordered * trade["amount"] >= minimum
                          and np.isclose(trade["amount"] / step, round(trade["amount"] / step), atol=1e-7)),
        exit_level=bool(
            abs(trade["exit_rate"] - p["target"]) <= tick + 1e-10 if trade["exit_reason"] == "roi"
            else (abs(trade["exit_rate"] - p["stop"]) <= tick + 1e-10
                  or sign * (trade["exit_rate"] - p["stop"]) < 0)
            if trade["exit_reason"] == "stop_loss" else True),
        no_forced_partition_exit=trade["exit_reason"] != "force_exit",
        scenario_pnl=bool(abs(reconstructed - trade["profit"]) < 2e-8),
        source_funding=bool(len(clocks) == len(set(clocks)) and all(fills < c <= close for c in clocks)
                            and abs(modeled_funding - trade["funding"]) < 1e-9),
        immutable_limit=bool(mode == "market" or abs(p["entry"] - ordered) <= tick + 1e-10),
    )


def report_partition(partition, spec, snapshot):
    root = WORK / partition
    scan = json.loads((root / "scan-freeze.json").read_text())
    with gzip.open(root / "opportunities.json.gz", "rt") as f:
        registry = json.load(f)
    datasets = {}

    def bars(symbol):
        if symbol not in datasets:
            datasets[symbol] = entry_features(load(symbol, "5m"))
        return datasets[symbol]

    report = dict(scan=scan, variants={})
    for dest in sorted(root.glob("native-*")):
        result_path = dest / "result.json"
        if not result_path.is_file():
            continue
        native = json.loads(result_path.read_text())
        if frame_hash(dest / native["archive"]) != native["archive_sha256"]:
            raise ValueError("native archive content changed")
        terminal = native["terminal"]
        audits = json.loads((dest / "order-audit.json").read_text())
        population = [x for x in registry if native["playbook"] in ("combined", x["playbook"])]
        trades, attribution, misses, trade_audit = [], [], {}, {}
        shortlist = Counter()
        end = pd.Timestamp(spec["partitions_utc"][partition][1], tz="UTC")
        for opp in population:
            tag = opp["opportunity_id"]
            native_row = terminal.get(tag)
            plan = opp.get("plan")
            record = dict(opportunity_id=tag, playbook=opp["playbook"], symbol=opp["symbol"],
                          armed_at=opp["armed_at"], gate=opp["status"], native=native_row,
                          pnl_usdt=native_row["profit"] if native_row and native_row["status"] == "FILLED" else 0)
            attribution.append(record)
            if native_row and native_row["status"] == "FILLED":
                trades.append(dict(**native_row, plan=plan))
                trade_audit[tag] = audit_trade(trades[-1], audits[tag], native["entry_mode"], snapshot[plan["symbol"]])
            elif native_row:
                misses[tag] = dict(native_status=native_row["status"],
                                   descriptive_path=candidate_path(plan, bars(plan["symbol"]), False))
            if opp["status"] == "REJECT_SHORTLIST" and native["playbook"] == "combined":
                counterfactual = dict(opp)
                examine(counterfactual, bars(opp["symbol"]), spec["gates"], end)
                hypothetical = counterfactual.get("plan")
                if hypothetical:
                    shortlist[candidate_path(hypothetical, bars(opp["symbol"]), True)] += 1
                else:
                    shortlist[counterfactual["status"]] += 1
        # Close-to-close wallet drawdown is distinct from native intrabar/mark exposure.
        value = stats(trades, len(population), spec)
        labels = {"playbook": lambda t: t["plan"]["playbook"], "symbol": lambda t: t["plan"]["symbol"],
                  "week_utc": lambda t: str(pd.Timestamp(t["closed_at"]).isocalendar()[:2])}
        pnl_breakdown = {}
        for field, label in labels.items():
            totals = Counter()
            for trade in trades:
                totals[label(trade)] += trade["profit"]
            pnl_breakdown[field] = dict(totals)
        failed = {tag: [k for k, v in tests.items() if not v]
                  for tag, tests in trade_audit.items() if not all(tests.values())}
        value.update(proposals=len(terminal), native_terminal_counts=dict(Counter(t["status"] for t in terminal.values())),
                     registered_opportunities=len(population), post_expiry_nonfill_paths=misses,
                     shortlist_counterfactual_descriptive=dict(shortlist), trade_audit=trade_audit,
                     trade_audit_failures=failed, pnl_breakdown=pnl_breakdown)
        report["variants"][dest.name.removeprefix("native-")] = value
        with gzip.open(dest / "all-opportunity-attribution.json.gz", "wt") as f:
            json.dump(attribution, f, allow_nan=False)
    return report


def main():
    spec = protocol()
    snapshot = {r["symbol"]: r for r in json.loads((WORK / "current-exchangeinfo.json").read_text())["symbols"]}
    report = dict(
        economic_status="NO_EDGE_ESTABLISHED",
        execution_status="UNQUALIFIED_SCENARIO",
        cost_model="Actual source event times with hourly mark-open proxies, modeled 5bp/side fees, "
                   "additional matched-fill friction at +5/10/20bp per side, admission allowance excluded from cash",
        caveat="Candle range and trade-through do not reconstruct execution queue or intrabar chronology.",
        partitions={p: report_partition(p, spec, snapshot) for p in spec["partitions_utc"]
                    if (WORK / p / "scan-freeze.json").exists()},
    )
    write_json(WORK / "cost-and-selection-report.json", report)
    for partition, data in report["partitions"].items():
        for variant, item in data["variants"].items():
            print(partition, variant, item["registered_opportunities"], item["proposals"],
                  item["fills"], item["pnl_usdt"], "audit_failures", item["trade_audit_failures"])


if __name__ == "__main__":
    main()
