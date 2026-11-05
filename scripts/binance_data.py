#!/usr/bin/env python3
"""Beginner-operable, bounded Binance Vision research-data acceptance CLI."""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from pathlib import Path

from binance_research_data import (
    AGG_COLUMNS, FUNDING_COLUMNS, KLINE_COLUMNS, DataError, INTERVAL_MS, archive_url, asof_features, cached_coverage, compare_candles,
    discover_archive_symbols, fetch_verified, parse_funding, parse_klines,
    probe_public_endpoints, resample_candles, summarize_aggregate_trades,
    resolve_cache_path, validate_cadence, verify_cached_archive,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CONFIG = ROOT / "research/binance_data_sample.json"
DEFAULT_CACHE = ROOT / "user_data/data/binance_verified"


def load_json(path: Path):
    return json.loads(path.read_text())


def sample_manifest_path(cache: Path, date: str) -> Path:
    return cache / "samples" / f"{date}.json"


def load_sample(cache: Path, date: str) -> dict:
    path = sample_manifest_path(cache, date)
    if not path.exists():
        raise DataError(f"sample receipt missing; run fetch-sample first: {path}")
    manifest = load_json(path)
    if manifest["utc_date"] != date:
        raise DataError("sample date does not match the requested date")
    for entry in manifest["sources"]:
        verify_cached_archive(resolve_cache_path(entry["cache_path"]), entry["official_sha256"])
    return manifest


def fetch_sample(args) -> None:
    config = load_json(Path(args.sample_config))
    date = args.date or config["utc_date"]
    dt.date.fromisoformat(date)
    month = args.funding_month or config["funding_month"]
    cache = Path(args.cache).resolve()
    sources = []
    total = 0

    def fetch(kind, symbol, *, timeframe=None, source_date=None, source_month=None):
        nonlocal total
        url = archive_url(kind, symbol, date=source_date, timeframe=timeframe, month=source_month)
        rec = fetch_verified(url, cache / kind / symbol,
                             max_archive_bytes=min(args.max_archive_bytes, config["max_archive_bytes"]))
        cache_hit = rec.pop("cache_hit", False)
        total += rec["bytes"]
        if total > min(args.max_total_bytes, config["max_total_archive_bytes"]):
            raise DataError("registered sample archive byte cap exceeded; cache remains intact")
        try:
            rec["cache_path"] = str(Path(rec["cache_path"]).resolve().relative_to(ROOT))
        except ValueError:
            pass
        rec.update({"kind": kind, "symbol": symbol, "timeframe": timeframe,
                    "utc_date": source_date, "month": source_month})
        sources.append(rec)
        print(f"{kind:16s} {symbol:16s} {timeframe or source_month or source_date:10s} "
              f"{rec['bytes']:>9d} bytes SHA256 {rec['official_sha256']} "
              f"cache_hit={str(cache_hit).lower()}")

    for symbol in config["symbols"]:
        for timeframe in config["timeframes"]:
            fetch("klines", symbol, timeframe=timeframe, source_date=date)
        fetch("markPriceKlines", symbol, timeframe=config["mark_timeframe"], source_date=date)
        fetch("fundingRate", symbol, source_month=month)
    trade = config["trade_sample"]
    fetch("aggTrades", trade["symbol"], source_date=trade["utc_date"])
    result = {"sample_config": "research/binance_data_sample.json", "sample_config_sha256": __import__("hashlib").sha256(Path(args.sample_config).read_bytes()).hexdigest(),
              "utc_date": date, "funding_month": month, "source_count": len(sources),
              "total_archive_bytes": total, "max_total_archive_bytes": min(args.max_total_bytes, config["max_total_archive_bytes"]),
              "sources": sources, "attribution": config["attribution"]}
    receipt = sample_manifest_path(cache, date)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if receipt.exists():
        if receipt.read_text() != encoded:
            raise DataError(f"sample receipt already exists with different content; preserved: {receipt}")
    else:
        receipt.write_text(encoded)
    print(f"Verified {len(sources)} archives ({total} bytes). Receipt: {receipt}")


def fetch_one(args) -> None:
    url = archive_url(args.kind, args.symbol, date=args.date,
                      timeframe=args.timeframe, month=args.month)
    receipt = fetch_verified(url, Path(args.cache).resolve() / args.kind / args.symbol,
                             max_archive_bytes=args.max_archive_bytes)
    receipt.update({"kind": args.kind, "symbol": args.symbol,
                   "timeframe": args.timeframe, "utc_date": args.date, "month": args.month})
    print(json.dumps(receipt, indent=2, sort_keys=True))


def cache_info(args) -> None:
    result = cached_coverage(Path(args.cache).resolve())
    print(json.dumps(result, indent=2, sort_keys=True))


def _source_entry(manifest, kind, symbol, timeframe=None):
    for row in manifest["sources"]:
        if row["kind"] == kind and row["symbol"] == symbol and row["timeframe"] == timeframe:
            expected = archive_url(kind, symbol, date=row.get("utc_date"),
                                   timeframe=timeframe, month=row.get("month"))
            if row.get("url") != expected:
                raise DataError(f"source receipt market/type/timeframe mismatch: {row.get('url')}")
            return row
    raise DataError(f"source receipt not found: {kind} {symbol} {timeframe}")


def _load_candles(manifest, symbol, timeframe, kind="klines"):
    source = _source_entry(manifest, kind, symbol, timeframe)
    return parse_klines(resolve_cache_path(source["cache_path"]), symbol=symbol, timeframe=timeframe,
                        kind=kind, source_url=source["url"], source_sha256=source["official_sha256"],
                        source_retrieved_at_utc=source["retrieved_at_utc"])


def validate_sample(args) -> dict:
    cache = Path(args.cache).resolve()
    manifest = load_sample(cache, args.date)
    config = load_json(Path(args.sample_config))
    mtf = {}; candles = {}
    for symbol in config["symbols"]:
        data = {tf: _load_candles(manifest, symbol, tf) for tf in config["timeframes"]}
        candles[symbol] = data
        date_start = int(dt.datetime.combine(dt.date.fromisoformat(args.date), dt.time(), dt.timezone.utc).timestamp() * 1000)
        for tf, rows in data.items():
            quality = validate_cadence(rows, tf)
            expected = 86_400_000 // INTERVAL_MS[tf]
            if len(rows) != expected or rows[0].open_time_ms != date_start:
                raise DataError(f"incomplete {symbol} {tf} source archive: {len(rows)} rows")
        a = resample_candles(data["1m"], "1m", "5m")
        b = resample_candles(data["5m"], "5m", "15m")
        c = resample_candles(data["15m"], "15m", "1h")
        four_hour = resample_candles(data["1h"], "1h", "4h")
        mtf[symbol] = {
            "1m_to_5m": compare_candles(a, data["5m"]),
            "5m_to_15m": compare_candles(b, data["15m"]),
            "15m_to_1h": compare_candles(c, data["1h"]),
            "derived_4h": {"bars": len(four_hour), "first": {
                "open_time_ms": four_hour[0]["open_time_ms"],
                "available_at_ms": four_hour[0]["available_at_ms"],
                "close": str(four_hour[0]["close"])},
                "source_timeframe": "1h", "source_url": four_hour[0]["source_url"],
                "source_sha256": four_hour[0]["source_sha256"]},
        }
    mark = {}
    date_start = int(dt.datetime.combine(dt.date.fromisoformat(args.date), dt.time(),
                                         dt.timezone.utc).timestamp() * 1000)
    for symbol in config["symbols"]:
        rows = _load_candles(manifest, symbol, config["mark_timeframe"], "markPriceKlines")
        validate_cadence(rows, config["mark_timeframe"])
        expected_mark_rows = 86_400_000 // INTERVAL_MS[config["mark_timeframe"]]
        if len(rows) != expected_mark_rows or rows[0].open_time_ms != date_start:
            raise DataError(f"incomplete {symbol} mark-price source archive: {len(rows)} rows")
        mark[symbol] = {"rows": len(rows), "first_open_time_ms": rows[0].open_time_ms,
                        "last_open_time_ms": rows[-1].open_time_ms,
                        "source_sha256": rows[0].source_sha256,
                        "volume_fields_are_not_executed_trade_volume": True}
    funding = {}
    for symbol in config["symbols"]:
        entry = _source_entry(manifest, "fundingRate", symbol, None)
        rows = parse_funding(resolve_cache_path(entry["cache_path"]), symbol=symbol,
                             source_url=entry["url"], source_sha256=entry["official_sha256"],
                             source_retrieved_at_utc=entry["retrieved_at_utc"])
        funding[symbol] = {"events": len(rows), "first_calc_time_ms": rows[0].calc_time_ms,
                           "last_calc_time_ms": rows[-1].calc_time_ms,
                           "timestamp_ordering": "STRICT_ASCENDING", "duplicate_event_timestamps": 0,
                           "funding_interval_hours_distribution": {
                               str(hours): sum(event.funding_interval_hours == hours for event in rows)
                               for hours in sorted({event.funding_interval_hours for event in rows})},
                           "first_funding_interval_hours": rows[0].funding_interval_hours,
                           "first_rate": str(rows[0].funding_rate),
                           "source_sha256": entry["official_sha256"],
                           "timestamps_preserved_as_published_milliseconds": True}
    trade_config = config["trade_sample"]
    trade_entry = _source_entry(manifest, "aggTrades", trade_config["symbol"], None)
    trade_symbol = trade_config["symbol"]
    trade_rows = candles[trade_symbol]["5m"]
    trade_summary = summarize_aggregate_trades(
        resolve_cache_path(trade_entry["cache_path"]), symbol=trade_symbol, date=args.date,
        source_url=trade_entry["url"], source_sha256=trade_entry["official_sha256"],
        source_retrieved_at_utc=trade_entry["retrieved_at_utc"],
        five_minute=trade_rows)
    btc = candles["BTCUSDT"]
    btc_4h = resample_candles(btc["1h"], "1h", "4h")
    asof = btc["1h"][12].available_at_ms
    causal = asof_features({"1m": btc["1m"], "5m": btc["5m"], "15m": btc["15m"],
                            "1h": btc["1h"], "4h": btc_4h}, asof)
    expected_hour = btc["1h"][12].open_time_ms
    if causal["timeframes"]["1h"].get("open_time_ms") != expected_hour:
        raise DataError("higher-timeframe as-of feature did not select the last completed hour")
    examples = {
        "btc_first_5m_research_record": btc["5m"][0].research_row(),
        "btc_first_5m_freqtrade_record": btc["5m"][0].freqtrade_row(),
        "asof_decision": causal,
    }
    all_reconstruction = all(mtf[symbol][step]["exact_match"]
                             for symbol in mtf
                             for step in ("1m_to_5m", "5m_to_15m", "15m_to_1h"))
    trade_recon = trade_summary["kline_reconciliation"]
    trade_recon_exact = trade_recon["bars_outside_tolerance"] == 0
    acceptance_status = "PASS_DATA_INTEGRITY" if all_reconstruction and trade_recon_exact else "PARTIAL_SOURCE_MISMATCH"
    source_receipts = []
    for item in manifest["sources"]:
        portable = dict(item)
        try:
            portable["cache_path"] = str(resolve_cache_path(item["cache_path"]).resolve().relative_to(ROOT))
        except ValueError:
            pass
        source_receipts.append(portable)
    report = {
        "schema_version": 1, "run_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "acceptance_status": acceptance_status,
        "candle_reconstruction_status": "PASS" if all_reconstruction else "PARTIAL_SOURCE_MISMATCH",
        "trade_to_kline_reconciliation_status": "PASS" if trade_recon_exact else "PARTIAL_SOURCE_MISMATCH",
        "scope": "Historical Binance Vision USD-M archive acceptance only; no strategy or profitability evaluation.",
        "sample_config_sha256": manifest["sample_config_sha256"],
        "utc_date": args.date, "funding_month": manifest["funding_month"],
        "source_count": manifest["source_count"], "archive_bytes": manifest["total_archive_bytes"],
        "symbols": config["symbols"], "source_receipts": source_receipts,
        "published_schemas": {"USD-M_kline_columns": list(KLINE_COLUMNS),
                               "USD-M_aggTrades_columns": list(AGG_COLUMNS),
                               "fundingRate_columns": list(FUNDING_COLUMNS)},
        "units": {"kline_volume": "base-asset units as published for the USD-M symbol; contract multiplier not independently qualified",
                  "kline_quote_volume": "quote-asset units (USDT) as published",
                  "taker_buy_volume": "aggressive buyer quantity in base-asset units as published by Binance kline",
                  "taker_sell_volume": "source total minus taker-buy quantity; consistency checked before derivation",
                  "aggTrades_quantity": "source quantity in symbol base units; contract multiplier not independently qualified",
                  "funding_rate": "published dimensionless rate; calc_time is Unix milliseconds UTC"},
        "candle_coverage": {symbol: {tf: {"rows": len(candles[symbol][tf]),
                                    "first_open_time_ms": candles[symbol][tf][0].open_time_ms,
                                    "last_open_time_ms": candles[symbol][tf][-1].open_time_ms,
                                    "first_available_at_ms": candles[symbol][tf][0].available_at_ms,
                                    "last_available_at_ms": candles[symbol][tf][-1].available_at_ms,
                                    "gaps": 0, "duplicates": 0,
                                    "bad_ohlc_rows": 0, "negative_volume_rows": 0,
                                    "taker_buy_exceeds_total_rows": 0,
                                    "source_sha256": candles[symbol][tf][0].source_sha256}
                                for tf in config["timeframes"]}
                            for symbol in config["symbols"]},
        "multi_timeframe_reconstruction": mtf, "mark_price": mark, "funding": funding,
        "aggregated_trade_demonstration": trade_summary, "causal_timing": examples["asof_decision"],
        "sample_records": examples,
        "execution_metadata_status": "UNQUALIFIED_EXECUTION_METADATA",
        "execution_readiness": "BLOCKED_FAIL_CLOSED",
        "current_contract_membership": "NOT_ESTABLISHED_BY_ARCHIVE; FAPI exchangeInfo HTTP 451",
        "data_license": "Binance Vision Dataset Terms v1.0, CC BY-NC-SA 4.0; non-commercial use only; attribution retained.",
        "limitations": ["Archive path identifies USD-M futures data but does not independently establish perpetual classification or current TRADING status.",
                        "REST public market data and historical execution rules were restricted; spreads, fills, queue priority, fees and historical filters remain unqualified.",
                        "Aggregated trades are executed-price records, not full level-2 order-book history."],
    }
    if args.write_report:
        out = Path(args.write_report)
        if out.exists():
            raise DataError(f"refusing to overwrite existing acceptance evidence: {out}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({"acceptance_status": report["acceptance_status"],
                      "candle_reconstruction_status": report["candle_reconstruction_status"],
                      "trade_to_kline_reconciliation_status": report["trade_to_kline_reconciliation_status"],
                      "source_count": report["source_count"],
                      "archive_bytes": report["archive_bytes"],
                      "symbols": report["symbols"],
                      "mtf_mismatch_counts": {s: {k: v["mismatches_by_field"] for k, v in d.items() if k != "derived_4h"} for s, d in mtf.items()},
                      "trade_rows": trade_summary["rows"],
                      "trade_duplicates": trade_summary["duplicate_aggregate_ids"],
                      "trade_cvd_base": trade_summary["cumulative_volume_delta_base"],
                      "trade_profile": trade_summary["volume_profile"],
                      "kline_reconciliation": {"within": trade_summary["kline_reconciliation"]["bars_within_1e-6_relative_or_1e-8_absolute"],
                                               "total": trade_summary["kline_reconciliation"]["five_minute_bars"]},
                      "execution_metadata_status": report["execution_metadata_status"],
                      "report": str(Path(args.write_report).resolve()) if args.write_report else None}, indent=2, default=str))
    return report


def show_record(args) -> None:
    manifest = load_sample(Path(args.cache).resolve(), args.date)
    rows = _load_candles(manifest, args.symbol, args.timeframe)
    for candle in rows[:args.limit]:
        print(json.dumps(candle.research_row(), sort_keys=True))


def orderflow(args) -> None:
    manifest = load_sample(Path(args.cache).resolve(), args.date)
    entry = _source_entry(manifest, "aggTrades", args.symbol, None)
    candles = _load_candles(manifest, args.symbol, "5m")
    summary = summarize_aggregate_trades(resolve_cache_path(entry["cache_path"]), symbol=args.symbol,
        date=args.date, source_url=entry["url"], source_sha256=entry["official_sha256"],
        source_retrieved_at_utc=entry["retrieved_at_utc"],
        five_minute=candles)
    print(json.dumps(summary, indent=2, sort_keys=True))


async def _websocket_probe(timeout: float) -> dict:
    try:
        import websockets
        async with websockets.connect("wss://fstream.binance.com/ws/btcusdt@markPrice",
                                     proxy=True, open_timeout=timeout, close_timeout=2,
                                     max_size=4096, ping_interval=None) as socket:
            message = await asyncio.wait_for(socket.recv(), timeout=timeout)
        return {"status": "PASS", "endpoint": "wss://fstream.binance.com/ws/btcusdt@markPrice",
                "message_bytes": len(message), "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    except Exception as exc:
        blocked = isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError)) or "451" in str(exc) or "403" in str(exc)
        return {"status": "BLOCKED" if blocked else "FAILED",
                "endpoint": "wss://fstream.binance.com/ws/btcusdt@markPrice",
                "error": f"{type(exc).__name__}: {exc}"[:500],
                "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}


def probe(args) -> None:
    result = {"retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "rest": probe_public_endpoints(timeout=args.timeout)}
    if args.websocket:
        result["websocket"] = asyncio.run(_websocket_probe(args.timeout))
    print(json.dumps(result, indent=2))


def universe(args) -> None:
    result = discover_archive_symbols(max_pages=args.max_pages, timeout=args.timeout)
    print(json.dumps({k: v for k, v in result.items() if k != "symbols"} | {
        "symbol_directories_ending_USDT": sum(symbol.endswith("USDT") for symbol in result["symbols"]),
        "first_symbols": result["symbols"][:20], "last_symbols": result["symbols"][-20:]}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fetch-sample", help="Download the registered bounded 8-symbol source sample")
    p.add_argument("--date"); p.add_argument("--funding-month")
    p.add_argument("--cache", default=str(DEFAULT_CACHE))
    p.add_argument("--sample-config", default=str(SAMPLE_CONFIG))
    p.add_argument("--max-archive-bytes", type=int, default=20 * 1024 * 1024)
    p.add_argument("--max-total-bytes", type=int, default=32 * 1024 * 1024)
    p.set_defaults(func=fetch_sample)
    p = sub.add_parser("fetch-one", help="Fetch one checksum-verified source archive within a byte cap")
    p.add_argument("--kind", choices=("klines", "markPriceKlines", "fundingRate", "aggTrades"), required=True)
    p.add_argument("--symbol", required=True); p.add_argument("--date"); p.add_argument("--month")
    p.add_argument("--timeframe", choices=("1m", "5m", "15m", "1h")); p.add_argument("--cache", default=str(DEFAULT_CACHE))
    p.add_argument("--max-archive-bytes", type=int, default=20 * 1024 * 1024)
    p.set_defaults(func=fetch_one)
    p = sub.add_parser("cache-info", help="List cached verified symbols, source ranges and provenance")
    p.add_argument("--cache", default=str(DEFAULT_CACHE)); p.set_defaults(func=cache_info)
    p = sub.add_parser("validate-sample", help="Check archives, resampling, funding, flow and causal timing")
    p.add_argument("--date", default="2026-10-05"); p.add_argument("--cache", default=str(DEFAULT_CACHE))
    p.add_argument("--sample-config", default=str(SAMPLE_CONFIG))
    p.add_argument("--write-report", default=None)
    p.set_defaults(func=validate_sample)
    p = sub.add_parser("show-5m", help="Print a verified 5m record with participation and provenance")
    p.add_argument("--symbol", default="BTCUSDT"); p.add_argument("--date", default="2026-10-05")
    p.add_argument("--timeframe", default="5m", choices=("1m", "5m", "15m", "1h"))
    p.add_argument("--limit", type=int, default=1); p.add_argument("--cache", default=str(DEFAULT_CACHE))
    p.set_defaults(func=show_record)
    p = sub.add_parser("orderflow", help="Reproduce real aggTrades volume profile and side summaries")
    p.add_argument("--symbol", default="XRPUSDT"); p.add_argument("--date", default="2026-10-05")
    p.add_argument("--cache", default=str(DEFAULT_CACHE)); p.set_defaults(func=orderflow)
    p = sub.add_parser("probe", help="Probe read-only public REST; optionally test one short public websocket read")
    p.add_argument("--timeout", type=float, default=8); p.add_argument("--websocket", action="store_true")
    p.set_defaults(func=probe)
    p = sub.add_parser("universe", help="Count public archive symbol folders; does not assert current eligibility")
    p.add_argument("--timeout", type=float, default=15); p.add_argument("--max-pages", type=int, default=10)
    p.set_defaults(func=universe)
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except (DataError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
