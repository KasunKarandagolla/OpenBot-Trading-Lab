"""One versioned feature and capability manifest, no secret file loading."""
import json
import os
from pathlib import Path
from .contracts import ContractError, Feasibility, digest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "researcher/config/discovery_specs.json"


def load_config():
    config = json.loads(MANIFEST.read_text())
    validate_config(config)
    return config


def validate_config(config):
    if config.get("schema_version") != "openbot.discovery-specs.v1" or config.get("session") != 3:
        raise ContractError("CONFIG_VERSION")
    if config.get("policy") != {
        "external_first": True, "context_policy": "ADVISORY_NON_VETO", "trade_authorization": False,
        "max_shortlist": 5, "scheduling_enabled": False, "whole_market_history_enabled": False,
    }:
        raise ContractError("RESEARCH_BOUNDARY_CHANGED")
    if [f["id"] for f in config["families"]] != [f"F{i}" for i in range(1, 10)]:
        raise ContractError("ALL_NINE_FAMILIES_REQUIRED")
    if [m["id"] for m in config["methods"]] != [f"M{i:02d}" for i in range(1, 32)]:
        raise ContractError("COMPLETE_METHOD_REGISTRY_REQUIRED")
    for entry in [*config["families"], *config["methods"], *config["packs"].values(),
                  *config["qualification_formulas"].values()]:
        Feasibility(entry["status"])
        if entry.get("enabled") is not False:
            raise ContractError("SESSION1_DETECTORS_DISABLED")
    for key, path in [("blueprint_sha256", "OpenBot_Final_External_First_Market_Discovery_Blueprint.md"),
                      ("plan_sha256", "OpenBot_Cloud_First_GitHub_Synced_Implementation_Plan.md")]:
        if digest((ROOT / "docs/implementation" / path).read_bytes()) != config["references"][key]:
            raise ContractError("IMMUTABLE_REFERENCE_DRIFT")
    discovery = config["external_discovery"]
    for name, path in [("observed_scope", "evidence/external-first/session1/runtime-samples-001.json"),
                       ("arithmetic", "evidence/external-first/session1/oracle-results.json")]:
        if (discovery[name + "_evidence"] != path
                or digest((ROOT / path).read_bytes()) != discovery[name + "_sha256"]):
            raise ContractError("QUALIFICATION_EVIDENCE_DRIFT")
    observed = json.loads((ROOT / discovery["observed_scope_evidence"]).read_text())
    sample_pairs = {(o["receipt"]["arguments"]["symbol"], o["receipt"]["arguments"]["timeframe"])
                    for o in observed["outcomes"] if o.get("status") == "LIVE_TESTED_NARROW"
                    and o.get("receipt", {}).get("tool") == "market_candles"}
    expected_pairs = {(n, tf) for n in discovery["observed_symbols"] for tf in ("1h", "15m")}
    arithmetic = json.loads((ROOT / discovery["arithmetic_evidence"]).read_text())
    if (sample_pairs != expected_pairs or len(discovery["observed_symbols"]) != 5
            or arithmetic["checks"]["width"]["passed"] is not True
            or arithmetic["checks"]["width"]["comparisons"] != 18):
        raise ContractError("UNPROVEN_OBSERVATION_SCOPE")
    if (discovery["scheduling_enabled"] is not False or discovery["concurrency"] != 1
            or not 1 <= discovery["partition_size"] <= 50
            or not 1 <= discovery["max_screen_requests"] <= 40
            or discovery["qualified_alternative_inventories"]):
        raise ContractError("DISCOVERY_CAPABILITY_BOUNDARY")
    for pack_id, tf in [("CORE_1H", "1h"), ("CORE_15M", "15m")]:
        pack = config["packs"][pack_id]
        if (pack["full_core_qualified"] is not False or pack["timeframe"] != tf
                or pack["lookback"] != 300 or len(pack["observation_columns"]) != 1):
            raise ContractError("UNQUALIFIED_CORE_CONTRACT")
        column = pack["observation_columns"][0]
        if (column["expression"] != config["qualification_formulas"]["width"]["expression"]
                or column["id"] != "NORMALIZED_WIDTH_3" or column["production_enabled"] is not False
                or column["independent_source_accuracy"] != "UNVERIFIED"):
            raise ContractError("UNQUALIFIED_FORMULA_PROMOTION")
    from .method_registry import validate_method_contracts
    validate_method_contracts(config)
    return {"status": "VALID", "families": 9, "methods": 31,
            "manifest_sha256": digest(MANIFEST.read_bytes()), "detectors_enabled": 0,
            "release": discovery["release"], "full_core_packs_enabled": 0}


def provider_status(config):
    # Only presence is exposed. Environment values never become requests/logs.
    return {"status_kind": "RECORDED_CAPABILITIES_NOT_LIVE_HEALTH",
            "providers": config["providers"],
            "external_discovery": config["external_discovery"],
            "optional_basis_key_present": bool(os.environ.get("OPENBOT_BASIS_TOKEN")),
            "optional_basis_key_used": False,
            "setup_keys": "DEFERRED: public runtime needs no keys; auth contract must be qualified first"}
