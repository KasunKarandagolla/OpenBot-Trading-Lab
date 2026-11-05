"""Verify monthly source clocks and prepare local native/participation inputs."""

import io
import zipfile

import numpy as np
import pandas as pd

from binance_research_data import (
    FUNDING_COLUMNS, INTERVAL_MS, KLINE_COLUMNS, DataError,
    convert_funding_frame, convert_kline_frame, verify_cached_archive,
)
from local_recovery_data import ROOT, STREAMS, WORK, monthly_url, protocol, write_json
import json

FUTURES = WORK / "binance/futures"
SIDECARS = WORK / "binance/research"
KINDS = {"klines": "futures", "markPriceKlines": "mark", "fundingRate": "funding_rate"}


def file_name(symbol, kind, timeframe):
    return f"{symbol.removesuffix('USDT')}_USDT_USDT-{timeframe or '1h'}-{KINDS[kind]}"


def load(symbol, timeframe, kind="klines", sidecar=False):
    directory = SIDECARS if sidecar else FUTURES
    return pd.read_feather(directory / (file_name(symbol, kind, timeframe) + ".feather"))


def convert_sources(sources, symbol, kind, timeframe):
    frames, sidecars = [], []
    for source in sources:
        month = source["month"]
        if source["url"] != monthly_url(kind, symbol, timeframe, month):
            raise DataError("archive identity does not match registered schedule")
        path = ROOT / source["cache_path"]
        verify_cached_archive(path, source["official_sha256"])
        with zipfile.ZipFile(path) as archive:
            members = [m for m in archive.infolist() if not m.is_dir()]
            if (len(members) != 1 or members[0].filename != path.stem + ".csv"
                    or members[0].file_size > 16 * 1024**2):
                raise DataError(f"unexpected monthly ZIP member in {path.name}")
            body = archive.read(members[0])
        schema = FUNDING_COLUMNS if kind == "fundingRate" else KLINE_COLUMNS
        has_header = body.startswith(schema[0].encode() + b",")
        frame = pd.read_csv(io.BytesIO(body), header=0 if has_header else None, names=schema)
        if kind == "fundingRate":
            standard, sidecar = convert_funding_frame(frame, source)
        elif kind == "markPriceKlines":
            # Binance may omit mark hours. Validate each contiguous segment
            # with the existing converter and keep missing hours explicit.
            boundaries = frame.open_time.diff().ne(INTERVAL_MS[timeframe]).cumsum()
            converted = [convert_kline_frame(chunk, source, kind=kind, timeframe=timeframe)
                         for _, chunk in frame.groupby(boundaries, sort=False)]
            standard = pd.concat([x[0] for x in converted], ignore_index=True)
            sidecar = pd.concat([x[1] for x in converted], ignore_index=True)
        else:
            standard, sidecar = convert_kline_frame(frame, source, kind=kind, timeframe=timeframe)
        start = pd.Timestamp(f"{month}-01", tz="UTC")
        end = start + pd.offsets.MonthBegin()
        if standard.empty or not standard.date.between(start, end, inclusive="left").all():
            raise DataError(f"rows outside registered UTC source month: {path.name}")
        if kind == "klines":
            step = pd.Timedelta(milliseconds=INTERVAL_MS[timeframe])
            if not pd.DatetimeIndex(standard.date).equals(pd.date_range(start, end, freq=step, inclusive="left")):
                raise DataError(f"incomplete monthly candle grid: {path.name}")
        frames.append(standard)
        sidecars.append(sidecar)
    ohlcv = pd.concat(frames, ignore_index=True)
    research = pd.concat(sidecars, ignore_index=True)
    if ohlcv.date.duplicated().any() or not ohlcv.date.is_monotonic_increasing:
        raise DataError(f"duplicate or unordered records across {symbol} {kind} month boundaries")
    return ohlcv, research


def aggregate(frame, interval):
    columns = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    grouped = frame.groupby(frame.date.dt.floor(interval))
    out = grouped.agg(columns)
    out["components"] = grouped.size()
    return out.rename_axis("date").reset_index()


def compare(fine, coarse, interval, components):
    grouped = aggregate(fine, interval)
    checks = grouped.merge(coarse, on="date", suffixes=("_derived", "_source"), how="outer",
                           validate="one_to_one", indicator=True)
    mismatch = {
        column: int((~np.isclose(checks[f"{column}_derived"], checks[f"{column}_source"],
                                  rtol=1e-9, atol=1e-10)).sum())
        for column in ("open", "high", "low", "close", "volume")
    }
    return dict(compared=len(checks), incomplete=int(checks.components.ne(components).sum()),
                missing_grid=int(checks["_merge"].ne("both").sum()), mismatches=mismatch)


def main():
    spec = protocol()
    source_receipt = json.loads((WORK / "sources.json").read_text())
    sources = source_receipt["sources"]
    quality = {}
    FUTURES.mkdir(parents=True, exist_ok=True)
    SIDECARS.mkdir(parents=True, exist_ok=True)
    for symbol in spec["symbols"]:
        record = quality[symbol] = {"streams": {}}
        frames = {}
        for kind, tf in STREAMS:
            selected = [s for s in sources if (s["symbol"], s["kind"], s["timeframe"]) == (symbol, kind, tf)]
            selected.sort(key=lambda row: row["month"])
            key = f"{kind}:{tf}"
            try:
                if [row["month"] for row in selected] != spec["source_months"]:
                    raise DataError("missing registered monthly sources")
                standard, research = convert_sources(selected, symbol, kind, tf)
            except (DataError, ValueError, OSError) as exc:
                record["streams"][key] = {"error": str(exc)}
                continue
            filename = file_name(symbol, kind, tf) + ".feather"
            native = standard
            if kind == "fundingRate":
                # IDataHandler expects OHLCV even for funding. Keep exact events
                # separately, then restore them after native loader normalization.
                native = standard.assign(open=standard.funding_rate, high=standard.funding_rate,
                                         low=standard.funding_rate, close=standard.funding_rate, volume=0)
                native = native[["date", "open", "high", "low", "close", "volume"]]
            native.to_feather(FUTURES / filename)
            research.to_feather(SIDECARS / filename)
            frames[(kind, tf)] = standard
            record["streams"][key] = dict(rows=len(standard), first=standard.date.iloc[0].isoformat(),
                                          last=standard.date.iloc[-1].isoformat())
        record["research_input_adequate"] = all(("klines", tf) in frames for tf in ("1h", "15m", "5m"))
        record["funding_inputs_present"] = all(k in frames for k in STREAMS[3:])
        if record["funding_inputs_present"]:
            marks = frames[("markPriceKlines", "1h")]
            funding = frames[("fundingRate", None)]
            mark_hours = pd.DatetimeIndex(marks.date)
            missing = funding.loc[~funding.date.dt.floor("h").isin(mark_hours), "date"]
            record["funding_events_missing_same_hour_mark"] = [x.isoformat() for x in missing]
            span = pd.date_range(marks.date.min(), marks.date.max(), freq="1h")
            record["mark_hour_gaps"] = len(span.difference(mark_hours))
        if record["research_input_adequate"]:
            record["cross_interval"] = {
                "5m_to_15m": compare(frames[("klines", "5m")], frames[("klines", "15m")], "15min", 3),
                "15m_to_1h": compare(frames[("klines", "15m")], frames[("klines", "1h")], "1h", 4),
            }
        print(symbol, record["research_input_adequate"], record["funding_inputs_present"], flush=True)
    write_json(WORK / "quality.json", quality)
    if not any(r["research_input_adequate"] for r in quality.values()):
        raise SystemExit("no adequate source streams")


if __name__ == "__main__":
    main()
