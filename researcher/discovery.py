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


def scan_live(*, qualification=False, api=None, client=None, config=None, ledger_path=None):
    """Automatic public API run; optional bounded, explicit provider qualification.

    Production broad packs stay gated. The qualification command exercises
    50+50+7 independent names, not a default top board; local history <=5 names.
    """
    from dataclasses import replace
    import math
    import time
    from .binance import OfficialResearchAPI
    from .cohorts import independent_partitions
    from .live_oracle import verify_sample
    from .method_registry import capability_coverage
    from .numerics import selected_measurements
    from .screening import (BasisScreenSource,CapabilityRegistry,PartitionEngine,
                            RequestBudget,closed_cutoff,safe_error)
    from .structures import (ResearchLedger,boundary_events,swing_references,
                             gap_lifecycle,swing_breaks,formation_candidates)
    from .transport import PublicHTTP
    started=time.monotonic();config=config or load_config();api=api or OfficialResearchAPI()
    report={'schema_version':'openbot.external-discovery.v3','environment':'CODEX_LOCAL_EXCEPTION',
        'created_at_utc':now_utc(),'operation_status':'BLOCKED_OR_UNQUALIFIED','mode':'PAUSE_UNQUALIFIED',
        'qualification_run':qualification,'trade_authorization':False,'new_orders_created':0,
        'scheduling_enabled':False,'source_faults':[],'shortlist':[],'watches':[],
        'context':{'policy':'ADVISORY_NON_VETO','context_interpretation':'LATER_WORK_PACKAGE'},
        'capability_coverage':capability_coverage(config),'packs':[],'selected_samples':[],'oracles':[],
        'coverage':{'eligible_contracts':None,'cheap_market_observed':0,'valid_remote_core_evaluated':0,
            'qualified_method_predicates_evaluated':0,'qualified_specialist_evaluated':0,
            'targeted_verified':0,'all_market_structurally_covered':False},
        'limitations':['Full CORE and all production strategy predicates remain disabled',
            'Selected local reconstruction is not market-wide structural discovery',
            'Earliest source publication unknown; historical reconstruction is not prospective nomination',
            'True profile/footprint, OI/liquidation history, sustainable Basis cadence unqualified',
            'Shortlist ranking, context interpretation and watch resumption remain later work packages']}
    inventory=None;connected=False;client=client or BasisMCP(PublicHTTP(max_requests=80),qualification=True)
    try:
        inventory=api.inventory()
        report['inventory']=inventory.report()
        report['coverage']['eligible_contracts']=inventory.report()['eligible_contracts']
        report['coverage']['inventory_seen']=len(inventory.symbols)+len(inventory.excluded)
        pulse=api.pulse(inventory)
        report['cheap_market']=pulse
        report['coverage']['cheap_market_observed']=len(pulse[0]['observations'])
        report['operation_status']='PARTIAL';report['mode']='CONTEXT_ONLY_DEGRADED'
        scan_time=now_utc();cutoffs={tf:closed_cutoff(scan_time,tf) for tf in ('1h','15m')}
        report['frozen_cutoffs']=cutoffs
        if qualification:
            cohort=independent_partitions(inventory,pulse[0],as_of=scan_time)
            report['quiet_tail']=cohort
            names=tuple(n for part in cohort['partitions'] for n in part)
        else:
            names=tuple(n for n in config['external_discovery']['observed_symbols'] if n in inventory.eligible_symbols)
            report['quiet_tail']={'status':'NOT_REQUESTED_USE_EXPLICIT_QUALIFICATION_COMMAND'}
        if inventory.mode!='VERIFIED_INVENTORY':
            raise ContractError('LIVE_INVENTORY_PARTIAL')
        # Cohort view retains the real exchange denominator in the enclosing
        # report; its source is explicitly a subset, never a new full inventory.
        selected=replace(inventory,instruments=tuple(next(i for i in inventory.instruments if i.native_symbol==n) for n in names),
                         eligible_symbols=names,mode='PARTIAL_INVENTORY',complete_source_snapshot=False)
        registry=CapabilityRegistry(config)
        budget=RequestBudget(8,retry_calls=2,interval_seconds=1)
        client.connect();connected=True
        engine=PartitionEngine(BasisScreenSource(client),budget)
        for pack in registry.packs.values():
            # Broadening is explicit qualification-only; no production promotion.
            probe=replace(pack,supported_symbols=names) if qualification else pack
            result=engine.run(selected,probe,cutoffs[pack.timeframe])
            result['exchange_eligible_denominator']=len(inventory.eligible_symbols)
            result['operating_scope']='INDEPENDENT_COHORT_QUALIFICATION_ONLY' if qualification else 'NARROW_OBSERVATION_ONLY'
            report['packs'].append(result)
        report['basis_budget']=budget.report()
        if qualification:
            members={i.native_symbol:i for i in inventory.instruments}
            young=cohort['verified_young_members'];unusual=cohort['unusual_native_spellings']
            sample=list(dict.fromkeys(['BTCUSDT','ETHUSDT',cohort['partitions'][0][0],*young[:1],*unusual[:1]]))
            if len(sample)<5:
                sample=list(dict.fromkeys([*sample,'1000PEPEUSDT',*cohort['partitions'][0]]))[:5]
            sample=[n for n in sample if n in members][:5]
            report['selected_sample_plan']={'symbols':sample,'max_symbols':5,'max_bars_per_tf':300,
                                           'purpose':'SMALL_INDEPENDENT_ORACLE_AND_EVENT_RECONSTRUCTION'}
            from .settings import ROOT
            ledger_path=ledger_path or ROOT/'work/research-metadata.sqlite'
            ledger=ResearchLedger(ledger_path)
            try:
                for name in sample:
                    for tf in ('1h','15m'):
                        try:
                            bars,source=api.klines(members[name],timeframe=tf,cutoff=cutoffs[tf])
                            sample_report={'source':source,'measurements':selected_measurements(bars,members[name].tick_size),
                                'formation_candidates':formation_candidates(bars,members[name].tick_size,as_of=source['receipt']['received_at_utc']),
                                'boundary_reconstructions':[],'gaps':gap_lifecycle(bars,members[name].tick_size,as_of=source['receipt']['received_at_utc']),
                                'swing_breaks':swing_breaks(bars,members[name].tick_size,as_of=source['receipt']['received_at_utc'])}
                            refs=swing_references(bars,members[name].tick_size,as_of=source['receipt']['received_at_utc'])
                            for ref in refs[-4:]:
                                ref=ledger.freeze_reference(ref)
                                causal=boundary_events(ref,bars,as_of=source['receipt']['received_at_utc'])
                                ledger.record(ref,causal['events'],hypotheses=causal['hypotheses'],cutoff=source['receipt']['received_at_utc'])
                                sample_report['boundary_reconstructions'].append({'reference':ref,**causal})
                            report['selected_samples'].append(sample_report)
                            labels=(['close','high','low','volume','width','prior_high','prior_low','lag','median','quantile','atr','buy_volume','delta']
                                    if name=='BTCUSDT' else ['close','volume','width','atr'] if name=='ETHUSDT'
                                    else ['close','volume','width'])
                            oracle=verify_sample(client,bars,members[name],labels=labels)
                            report['oracles'].append(oracle)
                            if oracle['all_blueprint_formula_checks_passed']:
                                report['coverage']['targeted_verified']+=1
                        except (ContractError,KeyError,TypeError,ValueError,IndexError) as error:
                            report['source_faults'].append({'phase':'selected_sample_or_oracle','symbol':name,'timeframe':tf,
                                'code':safe_error(error),'failure_class':type(error).__name__})
                            if isinstance(error,ProviderError) and str(error) in {'HTTP_403','HTTP_418','HTTP_429','HTTP_451','ROUTE_DISABLED','REQUEST_BUDGET_EXHAUSTED'}:
                                raise
                report['event_ledger']=ledger.counts()
                from pathlib import Path
                report['event_ledger']['disk_bytes']=Path(ledger_path).stat().st_size
                report['event_ledger']['storage']='work/research-metadata.sqlite'
            finally:ledger.close()
        verified_pairs=[{'native_symbol':o['native_symbol'],'timeframe':o['timeframe']}
                        for o in report['oracles'] if o['all_blueprint_formula_checks_passed']]
        report['coverage']['targeted_verified_symbol_timeframes']=verified_pairs
        report['coverage']['targeted_verified']=len({x['native_symbol'] for x in verified_pairs})
        report['mode']='TARGETED_RESEARCH' if report['selected_samples'] or not qualification else 'REMOTE_WIDE_PARTIAL'
    except (ContractError,KeyError,TypeError,ValueError,IndexError) as error:
        report['source_faults'].append({'phase':'live_run','code':safe_error(error),'failure_class':type(error).__name__})
    report['transport_receipts']=[*api.http.receipts,*client.http.receipts]
    receipts=report['transport_receipts'];durations=sorted(r['elapsed_ms'] for r in receipts)
    report['resources']={'http_requests':len(receipts),'response_bytes':sum(r.get('response_bytes') or 0 for r in receipts),
        'sum_request_elapsed_ms':sum(durations),'wall_elapsed_ms':round((time.monotonic()-started)*1000),
        'p50_ms':durations[(len(durations)-1)//2] if durations else None,
        'p95_ms':durations[math.ceil(len(durations)*.95)-1] if durations else None,
        'http_failures':sum(r.get('http_status') is None or r['http_status']>=400 for r in receipts),
        'api_cache_hits':api.http.cache_hits,'basis_charged_units':None,'sustainable_cadence':'UNQUALIFIED'}
    report['completed_at_utc']=now_utc()
    return report
