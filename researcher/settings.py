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
    if config.get("schema_version") != "openbot.discovery-specs.v1" or config.get("session") != 1:
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
    return {"status": "VALID", "families": 9, "methods": 31,
            "manifest_sha256": digest(MANIFEST.read_bytes()), "detectors_enabled": 0}


def provider_status(config):
    # Only presence is exposed. Environment values never become requests/logs.
    return {"status_kind": "RECORDED_CAPABILITIES_NOT_LIVE_HEALTH",
            "providers": config["providers"],
            "optional_basis_key_present": bool(os.environ.get("OPENBOT_BASIS_TOKEN")),
            "optional_basis_key_used": False,
            "setup_keys": "DEFERRED: public runtime needs no keys; auth contract must be qualified first"}
