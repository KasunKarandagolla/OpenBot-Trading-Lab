"""Bounded, checksum-verified Binance Vision USD-M research data helpers.

This module reads public historical archives only. It never calls order or
account endpoints. Execution metadata is deliberately kept separate from the
historical price and participation data.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Iterator
import xml.etree.ElementTree as ET


ARCHIVE_BASE = "https://data.binance.vision/data/futures/um"
FUTURES_API_BASE = "https://fapi.binance.com/fapi/v1"
INTERVAL_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000,
               "1h": 3_600_000, "4h": 14_400_000}
KLINE_COLUMNS = ("open_time", "open", "high", "low", "close", "volume",
                 "close_time", "quote_volume", "count", "taker_buy_volume",
                 "taker_buy_quote_volume", "ignore")
AGG_COLUMNS = ("agg_trade_id", "price", "quantity", "first_trade_id",
               "last_trade_id", "transact_time", "is_buyer_maker")
FUNDING_COLUMNS = ("calc_time", "funding_interval_hours", "last_funding_rate")


class DataError(RuntimeError):
    """An integrity, schema, or availability failure that must stop ingestion."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_cache_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[1] / path


def _request(url: str, *, timeout: float = 20, max_bytes: int = 32 * 1024 * 1024,
             request_headers: dict | None = None) -> tuple[bytes, int, str, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "OpenBot-research-data/1.0", **(request_headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                raise DataError(f"HTTP {response.status} from {url}")
            out = bytearray()
            while True:
                part = response.read(min(1024 * 1024, max_bytes + 1 - len(out)))
                if not part:
                    break
                out.extend(part)
                if len(out) > max_bytes:
                    raise DataError(f"response exceeded {max_bytes} byte cap: {url}")
            return bytes(out), response.status, response.geturl(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read(512).decode("utf-8", "replace")
        except Exception:
            detail = ""
        raise DataError(f"HTTP {exc.code} from {url}: {detail[:300]}") from exc
    except (TimeoutError, OSError) as exc:
        raise DataError(f"request failed for {url}: {type(exc).__name__}: {exc}") from exc


def archive_url(kind: str, symbol: str, *, date: str | None = None,
                timeframe: str | None = None, month: str | None = None) -> str:
    if not re.fullmatch(r"[A-Z0-9_]{2,32}", symbol):
        raise ValueError(f"invalid Binance symbol: {symbol!r}")
    if kind in ("klines", "markPriceKlines"):
        if timeframe not in INTERVAL_MS or timeframe == "4h" or not date:
            raise ValueError("klines require a supported source timeframe and UTC date")
        dt.date.fromisoformat(date)
        name = f"{symbol}-{timeframe}-{date}.zip"
        return f"{ARCHIVE_BASE}/daily/{kind}/{symbol}/{timeframe}/{name}"
    if kind == "aggTrades":
        if not date:
            raise ValueError("aggTrades require a UTC date")
        dt.date.fromisoformat(date)
        name = f"{symbol}-aggTrades-{date}.zip"
        return f"{ARCHIVE_BASE}/daily/aggTrades/{symbol}/{name}"
    if kind == "fundingRate":
        if not month or not re.fullmatch(r"\d{4}-\d{2}", month):
            raise ValueError("fundingRate archives require a UTC month (YYYY-MM)")
        name = f"{symbol}-fundingRate-{month}.zip"
        return f"{ARCHIVE_BASE}/monthly/fundingRate/{symbol}/{name}"
    raise ValueError(f"unsupported dataset: {kind}")


def fetch_verified(url: str, cache_dir: Path, *, max_archive_bytes: int = 20 * 1024 * 1024,
                  timeout: float = 25) -> dict:
    """Download or reuse one archive only after checking Binance's SHA256 file.

    Existing content is never overwritten. If the official checksum changes,
    the caller must select a new cache path and preserve the old receipt.
    """
    cache_dir = Path(cache_dir)
    filename = url.rsplit("/", 1)[-1]
    checksum_url = url + ".CHECKSUM"
    checksum_bytes, checksum_status, checksum_final, _ = _request(
        checksum_url, timeout=timeout, max_bytes=2048)
    parts = checksum_bytes.decode("ascii", "strict").split()
    if len(parts) < 2 or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]) or parts[1] != filename:
        raise DataError(f"unexpected official checksum schema at {checksum_url}")
    expected = parts[0].lower()
    target = cache_dir / filename
    receipt_path = target.with_suffix(target.suffix + ".source.json")
    if target.exists():
        body = target.read_bytes()
        actual = sha256(body)
        if actual != expected:
            raise DataError(f"cached bytes differ from current official checksum; preserved: {target}")
        cached = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        return {**cached, "url": url, "checksum_url": checksum_url,
                "official_sha256": expected, "sha256": actual,
                "bytes": len(body), "cache_hit": True, "cache_path": str(target)}
    body, status, final_url, headers = _request(url, timeout=timeout,
                                                max_bytes=max_archive_bytes)
    actual = sha256(body)
    if actual != expected:
        raise DataError(f"official checksum mismatch for {url}: expected {expected}, got {actual}")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise DataError(f"cache path was concurrently created; verify before reuse: {target}")
    with os.fdopen(fd, "wb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    receipt = {
        "url": url, "final_url": final_url, "checksum_url": checksum_url,
        "checksum_final_url": checksum_final, "http_status": status,
        "checksum_http_status": checksum_status, "retrieved_at_utc": utc_now(),
        "content_length_header": headers.get("Content-Length"),
        "bytes": len(body), "sha256": actual, "official_sha256": expected,
        "cache_hit": False, "cache_path": str(target),
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def verify_cached_archive(path: Path, expected_sha256: str) -> None:
    actual = sha256(Path(path).read_bytes())
    if actual.lower() != expected_sha256.lower():
        raise DataError(f"cached archive checksum mismatch: {path}")


def _zip_csv_bytes(source: Path | bytes) -> bytes:
    try:
        if isinstance(source, bytes):
            archive = zipfile.ZipFile(io.BytesIO(source))
        else:
            archive = zipfile.ZipFile(source)
        with archive:
            members = [n for n in archive.namelist() if not n.endswith("/")]
            if len(members) != 1 or not members[0].lower().endswith(".csv"):
                raise DataError("expected a ZIP containing exactly one CSV member")
            info = archive.getinfo(members[0])
            if info.file_size > 128 * 1024 * 1024:
                raise DataError("uncompressed CSV exceeds 128 MiB parser cap")
            return archive.read(members[0])
    except zipfile.BadZipFile as exc:
        raise DataError("invalid Binance ZIP archive") from exc


def _csv_records(raw: bytes, schema: tuple[str, ...]) -> Iterator[dict[str, str]]:
    stream = io.StringIO(raw.decode("utf-8-sig"), newline="")
    reader = csv.reader(stream)
    try:
        first = next(reader)
    except StopIteration:
        return
    normalized = [x.strip().lower() for x in first]
    expected = [x.lower() for x in schema]
    if normalized == expected:
        start = reader
    else:
        if len(first) != len(schema):
            raise DataError(f"CSV schema has {len(first)} columns; expected {len(schema)}")
        def rows():
            yield first
            yield from reader
        start = rows()
    for line_no, row in enumerate(start, start=2):
        if len(row) != len(schema):
            raise DataError(f"CSV row {line_no} has {len(row)} columns; expected {len(schema)}")
        yield dict(zip(schema, (v.strip() for v in row)))


def _dec(value: str, name: str) -> Decimal:
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise DataError(f"invalid decimal in {name}: {value!r}") from exc
    if not result.is_finite():
        raise DataError(f"non-finite decimal in {name}")
    return result


@dataclass(frozen=True)
class Candle:
    open_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    close_time_ms: int
    quote_volume: Decimal
    source_count: int
    taker_buy_base_volume: Decimal
    taker_buy_quote_volume: Decimal
    ignore: str
    symbol: str
    timeframe: str
    kind: str = "klines"
    source_url: str = ""
    source_sha256: str = ""
    source_retrieved_at_utc: str = ""
    venue: str = "binance"
    market_type: str = "USD-M futures archive"

    @property
    def available_at_ms(self) -> int:
        return self.close_time_ms + 1

    @property
    def taker_sell_base_volume(self) -> Decimal:
        return self.volume - self.taker_buy_base_volume

    @property
    def taker_sell_quote_volume(self) -> Decimal:
        return self.quote_volume - self.taker_buy_quote_volume

    @property
    def trade_count(self) -> int | None:
        return self.source_count if self.kind == "klines" else None

    def research_row(self) -> dict:
        return {
            "open_time_ms": self.open_time_ms, "close_time_ms": self.close_time_ms,
            "available_at_ms": self.available_at_ms, "open": str(self.open),
            "high": str(self.high), "low": str(self.low), "close": str(self.close),
            "base_volume": str(self.volume), "quote_volume": str(self.quote_volume),
            "trade_count": self.trade_count, "source_count": self.source_count,
            "taker_buy_base_volume": str(self.taker_buy_base_volume),
            "taker_sell_base_volume": str(self.taker_sell_base_volume),
            "taker_buy_quote_volume": str(self.taker_buy_quote_volume),
            "taker_sell_quote_volume": str(self.taker_sell_quote_volume),
            "source_symbol": self.symbol, "source_venue": self.venue,
            "market_type": self.market_type, "original_timeframe": self.timeframe,
            "source_kind": self.kind, "source_url": self.source_url,
            "source_sha256": self.source_sha256,
            "source_retrieved_at_utc": self.source_retrieved_at_utc,
        }

    def freqtrade_row(self) -> dict:
        """The six standard Freqtrade OHLCV fields, with open time as UTC datetime."""
        return {
            "date": dt.datetime.fromtimestamp(self.open_time_ms / 1000, dt.timezone.utc),
            "open": float(self.open), "high": float(self.high), "low": float(self.low),
            "close": float(self.close), "volume": float(self.volume),
        }


def _pandas_source_provenance(source_record: dict) -> dict:
    symbol = source_record.get("contract_id") or source_record.get("symbol")
    source_hash = source_record.get("sha256") or source_record.get("official_sha256")
    required = {"symbol": symbol, "url": source_record.get("url"),
                "sha256": source_hash, "retrieved_at_utc": source_record.get("retrieved_at_utc")}
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise DataError("source provenance missing: " + ", ".join(missing))
    return {"source_symbol": symbol, "source_venue": source_record.get("venue", "binance"),
            "source_url": source_record["url"], "source_sha256": source_hash,
            "source_checksum_url": source_record.get("checksum_url"),
            "source_checksum_sha256": source_record.get("official_sha256") or source_hash,
            "source_retrieved_at_utc": source_record["retrieved_at_utc"]}


def convert_kline_frame(source_frame, source_record: dict, *, kind: str,
                        timeframe: str):
    """Return unchanged-schema Freqtrade OHLCV plus a source-rich research sidecar."""
    import pandas as pd

    if kind not in ("klines", "markPriceKlines") or timeframe not in INTERVAL_MS or timeframe == "4h":
        raise ValueError("unsupported kline conversion kind or timeframe")
    if source_record.get("kind") not in (None, kind):
        raise DataError("source receipt kind does not match requested kline kind")
    if source_record.get("timeframe") not in (None, timeframe):
        raise DataError("source receipt timeframe does not match requested kline timeframe")
    if set(KLINE_COLUMNS) - set(source_frame.columns):
        raise DataError("source kline frame does not match Binance USD-M schema")
    provenance = _pandas_source_provenance(source_record)
    f = source_frame.copy()
    width = INTERVAL_MS[timeframe]
    for column in ("open_time", "close_time", "count"):
        f[column] = pd.to_numeric(f[column], errors="raise").astype("int64")
    for column in ("open", "high", "low", "close", "volume", "quote_volume",
                   "taker_buy_volume", "taker_buy_quote_volume"):
        f[column] = pd.to_numeric(f[column], errors="raise").astype("float64")
    if f.open_time.duplicated().any() or not f.open_time.is_monotonic_increasing:
        raise DataError("source kline timestamps must be strictly ascending and unique")
    numeric_columns = ("open", "high", "low", "close", "volume", "quote_volume",
                       "taker_buy_volume", "taker_buy_quote_volume")
    if f[list(numeric_columns)].isna().any().any() or not all(
            f[column].map(math.isfinite).all() for column in numeric_columns):
        raise DataError("source kline has missing or non-finite numeric fields")
    f["date"] = pd.to_datetime(f.open_time, unit="ms", utc=True).dt.as_unit("ns")
    invalid_ohlc = ((f.low > f.open) | (f.low > f.close) | (f.high < f.open)
                    | (f.high < f.close) | (f.low <= 0))
    invalid_volume = ((f.volume < 0) | (f.quote_volume < 0) | (f["count"] < 0)
                      | (f.taker_buy_volume < 0) | (f.taker_buy_volume > f.volume + 1e-12)
                      | (f.taker_buy_quote_volume < 0)
                      | (f.taker_buy_quote_volume > f.quote_volume + 1e-8))
    if invalid_ohlc.any() or invalid_volume.any():
        raise DataError("source kline OHLC or volume integrity check failed")
    if (f.open_time % width != 0).any() or (f.close_time != f.open_time + width - 1).any():
        raise DataError("source kline timestamp alignment/close convention failed")
    if len(f) > 1 and (f.open_time.diff().iloc[1:] != width).any():
        raise DataError("source kline cadence gap or duplicate detected")
    f["taker_sell_volume"] = f.volume - f.taker_buy_volume
    f["taker_sell_quote_volume"] = f.quote_volume - f.taker_buy_quote_volume
    standard = f[["date", "open", "high", "low", "close", "volume"]].copy()
    count_semantics = ("BINANCE_KLINE_NUMBER_OF_TRADES" if kind == "klines"
                       else "MARK_PRICE_ARCHIVE_SAMPLING_COUNT_NOT_EXECUTED_TRADE_COUNT")
    trade_count = (f["count"].copy() if kind == "klines"
                   else pd.Series(pd.NA, index=f.index, dtype="Int64"))
    sidecar = pd.DataFrame({
        "date": f.date, "open_time_ms": f.open_time, "close_time_ms": f.close_time,
        "available_at_ms": f.open_time + width, "open": f.open, "high": f.high,
        "low": f.low, "close": f.close, "base_volume": f.volume,
        "quote_volume": f.quote_volume, "source_count": f["count"],
        "trade_count": trade_count, "taker_buy_base_volume": f.taker_buy_volume,
        "taker_sell_base_volume": f.taker_sell_volume,
        "taker_buy_quote_volume": f.taker_buy_quote_volume,
        "taker_sell_quote_volume": f.taker_sell_quote_volume,
        "source_count_semantics": count_semantics,
        "market_type": "USD-M futures archive; perpetual status not historically qualified",
        "original_timeframe": timeframe,
        **{name: value for name, value in provenance.items() if value is not None},
    })
    return standard.reset_index(drop=True), sidecar.reset_index(drop=True)


def convert_funding_frame(source_frame, source_record: dict):
    """Return Freqtrade's date/rate funding input plus the exact millisecond event sidecar."""
    import pandas as pd

    required = set(FUNDING_COLUMNS)
    if required - set(source_frame.columns):
        raise DataError("source funding frame does not match Binance fundingRate schema")
    if source_record.get("kind") not in (None, "fundingRate"):
        raise DataError("source receipt kind does not match fundingRate")
    provenance = _pandas_source_provenance(source_record)
    f = source_frame.copy()
    exact_ms = pd.to_numeric(f.calc_time, errors="raise").astype("int64")
    interval = pd.to_numeric(f.funding_interval_hours, errors="raise").astype("int64")
    rate = pd.to_numeric(f.last_funding_rate, errors="raise").astype("float64")
    if exact_ms.duplicated().any() or not exact_ms.is_monotonic_increasing:
        raise DataError("funding event times must be strictly ascending and unique")
    if (interval <= 0).any() or (interval > 24).any() or not rate.map(lambda x: x == x and abs(x) != float("inf")).all():
        raise DataError("invalid funding event interval or rate")
    date = pd.to_datetime(exact_ms, unit="ms", utc=True).dt.as_unit("ns")
    standard = pd.DataFrame({"date": date, "funding_rate": rate})
    sidecar = pd.DataFrame({"date": date, "source_event_time_ms": exact_ms,
                            "funding_interval_hours": interval, "funding_rate": rate,
                            "original_timeframe": "funding_event", **provenance})
    return standard.reset_index(drop=True), sidecar.reset_index(drop=True)


def parse_klines(source: Path | bytes, *, symbol: str, timeframe: str,
                 kind: str = "klines", source_url: str = "",
                 source_sha256: str = "", source_retrieved_at_utc: str = "") -> list[Candle]:
    if timeframe not in INTERVAL_MS or timeframe == "4h":
        raise ValueError(f"unsupported archived timeframe: {timeframe}")
    values = []
    for row in _csv_records(_zip_csv_bytes(source), KLINE_COLUMNS):
        candle = Candle(
            int(row["open_time"]), _dec(row["open"], "open"),
            _dec(row["high"], "high"), _dec(row["low"], "low"),
            _dec(row["close"], "close"), _dec(row["volume"], "volume"),
            int(row["close_time"]), _dec(row["quote_volume"], "quote_volume"),
            int(row["count"]), _dec(row["taker_buy_volume"], "taker_buy_volume"),
            _dec(row["taker_buy_quote_volume"], "taker_buy_quote_volume"),
            row["ignore"], symbol, timeframe, kind, source_url, source_sha256,
            source_retrieved_at_utc)
        if candle.open <= 0 or not (candle.low <= min(candle.open, candle.close)
                                    <= max(candle.open, candle.close) <= candle.high):
            raise DataError(f"invalid OHLC relationship at {candle.open_time_ms}")
        if candle.volume < 0 or candle.quote_volume < 0:
            raise DataError(f"negative volume at {candle.open_time_ms}")
        if candle.source_count < 0:
            raise DataError(f"negative source count at {candle.open_time_ms}")
        if candle.taker_buy_base_volume < 0 or candle.taker_buy_base_volume > candle.volume:
            raise DataError(f"taker-buy base volume outside total at {candle.open_time_ms}")
        if candle.taker_buy_quote_volume < 0 or candle.taker_buy_quote_volume > candle.quote_volume:
            raise DataError(f"taker-buy quote volume outside total at {candle.open_time_ms}")
        values.append(candle)
    if not values:
        raise DataError("empty candle archive")
    validate_cadence(values, timeframe)
    return values


def validate_cadence(candles: list[Candle], timeframe: str) -> dict:
    width = INTERVAL_MS[timeframe]
    opens = [c.open_time_ms for c in candles]
    if opens != sorted(opens) or len(opens) != len(set(opens)):
        raise DataError("candle timestamps are unsorted or duplicated")
    if any(open_ms % width for open_ms in opens):
        raise DataError("candle open timestamps are not UTC-epoch aligned to the advertised interval")
    gaps = sum(b - a != width for a, b in zip(opens, opens[1:]))
    bad_closes = sum(c.close_time_ms != c.open_time_ms + width - 1 for c in candles)
    if gaps or bad_closes:
        raise DataError(f"candle cadence/close mismatch: gaps={gaps}, bad_closes={bad_closes}")
    return {"rows": len(candles), "gaps": gaps, "duplicates": 0,
            "first_open_time_ms": opens[0], "last_open_time_ms": opens[-1],
            "availability_rule": "close_time_ms + 1; never before interval end"}


ADDITIVE_FIELDS = ("volume", "quote_volume", "source_count",
                   "taker_buy_base_volume", "taker_buy_quote_volume")


def resample_candles(candles: list[Candle], source_tf: str, target_tf: str) -> list[dict]:
    source_ms, target_ms = INTERVAL_MS[source_tf], INTERVAL_MS[target_tf]
    if target_ms <= source_ms or target_ms % source_ms:
        raise ValueError("target timeframe must be an integer multiple of source timeframe")
    if not candles or any(c.timeframe != source_tf or c.kind != "klines" or c.venue != "binance"
                          for c in candles) or len({c.symbol for c in candles}) != 1:
        raise DataError("resampling requires one Binance USD-M kline symbol and matching source timeframe")
    groups: dict[int, list[Candle]] = defaultdict(list)
    for c in candles:
        groups[(c.open_time_ms // target_ms) * target_ms].append(c)
    expected = target_ms // source_ms
    result = []
    for start, rows in sorted(groups.items()):
        rows.sort(key=lambda c: c.open_time_ms)
        if len(rows) != expected or any(
            b.open_time_ms - a.open_time_ms != source_ms for a, b in zip(rows, rows[1:])
        ) or rows[0].open_time_ms != start:
            raise DataError(f"incomplete source bars in {target_tf} bucket {start}")
        item = {"open_time_ms": start, "close_time_ms": start + target_ms - 1,
                "available_at_ms": start + target_ms, "open": rows[0].open,
                "high": max(r.high for r in rows), "low": min(r.low for r in rows),
                "close": rows[-1].close, "symbol": rows[0].symbol,
                "timeframe": target_tf}
        item.update({name: sum((getattr(r, name) for r in rows), Decimal(0))
                     for name in ADDITIVE_FIELDS})
        item["taker_sell_base_volume"] = item["volume"] - item["taker_buy_base_volume"]
        item["taker_sell_quote_volume"] = item["quote_volume"] - item["taker_buy_quote_volume"]
        item["source_url"] = rows[0].source_url
        item["source_sha256"] = rows[0].source_sha256
        item["source_retrieved_at_utc"] = rows[0].source_retrieved_at_utc
        result.append(item)
    return result


def compare_candles(derived: list[dict], source: list[Candle]) -> dict:
    by_time = {c.open_time_ms: c for c in source}
    fields = ("open", "high", "low", "close", *ADDITIVE_FIELDS)
    mismatch = {field: 0 for field in fields}
    matched = 0; differences = []
    for d in derived:
        s = by_time.get(d["open_time_ms"])
        if s is None:
            for field in mismatch:
                mismatch[field] += 1
            differences.append({"open_time_ms": d["open_time_ms"], "source_row": "MISSING"})
            continue
        matched += 1
        row_diff = {}
        for field in fields:
            if d[field] != getattr(s, field):
                mismatch[field] += 1
                row_diff[field] = {"derived": str(d[field]), "source": str(getattr(s, field))}
        if row_diff:
            differences.append({"open_time_ms": d["open_time_ms"], "fields": row_diff})
    source_only = len(source) - matched
    return {"derived_rows": len(derived), "source_rows": len(source),
            "matched_rows": matched, "source_only_rows": source_only,
            "mismatches_by_field": mismatch,
            "differences": differences[:100], "differences_truncated": len(differences) > 100,
            "exact_match": matched == len(derived) == len(source)
            and not any(mismatch.values())}


def completed_asof(candles: Iterable[Candle | dict], asof_ms: int) -> list[Candle | dict]:
    return [c for c in candles if (c.available_at_ms if isinstance(c, Candle)
            else c["available_at_ms"]) <= asof_ms]


def asof_features(candles_by_tf: dict[str, list[Candle]], asof_ms: int) -> dict:
    """Latest completed source bar per timeframe; no partial bar is exposed."""
    out = {"asof_ms": asof_ms, "timeframes": {}}
    for timeframe, candles in sorted(candles_by_tf.items()):
        eligible = completed_asof(candles, asof_ms)
        if not eligible:
            out["timeframes"][timeframe] = {"status": "NO_COMPLETED_BAR"}
            continue
        row = eligible[-1]
        value = lambda name: getattr(row, name) if isinstance(row, Candle) else row[name]
        out["timeframes"][timeframe] = {
            "status": "VERIFIED_SOURCE_BAR", "open_time_ms": value("open_time_ms"),
            "available_at_ms": value("available_at_ms"), "close": str(value("close")),
            "base_volume": str(value("volume")),
            "taker_buy_base_volume": str(value("taker_buy_base_volume")),
            "taker_sell_base_volume": str(value("taker_sell_base_volume")),
            "source_url": value("source_url"), "source_sha256": value("source_sha256"),
            "source_retrieved_at_utc": value("source_retrieved_at_utc"),
        }
    return out


@dataclass(frozen=True)
class FundingEvent:
    calc_time_ms: int
    funding_interval_hours: int
    funding_rate: Decimal
    symbol: str
    source_url: str
    source_sha256: str
    source_retrieved_at_utc: str = ""


def parse_funding(source: Path | bytes, *, symbol: str, source_url: str = "",
                  source_sha256: str = "", source_retrieved_at_utc: str = "") -> list[FundingEvent]:
    events = []
    for row in _csv_records(_zip_csv_bytes(source), FUNDING_COLUMNS):
        events.append(FundingEvent(int(row["calc_time"]),
                                   int(row["funding_interval_hours"]),
                                   _dec(row["last_funding_rate"], "funding_rate"),
                                   symbol, source_url, source_sha256,
                                   source_retrieved_at_utc))
    times = [e.calc_time_ms for e in events]
    if not events or times != sorted(times) or len(times) != len(set(times)):
        raise DataError("funding timestamps are empty, unsorted, or duplicated")
    if any(e.funding_interval_hours <= 0 or e.funding_interval_hours > 24 for e in events):
        raise DataError("invalid published funding interval")
    return events


def funding_events_between(events: Iterable[FundingEvent], entry_ms: int, exit_ms: int) -> list[FundingEvent]:
    """Assign only published funding event clocks strictly after entry through exit.

    An event at the exact entry millisecond is excluded because the archive does
    not establish whether the position existed before settlement; exit is
    inclusive. Callers should preserve this declared boundary convention.
    """
    if exit_ms < entry_ms:
        raise ValueError("exit timestamp precedes entry timestamp")
    return [event for event in events if entry_ms < event.calc_time_ms <= exit_ms]


def funding_asof(events: Iterable[FundingEvent], asof_ms: int) -> list[FundingEvent]:
    return [event for event in events if event.calc_time_ms <= asof_ms]


@dataclass(frozen=True)
class AggregateTrade:
    agg_trade_id: int
    price: Decimal
    quantity: Decimal
    first_trade_id: int
    last_trade_id: int
    time_ms: int
    buyer_is_maker: bool


def parse_aggregate_trades(source: Path | bytes, *, date: str) -> Iterator[AggregateTrade]:
    day = dt.date.fromisoformat(date)
    start_ms = int(dt.datetime.combine(day, dt.time(), dt.timezone.utc).timestamp() * 1000)
    end_ms = start_ms + 86_400_000
    for row in _csv_records(_zip_csv_bytes(source), AGG_COLUMNS):
        side = row["is_buyer_maker"].lower()
        if side not in ("true", "false"):
            raise DataError(f"invalid buyer-maker flag: {side!r}")
        trade = AggregateTrade(int(row["agg_trade_id"]), _dec(row["price"], "price"),
                               _dec(row["quantity"], "quantity"),
                               int(row["first_trade_id"]), int(row["last_trade_id"]),
                               int(row["transact_time"]), side == "true")
        if trade.price <= 0 or trade.quantity <= 0 or trade.first_trade_id > trade.last_trade_id:
            raise DataError(f"invalid aggregate trade {trade.agg_trade_id}")
        if not start_ms <= trade.time_ms < end_ms:
            raise DataError(f"trade timestamp outside registered UTC date: {trade.time_ms}")
        yield trade


def volume_profile(traded_volume: dict[Decimal, Decimal], *, value_area_fraction: Decimal = Decimal("0.70")) -> dict:
    if not traded_volume or not Decimal(0) < value_area_fraction <= Decimal(1):
        raise ValueError("volume profile needs positive bins and a value area in (0, 1]")
    prices = sorted(traded_volume)
    poc = min(prices, key=lambda p: (-traded_volume[p], p))
    idx = prices.index(poc)
    lo = hi = idx
    total = sum(traded_volume.values(), Decimal(0))
    included = traded_volume[poc]
    target = total * value_area_fraction
    while included < target and (lo > 0 or hi < len(prices) - 1):
        down = traded_volume[prices[lo - 1]] if lo > 0 else Decimal(-1)
        up = traded_volume[prices[hi + 1]] if hi < len(prices) - 1 else Decimal(-1)
        if down >= up:  # deterministic lower-price tie break
            lo -= 1
            included += traded_volume[prices[lo]]
        else:
            hi += 1
            included += traded_volume[prices[hi]]
    return {"poc": str(poc), "val": str(prices[lo]), "vah": str(prices[hi]),
            "total_base_volume": str(total), "value_area_volume": str(included),
            "value_area_fraction_target": str(value_area_fraction),
            "method": "POC=max volume (ties lower price); expand adjacent observed price bins by larger next volume until target; ties lower price"}


def summarize_aggregate_trades(source: Path | bytes, *, symbol: str, date: str,
                               source_url: str, source_sha256: str,
                               source_retrieved_at_utc: str = "",
                               five_minute: list[Candle] | None = None) -> dict:
    profile: dict[Decimal, Decimal] = defaultdict(Decimal)
    buy = Decimal(0); sell = Decimal(0); quote = Decimal(0)
    bucket_flow: dict[int, dict[str, Decimal]] = defaultdict(lambda: {"buy": Decimal(0), "sell": Decimal(0), "total": Decimal(0)})
    first = last = None; previous_a = previous_time = previous_last_id = None
    id_gaps = trade_id_gaps = duplicates = out_of_order = overlaps = 0
    samples = []; count = 0
    for trade in parse_aggregate_trades(source, date=date):
        count += 1
        if first is None:
            first = {"agg_trade_id": trade.agg_trade_id, "first_trade_id": trade.first_trade_id,
                     "last_trade_id": trade.last_trade_id, "time_ms": trade.time_ms}
        if previous_a is not None:
            if trade.agg_trade_id == previous_a: duplicates += 1
            elif trade.agg_trade_id < previous_a: out_of_order += 1
            elif trade.agg_trade_id > previous_a + 1: id_gaps += trade.agg_trade_id - previous_a - 1
            if trade.time_ms < previous_time: out_of_order += 1
            if trade.first_trade_id <= previous_last_id: overlaps += 1
            elif trade.first_trade_id > previous_last_id + 1: trade_id_gaps += trade.first_trade_id - previous_last_id - 1
        if len(samples) < 5:
            samples.append({"agg_trade_id": trade.agg_trade_id, "price": str(trade.price),
                            "quantity": str(trade.quantity), "first_trade_id": trade.first_trade_id,
                            "last_trade_id": trade.last_trade_id, "time_ms": trade.time_ms,
                            "buyer_is_maker": trade.buyer_is_maker,
                            "aggressor_side": "sell" if trade.buyer_is_maker else "buy"})
        profile[trade.price] += trade.quantity
        notional = trade.price * trade.quantity
        quote += notional
        side = "sell" if trade.buyer_is_maker else "buy"
        if side == "buy": buy += trade.quantity
        else: sell += trade.quantity
        bucket = (trade.time_ms // 300_000) * 300_000
        bucket_flow[bucket][side] += trade.quantity
        bucket_flow[bucket]["total"] += trade.quantity
        previous_a = trade.agg_trade_id
        previous_time = trade.time_ms
        previous_last_id = trade.last_trade_id
        last = {"agg_trade_id": trade.agg_trade_id, "first_trade_id": trade.first_trade_id,
                "last_trade_id": trade.last_trade_id, "time_ms": trade.time_ms}
    if not count:
        raise DataError("aggregate-trade archive is empty")
    result = {
        "symbol": symbol, "venue": "binance", "market_type": "USD-M futures archive",
        "date_utc": date, "source_url": source_url, "source_sha256": source_sha256,
        "source_retrieved_at_utc": source_retrieved_at_utc,
        "rows": count, "first_record": first, "last_record": last,
        "timestamp_unit": "Unix milliseconds UTC", "quantity_unit": "source quantity for symbol base asset; contract multiplier is unqualified",
        "quote_notional_unit": "USDT from price x quantity; contract multiplier is unqualified",
        "duplicate_aggregate_ids": duplicates, "out_of_order_count": out_of_order,
        "aggregate_id_gaps": id_gaps, "constituent_trade_id_gaps": trade_id_gaps,
        "overlapping_constituent_id_ranges": overlaps,
        "total_base_quantity": str(buy + sell), "total_quote_notional": str(quote),
        "aggressive_buy_base_quantity": str(buy), "aggressive_sell_base_quantity": str(sell),
        "cumulative_volume_delta_base": str(buy - sell),
        "side_convention": "buyer_is_maker=true => seller taker/aggressive sell; false => buyer taker/aggressive buy",
        "volume_profile": volume_profile(profile), "sample_trades": samples,
    }
    if five_minute is not None:
        if any(c.symbol != symbol or c.timeframe != "5m" for c in five_minute):
            raise DataError("trade/kline market identity or timeframe mismatch")
        comparisons = []
        for candle in five_minute:
            flow = bucket_flow.get(candle.open_time_ms, {"buy": Decimal(0), "sell": Decimal(0), "total": Decimal(0)})
            tolerance = max(Decimal("0.00000001"), candle.volume * Decimal("0.000001"))
            comparisons.append({"open_time_ms": candle.open_time_ms,
                "kline_volume": str(candle.volume), "agg_trade_volume": str(flow["total"]),
                "kline_taker_buy_base": str(candle.taker_buy_base_volume),
                "agg_trade_aggressive_buy": str(flow["buy"]),
                "total_abs_diff": str(abs(candle.volume - flow["total"])),
                "buy_abs_diff": str(abs(candle.taker_buy_base_volume - flow["buy"])),
                "tolerance": str(tolerance),
                "within_tolerance": abs(candle.volume - flow["total"]) <= tolerance
                    and abs(candle.taker_buy_base_volume - flow["buy"]) <= tolerance})
        result["kline_reconciliation"] = {
            "five_minute_bars": len(comparisons),
            "bars_within_1e-6_relative_or_1e-8_absolute": sum(x["within_tolerance"] for x in comparisons),
            "bars_outside_tolerance": sum(not x["within_tolerance"] for x in comparisons),
            "comparisons": comparisons,
        }
    return result


def classify_specification(spec: dict | None, evaluation_start: str) -> str:
    """Current/unqualified fixture metadata cannot validate a historical period."""
    if (not spec or spec.get("status") != "VERIFIED"
            or spec.get("time_qualified") is not True
            or not spec.get("source_url") or not spec.get("source_sha256")
            or not spec.get("effective_from")):
        return "UNQUALIFIED_EXECUTION_METADATA"
    start = dt.date.fromisoformat(evaluation_start)
    effective = dt.date.fromisoformat(spec["effective_from"][:10])
    end = dt.date.fromisoformat(spec["effective_to"][:10]) if spec.get("effective_to") else None
    return "QUALIFIED_FOR_PERIOD" if effective <= start and (end is None or start <= end) else "UNQUALIFIED_EXECUTION_METADATA"


def validate_order_rules(spec: dict | None, *, evaluation_start: str,
                         price: Decimal, quantity: Decimal) -> dict:
    status = classify_specification(spec, evaluation_start)
    if status != "QUALIFIED_FOR_PERIOD":
        raise DataError(status)
    assert spec is not None
    required = ("tick_size", "quantity_step", "minimum_quantity", "maximum_quantity",
                "minimum_notional", "contract_size")
    missing = [name for name in required if name not in spec]
    if missing:
        raise DataError("UNQUALIFIED_EXECUTION_METADATA missing required fields: " + ", ".join(missing))
    if price <= 0 or quantity <= 0:
        raise DataError("price and quantity must be positive")
    if price % Decimal(str(spec["tick_size"])) != 0:
        raise DataError("price is not aligned to verified tick size")
    if quantity % Decimal(str(spec["quantity_step"])) != 0:
        raise DataError("quantity is not aligned to verified quantity step")
    if quantity < Decimal(str(spec["minimum_quantity"])):
        raise DataError("quantity below verified minimum")
    if quantity > Decimal(str(spec["maximum_quantity"])):
        raise DataError("quantity above verified maximum")
    notional = price * quantity * Decimal(str(spec.get("contract_size", "1")))
    if notional < Decimal(str(spec["minimum_notional"])):
        raise DataError("notional below verified minimum")
    return {"status": status, "notional": str(notional), "specification_effective_from": spec["effective_from"]}


def probe_public_endpoints(timeout: float = 10) -> list[dict]:
    urls = {
        "exchange_info": f"{FUTURES_API_BASE}/exchangeInfo",
        "ticker_24h": f"{FUTURES_API_BASE}/ticker/24hr?symbol=BTCUSDT",
        "candles_5m": f"{FUTURES_API_BASE}/klines?symbol=BTCUSDT&interval=5m&limit=2",
        "funding_and_mark": f"{FUTURES_API_BASE}/premiumIndex?symbol=BTCUSDT",
        "order_book_snapshot": f"{FUTURES_API_BASE}/depth?symbol=BTCUSDT&limit=5",
    }
    results = []
    for name, url in urls.items():
        started = utc_now()
        try:
            body, status, final, headers = _request(url, timeout=timeout, max_bytes=64 * 1024)
            results.append({"dataset": name, "url": url, "status": "PASS", "http_status": status,
                            "response_bytes": len(body), "retrieved_at_utc": started,
                            "final_url": final, "content_type": headers.get("Content-Type")})
        except DataError as exc:
            match = re.search(r"HTTP (\d+)", str(exc))
            http_status = int(match.group(1)) if match else None
            results.append({"dataset": name, "url": url,
                            "status": "BLOCKED" if http_status in (401, 403, 451) else "FAILED",
                            "http_status": http_status, "retrieved_at_utc": started,
                            "error": str(exc)[:500]})
    return results


def discover_archive_symbols(*, max_pages: int = 10, timeout: float = 15) -> dict:
    """Enumerate official public archive symbol directories, not active contracts.

    The official data.binance.vision index page publishes its public bucket URL.
    This list is historical archive inventory only; it is never used to infer a
    symbol's current TRADING status or to replace restricted FAPI metadata.
    """
    html, status, _, _ = _request("https://data.binance.vision/", timeout=timeout,
                                  max_bytes=256 * 1024)
    if status != 200:
        raise DataError("official archive index did not return HTTP 200")
    match = re.search(r"BUCKET_URL\s*=\s*['\"]([^'\"]+)['\"]", html.decode("utf-8", "replace"))
    if not match:
        raise DataError("official archive page did not publish its bucket URL")
    bucket = match.group(1).rstrip("/")
    prefix = "data/futures/um/daily/klines/"
    symbols: set[str] = set(); token = None; pages = 0; truncated = False
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    while pages < max_pages:
        params = {"list-type": "2", "prefix": prefix, "delimiter": "/", "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        body, code, _, _ = _request(bucket + "/?" + urllib.parse.urlencode(params),
                                     timeout=timeout, max_bytes=2 * 1024 * 1024)
        if code != 200:
            raise DataError(f"official archive inventory HTTP {code}")
        root = ET.fromstring(body); pages += 1
        for node in root.findall("s3:CommonPrefixes/s3:Prefix", ns):
            path = node.text or ""
            symbol = path.removeprefix(prefix).strip("/")
            if symbol:
                symbols.add(symbol)
        truncated = (root.findtext("s3:IsTruncated", default="false", namespaces=ns).lower() == "true")
        token = root.findtext("s3:NextContinuationToken", namespaces=ns)
        if not truncated or not token:
            break
    return {"source": "Binance Vision public archive bucket inventory",
            "inventory_retrieved_at_utc": utc_now(), "dataset_prefix": prefix,
            "archived_symbol_directory_count": len(symbols),
            "active_contract_count": None, "active_status": "NOT_ESTABLISHED_BY_ARCHIVE_DIRECTORY",
            "pages_read": pages, "inventory_complete": not truncated,
            "symbols": sorted(symbols),
            "limitations": ["A historical archive directory proves archive presence only.",
                            "Current futures TRADING membership remains unavailable while public FAPI exchangeInfo returns 451."]}


def cached_coverage(cache_dir: Path) -> dict:
    """List verified local sample coverage; directory presence alone is not trusted."""
    cache_dir = Path(cache_dir)
    manifests = sorted((cache_dir / "samples").glob("*.json"))
    sources = []
    for path in manifests:
        manifest = json.loads(path.read_text())
        for item in manifest.get("sources", []):
            verify_cached_archive(resolve_cache_path(item["cache_path"]), item["official_sha256"])
            if item.get("utc_date"):
                day = dt.date.fromisoformat(item["utc_date"])
                start = dt.datetime.combine(day, dt.time(), dt.timezone.utc)
                end = start + dt.timedelta(days=1)
            elif item.get("month"):
                year, month = map(int, item["month"].split("-"))
                start = dt.datetime(year, month, 1, tzinfo=dt.timezone.utc)
                end = dt.datetime(year + (month == 12), 1 if month == 12 else month + 1,
                                  1, tzinfo=dt.timezone.utc)
            else:
                start = end = None
            sources.append({"kind": item["kind"], "symbol": item["symbol"],
                            "timeframe": item.get("timeframe"),
                            "archive_start_utc": start.isoformat() if start else None,
                            "archive_end_exclusive_utc": end.isoformat() if end else None,
                            "archive_date_or_month": item.get("utc_date") or item.get("month"),
                            "sha256": item["official_sha256"], "bytes": item["bytes"],
                            "source_url": item["url"],
                            "source_retrieved_at_utc": item.get("retrieved_at_utc"),
                            "status": "CHECKSUM_VERIFIED"})
    contracts = sorted({x["symbol"] for x in sources})
    return {"cache_dir": str(cache_dir), "manifest_count": len(manifests),
            "supported_archive_symbols": contracts,
            "market_identity_status": "USD-M archive symbol; perpetual/current TRADING status unqualified",
            "sources": sources}
