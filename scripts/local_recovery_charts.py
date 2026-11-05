"""Render and seal a read-only point-in-time chart packet for OpenBot."""

import argparse
import gzip
import json
import sys

import numpy as np
import pandas as pd

from local_recovery_convert import aggregate, load
from local_recovery_data import ROOT, WORK, write_json
from local_recovery_scan import FIVE, frame_hash

PANELS = {
    "1d": (1440, 60, 2), "4h": (240, 120, 20), "1h": (60, 144, 48),
    "15m": (15, 144, 48), "5m_overview": (5, 144, 48), "5m_zoom": (5, 72, 48),
}


def source_panels(symbol, cutoff):
    sidecars = {tf: load(symbol, tf, sidecar=True) for tf in ("1h", "15m", "5m")}
    cutoff_ms = cutoff.value // 1_000_000
    closed = {tf: f.loc[f.available_at_ms.le(cutoff_ms)].reset_index(drop=True)
              for tf, f in sidecars.items()}
    frames = {tf: f.rename(columns={"base_volume": "volume"}) for tf, f in closed.items()}
    for label, freq, count in (("1d", "1D", 24), ("4h", "4h", 4)):
        agg = aggregate(frames["1h"], freq)
        frames[label] = agg.loc[(agg.components == count) & (agg.date + pd.Timedelta(freq) <= cutoff)]
    bars, manifest, receipts = {}, {}, {}
    for label, (minutes, visible, warmup) in PANELS.items():
        step = pd.Timedelta(minutes=minutes)
        source_tf = "5m" if label.startswith("5m") else label
        frame = frames[source_tf].tail(visible + warmup).copy()
        display = frame.tail(visible).copy()
        bars[label] = display
        last_open = cutoff.floor(step) - step
        expected = pd.date_range(end=last_open, periods=visible + warmup, freq=step)
        missing = expected.difference(pd.DatetimeIndex(frame.date))
        underlying = closed["1h" if label in ("1d", "4h") else source_tf]
        if not frame.empty:
            underlying = underlying.loc[underlying.date.ge(frame.date.iloc[0])]
        used = underlying[["source_url", "source_sha256", "source_retrieved_at_utc"]].drop_duplicates()
        for row in used.to_dict("records"):
            receipts[row["source_url"]] = row
        manifest[label] = dict(
            visible=len(display), required_visible=visible, warmup=max(0, len(frame) - visible),
            required_warmup=warmup, missing_bars=len(missing), clock="UTC",
            first_open=display.date.iloc[0].isoformat() if len(display) else None,
            last_available_at=(display.date.iloc[-1] + step).isoformat() if len(display) else None,
            source_sha256=sorted(set(used.source_sha256)), interval_minutes=minutes,
            price_units="USDT per published Binance symbol unit",
        )
    base = frames["5m"].copy()
    base["rvol"] = base.volume / base.volume.shift().rolling(48, min_periods=48).mean()
    base["taker_buy_share"] = base.taker_buy_quote_volume / base.quote_volume.replace(0, np.nan)
    return bars, manifest, list(receipts.values()), base.tail(72)


def draw_board(path, symbol, cutoff, boards, levels, case, participation=None):
    sys.path.append(str(WORK / "mpl"))
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from master_charts import candles

    figsize = (16, 10) if participation is None else (16, 11)
    fig, axes = plt.subplots(len(boards) + (participation is not None), 1,
                             figsize=figsize, layout="constrained")
    for ax, (label, frame) in zip(axes, boards.items()):
        minutes = PANELS[label][0]
        candles(ax, frame, minutes)
        ax.set_ylabel("Price (USDT)")
        ax.set_title(f"{label.replace('_', ' ')}  |  {len(frame)} completed candles", loc="left")
        if frame.empty:
            continue
        span = frame.high.max() - frame.low.min()
        xmin = frame.date.iloc[0] - pd.Timedelta(minutes=minutes / 2)
        is_entry_zoom = label == "5m_zoom"
        data_end = frame.date.iloc[-1] + pd.Timedelta(minutes=minutes)
        xmax = cutoff + 5 * FIVE if is_entry_zoom else data_end
        ax.set_xlim(xmin, xmax)
        if is_entry_zoom:
            ax.axvspan(cutoff, xmax, color="#eef3f9")
            ax.axvline(cutoff, color="#4b5e74", lw=1, label="Decision cutoff")
            if "armed_at" in case:
                ax.axvline(pd.Timestamp(case["armed_at"]), color="#8864a7", lw=1,
                           linestyle=":", label="15m setup armed")
        for level in levels:
            price = level["price"]
            known = pd.Timestamp(level["known_at"])
            prospective = level.get("proposed", False)
            if prospective and not is_entry_zoom:
                continue
            if known >= xmax or (not prospective and
                                 not frame.low.min() - .05 * span <= price <= frame.high.max() + .05 * span):
                continue
            ax.hlines(price, max(known, xmin), xmax, linestyles="dashed",
                      colors=level["color"], linewidth=1.3, label=level["label"])
        if ax.get_legend_handles_labels()[0]:
            ax.legend(loc="best", fontsize=9, ncols=3, framealpha=.96)
    if participation is not None:
        ax = axes[-1]
        dates = participation.date
        width = 4 / 1440
        quote = participation.quote_volume
        buy = participation.taker_buy_quote_volume
        ax.bar(dates, buy / 1e6, width=width, color="#178575", label="Taker buy")
        ax.bar(dates, (quote - buy) / 1e6, bottom=buy / 1e6, width=width,
               color="#bd555a", label="Taker sell")
        ax.set_ylabel("Quote volume (M USDT)")
        ax.set_title("Published 5m kline participation | prior 48 bars for RVOL", loc="left")
        ax.set_xlim(dates.iloc[0] - FIVE / 2, cutoff + 5 * FIVE)
        ax.axvspan(cutoff, cutoff + 5 * FIVE, color="#eef3f9")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H:%M", tz=dates.dt.tz))
        ax.legend(loc="upper left", fontsize=9)
        twin = ax.twinx()
        twin.plot(dates, participation.rvol, color="#233b81", linewidth=1.2, label="RVOL")
        twin.set_ylabel("RVOL (×)")
        twin.legend(loc="upper right", fontsize=9)
    state = case["status"].replace("_", " ").title()
    book = case.get("playbook", "").replace("_", " ").title()
    fig.suptitle(f"{symbol}  •  {book}  •  {state}\n"
                 f"Binance Vision USD-M  •  Closed data as of {cutoff:%Y-%m-%d %H:%M} UTC",
                 fontsize=17, fontweight="bold")
    fig.savefig(path, dpi=140, facecolor="white")
    plt.close(fig)


def packet(destination, case, cutoff):
    symbol = case["symbol"]
    panels, counts, sources, participation = source_panels(symbol, cutoff)
    adequate = all(r["missing_bars"] == 0 for r in counts.values())
    status = "ADEQUATE" if adequate else "INPUT_INSUFFICIENT"
    plan = case.get("plan")
    levels = []
    if "boundary" in case:
        levels.append(dict(price=case["boundary"], known_at=case["boundary_known_at"],
                           label=case["boundary_source"].replace("_", " "), color="#5540a0"))
    if plan:
        for k, label, color in (("stop", "Proposed stop", "#b23745"),
                                ("entry", "Proposed limit", "#344985"),
                                ("target", "Proposed objective", "#218060")):
            levels.append(dict(price=plan[k], known_at=plan["decision_at"], label=label,
                               color=color, proposed=True))
    assert all(pd.Timestamp(level["known_at"]) <= cutoff for level in levels)
    assert all(p["last_available_at"] is None or pd.Timestamp(p["last_available_at"]) <= cutoff
               for p in counts.values())
    destination.mkdir(parents=True)
    write_json(destination / "source-receipt.json", sources)
    images = []
    if adequate:
        for name, labels in [("context", ("1d", "4h", "1h", "15m")),
                             ("entry", ("5m_overview", "5m_zoom"))]:
            path = destination / (name + ".png")
            draw_board(path, symbol, cutoff, {label: panels[label] for label in labels}, levels, case,
                       participation=participation if name == "entry" else None)
            images.append(dict(file=path.name, sha256=frame_hash(path), image_role="analysis_input"))
    last = participation.iloc[-1] if len(participation) else None
    details = None if last is None else {
        "bar_available_at": (last.date + FIVE).isoformat(), "quote_usdt": float(last.quote_volume),
        "trade_count": int(last.trade_count),
        "taker_buy_quote_share": float(last.taker_buy_share) if np.isfinite(last.taker_buy_share) else None,
        "rvol_prior_48": float(last.rvol) if np.isfinite(last.rvol) else None,
    }
    card = dict(
        schema_version="openbot.historical.chart.v1", decision_id=case["opportunity_id"],
        symbol=symbol, as_of=cutoff.isoformat(), hidden_forward_cutoff=cutoff.isoformat(),
        source="Binance Vision USD-M", terms="CC BY-NC-SA 4.0 / Binance Vision Dataset Terms",
        input_status=status, panels=counts, images=images, levels=levels,
        participation=details, observations=[e for e in case.get("events", []) if pd.Timestamp(e["at"]) <= cutoff],
        plan=plan, playbook=case.get("playbook"), side=case.get("side"), state=case["status"],
        context={k: case.get(k) for k in ("hour_direction", "parent_direction", "hour_at", "parent_at",
                                        "atr_hour_frac", "relative_btc_4h", "breadth_positive_4h")},
        uncertainties=["EXECUTION_METADATA_UNQUALIFIED", "EXACT_SETTLEMENT_MARK_UNAVAILABLE",
                       "SIGNED_TRADE_PROFILE_UNAVAILABLE", "HISTORICAL_SPREAD_UNAVAILABLE"],
        source_receipt={"file": "source-receipt.json", "sha256": frame_hash(destination / "source-receipt.json")},
        render_sha256=frame_hash(ROOT / "scripts/local_recovery_charts.py"),
        candlestick_renderer_sha256=frame_hash(ROOT / "scripts/master_charts.py"),
    )
    write_json(destination / "evidence-card.json", card)
    return dict(id=card["decision_id"], status=status, as_of=card["as_of"],
                playbook=card["playbook"], state=card["state"])


def main(partition):
    paths = WORK / partition
    with gzip.open(paths / "opportunities.json.gz", "rt") as source:
        cases = sorted(json.load(source), key=lambda c: (c["armed_at"], c["opportunity_id"]))
    directory = paths / "analysis-packets"
    selected = []
    for playbook in ("continuation", "failed_auction"):
        eligible = [c for c in cases if c["playbook"] == playbook]
        chosen = next((c for c in eligible if "plan" in c), None)
        chosen = chosen or next((c for c in eligible if c.get("events")), None)
        if chosen:
            selected.append(chosen)
    invalid = next((c for c in cases if c["status"] == "INVALIDATED"), None)
    if invalid:
        selected.append(invalid)
    index = []
    for case in selected:
        cutoff = pd.Timestamp(case["events"][-1]["at"])
        index.append(packet(directory / case["opportunity_id"], case, cutoff))
    control = dict(symbol="BTCUSDT", opportunity_id="input-insufficient-control",
                   status="NO_TRADE", playbook=None)
    index.append(packet(directory / control["opportunity_id"], control,
                        pd.Timestamp("2026-05-02", tz="UTC")))
    write_json(directory / "index.json", index)
    print(json.dumps(index), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("partition")
    main(parser.parse_args().partition)
