"""One full registry, with honest implementation and remote capability states."""
from .contracts import ContractError

FIELDS={"state","execution_scope","dependencies","necessary_evidence","temporal_sequence",
        "valid_interpretation","false_positive_traps","competing_explanations","invalidation_conditions",
        "provider_requirements","fidelity","production_enabled","remote_qualification","definition_source"}
STATES={"IMPLEMENTED_TRIAL","PARTIAL_IMPLEMENTED","NOT_IMPLEMENTED","BLOCKED_DATA",
        "BLOCKED_DEFINITION","DEFINITION_PENDING"}


def validate_method_contracts(config):
    s=config.get("session3",{})
    if (s.get("max_selected_symbols")!=5 or s.get("max_sample_bars")!=300
            or s.get("max_kline_calls")!=10 or s.get("production_detectors_enabled") is not False
            or s.get("public_binance_hosts")!=["fapi.binance.com"] or s.get("proxies") is not False):
        raise ContractError("SESSION3_ARCHITECTURE_BOUNDARY")
    for m in config["methods"]:
        d=m.get("implementation",{})
        if (set(d)!=FIELDS or d["state"] not in STATES or d["production_enabled"] is not False
                or d["remote_qualification"]!="UNVERIFIED"
                or any(not d[k] for k in FIELDS-{"dependencies","production_enabled"})):
            raise ContractError("METHOD_CONTRACT_INCOMPLETE_OR_UNQUALIFIED")
    for f in config["families"]:
        d=f.get("implementation",{})
        if (d.get("production_enabled") is not False or d.get("ready_for_deep_enabled") is not False
                or d.get("null_hypothesis_required") is not True):
            raise ContractError("UNQUALIFIED_FAMILY_PROMOTION")


def capability_coverage(config):
    validate_method_contracts(config)
    return {"methods":[{"id":m["id"],"name":m["name"],"roles":m["roles"],**m["implementation"],
                        "qualified_market_wide_evaluations":0} for m in config["methods"]],
            "families":[{"id":f["id"],"name":f["name"],**f["implementation"],
                         "qualified_market_wide_evaluations":0} for f in config["families"]]}
