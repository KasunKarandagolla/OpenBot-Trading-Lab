"""Focused source-backed tests for Binance Vision parsing and causal availability."""
import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from binance_research_data import (  # noqa: E402
    DataError, asof_features, classify_specification, compare_candles,
    convert_funding_frame, convert_kline_frame,
    completed_asof, discover_archive_symbols, fetch_verified, funding_asof,
    funding_events_between, parse_aggregate_trades, parse_funding, parse_klines,
    probe_public_endpoints, resample_candles, summarize_aggregate_trades,
    validate_order_rules, verify_cached_archive, volume_profile,
)

FIX = ROOT / "tests/fixtures/binance_data"
PROVENANCE = json.loads((FIX / "provenance.json").read_text())


def fixture_receipt(name: str) -> dict:
    return next(x for x in PROVENANCE["fixtures"] if x["fixture"] == name)


def zipped_fixture(name: str) -> bytes:
    content = (FIX / name).read_bytes()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name.replace(".csv", ".csv"), content)
    return buffer.getvalue()


def pandas_source_frame(name: str):
    import pandas as pd
    return pd.read_csv(FIX / name)


def converter_source_record(name: str) -> dict:
    receipt = fixture_receipt(name)
    return {"symbol": receipt["symbol"], "venue": "binance", "kind": receipt["kind"],
            "timeframe": receipt.get("timeframe"), "url": receipt["source_url"],
            "checksum_url": receipt["source_url"] + ".CHECKSUM",
            "sha256": receipt["source_archive_sha256"],
            "official_sha256": receipt["source_archive_sha256"],
            "retrieved_at_utc": receipt["source_retrieved_at_utc"]}


class BackwardCompatibleConversion(unittest.TestCase):
    def test_real_kline_frame_keeps_freqtrade_shape_and_research_provenance(self):
        fixture = "BTCUSDT-5m-2026-10-05-first-hour.csv"
        standard, sidecar = convert_kline_frame(
            pandas_source_frame(fixture), converter_source_record(fixture),
            kind="klines", timeframe="5m")
        self.assertEqual(list(standard.columns),
                         ["date", "open", "high", "low", "close", "volume"])
        self.assertEqual(len(standard), 12)
        self.assertEqual(int(sidecar.loc[0, "open_time_ms"]), 1791158400000)
        self.assertEqual(int(sidecar.loc[0, "close_time_ms"]), 1791158699999)
        self.assertEqual(int(sidecar.loc[0, "available_at_ms"]), 1791158700000)
        self.assertEqual(sidecar.loc[0, "source_symbol"], "BTCUSDT")
        self.assertEqual(sidecar.loc[0, "source_venue"], "binance")
        self.assertEqual(sidecar.loc[0, "original_timeframe"], "5m")
        self.assertEqual(sidecar.loc[0, "source_sha256"],
                         fixture_receipt(fixture)["source_archive_sha256"])
        self.assertEqual(float(sidecar.loc[0, "taker_buy_base_volume"]), 380.486)
        self.assertAlmostEqual(float(sidecar.loc[0, "taker_sell_base_volume"]),
                               908.000 - 380.486)
        self.assertEqual(int(sidecar.loc[0, "trade_count"]), 18385)

    def test_mark_count_is_not_mislabeled_as_executed_trade_count(self):
        fixture = "BTCUSDT-markPriceKlines-1h-2026-10-05-first-2.csv"
        standard, sidecar = convert_kline_frame(
            pandas_source_frame(fixture), converter_source_record(fixture),
            kind="markPriceKlines", timeframe="1h")
        self.assertEqual(len(standard), 2)
        self.assertEqual(int(sidecar.loc[0, "source_count"]), 3600)
        self.assertTrue(sidecar.loc[0, "trade_count"] is None or
                        __import__("pandas").isna(sidecar.loc[0, "trade_count"]))
        self.assertIn("NOT_EXECUTED_TRADE_COUNT", sidecar.loc[0, "source_count_semantics"])
        self.assertEqual(float(sidecar.loc[0, "base_volume"]), 0.0)

    def test_funding_frame_preserves_published_millisecond_event_clock(self):
        fixture = "BTCUSDT-fundingRate-2026-10-first-2-events.csv"
        standard, sidecar = convert_funding_frame(
            pandas_source_frame(fixture), converter_source_record(fixture))
        self.assertEqual(list(standard.columns), ["date", "funding_rate"])
        self.assertEqual(list(sidecar["source_event_time_ms"]), [1790812800001, 1790841600005])
        self.assertEqual(list(sidecar["funding_interval_hours"]), [8, 8])
        self.assertEqual(sidecar.loc[0, "source_symbol"], "BTCUSDT")
        self.assertEqual(sidecar.loc[0, "source_checksum_url"],
                         fixture_receipt(fixture)["source_url"] + ".CHECKSUM")

    def test_conversion_rejects_wrong_coordinates_alignment_gaps_and_duplicates(self):
        fixture = "BTCUSDT-5m-2026-10-05-first-hour.csv"
        frame = pandas_source_frame(fixture)
        record = converter_source_record(fixture)
        with self.assertRaisesRegex(DataError, "timeframe"):
            convert_kline_frame(frame, record, kind="klines", timeframe="1h")
        unaligned = frame.copy()
        unaligned.loc[1, "open_time"] += 1
        with self.assertRaisesRegex(DataError, "timestamp alignment"):
            convert_kline_frame(unaligned, record, kind="klines", timeframe="5m")
        duplicate = frame.copy()
        duplicate.loc[1, "open_time"] = duplicate.loc[0, "open_time"]
        with self.assertRaisesRegex(DataError, "ascending and unique"):
            convert_kline_frame(duplicate, record, kind="klines", timeframe="5m")
        gap = frame.copy()
        gap.loc[2:, "open_time"] += 300_000
        gap.loc[2:, "close_time"] += 300_000
        with self.assertRaisesRegex(DataError, "cadence gap"):
            convert_kline_frame(gap, record, kind="klines", timeframe="5m")


class SourceBackedKlines(unittest.TestCase):
    def candles(self, timeframe):
        name = f"BTCUSDT-{timeframe}-2026-10-05-first-hour.csv"
        source = fixture_receipt(name)
        return parse_klines(zipped_fixture(name), symbol="BTCUSDT", timeframe=timeframe,
                            source_url=source["source_url"],
                            source_sha256=source["source_archive_sha256"],
                            source_retrieved_at_utc=source["source_retrieved_at_utc"])

    def test_reconstructs_real_source_hour_across_all_supported_steps(self):
        one = self.candles("1m")
        five = self.candles("5m")
        fifteen = self.candles("15m")
        hour = self.candles("1h")
        self.assertTrue(compare_candles(resample_candles(one, "1m", "5m"), five)["exact_match"])
        self.assertTrue(compare_candles(resample_candles(five, "5m", "15m"), fifteen)["exact_match"])
        self.assertTrue(compare_candles(resample_candles(fifteen, "15m", "1h"), hour)["exact_match"])

    def test_resampling_rejects_mixed_market_identity(self):
        from dataclasses import replace
        rows = self.candles("1m")
        rows[1] = replace(rows[1], symbol="ETHUSDT")
        with self.assertRaisesRegex(DataError, "one Binance USD-M kline symbol"):
            resample_candles(rows, "1m", "5m")

    def test_preserves_base_quote_taker_volume_trade_count_and_units(self):
        candle = self.candles("5m")[0]
        sidecar = candle.research_row()
        self.assertEqual(sidecar["source_symbol"], "BTCUSDT")
        self.assertEqual(sidecar["source_venue"], "binance")
        self.assertEqual(sidecar["original_timeframe"], "5m")
        self.assertEqual(sidecar["source_retrieved_at_utc"],
                         fixture_receipt("BTCUSDT-5m-2026-10-05-first-hour.csv")["source_retrieved_at_utc"])
        self.assertEqual(Decimal(sidecar["taker_sell_base_volume"]),
                         Decimal(sidecar["base_volume"]) - Decimal(sidecar["taker_buy_base_volume"]))
        self.assertEqual(Decimal(sidecar["taker_sell_quote_volume"]),
                         Decimal(sidecar["quote_volume"]) - Decimal(sidecar["taker_buy_quote_volume"]))
        self.assertGreater(sidecar["trade_count"], 0)
        self.assertEqual(sidecar["available_at_ms"], sidecar["close_time_ms"] + 1)

    def test_freqtrade_output_remains_six_ohlcv_fields(self):
        row = self.candles("5m")[0].freqtrade_row()
        self.assertEqual(set(row), {"date", "open", "high", "low", "close", "volume"})

    def test_cadence_duplicate_and_ohlc_corruption_fail_closed(self):
        first = self.candles("5m")[0]
        # Repeated source timestamp is rejected before downstream aggregation.
        with self.assertRaisesRegex(DataError, "unsorted or duplicated"):
            from binance_research_data import validate_cadence
            validate_cadence([first, first], "5m")
        row = (FIX / "BTCUSDT-5m-2026-10-05-first-hour.csv").read_text().splitlines()
        fields = row[1].split(",")
        fields[2] = "1"  # high below the source open/close
        row[1] = ",".join(fields)
        bad = io.BytesIO()
        with zipfile.ZipFile(bad, "w") as archive:
            archive.writestr("bad.csv", "\n".join(row) + "\n")
        with self.assertRaisesRegex(DataError, "OHLC"):
            parse_klines(bad.getvalue(), symbol="BTCUSDT", timeframe="5m")

    def test_asof_features_never_expose_incomplete_hour_or_four_hour(self):
        fixture = "BTCUSDT-1h-2026-10-05-first-four-hours.csv"
        source = fixture_receipt(fixture)
        hour = parse_klines(zipped_fixture(fixture), symbol="BTCUSDT", timeframe="1h",
                            source_url=source["source_url"],
                            source_sha256=source["source_archive_sha256"],
                            source_retrieved_at_utc=source["source_retrieved_at_utc"])
        four = resample_candles(hour, "1h", "4h")
        start = hour[0].open_time_ms
        self.assertEqual(completed_asof(hour, start + 3_599_999), [])
        self.assertEqual(len(completed_asof(hour, start + 3_600_000)), 1)
        out = asof_features({"1h": hour, "4h": four}, start + 3_600_000)
        self.assertEqual(out["timeframes"]["1h"]["open_time_ms"], start)
        self.assertEqual(out["timeframes"]["4h"]["status"], "NO_COMPLETED_BAR")
        out = asof_features({"1h": hour, "4h": four}, start + 14_400_000)
        self.assertEqual(out["timeframes"]["4h"]["available_at_ms"], start + 14_400_000)


class SourceBackedFundingAndTrades(unittest.TestCase):
    def test_funding_published_millisecond_clocks_and_holding_assignment(self):
        fixture = "BTCUSDT-fundingRate-2026-10-first-2-events.csv"
        source = fixture_receipt(fixture)
        events = parse_funding(zipped_fixture(fixture), symbol="BTCUSDT",
                               source_url=source["source_url"],
                               source_sha256=source["source_archive_sha256"],
                               source_retrieved_at_utc=source["source_retrieved_at_utc"])
        self.assertEqual([e.calc_time_ms for e in events], [1790812800001, 1790841600005])
        self.assertEqual(events[0].source_retrieved_at_utc, source["source_retrieved_at_utc"])
        self.assertEqual(funding_asof(events, events[0].calc_time_ms), events[:1])
        # Entry equality is excluded as boundary-order is not established; exit is included.
        self.assertEqual(funding_events_between(events, events[0].calc_time_ms,
                                                events[1].calc_time_ms), events[1:])

    def test_real_aggtrade_rows_keep_ids_units_and_aggressor_side(self):
        fixture = "XRPUSDT-aggTrades-2026-10-05-first-500.csv"
        trades = list(parse_aggregate_trades(
            zipped_fixture(fixture), date="2026-10-05"))
        self.assertEqual(len(trades), 500)
        self.assertLess(trades[0].agg_trade_id, trades[-1].agg_trade_id)
        self.assertEqual(trades[0].time_ms, 1791158400003)
        self.assertTrue(trades[0].buyer_is_maker)
        self.assertFalse(trades[2].buyer_is_maker)
        self.assertGreater(trades[0].quantity, 0)  # source quantity is XRP for XRPUSDT

    def test_profile_is_transparent_and_ties_choose_lower_price(self):
        result = volume_profile({Decimal("1.0"): Decimal("4"),
                                 Decimal("1.1"): Decimal("4"),
                                 Decimal("1.2"): Decimal("2")})
        self.assertEqual(result["poc"], "1.0")
        self.assertEqual(result["method"].startswith("POC=max volume"), True)
        self.assertEqual(result["total_base_volume"], "10")
        self.assertEqual(result["value_area_fraction_target"], "0.70")

    def test_real_excerpt_orderflow_uses_true_buyer_maker_side(self):
        fixture = "XRPUSDT-aggTrades-2026-10-05-first-500.csv"
        source = fixture_receipt(fixture)
        summary = summarize_aggregate_trades(
            zipped_fixture(fixture), symbol="XRPUSDT", date="2026-10-05",
            source_url=source["source_url"], source_sha256=source["source_archive_sha256"],
            source_retrieved_at_utc=source["source_retrieved_at_utc"])
        self.assertEqual(summary["rows"], 500)
        self.assertEqual(summary["source_retrieved_at_utc"], source["source_retrieved_at_utc"])
        self.assertEqual(summary["duplicate_aggregate_ids"], 0)
        self.assertEqual(summary["side_convention"].split(";")[0],
                         "buyer_is_maker=true => seller taker/aggressive sell")
        self.assertNotEqual(summary["cumulative_volume_delta_base"], "0")
        self.assertIn("poc", summary["volume_profile"])

    def test_aggregate_trade_duplicate_and_sequence_gaps_are_reported(self):
        rows = [
            "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
            "1,1.0,2,100,100,1791158400001,true",
            "1,1.0,3,100,100,1791158400002,false",
            "3,1.1,4,102,103,1791158400003,false",
        ]
        body = io.BytesIO()
        with zipfile.ZipFile(body, "w") as archive:
            archive.writestr("trades.csv", "\n".join(rows) + "\n")
        summary = summarize_aggregate_trades(body.getvalue(), symbol="XRPUSDT",
            date="2026-10-05", source_url="test fixture", source_sha256="test")
        self.assertEqual(summary["duplicate_aggregate_ids"], 1)
        self.assertEqual(summary["aggregate_id_gaps"], 1)
        self.assertEqual(summary["constituent_trade_id_gaps"], 1)
        self.assertEqual(summary["overlapping_constituent_id_ranges"], 1)


class AccessAndQualification(unittest.TestCase):
    def test_committed_source_excerpts_match_their_recorded_hashes(self):
        for item in PROVENANCE["fixtures"]:
            path = FIX / item["fixture"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["fixture_excerpt_sha256"])

    def test_checksum_validates_and_rejects_modified_content(self):
        data = b"verified source bytes"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.zip"
            path.write_bytes(data)
            verify_cached_archive(path, hashlib.sha256(data).hexdigest())
            path.write_bytes(data + b" changed")
            with self.assertRaisesRegex(DataError, "checksum mismatch"):
                verify_cached_archive(path, hashlib.sha256(data).hexdigest())

    def test_cache_reuse_is_content_verified_and_never_replaces_corruption(self):
        data = b"small verified archive"
        archive_url = "https://data.binance.vision/sample.zip"
        checksum_url = archive_url + ".CHECKSUM"
        checksum = f"{hashlib.sha256(data).hexdigest()} sample.zip\n".encode()
        calls = []

        class Response(io.BytesIO):
            status = 200
            headers = {"Content-Length": str(len(data))}
            def geturl(self): return self.url
            def __enter__(self): return self
            def __exit__(self, *exc): self.close()

        def fake_open(request, timeout=0):
            url = request.full_url
            calls.append(url)
            response = Response(checksum if url == checksum_url else data)
            response.url = url
            return response

        with tempfile.TemporaryDirectory() as temp, patch("urllib.request.urlopen", side_effect=fake_open):
            first = fetch_verified(archive_url, Path(temp))
            second = fetch_verified(archive_url, Path(temp))
            self.assertFalse(first["cache_hit"])
            self.assertTrue(second["cache_hit"])
            self.assertEqual(calls.count(archive_url), 1)
            target = Path(first["cache_path"])
            target.write_bytes(b"tampered")
            with self.assertRaisesRegex(DataError, "differ from current official checksum"):
                fetch_verified(archive_url, Path(temp))
            self.assertEqual(target.read_bytes(), b"tampered")

    def test_restricted_public_source_is_reported_blocked(self):
        def blocked(request, timeout=0):
            raise urllib.error.HTTPError(request.full_url, 451, "restricted", {}, io.BytesIO(b"policy"))
        with patch("urllib.request.urlopen", side_effect=blocked):
            result = probe_public_endpoints(timeout=1)
        self.assertEqual(len(result), 5)
        self.assertTrue(all(x["status"] == "BLOCKED" and x["http_status"] == 451 for x in result))

    def test_missing_archive_checksum_is_not_treated_as_data(self):
        def missing(request, timeout=0):
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, io.BytesIO(b""))
        with tempfile.TemporaryDirectory() as temp, patch("urllib.request.urlopen", side_effect=missing):
            with self.assertRaisesRegex(DataError, "HTTP 404"):
                fetch_verified("https://data.binance.vision/missing.zip", Path(temp))

    def test_unqualified_historical_contract_specs_fail_closed(self):
        self.assertEqual(classify_specification(None, "2026-01-01"), "UNQUALIFIED_EXECUTION_METADATA")
        current_only = {"status": "VERIFIED", "effective_from": "2026-11-05T00:00:00Z"}
        with self.assertRaisesRegex(DataError, "UNQUALIFIED_EXECUTION_METADATA"):
            validate_order_rules(current_only, evaluation_start="2026-01-01",
                                 price=Decimal("100"), quantity=Decimal("1"))

    def test_verified_tick_step_and_minimum_notional_rules(self):
        spec = {"status": "VERIFIED", "effective_from": "2025-01-01T00:00:00Z",
                "time_qualified": True,
                "source_url": "https://official.example/metadata",
                "source_sha256": "dated-source-hash",
                "tick_size": "0.1", "quantity_step": "0.01",
                "minimum_quantity": "0.01", "maximum_quantity": "100",
                "minimum_notional": "10", "contract_size": "1"}
        self.assertEqual(validate_order_rules(spec, evaluation_start="2026-01-01",
                          price=Decimal("100"), quantity=Decimal("0.1"))["notional"], "10.0")
        with self.assertRaisesRegex(DataError, "tick"):
            validate_order_rules(spec, evaluation_start="2026-01-01",
                                 price=Decimal("100.05"), quantity=Decimal("0.1"))
        with self.assertRaisesRegex(DataError, "minimum"):
            validate_order_rules(spec, evaluation_start="2026-01-01",
                                 price=Decimal("100"), quantity=Decimal("0.01"))

    def test_archive_paths_require_documented_dataset_coordinates(self):
        with self.assertRaises(ValueError):
            from binance_research_data import archive_url
            archive_url("klines", "BTCUSDT", date="2026-10-05", timeframe="4h")
        with self.assertRaises(ValueError):
            from binance_research_data import archive_url
            archive_url("fundingRate", "BTCUSDT", date="2026-10-05")


if __name__ == "__main__":
    unittest.main()
