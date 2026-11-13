"""On-demand external observations and coverage. No detector or trading path."""
from dataclasses import asdict
from .basis import BasisMCP
from .contracts import Coverage, ContractError, ResearchReport, digest, encode, now_utc
from .observations import candle_observation
from .settings import MANIFEST, load_config, provider_status
from .transport import ProviderError


def scan_now(*, client=None, inventory=None, config=None, started_at=None, budget=None):
    """Session 2 on-demand partial observation. No detectors or orders.

    No remote inventory call is made on the recorded Binance-denied host. The
    fallback is the five previously observed native spellings, explicitly
    provisional; it is neither a full exchange universe nor a quiet-tail cohort.
    """
    import json
    import math
    import time
    from .inventory import provisional_inventory
    from .nominations import NominationRouter
    from .screening import (BasisScreenSource, CapabilityRegistry, PartitionEngine,
                            RequestBudget, closed_cutoff, safe_error)
    from .settings import ROOT
    from .transport import PublicHTTP

    started = time.monotonic()
    started_at = started_at or now_utc()
    config = config or load_config()
    policy = config["external_discovery"]
    if inventory is None:
        artifact = ROOT / policy["observed_scope_evidence"]
        recorded = json.loads(artifact.read_text())
        captured = max(r["received_at_utc"] for r in recorded["http_receipts"])
        inventory = provisional_inventory(policy["observed_symbols"],
            source_id="SESSION1_BASIS_OBSERVED_SPELLINGS_NOT_EXCHANGE_INVENTORY",
            source_url=config["providers"]["basis"]["endpoint"], captured_at=captured,
            received_at=started_at, content_hash=digest(artifact.read_bytes()))
    inventory = inventory.at(started_at)
    registry = CapabilityRegistry(config)
    budget = budget or RequestBudget(policy["max_screen_requests"], retry_calls=policy["retry_budget"],
                                     interval_seconds=policy["min_request_interval_seconds"])
    client = client or BasisMCP(PublicHTTP(max_requests=policy["max_http_requests"]), qualification=True)
    # Same client and MCP session for all packs; no duplicate transport.
    report = {
        "schema_version": "openbot.external-discovery.v2", "created_at_utc": started_at,
        "run_id": digest((started_at + inventory.content_sha256).encode()),
        "mode": "PAUSE_UNQUALIFIED", "release": "R0_ON_DEMAND_OBSERVATION",
        "manifest_sha256": digest(MANIFEST.read_bytes()), "inventory": inventory.report(),
        "provider_status": provider_status(config), "source_faults": [], "observations": [],
        "shortlist": [], "watches": [], "near_misses": [],
        "context": {"policy": "ADVISORY_NON_VETO", "btc": "UNVERIFIED", "eth": "UNVERIFIED"},
        "nomination_routes": NominationRouter(config, inventory).coverage(),
        "trade_authorization": False, "new_orders_created": 0, "scheduling_enabled": False,
        "quiet_tail": {"status": "BLOCKED_CURRENT_INVENTORY_AND_INDEPENDENT_LIQUIDITY_COHORT",
                       "partitions_sent": 0, "not_substituted_by_provider_top_lists": True},
        "independent_numerical_oracle": "UNVERIFIED_NO_LAWFUL_ALIGNED_SAMPLE",
        "cheap_market": {"status": "DATA_UNAVAILABLE_RECORDED_HTTP_451", "observed": 0},
        "limitations": ["Authoritative complete Binance universe not established on this host",
            "Finite width3 probe is not the full CORE contract or historical compression",
            "Source accuracy, volume units and per-row history completeness unverified",
            "All F1-F9 and 31 method detectors disabled; no opportunity conclusion",
            "True profile, footprint, structural room and causal event review unavailable",
            "Free credits actually charged and sustainable cadence unknown"],
    }
    connected = True
    try:
        client.connect()
    except (ContractError, KeyError, TypeError, ValueError) as error:
        connected = False
        report["source_faults"].append({"provider": "basis", "code": safe_error(error), "phase": "connect"})
    engine = PartitionEngine(BasisScreenSource(client), budget, partition_size=policy["partition_size"])
    results = []
    for pack in registry.packs.values():
        cutoff = closed_cutoff(started_at, pack.timeframe)
        if connected:
            result = engine.run(inventory, pack, cutoff)
        else:
            result = {"pack_id": pack.id, "timeframe": pack.timeframe, "cutoff_utc": cutoff,
                "formula_version": pack.version, "formula_sha256": pack.formula_hash,
                "planned_symbols": list(inventory.symbols), "requested_symbols": [],
                "recognized_symbols": [], "returned_symbols": [], "evaluated_symbols": [],
                "matched_symbols": [], "missing_symbols": [], "not_requested_symbols": list(inventory.symbols),
                "failed_symbols": {n: "PROVIDER_CONNECT_FAILED" for n in inventory.symbols},
                "provider_added_fillers": [], "truncated_attempts": 0, "source_cutoffs": {},
                "valid_remote_core_evaluated": 0, "qualified_method_predicates_evaluated": 0,
                "attempts": [], "calculation_coverage": [], "observations": [],
                "zero_opportunities_established": False}
        result["disabled_calculations"] = {name: {**details,
            "eligible_contracts": inventory.report()["eligible_contracts"],
            "provisionally_identified_contracts": list(inventory.provisional_symbols),
            "requested_symbols": [], "recognized_symbols": [], "evaluated_symbols": [],
            "returned_symbols": [], "matched_symbols": [], "missing_symbols": [],
            "not_evaluated_symbols": list(inventory.symbols), "formula_version": pack.version,
            "source_cutoffs": {}, "quota_usage": {"charged_units": None}, "requests": 0,
            "fidelity": "INCOMPLETE_HISTORY" if details["status"] == "INCOMPLETE_HISTORY" else "DATA_UNAVAILABLE"}
            for name, details in config["packs"][pack.id]["required_outputs"].items()}
        report["observations"].extend(result.pop("observations"))
        results.append(result)
    report["packs"] = results
    report["method_coverage"] = [{"method_id": m["id"], "status": m["status"],
        "enabled": False, "evaluated_symbols": [], "eligible_contracts": inventory.report()["eligible_contracts"],
        "not_evaluated_symbols": list(inventory.symbols), "timeframes": ["1h", "15m"]} for m in config["methods"]]
    report["family_coverage"] = [{"family_id": f["id"], "status": f["status"], "enabled": False,
                                  "evaluated_symbols": []} for f in config["families"]]
    report["coverage"] = {"eligible_contracts": inventory.report()["eligible_contracts"],
        "inventory_seen": len(inventory.symbols), "denominator_status": inventory.mode,
        "cheap_market_observed": 0, "valid_remote_core_evaluated": 0,
        "qualified_specialist_evaluated": 0, "targeted_verified": 0,
        "all_market_structurally_covered": False,
        "provider_reported_scalar_evaluated_by_timeframe": {r["timeframe"]: len(r["evaluated_symbols"]) for r in results}}
    receipts = client.http.receipts
    durations = sorted(r["elapsed_ms"] for r in receipts)
    report["resources"] = {**budget.report(), "http_requests": len(receipts),
        "http_response_bytes": sum(r.get("response_bytes") or 0 for r in receipts),
        "sum_http_elapsed_ms": sum(durations), "wall_elapsed_ms": round((time.monotonic() - started) * 1000),
        "http_p50_ms": durations[(len(durations) - 1) // 2] if durations else None,
        "http_p95_ms": durations[math.ceil(len(durations) * .95) - 1] if durations else None,
        "http_failures": [r for r in receipts if r.get("http_status") is None or r["http_status"] >= 400],
        "screen_failures": [{"pack_id": p["pack_id"], "code": a["provider_error"],
                            "source_hash": a["source_hash"]}
                            for p in results for a in p["attempts"] if a["provider_error"]]}
    report["transport_receipts"] = receipts
    has_values = bool(report["observations"])
    report["operation_status"] = "PARTIAL" if has_values else "BLOCKED_OR_UNQUALIFIED"
    report["mode"] = "TARGETED_RESEARCH" if has_values else "PAUSE_UNQUALIFIED"
    report["completed_at_utc"] = now_utc()
    return report


def smoke(client=None) -> ResearchReport:
    config = load_config()
    client = client or BasisMCP()
    report = {
        "schema_version": "openbot.research-smoke.v1", "created_at_utc": now_utc(),
        "mode": "PAUSE_UNQUALIFIED", "trade_authorization": False, "new_orders_created": 0,
        "manifest_sha256": digest(MANIFEST.read_bytes()),
        "coverage": asdict(Coverage(None, None, 0, 0, {"1h": 0, "15m": 0}, 0, 0,
                                   "UNKNOWN_EXCHANGE_INVENTORY_HTTP_451")),
        "context": {"policy": "ADVISORY_NON_VETO", "btc": "UNVERIFIED", "eth": "UNVERIFIED"},
        "shortlist": [], "watches": [], "near_misses": [], "observations": [],
        "source_faults": [], "provider_status": provider_status(config),
        "limitations": ["No quiet-tail qualification", "No independent source oracle",
                        "No detectors enabled", "Earliest source availability UNKNOWN"],
    }
    try:
        if not config["providers"]["basis"]["operations"]["market_candles"]["enabled"]:
            raise ContractError("CAPABILITY_DISABLED")
        client.connect()
        data = client.call("market_candles", {"symbol": "BTCUSDT", "exchange": "binance",
                           "market": "futures", "timeframe": "1h", "bars": 3, "withDerivatives": False})
        metadata = client.http.receipts[-1]
        evidence = candle_observation(data, requested_symbol="BTCUSDT", timeframe="1h",
            received_at=metadata["received_at_utc"],
            schema_hash=digest(encode(client.tools["market_candles"]["inputSchema"]).encode()),
            response_hash=metadata["response_sha256"])
        report["observations"].append(asdict(evidence))
        report["mode"] = "TARGETED_RESEARCH"
        report["operation_status"] = "LIVE_TESTED_NARROW"
    except (ProviderError, ContractError, KeyError, TypeError, ValueError) as error:
        report["operation_status"] = "BLOCKED_OR_UNQUALIFIED"
        # Never print remote message text or exception values from arbitrary sources.
        from .screening import safe_error
        code = safe_error(error)
        report["source_faults"].append({"code": code})
    report["transport_receipts"] = client.http.receipts
    return report
