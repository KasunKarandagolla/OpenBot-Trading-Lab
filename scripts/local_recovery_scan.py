"""Historical 15m suitability scan followed by independent completed 5m decisions."""

import argparse
import gzip
import hashlib
import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

from local_recovery_convert import aggregate, load
from local_recovery_data import ROOT, WORK, protocol, write_json

for directory in ("session3", "setup", "session4", "policy", "intelligence"):
    sys.path.insert(0, str(ROOT / "research" / directory))
from causal_structure import structure
from setup_map import four_hour_map

FIVE = pd.Timedelta(minutes=5)
FIFTEEN = 3 * FIVE
COST = .0038  # Round trip admission allowance from the setup control, never a cash charge.


def frame_hash(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def cheap_frame(hours, quarters):
    """Only completed bars contribute. Location references must precede formation."""
    daily = aggregate(hours, "1D").rename(columns={"high": "day_high", "low": "day_low"})
    daily["quote"] = hours.groupby(hours.date.dt.floor("1D")).quote_volume.sum().to_numpy()
    daily.loc[daily.components.ne(24), ["quote", "day_high", "day_low"]] = np.nan
    lookback = protocol()["gates"]["lookback_days"]
    daily["activity"] = daily.quote.rolling(lookback, min_periods=lookback).median()
    daily["daily_at"] = daily.date + pd.Timedelta(days=1)
    hourly = structure(hours, "1h")
    hourly["hourly_at"] = hourly.struct_known_at
    hourly["return4h"] = hourly.close.pct_change(4, fill_method=None)
    last_close = hourly.close.shift()
    hourly["atr_hour_frac"] = pd.concat(
        [hourly.high - hourly.low, (hourly.high - last_close).abs(),
         (hourly.low - last_close).abs()], axis=1).max(axis=1).rolling(14).mean() / hourly.close
    hcols = ["hourly_at", "return4h", "atr_hour_frac", "struct_direction", "swing_high",
             "swing_low", "swing_high_known_at", "swing_low_known_at"]
    h4 = four_hour_map(hours)
    q = quarters.copy()
    q["at"] = q.date + FIFTEEN
    q["previous_close"] = q.close.shift()
    q["prior_high"] = q.high.shift().rolling(6).max()
    q["prior_low"] = q.low.shift().rolling(6).min()
    q["atr15"] = pd.concat(
        [q.high - q.low, (q.high - q.previous_close).abs(),
         (q.low - q.previous_close).abs()], axis=1).max(axis=1).rolling(14).mean()
    for other, clock in [
        (daily[["day_high", "day_low", "activity", "daily_at"]], "daily_at"),
        (hourly[hcols], "hourly_at"),
        (h4[["known4h", "struct_direction_4h", "map4h_ready",
             "swing_high_4h", "swing_low_4h", "swing_high_known_at_4h",
             "swing_low_known_at_4h"]], "known4h"),
    ]:
        q = pd.merge_asof(q, other, left_on="date", right_on=clock)
    return q


def candidate_rows(frame, symbol, start, stop, btc, breadth, gates):
    eligible_data = (frame.hourly_at.notna() & frame.known4h.notna()
                     & frame.map4h_ready.eq(True) & frame.activity.notna()
                     & (frame.date - frame.hourly_at < pd.Timedelta(hours=1))
                     & (frame.date - frame.known4h < pd.Timedelta(hours=4)))
    activity_ok = (frame.activity.ge(gates["median_daily_quote_usdt"])
                   & frame.atr_hour_frac.ge(gates["minimum_1h_atr_fraction"]))
    frame["market_status"] = np.select(
        [~eligible_data, ~activity_ok], ["REJECT_DATA", "REJECT_LIQUIDITY"], default="RESEARCHABLE")
    result = []
    for sign, side, near, far, direction in [(1, "long", "low", "high", "UP"),
                                            (-1, "short", "high", "low", "DOWN")]:
        extreme = frame[near]
        swing = frame[f"swing_{near}"]
        day = frame[f"day_{near}"]
        aligned = frame.struct_direction.eq(direction) & frame.struct_direction_4h.eq(direction)
        continuation = (aligned & (extreme - swing).abs().le(.5 * frame.atr15)
                        & (sign * (frame.previous_close - swing)).gt(0)
                        & (sign * (frame.close - swing)).ge(-.25 * frame.atr15)
                        & (sign * (frame.previous_close - frame[f"prior_{near}"])).ge(frame.atr15))
        sweep = (sign * (day - extreme) / frame.atr15).between(.1, 1)
        against = "DOWN" if sign == 1 else "UP"
        failed_auction = (sweep & (sign * (frame.close - day)).gt(0)
                          & (sign * (frame.previous_close - day)).ge(0)
                          & ~(frame.struct_direction.eq(against)
                              & frame.struct_direction_4h.eq(against)))
        for book, conditions in (("continuation", continuation), ("failed_auction", failed_auction)):
            keep = conditions & frame["at"].between(start, stop, inclusive="left")
            for row in frame.loc[keep].to_dict("records"):
                trend = book == "continuation"
                at = row["at"]
                boundary = row[f"swing_{near}"] if trend else row[f"day_{near}"]
                stamp = row[f"swing_{near}_known_at"] if trend else row["daily_at"]
                mid = (row["day_high"] + row["day_low"]) / 2
                objectives = [(row[f"swing_{far}"], row[f"swing_{far}_known_at"], "1h_swing"),
                              (row[f"swing_{far}_4h"], row[f"swing_{far}_known_at_4h"], "4h_swing")]
                if not trend:
                    objectives.append((mid, row["daily_at"], "prior_utc_day_midpoint"))
                objectives = [dict(price=float(price), known_at=clock.isoformat(), source=source)
                              for price, clock, source in objectives
                              if np.isfinite(price) and pd.notna(clock) and clock <= row["date"]]
                assert stamp <= row["date"] < at
                btc_return = btc.get(at)
                ident = hashlib.sha256(f"{symbol}|{at}|{book}|{side}".encode()).hexdigest()[:24]
                result.append(dict(
                    opportunity_id=ident, symbol=symbol, armed_at=at.isoformat(), side=side,
                    playbook=book, sign=sign, status=row["market_status"], arm_close=row["close"],
                    boundary=float(boundary), boundary_known_at=stamp.isoformat(),
                    boundary_source=f"confirmed_1h_{near}" if trend else f"prior_utc_day_{near}",
                    extreme=row[near], atr15=row["atr15"], objective_candidates=objectives,
                    location_atr=abs(row["close"] - boundary) / row["atr15"],
                    activity=row["activity"], hour_direction=row["struct_direction"],
                    parent_direction=row["struct_direction_4h"], hour_at=row["hourly_at"].isoformat(),
                    parent_at=row["known4h"].isoformat(), atr_hour_frac=row["atr_hour_frac"],
                    relative_btc_4h=row["return4h"] - btc_return if btc_return is not None else None,
                    breadth_positive_4h=breadth.get(at), registered_extreme=row[near],
                    support=["completed_parent_map", "registered_location", "completed_15m_formation"],
                    unknowns=["historical_execution_metadata", "observed_spread", "signed_trade_profile"]))
    return result


def entry_features(base):
    f = base.copy()
    f["at"] = f.date + FIVE
    f["rvol"] = f.volume / f.volume.shift().rolling(48, min_periods=48).mean()
    f["prior_high"] = f.high.shift().rolling(3).max()
    f["prior_low"] = f.low.shift().rolling(3).min()
    return f.set_index("at", drop=False)


def examine(candidate, bars, gates, end):
    """The setup candle can never serve as its own confirmation."""
    at = pd.Timestamp(candidate["armed_at"])
    sign, boundary, atr = (candidate[k] for k in ("sign", "boundary", "atr15"))
    extreme = candidate["extreme"]
    events = [dict(at=at.isoformat(), state="ARMED", reason="WAIT_LATER_5M_CONFIRMATION")]
    candidate["events"] = events

    def event(state, reason, clock, **evidence):
        events.append(dict(at=clock.isoformat(), state=state, reason=reason, **evidence))
        candidate["status"] = state

    for step in range(1, 7):
        clock = at + step * FIVE
        if clock not in bars.index:
            event("INVALIDATED", "MISSING_5M_CANDLE", clock)
            return
        row = bars.loc[clock]
        adverse = row.low if sign == 1 else row.high
        if sign * (row.close - boundary) < -.25 * atr or sign * (adverse - extreme) < -.2 * atr:
            event("INVALIDATED", "REGISTERED_BOUNDARY_OR_EXTREME_FAILED", clock)
            return
        extreme = min(extreme, adverse) if sign == 1 else max(extreme, adverse)
        prior = row.prior_high if sign == 1 else row.prior_low
        trigger = (sign * (row.close - prior) > 0 and sign * (row.close - row.open) > 0
                   and 0 < sign * (row.close - boundary) <= 2.5 * atr
                   and np.isfinite(row.rvol) and row.rvol >= gates["minimum_rvol_5m"])
        if not trigger:
            event("WAITING", "NO_COMPLETED_5M_BREAK_WITH_PARTICIPATION", clock)
            continue
        event("TRIGGERED", "CLOSED_5M_LOCAL_BREAK", clock, previous_three_level=float(prior),
              rvol=float(row.rvol), trigger_close=float(row.close), trigger_bar_open=row.date.isoformat())
        entry = float(row.close)
        stop = float(extreme - sign * .2 * atr)
        risk = sign * (entry - stop) / entry
        objectives = [x for x in candidate["objective_candidates"] if sign * (x["price"] - entry) > 0]
        objective = min(objectives, key=lambda x: sign * (x["price"] - entry), default=None)
        if objective is None or not gates["minimum_stop_fraction"] <= risk <= gates["maximum_stop_fraction"]:
            event("REJECT_GEOMETRY", "NO_OBJECTIVE_OR_STOP_OUTSIDE_BOUNDS", clock)
            return
        target = objective["price"]
        rr = (sign * (target - entry) / entry - COST) / (risk + COST)
        if rr < gates["minimum_net_reward_risk"] or abs(target - entry) > 6 * atr:
            event("REJECT_GEOMETRY", "FIRST_OBJECTIVE_REWARD_OR_HORIZON", clock, net_rr=rr)
            return
        expiry = clock + FIVE
        hold = 480 if candidate["playbook"] == "continuation" else 240
        if clock + FIVE + pd.Timedelta(hours=15) >= end:
            event("NO_TRADE", "PARTITION_EXIT_PURGE", clock)
            return
        candidate["plan"] = dict(
            decision_id=candidate["opportunity_id"], symbol=candidate["symbol"],
            side=candidate["side"], playbook=candidate["playbook"], entry=entry, stop=stop,
            target=target, objective=objective, decision_at=clock.isoformat(),
            earliest_order_at=clock.isoformat(), expires_at=expiry.isoformat(),
            max_hold_minutes=hold, admission_cost_allowance=COST, net_rr=rr,
            boundary=boundary, atr15=atr, max_deviation=min(.0015, .25 * atr / entry),
            scenario_status="EXECUTION_METADATA_UNQUALIFIED",
        )
        event("ORDER_PROPOSED", "IMMUTABLE_5M_TRADE_CONTRACT", clock)
        return
    event("EXPIRED", "NO_TRIGGER_IN_SIX_COMPLETED_5M_BARS", at + 6 * FIVE)


def scan(partition):
    spec = protocol()
    start, end = [pd.Timestamp(t, tz="UTC") for t in spec["partitions_utc"][partition]]
    dest = WORK / partition
    if (dest / "scan-freeze.json").exists():
        raise ValueError("completed scan already frozen")
    quality = json.loads((WORK / "quality.json").read_text())
    frames = {symbol: cheap_frame(
        load(symbol, "1h", sidecar=True).rename(columns={"base_volume": "volume"}),
        load(symbol, "15m"),
    ) for symbol in spec["symbols"] if quality[symbol]["research_input_adequate"]}
    btc_frame = frames.get("BTCUSDT")
    btc = dict(zip(btc_frame["at"], btc_frame.return4h)) if btc_frame is not None else {}
    returns = pd.concat([f.set_index("at").return4h for f in frames.values()], axis=1)
    breadth = returns.gt(0).where(returns.notna()).mean(axis=1).to_dict()
    universe = pd.date_range(start, end, freq=FIFTEEN, inclusive="left")
    candidates = []
    gates = spec["gates"]
    market = []
    for symbol in spec["symbols"]:
        if symbol not in frames:
            market.append(pd.DataFrame(dict(at=universe, symbol=symbol, market_status="REJECT_DATA")))
            continue
        frame = frames[symbol]
        candidates.extend(candidate_rows(frame, symbol, start, end, btc, breadth, gates))
        market.append(frame.set_index("at").reindex(universe).rename_axis("at").reset_index()[
            ["at", "market_status", "activity", "atr_hour_frac", "return4h"]
        ].assign(symbol=symbol, market_status=lambda f: f.market_status.fillna("REJECT_DATA")))
    groups = {}
    for item in candidates:
        if item["status"] == "RESEARCHABLE":
            groups.setdefault(item["armed_at"], []).append(item)
    bases = {}
    for group in groups.values():
        group.sort(key=lambda c: (c["location_atr"], -c["activity"], c["symbol"], c["playbook"], c["side"]))
        for index, item in enumerate(group):
            if index >= gates["active_shortlist_per_cutoff"]:
                item["status"] = "REJECT_SHORTLIST"
                continue
            symbol = item["symbol"]
            if symbol not in bases:
                bases[symbol] = entry_features(load(symbol, "5m"))
            examine(item, bases[symbol], gates, end)
    clashes = Counter((x["symbol"], x["plan"]["decision_at"]) for x in candidates if "plan" in x)
    for item in candidates:
        plan = item.get("plan")
        if plan and clashes[(item["symbol"], plan["decision_at"])] > 1:
            item["status"] = "REJECT_CONTRADICTION"
            item["events"][-1].update(state="REJECT_CONTRADICTION", reason="COMPETING_SAME_SYMBOL_CLOCK")
            del item["plan"]
    dest.mkdir(parents=True, exist_ok=True)
    market_file = dest / "market-scan.csv.gz"
    pd.concat(market, ignore_index=True).to_csv(market_file, index=False)
    registry = dest / "opportunities.json.gz"
    with gzip.open(registry, "wt") as out:
        json.dump(candidates, out, allow_nan=False)
    plans = [x["plan"] for x in candidates if "plan" in x]
    plans_file = dest / "plans.json"
    write_json(plans_file, plans)
    receipt = {
        "partition": partition, "market_checks": sum(map(len, market)),
        "market_gate_counts": dict(Counter(status for table in market for status in table.market_status)),
        "opportunities": len(candidates), "opportunity_gate_counts": dict(Counter(x["status"] for x in candidates)),
        "proposed_by_playbook": dict(Counter(x["playbook"] for x in plans)),
        "sha256": {path.name: frame_hash(path) for path in (market_file, registry, plans_file)},
        "freeze_sha256": frame_hash(WORK / "research-freeze.json"),
    }
    write_json(dest / "scan-freeze.json", receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("partition", choices=protocol()["partitions_utc"])
    args = parser.parse_args()
    scan(args.partition)
