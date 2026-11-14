"""Synthetic adversarial contracts plus immutable Session 1 source fixtures.

Synthetic metadata and tail names below are never live qualification evidence.
"""
import copy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.basis import BasisMCP, tool_object
from researcher.cohorts import independent_tail_cohort
from researcher.contracts import ContractError, Evidence, Fidelity, digest, encode
from researcher.discovery import scan_now
from researcher.inventory import (INVENTORY_URL, InventorySources, OfficialBinanceInventory,
    OwnerOfficialSnapshot, json_document, official_snapshot, provisional_inventory)
from researcher.market import OfficialMarketPulse, normalize_market
from researcher.nominations import Nomination, NominationRouter
from researcher.screening import (BasisScreenSource, CapabilityRegistry, PartitionEngine, RequestBudget,
    closed_cutoff, coherent_observations, normalize_screen, partitions)
from researcher.settings import ROOT, load_config, validate_config
from researcher.transport import ProviderError, PublicHTTP, safe_retry_after

AT = "2026-11-13T05:17:00+00:00"
CUTOFF = "2026-11-13T05:00:00+00:00"
FIX = ROOT / "tests/fixtures/session1"


def setUpModule():
    (ROOT / "work").mkdir(exist_ok=True)


def provisional(names=("BTCUSDT", "ETHUSDT")):
    return provisional_inventory(names, source_id="SYNTHETIC_TEST", source_url="urn:test",
        captured_at=CUTOFF, received_at=AT, content_hash="synthetic")


def official_row(name="BTCUSDT"):
    return {"symbol": name, "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT",
        "status": "TRADING", "underlyingType": "COIN", "onboardDate": 1600000000000,
        "filters": [{"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                    {"filterType": "LOT_SIZE", "minQty": "0.001", "maxQty": "1000", "stepSize": "0.001"}]}


def source_manifest(body):
    return {"schema_version": "openbot.inventory-source.v1", "source_kind": "OWNER_OFFICIAL_SNAPSHOT",
        "source_url": INVENTORY_URL, "captured_at_utc": CUTOFF, "authorized_capture": True,
        "lawful_source_statement": "SYNTHETIC CONTRACT TEST ONLY", "complete_exchange_info": True,
        "payload_sha256": digest(body), "max_age_seconds": 86400}


def official(rows=None, mutate_manifest=None):
    payload = {"symbols": rows if rows is not None else [official_row()]}
    body = json.dumps(payload).encode()
    manifest = source_manifest(body)
    if mutate_manifest:
        mutate_manifest(manifest)
    return official_snapshot(payload, manifest=manifest, content_hash=digest(body), received_at=AT)


def pack(tf="1h"):
    return CapabilityRegistry(load_config()).packs["CORE_1H" if tf == "1h" else "CORE_15M"]


def metadata():
    return {"response_bytes": 100, "elapsed_ms": 10, "response_sha256": "synthetic_source_hash",
        "received_at_utc": AT, "schema_sha256": "synthetic_schema_hash"}


def response(names=("BTCUSDT", "ETHUSDT"), tf="1h", extra=()):
    names = tuple(names) + tuple(extra)
    width = 3600 if tf == "1h" else 900
    timestamp = int(datetime.fromisoformat(closed_cutoff(AT, tf)).timestamp()) - width
    return {"exchange": "binance", "market": "futures", "quote": "USDT", "timeframe": tf,
        "screened": len(names), "evaluated": len(names), "matched": len(names),
        "couldNotEvaluate": 0, "returned": len(names), "truncated": False,
        "rules": [{"id": "width", "left": {"kind": "formula", "expression": pack(tf).expression},
                   "operator": "atOrAbove", "right": {"kind": "constant", "value": 0}}],
        "results": [{"symbol": n, "last": 100, "observationTime": timestamp,
            "values": [{"ruleId": "width", "left": .01, "right": 0, "matched": True}]} for n in names]}


class Source:
    def __init__(self, fn=None):
        self.calls = []
        self.fn = fn

    def screen(self, names, spec):
        self.calls.append((names, spec))
        return (self.fn(names, spec) if self.fn else response(names, spec.timeframe)), metadata()


def budget(calls=8, retries=2):
    return RequestBudget(calls, retry_calls=min(retries, calls), interval_seconds=0)


class InventoryContracts(unittest.TestCase):
    def test_exact_official_identity_and_no_multiplier_guess(self):
        snapshot = official([official_row("1000PEPEUSDT")])
        self.assertEqual(snapshot.mode, "VERIFIED_INVENTORY")
        item = snapshot.instruments[0]
        self.assertEqual(item.native_symbol, "1000PEPEUSDT")
        self.assertIsNone(item.contract_multiplier)
        self.assertIn("contract_multiplier", item.unsupported_fields)
        self.assertEqual(item.identity_status, "EXCHANGE_VERIFIED")
        self.assertEqual(item.tick_size, Decimal("0.01"))
        self.assertEqual(item.trading_status, "TRADING")

    def test_missing_essential_fields_retains_provisional_member(self):
        row = official_row(); row.pop("marginAsset"); row.pop("underlyingType"); row.pop("filters")
        result = official([row])
        self.assertEqual(result.mode, "PARTIAL_INVENTORY")
        self.assertIsNone(result.report()["eligible_contracts"])
        self.assertEqual(result.provisional_symbols, ("BTCUSDT",))
        self.assertIn("settlement", provisional().instruments[0].unsupported_fields)

    def test_unknown_classification_prevents_complete_universe_claim(self):
        row = official_row(); row["underlyingType"] = "UNKNOWN_OR_NONCRYPTO"
        self.assertEqual(official([row]).mode, "PARTIAL_INVENTORY")

    def test_suffix_is_not_eligibility_and_status_is_required(self):
        rows = [official_row("SPOTLIKEUSDT"), official_row("SETTLEUSDT"), official_row("DELISTUSDT")]
        rows[0]["contractType"] = "CURRENT_QUARTER"
        rows[1]["marginAsset"] = "USDC"
        rows[2]["status"] = "CLOSE"
        result = official(rows)
        self.assertEqual(len(result.excluded), 3)
        self.assertFalse(result.eligible_symbols)

    def test_owner_attestation_hash_source_and_capture_are_required(self):
        mutations = [lambda m: m.update(authorized_capture=False), lambda m: m.pop("captured_at_utc"),
            lambda m: m.update(source_url="https://unqualified.test/list"),
            lambda m: m.update(payload_sha256="wrong"), lambda m: m.update(lawful_source_statement="")]
        for mutate in mutations:
            with self.subTest(mutate=mutate), self.assertRaises(ContractError):
                official(mutate_manifest=mutate)

    def test_stale_inventory_and_incomplete_snapshot_are_partial(self):
        stale = official(mutate_manifest=lambda m: m.update(captured_at_utc="2026-11-11T05:00:00Z"))
        self.assertEqual(stale.mode, "PARTIAL_INVENTORY")
        self.assertEqual(stale.freshness, "STALE")
        self.assertFalse(stale.eligible_symbols)
        incomplete = official(mutate_manifest=lambda m: m.update(complete_exchange_info=False))
        self.assertEqual(incomplete.mode, "PARTIAL_INVENTORY")
        self.assertEqual(len(incomplete.eligible_symbols), 1)

    def test_cached_inventory_rechecks_freshness_at_scan_time(self):
        inventory = official()
        self.assertEqual(inventory.at("2026-11-15T05:17:00Z").mode, "PARTIAL_INVENTORY")
        self.assertFalse(inventory.at("2026-11-15T05:17:00Z").eligible_symbols)
        with self.assertRaisesRegex(ContractError, "INVENTORY_NOT_KNOWN_AT_SCAN"):
            inventory.at(CUTOFF)

    def test_future_capture_and_extended_ttl_rejected(self):
        for mutation in [lambda m: m.update(captured_at_utc="2026-11-14T05:00:00Z"),
                         lambda m: m.update(max_age_seconds=86401)]:
            with self.assertRaises(ContractError):
                official(mutate_manifest=mutation)

    def test_duplicates_bad_tick_and_quantity_are_rejected(self):
        with self.assertRaises(ContractError):
            official([official_row(), official_row()])
        for key, value in [("tickSize", "NaN"), ("tickSize", "0")]:
            row = official_row(); row["filters"][0][key] = value
            with self.assertRaises(ContractError):
                official([row])
        row = official_row(); row["filters"][1]["minQty"] = "2000"
        with self.assertRaises(ContractError):
            official([row])

    def test_owner_files_are_read_only_and_hash_bound(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as directory:
            raw = Path(directory) / "exchangeInfo.json"
            provenance = Path(directory) / "source.json"
            body = json.dumps({"symbols": [official_row()]}).encode()
            raw.write_bytes(body); provenance.write_text(json.dumps(source_manifest(body)))
            result = OwnerOfficialSnapshot(raw, provenance).load(AT)
            self.assertEqual(result.mode, "VERIFIED_INVENTORY")
            self.assertEqual(raw.read_bytes(), body)
            raw.write_bytes(body + b" ")
            with self.assertRaises(ContractError):
                OwnerOfficialSnapshot(raw, provenance).load(AT)

    def test_duplicate_json_keys_and_nonfinite_are_rejected(self):
        for body in [b'{"symbols":[],"symbols":[]}', b'{"x":NaN}', b'garbage']:
            with self.assertRaises(ContractError):
                json_document(body)

    def test_recorded_denial_stops_inventory_and_market_without_http(self):
        http = PublicHTTP()
        with patch.object(http, "request") as request:
            for adapter, fn in [(OfficialBinanceInventory(http), lambda a: a.load(AT)),
                                (OfficialMarketPulse(http), lambda a: a.read(provisional()))]:
                with self.assertRaisesRegex(ProviderError, "RECORDED_BINANCE_ACCESS_DENIAL"):
                    fn(adapter)
            request.assert_not_called()

    def test_source_registration_does_not_qualify_third_party_strings(self):
        registry = InventorySources()
        with self.assertRaises(ContractError):
            registry.load("unqualified_third_party", AT)


class PartitionAndCoverage(unittest.TestCase):
    def test_exact_full_partition_and_footer(self):
        names = tuple(f"ASSET{i}USDT" for i in range(57))
        self.assertEqual([len(p) for p in partitions(names)], [50, 7])
        self.assertEqual(tuple(n for p in partitions(names) for n in p), names)
        for bad, size in [(names + names[:1], 50), (names, 51), (names, 0)]:
            with self.assertRaises(ContractError):
                partitions(bad, size)

    def test_actual_footer_filler_exclusion_preserves_precision_and_fidelity(self):
        source = tool_object(json.loads((FIX / "screen_finite_footer.json").read_text())["result"])
        meta = json.loads((FIX / "screen_finite_footer.receipt.json").read_text())
        receipt, readings = normalize_screen(("BTCUSDT", "ETHUSDT"), source,
            {**metadata(), "response_sha256": meta["response_sha256"], "received_at_utc": meta["received_at_utc"]},
            pack=pack(), instruments={i.native_symbol: i for i in provisional().instruments}, cutoff=CUTOFF)
        self.assertEqual(len(receipt.filler_symbols), 18)
        self.assertEqual(len(readings), 2)
        self.assertEqual(readings[0]["fidelity"], "EXACT_REPORTED")
        self.assertEqual(readings[0]["independent_source_accuracy"], "UNVERIFIED")
        self.assertFalse(readings[0]["complete"])
        self.assertEqual(readings[0]["precision_absolute"], "0.00005")

    def test_50_and_footer_engine_never_invents_tail_qualification(self):
        names = tuple(f"ASSET{i}USDT" for i in range(57))
        source = Source()
        # Synthetic registration only; not a live capability promotion.
        result = PartitionEngine(source, budget()).run(provisional(names), replace(pack(), supported_symbols=names), CUTOFF)
        self.assertEqual([len(n) for n, _ in source.calls], [50, 7])
        self.assertEqual(len(result["evaluated_symbols"]), 57)
        self.assertEqual(result["valid_remote_core_evaluated"], 0)
        self.assertEqual(result["inventory_mode"], "PARTIAL_INVENTORY")

    def test_missing_symbol_and_unsupported_symbol_are_distinct(self):
        source = Source(lambda names, p: response(names[:1]))
        result = PartitionEngine(source, budget()).run(provisional(("BTCUSDT", "ETHUSDT", "NEWUSDT")), pack(), CUTOFF)
        self.assertEqual(result["requested_symbols"], ["BTCUSDT", "ETHUSDT"])
        self.assertEqual(result["not_requested_symbols"], ["NEWUSDT"])
        self.assertEqual(result["missing_symbols"], ["ETHUSDT"])
        self.assertIn("UNVERIFIED_PROVIDER_SYMBOL_SCOPE", result["failed_symbols"].values())
        self.assertFalse(result["zero_opportunities_established"])

    def test_truncation_is_bisected_with_a_finite_recovery_budget(self):
        def truncate(names, p):
            data = response(names)
            if len(names) > 1:
                data["truncated"] = True
            return data
        source = Source(truncate)
        result = PartitionEngine(source, budget()).run(provisional(), pack(), CUTOFF)
        self.assertEqual(len(source.calls), 3)
        self.assertEqual(result["truncated_attempts"], 1)
        self.assertEqual(len(result["evaluated_symbols"]), 2)
        self.assertEqual(len(result["attempts"]), 3)

    def test_hidden_truncation_is_rejected(self):
        def hidden(names, p):
            data = response(names); data["results"].pop(); data["returned"] -= 1
            return data
        result = PartitionEngine(Source(hidden), budget()).run(provisional(), pack(), CUTOFF)
        self.assertFalse(result["evaluated_symbols"])
        self.assertEqual(set(result["failed_symbols"].values()), {"SCREEN_HIDDEN_TRUNCATION_OR_COUNTS"})

    def test_http200_tool_error_isolated_and_other_timeframe_survives(self):
        class Fault(Source):
            def screen(self, names, p):
                if p.timeframe == "1h":
                    raise ProviderError("MCP_TOOL_ERROR", metadata())
                return super().screen(names, p)
        b = budget()
        engine = PartitionEngine(Fault(), b)
        failed = engine.run(provisional(), pack(), CUTOFF)
        recovered = engine.run(provisional(), pack("15m"), closed_cutoff(AT, "15m"))
        self.assertFalse(failed["evaluated_symbols"])
        self.assertEqual(len(recovered["evaluated_symbols"]), 2)
        self.assertEqual(b.retries, 2)

    def test_denial_and_quota_stop_later_partitions_without_retry(self):
        for code in ["HTTP_403", "HTTP_451", "HTTP_429"]:
            class Denied(Source):
                def screen(self, names, p):
                    self.calls.append(names)
                    raise ProviderError(code, metadata())
            source = Denied(); b = budget()
            result = PartitionEngine(source, b, partition_size=1).run(provisional(), pack(), CUTOFF)
            self.assertEqual(len(source.calls), 1)
            self.assertEqual(len(result["failed_symbols"]), 2)
            self.assertFalse(result["evaluated_symbols"])
            self.assertEqual(b.stopped_reason, code)
            self.assertEqual(result["requested_symbols"], ["BTCUSDT"])

    def test_request_and_byte_budgets_do_not_silently_omit_names(self):
        for b in [budget(calls=1, retries=0), RequestBudget(8, interval_seconds=0, max_response_bytes=50)]:
            source = Source()
            result = PartitionEngine(source, b, partition_size=1).run(provisional(), pack(), CUTOFF)
            self.assertEqual(len(source.calls), 1)
            self.assertEqual(result["evaluated_symbols"], ["BTCUSDT"])
            self.assertIn("ETHUSDT", result["failed_symbols"])

    def test_serial_pacing_is_bounded(self):
        clock = iter([0, .25, 1])
        sleeps = []
        b = RequestBudget(interval_seconds=1, clock=lambda: next(clock), sleeper=sleeps.append)
        b.acquire(); b.acquire()
        self.assertEqual(sleeps, [.75])

    def test_old_or_after_frozen_cutoff_cannot_join(self):
        for shift, reason in [(-3600, "STALE_SOURCE_CUTOFF"), (3600, "INVALID_SCALAR_OR_CLOCK")]:
            def shifted(names, p):
                data = response(names)
                for r in data["results"]:
                    r["observationTime"] += shift
                return data
            result = PartitionEngine(Source(shifted), budget()).run(provisional(), pack(), CUTOFF)
            self.assertFalse(result["evaluated_symbols"])
            self.assertEqual(set(result["failed_symbols"].values()), {reason})

    def test_15m_has_its_own_frozen_cutoff_and_no_extra_shift(self):
        result = PartitionEngine(Source(), budget()).run(provisional(), pack("15m"), closed_cutoff(AT, "15m"))
        self.assertEqual(result["source_cutoffs"]["BTCUSDT"], "2026-11-13T05:15:00+00:00")
        self.assertEqual(result["observations"][0]["window_start_utc"], CUTOFF)
        with self.assertRaisesRegex(ContractError, "INCOHERENT_TEMPORAL_JOIN"):
            coherent_observations(result["observations"], timeframe="1h", cutoff=CUTOFF)

    def test_wrong_formula_nonfinite_missing_and_malformed_fail_closed(self):
        mutations = [lambda d: d["rules"][0]["left"].update(expression="atr(14)"),
            lambda d: d["results"][0]["values"][0].update(left="NaN"),
            lambda d: d["results"][0].update(values=[]),
            lambda d: d.update(results=[None]), lambda d: d["rules"][0].update(left=None)]
        for mutate in mutations:
            def broken(names, p):
                data = response(names); mutate(data); return data
            result = PartitionEngine(Source(broken), budget()).run(provisional(), pack(), CUTOFF)
            self.assertIn("BTCUSDT", result["failed_symbols"])
            self.assertFalse(result["zero_opportunities_established"])

    def test_untrusted_error_text_is_not_logged(self):
        class Bad(Source):
            def screen(self, names, p):
                raise ProviderError("private-key-and-session-canary")
        result = PartitionEngine(Bad(), budget()).run(provisional(), pack(), CUTOFF)
        self.assertNotIn("private-key-and-session-canary", encode(result))

    def test_malformed_diagnostic_counts_cannot_log_arbitrary_provider_text(self):
        def bad_count(names, p):
            data = response(names); data["evaluated"] = "private-provider-text-canary"
            return data
        result = PartitionEngine(Source(bad_count), budget()).run(provisional(), pack(), CUTOFF)
        self.assertFalse(result["evaluated_symbols"])
        self.assertNotIn("private-provider-text-canary", encode(result))

    def test_retry_after_preserves_delay_but_not_arbitrary_header_text(self):
        self.assertEqual(safe_retry_after("60"), "60")
        self.assertEqual(safe_retry_after("Fri, 13 Nov 2026 06:00:00 GMT"), "Fri, 13 Nov 2026 06:00:00 GMT")
        self.assertIsNone(safe_retry_after("private-header-canary"))


class MarketAndRouting(unittest.TestCase):
    def test_market_snapshot_is_not_closed_bar_structural_coverage(self):
        now = int(datetime.fromisoformat(AT).timestamp() * 1000)
        rows = [{"symbol": "BTCUSDT", "time": now, "bidPrice": "100", "askPrice": "101"}]
        result = normalize_market(rows, kind="book", inventory=provisional(), captured_at=AT, response_hash="test")
        self.assertFalse(result["synchronized_closed_bar_cross_section"])
        self.assertEqual(result["missing_symbols"], ["ETHUSDT"])
        self.assertFalse(result["observations"][0]["structural_coverage"])
        rows[0]["time"] += 1
        result = normalize_market(rows, kind="book", inventory=provisional(), captured_at=AT, response_hash="test")
        self.assertIn("BTCUSDT", result["failed_symbols"])

    def test_tail_uses_independent_liquidity_and_preserves_exact_multiplier(self):
        rows = [official_row(f"SYNTH{i}USDT") for i in range(100)]
        rows[0]["contractMultiplier"] = "1000"
        rows[1]["onboardDate"] = int(datetime.fromisoformat(CUTOFF).timestamp() * 1000) - 86400000
        inventory = official(rows)
        ticker = {"kind": "ticker", "observations": [{"native_symbol": i.native_symbol,
            "source_scope": "OFFICIAL_BINANCE_USDM", "received_at_utc": AT,
            "values": {"quoteVolume": index + 1, "priceChangePercent": -10}} for index, i in enumerate(inventory.instruments)]}
        first = independent_tail_cohort(inventory, ticker, as_of=AT)
        for row in ticker["observations"]:
            row["values"]["priceChangePercent"] = 10
        second = independent_tail_cohort(inventory, ticker, as_of=AT)
        self.assertEqual(first, second)
        self.assertEqual(len(first["full_partition"]), 50)
        self.assertEqual(len(first["footer_partition"]), 7)
        self.assertIn("SYNTH0USDT", first["verified_multiplier_members"])
        self.assertIn("SYNTH1USDT", first["verified_young_members"])
        self.assertFalse(first["provider_top_lists_used"])

    def test_provisional_inventory_cannot_fabricate_quiet_tail(self):
        with self.assertRaises(ContractError):
            independent_tail_cohort(provisional(), {"kind": "ticker"}, as_of=AT)

    def test_all_routes_union_without_context_veto_or_readiness_claim(self):
        inventory = provisional()
        evidence = Evidence("e1", inventory.instruments[0], "TEST_ONLY", Decimal(1), "TEST",
            "1h", "2026-11-13T04:00:00Z", CUTOFF, AT, None, AT, "test", "TEST_SCOPE",
            "schema", "source", None, False, "SUPPORTED", Fidelity.PROXY_ONLY, "CLOSED_CURRENT")
        n = Nomination("BTCUSDT", "QUIET_TAIL", ("F4",), ("M05",), "test", ("e1",), CUTOFF,
            AT, AT, "PROXY_ONLY", "PROXY_ONLY", "Synthetic question only", direction="BEARISH")
        outputs = []
        for context in ["BULLISH", "BEARISH", "UNKNOWN"]:
            # Context only exists in downstream agenda; not passed to router.
            router = NominationRouter(load_config(), inventory)
            router.add(n, {"e1": evidence}); router.add(n, {"e1": evidence})
            outputs.append(router.union())
            self.assertEqual(len(router.coverage()), 11)
        self.assertEqual(outputs[0], outputs[1]); self.assertEqual(outputs[1], outputs[2])
        with self.assertRaises(ContractError):
            replace(n, stage="READY_FOR_DEEP")
        with self.assertRaises(ContractError):
            router.add(replace(n, route="SPECIALIST"), {"e1": evidence})
        with self.assertRaises(ContractError):
            router.add(replace(n, method_ids=("M15",)), {"e1": evidence})
        with self.assertRaises(ContractError):
            router.add(n, {})
        with self.assertRaises(ContractError):
            router.add(replace(n, source_id="wrong-provider"), {"e1": evidence})


class OnDemandIntegration(unittest.TestCase):
    def test_capability_scope_is_bound_to_existing_hashed_source_evidence(self):
        config = load_config()
        config["external_discovery"]["observed_symbols"].append("UNPROVENUSDT")
        with self.assertRaisesRegex(ContractError, "UNPROVEN_OBSERVATION_SCOPE"):
            validate_config(config)
        config = load_config()
        config["external_discovery"]["arithmetic_sha256"] = "wrong"
        with self.assertRaisesRegex(ContractError, "QUALIFICATION_EVIDENCE_DRIFT"):
            validate_config(config)

    def test_real_client_adapter_builds_exact_readonly_payload(self):
        client = BasisMCP(qualification=True)
        client.tools = {t["name"]: t for t in json.loads((FIX / "read_tools.json").read_text())}
        client.http.receipts = [metadata()]
        with patch.object(client, "call", return_value=response()) as call:
            BasisScreenSource(client).screen(("BTCUSDT", "ETHUSDT"), pack())
        args = call.call_args.args
        self.assertEqual(args[0], "screener_run")
        self.assertEqual(args[1]["manualSymbols"], ["BTCUSDT", "ETHUSDT"])
        self.assertEqual(args[1]["universeSize"], 20)
        self.assertEqual(args[1]["limit"], 60)

    def test_on_demand_two_timeframes_truthful_partial_and_no_orders(self):
        client = BasisMCP(qualification=True)
        client.tools = {t["name"]: t for t in json.loads((FIX / "read_tools.json").read_text())}
        client.http.receipts = [metadata()]
        def call(tool, arguments):
            return response(arguments["manualSymbols"], arguments["timeframe"])
        with patch.object(client, "connect"), patch.object(client, "call", side_effect=call):
            result = scan_now(client=client, inventory=provisional(), started_at=AT, budget=budget())
        self.assertEqual(result["operation_status"], "PARTIAL")
        self.assertEqual(len(result["observations"]), 4)
        self.assertEqual(result["coverage"]["valid_remote_core_evaluated"], 0)
        self.assertIsNone(result["coverage"]["eligible_contracts"])
        self.assertEqual(len(result["method_coverage"]), 31)
        self.assertEqual(len(result["family_coverage"]), 9)
        self.assertEqual(result["shortlist"], [])
        self.assertEqual(result["new_orders_created"], 0)
        self.assertFalse(result["scheduling_enabled"])
        self.assertFalse(result["trade_authorization"])

    def test_connection_failure_has_no_phantom_requested_symbols(self):
        client = BasisMCP(qualification=True)
        with patch.object(client, "connect", side_effect=ProviderError("HTTP_429")):
            result = scan_now(client=client, inventory=provisional(), started_at=AT, budget=budget())
        self.assertEqual(result["operation_status"], "BLOCKED_OR_UNQUALIFIED")
        self.assertEqual(result["resources"]["http_requests"], 0)
        for entry in result["packs"]:
            self.assertEqual(entry["requested_symbols"], [])
            self.assertEqual(len(entry["failed_symbols"]), 2)


if __name__ == "__main__":
    unittest.main()
