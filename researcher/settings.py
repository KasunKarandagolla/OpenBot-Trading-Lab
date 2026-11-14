"""One versioned feature and capability manifest, no secret file loading."""
import json
import os
from pathlib import Path
from .contracts import ContractError, Feasibility, digest, encode

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "researcher/config/discovery_specs.json"


def load_config():
    config = json.loads(MANIFEST.read_text())
    validate_config(config)
    return config


def validate_config(config):
    if config.get("schema_version") != "openbot.discovery-specs.v1" or config.get("session") != 4:
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
    s4=config.get('session4',{})
    if (s4.get('default_llm_calls')!=0 or s4.get('optional_llm_provider_enabled') is not False
            or s4.get('max_horizon_seconds')!=54000 or s4.get('max_shortlist')!=5
            or s4.get('atr_remote_status')!='ATR_REMOTE_UNQUALIFIED' or s4.get('full_core_enabled') is not False
            or s4.get('specialist_runtime_sources')!={} or s4.get('scheduling_enabled') is not False
            or s4.get('max_remote_selected_bars')!=300 or s4.get('max_live_probe_requests')!=45
            or s4.get('budget_pools')!=['broad','targeted','exception','watch']
            or s4.get('quiet_trial_percentile_max')!='0.25'):
        raise ContractError('SESSION4_CAPABILITY_BOUNDARY')
    if 'session5' in config:
        validate_session5(config['session5'])
    if 'session55' in config:
        validate_session55(config['session55'])
    return {"status": "VALID", "families": 9, "methods": 31,
            "manifest_sha256": digest(MANIFEST.read_bytes()), "detectors_enabled": 0,
            "release": discovery["release"], "research_review_release":s4['release'],
            "full_core_packs_enabled": 0,
            "market_research_release":config.get('session5',{}).get('release'),
            "qualified_remote_price_columns":len(config.get('session5',{}).get('qualified_price_columns',()))}


def provider_status(config):
    # Only presence is exposed. Environment values never become requests/logs.
    return {"status_kind": "RECORDED_CAPABILITIES_NOT_LIVE_HEALTH",
            "providers": config["providers"],
            "external_discovery": config["external_discovery"],
            "session4": config['session4'],
            "session5": config.get('session5'),
            "session55": config.get('session55'),
            "optional_basis_key_present": bool(os.environ.get("OPENBOT_BASIS_TOKEN")),
            "optional_basis_key_used": False,
            "setup_keys": "DEFERRED: public runtime needs no keys; auth contract must be qualified first"}


def validate_session5(spec):
    from .core import CORE,manifest
    columns=spec.get('qualified_price_columns',[])
    if (not columns or len(columns)!=len(set(columns)) or not set(columns)<=set(CORE) or spec.get('full_core_enabled') is not False
            or spec.get('production_remote_family_detectors_enabled') is not False
            or spec.get('scheduling_enabled') is not False or spec.get('specialist_runtime_sources')!={}
            or spec.get('default_llm_calls')!=0 or spec.get('max_horizon_seconds')!=54000
            or spec.get('max_screen_requests')!=26 or spec.get('max_targeted_alt_symbols')!=2
            or spec.get('max_http_requests')!=40 or spec.get('cache_ttl_seconds')!=300
            or spec.get('source_availability_delay_seconds')!=0
            or spec.get('qualification_evidence')!='evidence/external-first/session5/core-qualification.json'):
        raise ContractError('SESSION5_CAPABILITY_BOUNDARY')
    raw=(ROOT/spec['qualification_evidence']).read_bytes()
    if digest(raw)!=spec.get('qualification_sha256'):raise ContractError('QUALIFICATION_EVIDENCE_DRIFT')
    proof=json.loads(raw)
    current=json.loads(encode(manifest()))
    if any(proof.get('formula_manifest',{}).get(k)!=current[k] for k in columns):
        raise ContractError('QUALIFICATION_EVIDENCE_DRIFT')
    checks=[c for s in proof['screens'] for c in s['oracle_checks']]
    if (len(checks)!=10*len(proof['formula_manifest']) or not all(c['passed'] for c in checks)
            or len([c for c in proof['checks'] if c['feature']=='atr_explicit'])!=16
            or not all(c['passed'] for c in proof['checks'])):
        raise ContractError('QUALIFICATION_EVIDENCE_DRIFT')


def validate_session55(spec):
    from .remote_structure import manifest
    if (spec.get('causal_timeframes')!=['1h'] or spec.get('method_screen_requests')!=14
            or spec.get('method_recovery_requests')!=2 or spec.get('qualified_bits')!=[2,4,8,16,32]
            or spec.get('full_core_enabled') is not False or spec.get('all_methods_enabled') is not False
            or spec.get('llm_status')!='LLM_DISABLED_NO_APPROVED_PROVIDER'
            or spec.get('qualification_evidence')!='evidence/external-first/session55/causal-qualification.json'):
        raise ContractError('SESSION5_CAPABILITY_BOUNDARY')
    raw=(ROOT/spec['qualification_evidence']).read_bytes()
    if digest(raw)!=spec.get('qualification_sha256'):raise ContractError('QUALIFICATION_EVIDENCE_DRIFT')
    proof=json.loads(raw)
    if proof['manifest']!=json.loads(encode(manifest())) or proof['qualified_bits']!=spec['qualified_bits']:
        raise ContractError('QUALIFICATION_EVIDENCE_DRIFT')
    checks=[r for c in proof['tail_checks'] for r in c['rows']]+proof['screen_checks']+proof['positive_checks']
    if len(checks)!=515 or not all(c['passed'] for c in checks):raise ContractError('QUALIFICATION_EVIDENCE_DRIFT')
    e=spec.get('economics',{})
    if (e.get('max_horizon_seconds')!=54000 or set(e)!={'max_horizon_seconds','probe_notional_usdt',
            'round_trip_fee_assumption_bps','additional_slippage_assumption_bps','funding_assumption_bound_bps',
            'fee_source','bound_status'} or e.get('fee_source')!='https://www.binance.com/en/support/faq/detail/360033544231'):
        raise ContractError('SESSION5_CAPABILITY_BOUNDARY')
    for key in ('probe_notional_usdt','round_trip_fee_assumption_bps','additional_slippage_assumption_bps','funding_assumption_bound_bps'):
        from .contracts import number
        number(e[key],positive=True)
