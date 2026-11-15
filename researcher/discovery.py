"""On-demand external observations and coverage. No detector or trading path."""
from dataclasses import asdict
from .basis import BasisMCP
from .contracts import Coverage, ContractError, ResearchReport, digest, encode, now_utc, utc
from .observations import candle_observation
from .settings import MANIFEST, load_config, provider_status
from .transport import ProviderError


def implementation_revision():
    """Closed-source caches cannot survive a change to their analyzer code."""
    from .settings import ROOT
    return digest(encode({p.name:digest(p.read_bytes()) for p in sorted((ROOT/'researcher').glob('*.py'))}).encode())


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


def scan_market_research(*,api=None,client=None,config=None,ledger_path=None,clock=now_utc,
                         mode='LIVE',crash_hook=None,sources=None,context_prioritized=True,route_ablation=None,
                         native_review_dir=None,native_audit_config=None,native_wait_seconds=0,native_max_cards=4,progress=None):
    """One on-demand read-only path: live sources → remote packs → saved research.

    Historical price precursors nominate questions independently. The protected
    audit lane and adaptive operational investigation are separate. Selected
    reconstruction cannot certify whole-market coverage or missing specialists.
    """
    import math
    import time
    from decimal import Decimal as D
    from dataclasses import asdict,replace
    from .binance import OfficialResearchAPI
    from .core import CORE,REVISION,make_pack
    from .context import benchmark_fact,build_context,matched_budget_study
    from .candidate_review import boundary_card,review_card,shortlist,formation_cards
    from .method_registry import capability_coverage
    from .observations import WIDTHS
    from .persistence import RunLedger
    from .query_planner import QueryPlanner,ResearchSources,decision_questions
    from .resource_planner import plan_resources
    from .research import Fact,fact_id
    from .settings import ROOT,validate_config
    from .screening import BasisScreenSource,PartitionEngine,RequestBudget,closed_cutoff,safe_error
    from .structures import Reference,swing_references,equal_level_references,boundary_events,selected_family_facts,gap_lifecycle
    from .transport import PublicHTTP
    if mode not in {'LIVE','SYNTHETIC','AUTHENTIC_REPLAY'}:raise ContractError('FACT_PROVENANCE')
    if native_audit_config and (mode!='LIVE' or native_review_dir is None):raise ContractError('NATIVE_AGENT_AUDIT_REQUIRED')
    if type(native_max_cards) is not int or not 1<=native_max_cards<=4:raise ContractError('AGENT_INPUT_SIZE')
    if route_ablation is not None and (mode!='SYNTHETIC' or not set(route_ablation)<={'A','B','C'}):
        raise ContractError('OFFLINE_REPLAY_SCOPE')
    sources=sources or ResearchSources(mode=mode)
    if sources.mode!=mode:raise ContractError('SOURCE_QUALIFICATION_CONTRACT')
    wall=time.monotonic();start=clock();config=config or load_config();validate_config(config)
    implementation=implementation_revision()
    import os
    cpu_start=os.times()
    spec=config['session5'];cutoffs={tf:closed_cutoff(start,tf) for tf in ('1h','15m','4h')}
    completion=config.get('session55',{})
    recovery=config.get('recovery',{}) if mode=='LIVE' else {}
    alt_capacity=spec['max_targeted_alt_symbols']+recovery.get('operational_alt_capacity',0)
    api=api or OfficialResearchAPI(PublicHTTP(max_requests=recovery.get('official_http_limit',20)),
        max_sample_symbols=max(5,alt_capacity+2),max_sample_calls=max(10,6+2*alt_capacity))
    client=client or BasisMCP(PublicHTTP(max_requests=spec['max_http_requests']),qualification=True,session5=True,session6a=True)
    ledger=RunLedger(ledger_path or ROOT/'work/research-metadata.sqlite')
    report={'schema_version':'openbot.market-research.v5','environment':'CODEX_LOCAL' if mode=='LIVE' else 'OFFLINE_REPLAY_HOST','mode':mode,
        'created_at_utc':start,'frozen_cutoffs':cutoffs,'operation_status':'BLOCKED_OR_UNQUALIFIED',
        'release_status':'PARTIAL','operating_mode':'PAUSE_UNQUALIFIED','shortlist':[],'watches':[],
        'near_misses':[],'invalidations':[],'not_reviewed_budget':[],'time_gaps':[],'consumed_obstacles':[],
        'source_health':[],'packs':[],'optional_packs':[],'nominations':[],'selected_research':[],'planner':[],
        'causal_packs':[],'specialist_observations':[],'economic_observations':[],
        'llm_status':completion.get('llm_status','LLM_DISABLED_NO_APPROVED_PROVIDER'),
        'research_shortlist_version':'openbot.research-shortlist.6b.1',
        'offline_source_provenance':getattr(sources,'provenance',{}),
        'synthetic_route_ablation':route_ablation,
        'evidence_mode':{'LIVE':'LIVE_PARTIAL','SYNTHETIC':'SYNTHETIC_TEST','AUTHENTIC_REPLAY':'AUTHENTIC_RETAINED_REPLAY'}[mode],
        'source_faults':[],'capability_revision':REVISION,'method_coverage':capability_coverage(config),
        'empty_shortlist_reason':'INSUFFICIENT_QUALIFIED_CAUSAL_SOURCE_AND_ECONOMIC_COVERAGE; NOT_NO_OPPORTUNITIES',
        'coverage':{'eligible_contracts':None,'full_core_evaluated':0,'production_remote_method_evaluated':0,
            'all_market_structurally_covered':False,'specialist_evaluated':0},
        'trade_authorization':False,'new_orders_created':0,'scheduling_enabled':False,'llm_calls':0,
        'limitations':['QUALIFIED_PRICE_PRECURSORS_ARE_NOT_COMPLETE_CORE_OR_FAMILY_DETECTORS',
            'QUOTE_RVOL_ZERO_BASELINE_IS_UNKNOWN; PARTICIPATION_IS_NOT_A_PRICE_FAMILY_GATE',
            'TRUE_PROFILE_FOOTPRINT_OI_DIRECTION_LIQUIDATIONS_UNSUPPORTED',
            'CURRENT_RECONSTRUCTION_IS_NOT_PROSPECTIVE_HISTORICAL_DISCOVERY',
            'FEES_DEPTH_SLIPPAGE_FUNDING_BOUNDS_AND_HORIZON_UNVERIFIED; NO_FAKE_READY',
            'PUBLISH_LAG_AND_SUSTAINABLE_QUOTA_UNKNOWN; SCHEDULING_DISABLED']}
    report['planning_cutoffs']=dict(cutoffs)
    report['implementation_sha256']=implementation
    stage_started=wall;stage_times={}
    def mark_stage(name):
        nonlocal stage_started
        current=time.monotonic();stage_times[name]=round(current-stage_started,6);stage_started=current
        if progress:progress(name,stage_times[name])
    bundles=[];verified=[];terminals=[];facts={};cards=[];references=[];reviews=[];cached=False
    observed_times=[start]
    def evaluation_time():
        # Local UTC can step backwards between completed HTTP requests. Preserve
        # every original receipt/availability; use a conservative logical upper
        # bound for metadata ordering and disclose the clock uncertainty.
        wall_at=clock()
        received=[r['received_at_utc'] for r in (*api.http.receipts,*client.http.receipts)]
        bound=max([wall_at,*observed_times,*received],key=utc)
        if utc(bound)>utc(wall_at):
            report.setdefault('clock_anomalies',[]).append({'kind':'HOST_UTC_REGRESSION_OR_RECEIPT_SKEW',
                'observed_wall_utc':wall_at,'conservative_known_by_bound':bound,
                'seconds':(utc(bound)-utc(wall_at)).total_seconds(),
                'original_source_times_modified':False})
        observed_times.append(bound)
        return bound
    try:
        with ledger.writer(start) as attempt:
            previous=ledger.latest();prior_watches={w['id']:w for w in previous['watches']} if previous else {}
            prior_active_coins=previous.get('active_coin_watchlist',()) if previous else ()
            report['consumed_obstacles']=[x for x in previous.get('consumed_obstacles',())
                if utc(x['valid_until'])>=utc(start)] if previous else []
            if previous:observed_times.append(previous['completed_at_utc'])
            old_cutoffs=ledger.cutoffs()
            try:
                inventory=api.inventory();members={i.native_symbol:i for i in inventory.instruments}
                observed_times.append(inventory.received_at_utc)
                ir=inventory.report();report['inventory']={k:v for k,v in ir.items() if k!='instruments'}
                report['inventory']['source_total_rows']=len(inventory.symbols)+len(inventory.excluded)
                report['coverage']['eligible_contracts']=ir['eligible_contracts']
                if inventory.mode!='VERIFIED_INVENTORY' and mode=='LIVE':raise ContractError('LIVE_INVENTORY_PARTIAL')
                identity={n:digest(encode([i.venue,n,i.contract_type,i.quote,i.settlement,i.onboard_at_utc,
                    i.contract_multiplier,i.tick_size,i.quantity_rules]).encode()) for n,i in members.items()}
                report['inventory']['identity_hashes']=identity
                quarantined={w['native_symbol'] for w in prior_watches.values()
                    if w['native_symbol'] in identity and w['identity_hash']!=identity[w['native_symbol']]}
                old_identity=previous.get('inventory',{}).get('identity_hashes',{}) if previous else {}
                quarantined.update(n for n in identity if n in old_identity and old_identity[n]!=identity[n])
                report['identity_quarantine']=sorted(quarantined)
                # Obstacle-only frozen metadata has no watch row. Delisting or
                # changed identity must retire those references as well.
                retained_obstacles=[]
                for raw in ledger.active_references(evaluation_time()):
                    raw={**raw}
                    for field in ('lo','hi','atr','tick'):raw[field]=D(str(raw[field]))
                    raw['source_ids']=tuple(raw['source_ids'])
                    if raw['native_symbol'] not in members or raw['native_symbol'] in quarantined:
                        terminals.append((Reference(**raw),'INVALIDATED',evaluation_time()))
                    else:retained_obstacles.append(Reference(**raw))
                references.extend(retained_obstacles)
                pulse=api.pulse(inventory,partial=True)
                report['source_health']=[{**{k:v for k,v in p.items() if k!='observations'},
                    'accepted':len(p['observations']),'eligible':len(members)} for p in pulse]
                mark_stage('inventory_and_initial_context')
                report['operation_status']='PARTIAL';report['operating_mode']='REMOTE_WIDE_PARTIAL'
                key=digest(encode([cutoffs,identity,spec,completion,recovery,mode,sources.certificates,
                    sources.nominations,sources.selected_inputs,route_ablation,context_prioritized,implementation]).encode())
                # Fresh official access/identity is mandatory even for unchanged
                # bars. Reuse preserves first knowledge and original receipts.
                previous_reusable=previous and previous.get('numeric_cache_available',True) and len(previous.get('packs',()))==2 and all(
                    p.get('evaluated',0)>0 and not p.get('truncated_attempts') for p in previous['packs'])
                if (previous_reusable and previous.get('cache_key')==key
                        and 0<=(utc(clock())-utc(previous['completed_at_utc'])).total_seconds()<spec['cache_ttl_seconds']):
                    cached=True
                    fresh={k:report[k] for k in ('inventory','source_health','created_at_utc')}
                    report=previous;report.update(fresh);report['reuse']={'status':'UNCHANGED_CLOSED_BARS',
                        'original_snapshot':previous.get('reuse',{}).get('original_snapshot',previous['run_key']),
                        'original_evidence_cutoffs':cutoffs,
                        'fresh_remote_requests':0,'retained_partial_failures_are_not_retried_until_cache_expiry':True}
                    report['llm_calls']=0
                    selected_names=set(report.get('current_economics',{}))
                    report['current_economics']={n:[o for p in pulse if p['kind'] in {'book','premium'}
                        for o in p['observations'] if o['native_symbol']==n] for n in selected_names}
                    report['reuse']['closed_bar_review_recomputed']=False
                    # No fresh READY assertion may inherit cached execution facts.
                    unchanged_quote_hashes={o['source_response_sha256'] for p in pulse if p['kind']=='book'
                        for o in p['observations']}
                    same_source_admission=(utc(start)==utc(previous['completed_at_utc']) and all(
                        f['response_hash'] in unchanged_quote_hashes for packet in report.get('handoff_export',{}).get('research_handoffs',())
                        for f in packet['evidence'].values() if f['measurement']=='RESEARCH_PRICE'))
                    if report['shortlist']:
                        from .admission_facts import refresh_cached
                        cards,facts,references,refresh_faults,consumed=refresh_cached(report['handoff_export'],api,pulse,
                            members,completion['economics'],clock=evaluation_time,sources=sources,
                            refresh=not same_source_admission)
                        for observation in consumed:
                            observation['identity_hash']=identity[observation['native_symbol']]
                            if not any(x['fact']['id']==observation['fact']['id'] for x in report['consumed_obstacles']):
                                report['consumed_obstacles'].append(observation)
                        report['source_faults'].extend(refresh_faults)
                        fresh_reviews=[review_card(c,facts,[r for r in references if r.native_symbol==c.native_symbol],
                            as_of=evaluation_time()) for c in cards]
                        reviews=fresh_reviews
                        refreshed=shortlist(fresh_reviews,coverage=report['coverage'])
                        report['shortlist']=refreshed['shortlist']
                        for r in fresh_reviews:
                            if r['stage'] not in {'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'}:
                                report['near_misses'].append({**r,'admission_reason':'CACHED_ADMISSION_REASSESSED_WITH_CURRENT_POINT_SOURCES'})
                                if r['stage']=='LATE':report.setdefault('late',[]).append(r)
                        report['empty_shortlist_reason']=refreshed['empty_shortlist_reason']
                        report['reuse']['admission_revalidated_from_frozen_export']=True
                        report['reuse']['closed_history_replayed']=False
                    if recovery and report.get('conditional_research_export',{}).get('research_handoffs'):
                        from .handoff import decode_export
                        from .admission_facts import refresh_selected
                        saved=decode_export(report['conditional_research_export'])
                        cards=[c for c,own,refs in saved]
                        facts={i:f for c,own,refs in saved for i,f in own.items()}
                        references=list({r.id:r for c,own,refs in saved for r in refs}.values())
                        cards,depths,point_faults,at=refresh_selected(cards,facts,references,api,inventory,
                            completion['economics'],clock=evaluation_time,max_depth=recovery['targeted_depth_symbols'])
                        report['source_faults'].extend(point_faults)
                        reviews=[review_card(c,facts,[r for r in references if r.native_symbol==c.native_symbol],as_of=at) for c in cards]
                        report['reuse']['conditional_research_revalidated']=True
                else:
                    report['cache_key']=key
                    for scope,old in old_cutoffs.items():
                        tf=scope.rsplit(':',1)[-1]
                        if tf not in cutoffs:continue
                        delta=int((utc(cutoffs[tf])-utc(old['cutoff'])).total_seconds())
                        if delta>WIDTHS[tf]:
                            report['time_gaps'].append({'status':'GAP_UNOBSERVED','scope':scope,
                                'after':old['cutoff'],'before_current':cutoffs[tf],
                                'missed_closes':delta//WIDTHS[tf]-1,'symbols':old['symbols'],
                                'last_verified_run':old['run_key'],'reason':'NO_QUALIFIED_HISTORICAL_REMOTE_REPLAY',
                                'current_reconstruction_repairs_prospective_gap':False})
                    for w in prior_watches.values():
                        tf=w['timeframe'];last=w.get('last_verified_cutoff') or w.get('review',{}).get('event_window',[None,None])[1]
                        if last and (utc(cutoffs[tf])-utc(last)).total_seconds()>WIDTHS[tf]:
                            report['time_gaps'].append({'status':'GAP_UNOBSERVED','scope':'WATCH:'+w['id'],
                                'timeframe':tf,
                                'after':last,'before_current':cutoffs[tf],'symbols':[w['native_symbol']],
                                'last_viable_reference':w['reference'],
                                'reason':'CURRENT_PRICE_RECONSTRUCTION_CANNOT_PROVE_TIMELY_HISTORICAL_ACTIONABILITY',
                                'current_reconstruction_repairs_prospective_gap':False})
                    for gap in report['time_gaps']:
                        if sources.covered_gap(gap):
                            gap.update(status='HISTORY_INTERVAL_RECONSTRUCTED',
                                reason='QUALIFIED_CONTIGUOUS_SELECTED_SOURCE_HISTORY; NOT_PAST_READY_DISCOVERY',
                                historical_actionability_certified=False)
                    from .pack_contracts import contracts as pack_contracts
                    screen_inventory=inventory
                    if recovery:
                        from .audit import broad_order
                        tickers={o['native_symbol']:o for p in pulse if p['kind']=='ticker' for o in p['observations']}
                        ordered,report['broad_partition_policy']=broad_order(inventory.symbols,tickers,cutoffs['15m'],
                            active_watches=[w['native_symbol'] for w in previous.get('active_coin_watchlist',())] if previous else ())
                        screen_inventory=replace(inventory,instruments=tuple(members[n] for n in ordered))
                    qualified_packs={pid for pid,p in pack_contracts().items() if p.get('timeframe') and all(
                        pid in sources.qualified(n,p['timeframe'],cutoffs[p['timeframe']],field='packs',as_of=evaluation_time())
                        for n in members)}
                    report['resource_plan']=plan_resources(screen_inventory.symbols,cap=spec['max_screen_requests'],
                        qualified_packs=qualified_packs,samples=getattr(sources,'retained_receipts',()),fallback_qualified=True)
                    basis_unavailable=None
                    try:client.connect()
                    except (ContractError,OSError,KeyError,TypeError,ValueError) as e:
                        basis_unavailable=safe_error(e)
                        report['source_faults'].append({'phase':'basis_connect','code':basis_unavailable})
                    mark_stage('basis_handshake_and_resource_plan')
                    budget=RequestBudget(spec['max_screen_requests'],retry_calls=2,
                        interval_seconds=0 if mode!='LIVE' else 1,max_elapsed_seconds=120 if recovery else None)
                    screen_source=sources.screen_source or BasisScreenSource(client)
                    engine=PartitionEngine(screen_source,budget,deferred_tool_recovery=True,transient_recovery=bool(recovery),
                        unavailable_reason=basis_unavailable,anchor_first_response=bool(recovery),
                        max_pack_seconds=60 if recovery else None,
                        minimum_anchor_cutoff=previous.get('frozen_cutoffs',{}).get('15m')
                            if previous and previous.get('selected_research') else None)
                    rows_by_tf={}
                    for tf in ('15m','1h'):
                        price_columns=[c for c in spec['qualified_price_columns'] if c!='quote_rvol32']
                        from .pack_contracts import make_remote_pack
                        pack_id='CORE_'+('1H' if tf=='1h' else '15M')
                        if pack_id in qualified_packs:
                            pack=make_remote_pack(pack_id,inventory.eligible_symbols)
                            price_columns=[c[0] for c in pack.columns]
                        else:pack=make_pack(tf,inventory.eligible_symbols,price_columns)
                        result=engine.run(screen_inventory,pack,cutoffs[tf]);rows={}
                        if result.get('snapshot_anchor'):
                            anchor=result['snapshot_anchor'];cutoffs.update({t:closed_cutoff(anchor['frozen_cutoff'],t) for t in cutoffs})
                            report['snapshot_policy']=anchor
                            # No observation/history has been admitted before
                            # this first partition. Never rebase an existing run.
                            report['cache_key']=digest(encode([cutoffs,identity,spec,completion,recovery,mode,sources.certificates,
                                sources.nominations,sources.selected_inputs,route_ablation,context_prioritized,implementation]).encode())
                        for o in result.pop('observations'):
                            n=o['instrument']['native_symbol'];r=rows.setdefault(n,{'values':{},'evidence_ids':[],
                                'source_hashes':[],'received_at':o['received_at_utc'],'closed_close':o['source_closed_close']})
                            r['values'][o['measurement_id']]=o['value'];r['evidence_ids'].append(o['id'])
                            if o['source_response_hash'] not in r['source_hashes']:r['source_hashes'].append(o['source_response_hash'])
                        for n,r in rows.items():
                            # One cited row binds every exported column to the
                            # same partition/formula/window; don't persist 15
                            # redundant random hashes per symbol per snapshot.
                            r['evidence_ids']=[digest(encode([n,pack.formula_hash,cutoffs[tf],r['source_hashes']]).encode())]
                        result['evidence_id_scope']='EXACT_SYMBOL_ROW; ALL_DECLARED_COLUMNS; SOURCE_HASH_AND_PACK_HASH'
                        result['measurements']=rows;result['column_ids']=price_columns
                        result['operating_scope']='SOURCE_QUALIFIED_CORE; NOT_FULL_METHODS' if pack_id in qualified_packs else 'QUALIFIED_SAMPLED_PRICE_PRECURSORS; NOT_FULL_CORE_OR_METHODS'
                        result['numerical_qualification']={'scope':'SELECTED_SOURCE_ORACLE; NOT_EVERY_SYMBOL_HISTORY',
                            'evidence':spec['qualification_evidence'],'sha256':spec['qualification_sha256']}
                        result['requested']=len(result['requested_symbols']);result['evaluated']=len(result['evaluated_symbols'])
                        result['returned']=len(result['returned_symbols']);result['missing']=len(result['missing_symbols'])
                        result['failed']=len(result['failed_symbols']);result['unsupported']=0
                        result['not_requested']=len(result.get('not_requested_symbols',()))
                        result['time_accepted']=len(result.get('time_accepted_symbols',result['evaluated_symbols']))
                        result['selected_for_current_screen_count']=len(result.get('selected_for_current_screen',inventory.symbols))
                        result['rejected_after_cutoff_count']=len(result.get('rejected_after_cutoff',()))
                        result['per_formula']={f:{'eligible':len(members),'requested':result['requested'],
                            'evaluated':sum(r['values'].get(f) is not None for r in rows.values()),
                            'returned':result['returned'],'missing':result['missing'],
                            'failed':result['failed'],'unavailable':sum(r['values'].get(f) is None for r in rows.values()),
                            'unavailable_symbols':[n for n,r in rows.items() if r['values'].get(f) is None],
                            'unsupported':0,'units':next(c[2] for c in pack.columns if c[0]==f)} for f in price_columns}
                        report['packs'].append(result);rows_by_tf[tf]=rows
                        if rows:verified.append(('PRICE_PRECURSORS:'+tf,cutoffs[tf],tuple(rows)))
                    # Spend the existing ceiling on mandatory price packs first.
                    # Optional participation faults and budget omissions cannot
                    # erase price rows or starve the second timeframe.
                    if 'quote_rvol32' in spec['qualified_price_columns']:
                        for tf in ('15m','1h'):
                            optional=engine.run(screen_inventory,make_pack(tf,inventory.eligible_symbols,
                                ('quote_rvol32',)),cutoffs[tf])
                            values=optional.pop('observations');rows=rows_by_tf[tf]
                            for o in values:
                                n=o['instrument']['native_symbol']
                                if n in rows:
                                    rows[n]['values']['quote_rvol32']=o['value']
                                    rows[n]['evidence_ids'].append(o['id'])
                                    rows[n].setdefault('optional_source_hashes',[]).append(o['source_response_hash'])
                            optional['isolation']='OPTIONAL_ONLY; NEVER_INTERSECTS_PRICE_EVALUABILITY'
                            report['optional_packs'].append(optional)
                            parent=next(p for p in report['packs'] if p['timeframe']==tf)
                            parent['per_formula']['quote_rvol32']={'eligible':len(members),
                                'requested':len(optional['requested_symbols']),
                                'evaluated':sum(o['value'] is not None for o in values),
                                'returned':len(optional['returned_symbols']),
                                'failed':len(optional['failed_symbols']),'missing':len(optional['missing_symbols']),
                                'not_requested':len(optional.get('not_requested_symbols',())),
                                'unavailable':sum(o['value'] is None for o in values),'units':'QUOTE_VOLUME_RATIO',
                                'scope':'SEPARATE_OPTIONAL_PARTICIPATION_PACK'}
                    report['broad_budget']=budget.report()
                    registered_results=[]
                    for pid in sorted(qualified_packs):
                        if pid.startswith(('CORE_','PARTICIPATION_')):continue
                        pack=make_remote_pack(pid,inventory.eligible_symbols)
                        registered=engine.run(screen_inventory,pack,cutoffs[pack.timeframe])
                        registered_results.extend((pid,o) for o in registered.pop('observations'))
                        registered['qualification']='EXACT_REGISTERED_SOURCE_SCOPE; PRECURSOR_NOT_FULL_FORMATION'
                        report['optional_packs'].append(registered)
                    report['broad_budget']=budget.report()
                    report['coverage']['full_core_evaluated']=len(set.intersection(*(
                        set(p['evaluated_symbols']) for p in report['packs']))) if all(
                        p['operating_scope']=='SOURCE_QUALIFIED_CORE; NOT_FULL_METHODS' for p in report['packs']) else 0
                    # Separate finite event packs from long quiet/RVOL columns.
                    # The current qualified manual envelope adds ONE broad 1H
                    # causal pass; 15M/4H broad methods remain unqualified.
                    from .remote_structure import scan_registered,BITS,oracle_masks
                    source_schema=getattr(client,'tools',{}).get('screener_run',{}).get('inputSchema')
                    causal_enabled=(completion.get('enabled') and source_schema is not None
                        and digest(encode(source_schema).encode())==completion['screen_schema_sha256'])
                    remaining_transport=max(0,spec['max_http_requests']-len(client.http.receipts))
                    if causal_enabled and remaining_transport:
                        method_ceiling=min(completion['method_screen_requests'],remaining_transport)
                        method_budget=RequestBudget(method_ceiling,
                            retry_calls=min(completion['method_recovery_requests'],method_ceiling),
                            max_elapsed_seconds=30 if recovery else None)
                        method_engine=PartitionEngine(screen_source,method_budget,deferred_tool_recovery=True,transient_recovery=bool(recovery))
                        for tf in completion['causal_timeframes']:
                            cp=scan_registered(method_engine,screen_inventory,tf,cutoffs[tf],completion['qualified_bits'])
                            report['causal_packs'].append(cp)
                            if cp['evaluated_symbols']:verified.append(('METHOD_STRUCTURE:'+tf,cutoffs[tf],tuple(cp['evaluated_symbols'])))
                        report['causal_budget']=method_budget.report()
                    else:report['causal_status']='SOURCE_SCHEMA_NOT_ATTESTED; NO_CAUSAL_PROMOTION' if not causal_enabled else 'NOT_REVIEWED_BUDGET; BASIS_TRANSPORT_LIMIT'
                    mark_stage('basis_broad_and_causal_batches')
                    # Synchronized remote returns become breadth; rolling 24h
                    # tickers remain only turnover/economics/exception sources.
                    return_ids=[]
                    for n,r in rows_by_tf['1h'].items():
                        f=Fact(fact_id(n,cutoffs['1h'],'RETURN16'),members[n],'CLOSED_LOG_RETURN_16',
                            D(str(r['values']['progress16'])).ln(),'LOG_RETURN','1h',cutoffs['1h'],
                            r['received_at'],r['received_at'],r['received_at'],'BASIS_SAMPLED_QUALIFIED_PRICE',
                            r['source_hashes'][0],'EXACT_REPORTED',True,'QUALIFIED',mode,7200)
                        facts[f.id]=f;return_ids.append(f.id)
                    union={}
                    def nominate(n,tf,route,families,question):
                        if route_ablation is not None and route[0] not in route_ablation:return
                        k=(n,tf);r=rows_by_tf.get(tf,{}).get(n)
                        x=union.setdefault(k,{'native_symbol':n,'timeframe':tf,'routes':[], 'families':[],
                            'questions':[],'evidence_ids':r['evidence_ids'] if r else [],'cutoff':cutoffs[tf],
                            'stage':'PREMATURE','formation_supported':False})
                        x['routes']=list(dict.fromkeys(x['routes']+[route]));x['families']=list(dict.fromkeys(x['families']+list(families)))
                        x['questions'].append(question)
                    for tf,rows in rows_by_tf.items():
                        btc=rows.get('BTCUSDT',{}).get('values',{}).get('progress16')
                        for n,r in rows.items():
                            v=r['values'];quiet=v.get('quiet_percentile') is not None and D(str(v['quiet_percentile']))<=D('.25')
                            if quiet:nominate(n,tf,'C_QUIET',('F2','F3','F6'),'Does historical quiet attach to a pre-known decision reference?')
                            if v.get('pressure_upper') or v.get('pressure_lower'):
                                nominate(n,tf,'A_FIXED_WINDOW_PRESSURE_PRECURSOR',('F2','F4','F5','F6'),'Verify separated retreats and the same frozen reference chronology')
                            if v.get('displacement') is not None and D(str(v['displacement']))>=3:
                                nominate(n,tf,'A_POST_SHOCK_PRECURSOR',('F9',),'Has this price shock stabilized or made another extreme? No liquidation assertion.')
                            if btc is not None and abs(D(str(v['progress16']))/D(str(btc))-1)>=D('.015'):
                                nominate(n,tf,'C_RELATIVE_EXCEPTION',('F8','F1'),'Does lag-trained relative evidence survive local structure and peer checks?')
                    for pid,o in registered_results:
                        if o['value'] is None or D(str(o['value']))<=0:continue
                        families=('F1',) if 'CORRECTION' in pid else ('F3','F6') if 'QUIET' in pid else ('F2','F4','F5','F6')
                        nominate(o['instrument']['native_symbol'],o['timeframe'],'A_REGISTERED_PRECURSOR',families,
                            'Reconstruct the original frozen reference and event order; a scalar mask is only an initiating question')
                    for w in prior_watches.values():
                        n=w['native_symbol'];tf=w['timeframe']
                        if n in members and w['identity_hash']==identity[n]:nominate(n,tf,'C_SAVED_WATCH',w['families'],'Reassess original frozen reference without inventing missed events')
                    for n,i in members.items():
                        if i.onboard_at_utc and 0<=(utc(clock())-utc(i.onboard_at_utc)).total_seconds()<=30*86400:
                            nominate(n,'15m','C_NEW_LISTING',('F2','F3','F9'),
                                'Which shorter-history price structure is sourceable? Missing long baseline stays UNKNOWN.')
                    for cp in report['causal_packs']:
                        for n,positive in cp['positive_observations'].items():
                            families={family for x in positive for bit,(family,side) in BITS.items() if x['qualified_mask']&bit}
                            if families:
                                nominate(n,cp['timeframe'],'A_REMOTE_CAUSAL',sorted(families),
                                    'Verify the remote fixed-age confirmed pivot and ordered events, significance, first obstacle and friction')
                                if (n,cp['timeframe']) in union:union[n,cp['timeframe']]['remote_causal_evidence']=positive
                    # A uniform hash audit is independent of any price/volume
                    # screen and also supplies one native OI investigation lane.
                    from .audit import lottery,allocate
                    nominated_symbols={n for n,tf in union}
                    tail=[n for n in members if n not in {*nominated_symbols,'BTCUSDT','ETHUSDT'}]
                    audit_pool=tail or [n for n in members if n not in {'BTCUSDT','ETHUSDT'}]
                    audit_names=lottery(audit_pool,cutoffs['15m'])[:1]
                    ticker_rows={o['native_symbol']:o for p in pulse if p['kind']=='ticker' for o in p['observations']}
                    if recovery:
                        # Independent lightweight precursor questions for source
                        # gaps, stratified by turnover rather than a top-volume
                        # eligibility gate. These never establish a structure.
                        missing=[n for n in ticker_rows if n not in {'BTCUSDT','ETHUSDT'} and
                            all(n not in rows for rows in rows_by_tf.values())]
                        ordered=sorted(missing,key=lambda n:D(str(ticker_rows[n]['values']['quoteVolume'])))
                        cheap=[]
                        for j in range(4):
                            stratum=ordered[len(ordered)*j//4:len(ordered)*(j+1)//4]
                            cheap.extend(lottery(stratum,[cutoffs['15m'],'UNOBSERVED_TURNOVER',j])[:2])
                        for n in cheap:
                            nominate(n,'1h','C_UNOBSERVED_STRATIFIED_SOURCE_RECOVERY',('F1','F2','F3','F4','F8'),
                                'Source gap: inspect this stratified current-market observation without assuming a missed opportunity')
                            union[n,'1h']['evidence_ids']=[ticker_rows[n]['id']] if 'id' in ticker_rows[n] else [
                                ticker_rows[n]['source_response_sha256']]
                        report['cheap_missing_source_recovery']={'unobserved_pool':len(missing),'selected':cheap,
                            'selection':'TWO_HASH_SAMPLES_PER_TURNOVER_QUARTILE; NOT_A_METHOD_OR_OPPORTUNITY_CLAIM'}
                    report['prospective_audit']={'registered_at':evaluation_time(),'frozen_cutoffs':cutoffs,
                        'eligible_denominator':len(members),'eligible_set_hash':digest(encode(sorted(members)).encode()),
                        'non_nominated_tail_denominator':len(tail),'sampling':'UNIFORM_HASH_STRATUM_LOTTERY; ONE_SELECTED_PUBLIC_OI_AUDIT',
                        'sample':[{'symbol':n,'selection_probability':1/len(audit_pool),
                            'identity_hash':identity[n],'first_price_observation':ticker_rows.get(n),
                            'price_history_reviewed':False} for n in audit_names],
                        'cheap_baseline':{'top_return':sorted(ticker_rows,key=lambda n:D(str(ticker_rows[n]['values']['priceChangePercent'])),reverse=True)[:5],
                            'top_quote_turnover':sorted(ticker_rows,key=lambda n:D(str(ticker_rows[n]['values']['quoteVolume'])),reverse=True)[:5]},
                        'outcome':'PENDING_PROSPECTIVE_OBSERVATION; NO_EARLY_LEAD_TIME_OR_RECALL_CLAIM'}
                    for n in audit_names:
                        nominate(n,'1h','C_STRATIFIED_AUDIT',tuple(f'F{i}' for i in range(1,10)),
                            'Non-nominated-tail audit; no historical actionability reconstruction')
                    independent,specialist_faults=([],[]) if route_ablation is not None and 'B' not in route_ablation else sources.independent(as_of=evaluation_time(),eligible=members)
                    facts.update(sources.normalized_facts)
                    report['source_faults'].extend(specialist_faults)
                    for candidate in independent:
                        for family in candidate['families']:
                            nominate(candidate['native_symbol'],candidate['timeframe'],'B_SPECIALIST',(family,),candidate['questions'][0])
                        union[candidate['native_symbol'],candidate['timeframe']]['specialist_source']=candidate
                    if causal_enabled:
                        from .economic_sources import oi_observation
                        for n in ('BTCUSDT',*audit_names):
                            try:
                                oi=oi_observation(api,members[n]);report['specialist_observations'].append(oi)
                                observed_times.append(oi['received'])
                                if oi['nomination']:nominate(n,'1h','B_NATIVE_OI_CHANGE',('F9','F8'),
                                    'Native aggregate OI changed; discriminate price shock, carry and ordinary positioning without inferring direction')
                            except (ContractError,KeyError,TypeError,ValueError) as e:
                                report['source_faults'].append({'phase':'native_oi','symbol':n,'code':safe_error(e)})
                    report['nominations']=list(union.values())
                    selected={};benchmark_ids=[]
                    investigation_started=time.monotonic();history_costs=[]
                    def fetch_selected(names):
                        for n in names:
                            if n not in members:continue
                            if n in quarantined:
                                report['source_faults'].append({'phase':'contract_identity','symbol':n,'code':'CONTRACT_IDENTITY_CHANGED'})
                                continue
                            for tf in (('1h','15m','4h') if n in {'BTCUSDT','ETHUSDT'} else ('1h','15m')):
                                elapsed=time.monotonic()-investigation_started
                                estimate=sum(history_costs)/len(history_costs) if history_costs else 1
                                if recovery and n in {'BTCUSDT','ETHUSDT'} and elapsed>=45:
                                    report.setdefault('investigation_deferred',[]).append({'native_symbol':n,'timeframe':tf,
                                        'reason':'CONTEXT_SOURCE_COST_RESERVE_FOR_INDEPENDENT_ALT_RESEARCH',
                                        'elapsed_seconds':elapsed})
                                    continue
                                if (recovery and n not in {'BTCUSDT','ETHUSDT'} and
                                        elapsed+estimate>recovery['investigation_wall_seconds']):
                                    report.setdefault('investigation_deferred',[]).append({'native_symbol':n,'timeframe':tf,
                                        'reason':'MEASURED_INVESTIGATION_WALL_BUDGET','elapsed_seconds':elapsed,
                                        'estimated_next_history_seconds':estimate})
                                    continue
                                fetched_at=time.monotonic()
                                try:
                                    bars,source=api.klines(members[n],timeframe=tf,cutoff=cutoffs[tf])
                                    selected[n,tf]=(bars,source)
                                    observed_times.append(source['receipt']['received_at_utc'])
                                    if n in {'BTCUSDT','ETHUSDT'} and tf in {'1h','4h'}:
                                        f=benchmark_fact(bars,members[n],as_of=evaluation_time(),mode=mode,qualification='QUALIFIED')
                                        facts[f.id]=f;benchmark_ids.append(f.id)
                                except (ContractError,KeyError,ValueError,TypeError) as e:
                                    report['source_faults'].append({'phase':'targeted_history','symbol':n,'timeframe':tf,'code':safe_error(e)})
                                finally:history_costs.append(time.monotonic()-fetched_at)
                    fetch_selected(('BTCUSDT','ETHUSDT'))
                    context=build_context(facts,as_of=evaluation_time(),eligible_symbols=inventory.eligible_symbols,
                        eligible_known=True,benchmark_ids=benchmark_ids,return_ids=return_ids)
                    report['context']=asdict(context)
                    # Separate watch, exception and structural allocations. All
                    # remaining questions retain NOT_REVIEWED_BUDGET explicitly.
                    if recovery:
                        from .audit import investigate
                        mean_cost=sum(history_costs)/len(history_costs) if history_costs else 1
                        remaining=max(0,recovery['investigation_wall_seconds']-(time.monotonic()-investigation_started))
                        adaptive_capacity=min(recovery['operational_alt_capacity'],max(0,
                            int(remaining/max(.001,2*mean_cost))-spec['max_targeted_alt_symbols']))
                        alt,allocations,allocation_study=investigate(list(union.values()),context,cutoffs,
                            rows_by_tf,ticker_rows,protected=spec['max_targeted_alt_symbols'],
                            capacity=adaptive_capacity)
                        allocation_study.update(configured_operational_ceiling=recovery['operational_alt_capacity'],
                            measured_history_mean_seconds=mean_cost,remaining_history_seconds=remaining,
                            adaptive_operational_capacity=adaptive_capacity)
                    else:
                        alt,allocations,allocation_study=allocate(list(union.values()),context,cutoffs,
                            limit=spec['max_targeted_alt_symbols'])
                    report['allocation_study']=allocation_study
                    report['targeted_allocation']=allocations
                    for sample in report['prospective_audit']['sample']:
                        sample['price_history_reviewed']=sample['symbol'] in alt
                    report['not_reviewed_budget']=[{**n,'reason':'NOT_REVIEWED_BUDGET'} for n in union.values()
                        if n['native_symbol'] not in {*alt,'BTCUSDT','ETHUSDT'}]
                    fetch_selected(alt)
                    mark_stage('nomination_context_and_selected_history')
                    investigated={n for n,tf in selected if n not in {'BTCUSDT','ETHUSDT'}}
                    report['investigation_funnel']={'planned_alt_symbols':alt,'actual_alt_symbols':sorted(investigated),
                        'actual_non_context_alt_count':len(investigated),
                        'aligned_history_symbol_timeframes':[{'native_symbol':n,'timeframe':tf,
                            'cutoff':s['cutoff'],'bars':len(b),'source_hash':s['source_response_sha256']}
                            for (n,tf),(b,s) in selected.items() if n not in {'BTCUSDT','ETHUSDT'}],
                        'history_wall_seconds':time.monotonic()-investigation_started,
                        'observed_mean_history_seconds':sum(history_costs)/len(history_costs) if history_costs else None,
                        'protected_audit_budget':spec['max_targeted_alt_symbols'],
                        'operational_capacity':recovery.get('operational_alt_capacity',0),
                        'wall_budget_seconds':recovery.get('investigation_wall_seconds'),
                        'official_endtime_fallback':[{'native_symbol':n,'timeframe':tf,
                            'reason':'REMOTE_ROW_UNAVAILABLE_AT_FROZEN_CUTOFF','source_hash':s['source_response_sha256']}
                            for (n,tf),(b,s) in selected.items() if n not in rows_by_tf.get(tf,{}) and tf!='4h']}
                    report['nominee_dispositions']=[{'native_symbol':n,'timeframe':tf,'routes':x['routes'],
                        'disposition':'INVESTIGATED' if (n,tf) in selected else
                            'DEFERRED_BUDGET' if any(d['native_symbol']==n and d['timeframe']==tf
                                for d in report.get('investigation_deferred',())) else
                            'SOURCE_GAP' if n in alt else 'DEFERRED_BUDGET',
                        'recheck':'NEXT_ON_DEMAND_RUN; RETAIN_NOMINATION_AND_SOURCE_IDS',
                        'evidence_ids':x['evidence_ids']} for (n,tf),x in union.items()]
                    if (causal_enabled or sources.certificates) and not recovery:
                        from .economic_sources import depth_snapshot
                        for n in alt[:recovery.get('targeted_depth_symbols',len(alt))]:
                            try:
                                depth=depth_snapshot(api,members[n]);report['economic_observations'].append(depth)
                                observed_times.append(depth['received'])
                            except (ContractError,KeyError,TypeError,ValueError) as e:
                                report['source_faults'].append({'phase':'native_depth','symbol':n,'code':safe_error(e)})
                    # Only decision-relevant current economics are refreshed;
                    # top-of-book never becomes depth or an actual fee tier.
                    econ_ids={};economics=api.pulse(inventory,partial=True,kinds=('book','premium'))
                    report['current_economics_health']=[{**{k:v for k,v in p.items() if k!='observations'},
                        'accepted':len(p['observations'])} for p in economics]
                    report['current_economics']={n:[] for n in ('BTCUSDT','ETHUSDT',*alt)}
                    for p in economics:
                        for o in p['observations']:
                            n=o['native_symbol']
                            if n not in report['current_economics']:continue
                            report['current_economics'][n].append(o)
                            if p['kind']!='book':continue
                            for measurement,value,unit in [('RESEARCH_PRICE',(o['values']['bid']+o['values']['ask'])/2,'USDT_PER_BASE'),
                                ('SPREAD_BPS',o['values']['spread_bps'],'BPS')]:
                                f=Fact(fact_id(n,measurement,o['source_response_sha256']),members[n],measurement,value,unit,'CURRENT',
                                    o['source_time_utc'],o['source_time_utc'],o['received_at_utc'],o['received_at_utc'],
                                    'OFFICIAL_BINANCE_TOP_OF_BOOK',o['source_response_sha256'],'EXACT_REPORTED',True,'QUALIFIED',mode,30,
                                    cluster='EXECUTION_FRICTION')
                                facts[f.id]=f;econ_ids.setdefault(n,[]).append(f.id)
                    as_of=evaluation_time()
                    planner=QueryPlanner()
                    for (n,tf),(bars,source) in selected.items():
                        if tf=='4h':continue
                        if route_ablation is not None and n not in {'BTCUSDT','ETHUSDT'} and (n,tf) not in union:continue
                        bench=selected.get(('BTCUSDT',tf))
                        family=selected_family_facts(bars,members[n].tick_size,as_of=as_of,
                            benchmark=bench[0] if bench and len(bench[0])==len(bars) else None)
                        report['selected_research'].append({'native_symbol':n,'timeframe':tf,'source':source,
                            'family_facts':family,'gap_lifecycles':gap_lifecycle(bars,members[n].tick_size,as_of=as_of),
                            'scope':'TARGETED_CURRENT_HISTORICAL_RECONSTRUCTION; NOT_PROSPECTIVE_DISCOVERY'})
                        if recovery:
                            from .numerics import relative_quote_volume,anchored_value
                            from statistics import median
                            values={'close':bars[-1].close,'progress16':bars[-1].close/bars[-17].close,
                                'prior_high16':max(b.high for b in bars[-17:-1]),
                                'prior_low16':min(b.low for b in bars[-17:-1]),
                                'quote_rvol32':relative_quote_volume(bars)}
                            remote=rows_by_tf.get(tf,{}).get(n,{}).get('values',{})
                            checks=[]
                            for label,independent in values.items():
                                actual=remote.get(label)
                                if actual is not None and independent is not None:
                                    tolerance=max(D('1e-9'),abs(independent)*D('1e-8'))
                                    checks.append({'measurement':label,'remote':actual,'independent':independent,
                                        'tolerance':tolerance,'passed':abs(D(str(actual))-independent)<=tolerance})
                            session_ms=bars[-1].open_ms//86400000*86400000
                            session=[b for b in bars if b.open_ms>=session_ms]
                            from datetime import datetime,timezone
                            vwap=anchored_value(session,anchor_ms=session_ms,
                                anchor_known_at=datetime.fromtimestamp(session_ms/1000,
                                    timezone.utc).isoformat()) if session and session[0].open_ms==session_ms else None
                            report['selected_research'][-1]['live_measurements']={
                                'quote_rvol32':values['quote_rvol32'],'quote_rvol_source':'OFFICIAL_CLOSED_QUOTE_VOLUME; LAST_33_BARS',
                                'quote_rvol_independent_ratio':bars[-1].quote_volume/median(b.quote_volume for b in bars[-33:-1])
                                    if median(b.quote_volume for b in bars[-33:-1])>0 else None,
                                'session_whole_bar_q_over_v':vwap,
                                'session_q_over_v_independent':sum((b.quote_volume for b in session),D(0))/sum(
                                    (b.base_volume for b in session),D(0)) if session and sum((b.base_volume for b in session),D(0))>0 else None,
                                'independent_remote_checks':checks,'source_hash':source['source_response_sha256'],
                                'qualification':'SELECTED_TIMESTAMPED_ARITHMETIC; NOT_COMPLETE_METHOD_QUALIFICATION'}
                        # Cite actual selected bars. They were first available
                        # to this researcher at retrieval, never backdated.
                        for b in bars:
                            facts[b.id]=Fact(b.id,members[n],'SELECTED_CLOSED_BAR',{'close':b.close},'USDT_PER_BASE',tf,
                                b.end,b.end,b.received_at,b.received_at,'OFFICIAL_BINANCE_SELECTED',b.source_hash,
                                'EXACT_REPORTED',True,'QUALIFIED',mode,300*WIDTHS[tf])
                        terminal_ids={r[0] for r in ledger.db.execute('SELECT reference_id FROM lifecycle WHERE at<=?',(as_of,))}
                        all_swings=swing_references(bars,members[n].tick_size,as_of=as_of)
                        # Reopen the original watch even when a rolling selected
                        # pivot list would no longer propose it from scratch.
                        for w in prior_watches.values():
                            if w['native_symbol']!=n or w['timeframe']!=tf or w['id'] in terminal_ids:continue
                            raw={k:v for k,v in w['reference'].items() if k!='id'}
                            for field in ('lo','hi','atr','tick'):raw[field]=D(str(raw[field]))
                            raw['source_ids']=tuple(raw['source_ids']);old_ref=Reference(**raw)
                            if utc(old_ref.valid_until)<utc(as_of):continue
                            if not all(i in facts for i in old_ref.source_ids):
                                report.setdefault('watch_refresh_faults',[]).append({'watch_id':w['id'],
                                    'status':'SOURCE_COVERAGE_LOST','reason':'ORIGINAL_REFERENCE_SOURCE_OUTSIDE_SELECTED_WINDOW'})
                            elif old_ref.id not in {r.id for r in all_swings}:all_swings.append(old_ref)
                        from .engine_capabilities import analyze_selected,qualified_route_a
                        analytical_refs=all_swings
                        if recovery:
                            live_refs=[r for r in all_swings if utc(r.valid_until)>=utc(as_of) and
                                max(r.lo-bars[-1].close,bars[-1].close-r.hi,D(0))<=4*r.atr]
                            # Current research investigates current decision
                            # zones. Every other reference remains in the archive
                            # and first-obstacle search, with a named disposition.
                            analytical_refs=sorted(live_refs,key=lambda r:(
                                max(r.lo-bars[-1].close,bars[-1].close-r.hi,D(0))/r.atr,
                                -utc(r.known_at).timestamp(),r.id))
                            allowance=max(4,min(12,int(60/max(1,sum(history_costs)/len(history_costs)))))
                            analytical_refs=analytical_refs[:allowance]
                            report.setdefault('reference_investigation_dispositions',[]).append({
                                'native_symbol':n,'timeframe':tf,'available_references':len(all_swings),
                                'current_references_evaluated':[r.id for r in analytical_refs],
                                'archive_only_outside_current_radius':[r.id for r in all_swings if r not in live_refs],
                                'deferred_reference_budget':[r.id for r in live_refs if r not in analytical_refs],
                                'scope':'CURRENT_RESEARCH_ALLOCATION; ALL_FROZEN_REFERENCES_RETAINED_AS_OBSTACLES',
                                'allowance_from_measured_source_cost':allowance})
                        report['selected_research'][-1]['analytical_engine']=analyze_selected(
                            bars,members[n].tick_size,cutoff=cutoffs[tf],as_of=as_of,
                            benchmark=bench[0] if bench and len(bench[0])==len(bars) else None,
                            references=analytical_refs,inputs=sources.inputs_for(n,tf,cutoffs[tf],as_of),
                            current_episodes=bool(recovery))
                        report['selected_research'][-1]['analytical_source_gaps']=[{
                            'family':h['family'],'status':h['status'],'reason':h.get('details',{}),
                            'source_hash':source['source_response_sha256'],'cutoff':cutoffs[tf],
                            'opportunity_absence_established':False}
                            for h in report['selected_research'][-1]['analytical_engine']['families']
                            if h['status'] not in {'COMPUTED','NO_EVENT_IN_COMPLETE_WINDOW'}]
                        # The registered adapter is exercised in ordinary scans,
                        # while current new full-family source gates stay closed.
                        report['selected_research'][-1]['analytical_route_a']=qualified_route_a(
                            report['selected_research'][-1]['analytical_engine'],None,
                            native_symbol=n,timeframe=tf,cutoff=cutoffs[tf])
                        # Wider selected reference metadata supplies the actual
                        # first opposing obstacle; no universe history download.
                        obstacle_refs=[ledger.freeze_reference(r) for r in all_swings if r.id not in terminal_ids]
                        remote_rows=next((cp['positive_observations'].get(n,[]) for cp in report['causal_packs'] if cp['timeframe']==tf),[])
                        native_masks=oracle_masks(bars[-299:])
                        exported_masks={label:next((D(x['mask']) for x in remote_rows if x['column']==label),D(0))
                            for label in ('boundary_8','boundary_12','boundary_16')}
                        compared=next((cp for cp in report['causal_packs'] if cp['timeframe']==tf and n in cp['evaluated_symbols']),None)
                        masks_match=native_masks==exported_masks
                        if compared is not None:
                            compared.setdefault('selected_independent_verifications',[]).append({'symbol':n,
                                'source_response_hash':source['source_response_sha256'],'cutoff':cutoffs[tf],
                                'native_masks':native_masks,'remote_masks':exported_masks,'passed':masks_match})
                            if not masks_match:
                                compared['qualification']='REVOKED_SELECTED_ORACLE_MISMATCH'
                                compared['qualified_method_predicates_evaluated']=0
                        remote_ages={x['pivot_age'] for x in remote_rows if x['qualified_mask']}
                        remote_refs=[r for r in all_swings if any(utc(r.created_at).timestamp()*1000==bars[-1-age].open_ms for age in remote_ages)]
                        proposed=[*(analytical_refs[-4:] if recovery else all_swings[-4:]),*remote_refs,
                            *equal_level_references(bars,members[n].tick_size,as_of=as_of)[-2:]]
                        refs=list({r.id:ledger.freeze_reference(r) for r in proposed if r.id not in terminal_ids}.values())
                        references.extend(r for r in [*obstacle_refs,*refs] if r.id not in {v.id for v in references})
                        for r in obstacle_refs:
                            if r.id not in {v.id for v in refs}:bundles.append((r,[],[]))
                        new_cards,new_refs,new_bundles=formation_cards(
                            report['selected_research'][-1]['analytical_engine'],members[n],facts,
                            cutoff=cutoffs[tf],as_of=as_of,mode=mode,
                            qualified_families=sources.qualified(n,tf,cutoffs[tf],as_of=as_of),
                            origins=tuple(union.get((n,tf),{}).get('routes',())) or ('C_SELECTED_FORMATION',),
                            initiator_methods=tuple([union[n,tf]['specialist_source']['specialist_method']]) if
                                (n,tf) in union and 'specialist_source' in union[n,tf] else (),
                            freeze=ledger.freeze_reference)
                        references.extend(r for r in new_refs if r.id not in {v.id for v in references})
                        bundles.extend(new_bundles)
                        for c in new_cards:
                            c=replace(c,evidence_ids=(*c.evidence_ids,*econ_ids.get(n,())))
                            from .admission_facts import attach
                            depth=next((d for d in report['economic_observations'] if d['native_symbol']==n),None)
                            added,assessment=attach(c,facts,obstacle_refs,bars,members[n],source,depth,
                                completion['economics'],as_of=as_of)
                            cards.append(replace(c,evidence_ids=added))
                        for ref in refs:
                            result=boundary_events(ref,bars,as_of=as_of)
                            bundles.append((ref,result['events'],result['hypotheses']))
                            primary=max((h for h in result['hypotheses'] if h['family'] in {'F2','F4','F5'}),
                                key=lambda h:(h['current_formation_verdict']=='SUPPORTED',len(h['supporting_ids']),h['family']))['family']
                            fid=fact_id(ref.id,cutoffs[tf],'CAUSAL')
                            remote_families={family for row in remote_rows for bit,(family,side) in BITS.items()
                                if row['qualified_mask']&bit and side==ref.direction
                                and utc(ref.created_at).timestamp()*1000==bars[-1-row['pivot_age']].open_ms}
                            causal_qualified=primary in remote_families and masks_match
                            facts[fid]=Fact(fid,members[n],'CAUSAL_SEQUENCE',True,'BOOLEAN',tf,cutoffs[tf],
                                source['receipt']['received_at_utc'],source['receipt']['received_at_utc'],source['receipt']['received_at_utc'],
                                'TARGETED_CAUSAL_RECONSTRUCTION',source['source_response_sha256'],
                                'SYNCHRONIZED_REMOTE_RECONSTRUCTION',True,'QUALIFIED' if causal_qualified else 'TRIAL',mode,2*WIDTHS[tf])
                            card=boundary_card(ref,result,cutoff=cutoffs[tf],evidence_ids=(fid,*econ_ids.get(n,())),primary_family=primary,
                                mode=mode,origins=('A_REMOTE_CAUSAL' if causal_qualified else 'C_TARGETED_SOURCE_BACKED_CAUSAL_WATCH',),
                                qualification='QUALIFIED' if causal_qualified else 'TRIAL')
                            if ref.origin.startswith('EQH_EQL:'):card=replace(card,method_ids=('M04','M05'))
                            if completion.get('enabled'):
                                from .admission_facts import attach
                                depth=next((d for d in report['economic_observations'] if d['native_symbol']==n),None)
                                added,assessment=attach(card,facts,obstacle_refs,bars,members[n],source,depth,
                                    completion['economics'],as_of=as_of)
                                card=replace(card,evidence_ids=added)
                                report.setdefault('admission_assessments',[]).append({'card_id':card.id,**assessment})
                            cards.append(card)
                    # The same bounded planner runs for every interpreted card.
                    # A query must document alternative dispositions before I/O.
                    if recovery:
                        archive=[];current_groups={}
                        for c in cards:
                            primary=next(h for h in c.hypotheses if h.family==c.primary_family)
                            latest=(c.formation['families'][c.primary_family]['timeline'][-1] if c.formation else
                                c.events[-1] if c.events else None)
                            bars=selected[c.native_symbol,c.timeframe][0]
                            d=max(c.reference.lo-bars[-1].close,bars[-1].close-c.reference.hi,D(0))/c.reference.atr
                            reason=('REFERENCE_EXPIRED' if utc(c.reference.valid_until)<utc(as_of) else
                                'PRIMARY_CAUSAL_CONTRADICTION' if primary.contradicting_ids else
                                'NO_CURRENT_SUPPORTING_EVENT' if not primary.supporting_ids or not latest else
                                'HISTORICAL_EVENT_OUTSIDE_RESEARCH_HORIZON' if (utc(as_of)-utc(latest['known_at'])).total_seconds()>54000 else
                                'OUTSIDE_CURRENT_REFERENCE_RADIUS' if d>4 else None)
                            if reason:
                                archive.append({'card_id':c.id,'native_symbol':c.native_symbol,'family':c.primary_family,
                                    'reference_id':c.reference.id,'disposition':reason,'distance_atr':d})
                            else:current_groups.setdefault((c.native_symbol,c.primary_family),[]).append((c,d,latest))
                        cards=[]
                        for group in current_groups.values():
                            group.sort(key=lambda x:(x[1],-utc(x[2]['known_at']).timestamp(),x[0].id))
                            # One primary case per family/coin; independent TF
                            # and reference alternatives remain in the ledger.
                            cards.append(group[0][0])
                            archive.extend({'card_id':c.id,'native_symbol':c.native_symbol,'family':c.primary_family,
                                'reference_id':c.reference.id,'disposition':'ALTERNATIVE_SAME_FAMILY_REFERENCE',
                                'distance_atr':d} for c,d,latest in group[1:])
                        report['historical_case_dispositions']=archive
                        report['investigation_funnel']['current_interpreted_card_count']=len(cards)
                        report['investigation_funnel']['archived_or_alternative_card_count']=len(archive)
                    from .context import investigation_order
                    cards=investigation_order(cards,context,prioritized=context_prioritized)
                    report['context_questions']={'actual_order':'CONTEXT_PRIORITY' if context_prioritized else 'NEUTRAL',
                        'agenda':context.agenda,'raw_nomination_set_unchanged':True,
                        'verification_allowance':dict(planner.budgets),'eligibility_or_direction_veto':False}
                    for index,c in enumerate(cards):
                        # A quoted crossing witnessed in an earlier voluntary
                        # run remains consumed even if price later returns before
                        # another completed candle. Never skip that obstacle.
                        carried=[]
                        for observation in report['consumed_obstacles']:
                            if (observation['candidate_reference_id']==c.reference.id
                                    and observation['event_window_start']==c.window_start
                                    and observation['identity_hash']==identity[c.native_symbol]):
                                from .contracts import Instrument
                                raw=observation['fact'];witness=Fact(**{**raw,'instrument':Instrument(**raw['instrument'])})
                                facts[witness.id]=witness;carried.append(witness.id)
                        if carried:c=replace(c,evidence_ids=tuple(dict.fromkeys((*c.evidence_ids,*carried))))
                        refs_for=[r for r in references if r.native_symbol==c.native_symbol]
                        before=review_card(c,facts,refs_for,as_of=as_of)
                        own_ids=set(c.evidence_ids)|set(c.reference.source_ids)|{i for e in c.events for i in e['source_ids']}
                        answers,decisions=planner.investigate(c,decision_questions(before),sources.questions(c,as_of,before),
                            {i:facts[i] for i in own_ids},as_of=as_of,adapters=sources.adapters,max_steps=6)
                        facts.update(answers)
                        added=tuple(i for i in answers if i not in own_ids and answers[i].instrument.native_symbol==c.native_symbol)
                        cards[index]=replace(c,evidence_ids=tuple(dict.fromkeys((*c.evidence_ids,*added))))
                        after=review_card(cards[index],facts,refs_for,as_of=as_of) if added else before
                        for decision in decisions:
                            q=decision.get('question')
                            report['planner'].append({'card_id':c.id,'status':decision['status'],
                                'next_fact':q.fact if q else None,'possible_decision_changes':q.changes if q else (),
                                'query_id':decision['query'].key if decision.get('query') else None,
                                'shared_source_gap_key':decision.get('source_gap_key'),
                                'stage_before':before['stage'],'stage_after':after['stage'],
                                'rival_or_admission_changed':decision['status'] in {'QUERY','CACHED'} and (
                                    before['stage']!=after['stage'] or before['economics']!=after['economics']
                                    or before['room']!=after['room'] or before['missing_necessary_inputs']!=after['missing_necessary_inputs'])})
                    report['question_audit']=planner.audit
                    report['planner_raw_hypothesis_links']=len(report['planner'])
                    consolidated={};meaningful=[]
                    for p in report['planner']:
                        key=p.get('shared_source_gap_key') or ('NO_MORE_DECISIVE_QUESTIONS' if
                            p['status']=='STOP_NO_DECISION_CHANGING_QUERY' else None)
                        if key and not p['rival_or_admission_changed']:
                            if key not in consolidated:
                                consolidated[key]={**p,'affected_card_ids':[],'shared_gap_reuses':0}
                                meaningful.append(consolidated[key])
                            consolidated[key]['affected_card_ids'].append(p['card_id'])
                            consolidated[key]['shared_gap_reuses']+=1
                        else:meaningful.append(p)
                    report['planner']=meaningful
                    if recovery:
                        from .admission_facts import refresh_selected
                        cards,depths,point_faults,as_of=refresh_selected(cards,facts,references,api,inventory,
                            completion['economics'],clock=evaluation_time,max_depth=recovery['targeted_depth_symbols'])
                        report['economic_observations'].extend(depths);report['source_faults'].extend(point_faults)
                        from .method_engine import specialist_method
                        for sample in report['selected_research']:
                            depth=next((d for d in depths if d['native_symbol']==sample['native_symbol']),None)
                            if depth:
                                observed=specialist_method('M25',snapshot=depth)
                                observed.update(source_hash=depth['source_hash'],source_time=depth['time'],
                                    scope='CURRENT_DISPLAYED_DEPTH_ONLY; NO_PERSISTENT_WALL_OR_EXECUTED_ABSORPTION')
                                sample['analytical_engine']['methods']=[observed if m['method_id']=='M25' else m
                                    for m in sample['analytical_engine']['methods']]
                    reviews=[review_card(c,facts,[r for r in references if r.native_symbol==c.native_symbol],as_of=as_of) for c in cards]
                    mark_stage('structure_methods_questions_and_point_refresh')
                    if native_review_dir is not None and recovery.get('native_pre_admission_enabled'):
                        from .candidate_review import native_review_selection
                        from .agent_review import exchange
                        wanted,selection=native_review_selection(reviews,cards,facts,references,as_of=as_of,max_cards=native_max_cards)
                        from .candidate_review import conditional_research
                        provisional,_=conditional_research(reviews,cards,facts,references,as_of=as_of)
                        native_reviews=[*reviews,*provisional]
                        pre_cards=sorted((c for c in cards if c.id in wanted),key=lambda c:wanted.index(c.id))
                        report['native_review_phase']='PRE_ADMISSION_CURRENT_COIN_HYPOTHESES'
                        report['native_selection']=selection
                        native_prepared=time.monotonic()
                        report['consultant']=exchange(native_review_dir,pre_cards,facts,as_of=evaluation_time(),
                            context=report.get('context'),reviews=native_reviews,max_cards=native_max_cards,ordered_card_ids=wanted)
                        stage_times['native_request_preparation']=round(time.monotonic()-native_prepared,6)
                        stage_started=time.monotonic()
                        if native_audit_config and report['consultant']['status']=='AWAITING_NATIVE_APP_RESPONSE':
                            import sqlite3
                            try:
                                from .native_app import wait_for_reply
                                receipt=wait_for_reply(native_review_dir,report['consultant']['material_sha256'],
                                    native_audit_config,wait_seconds=native_wait_seconds,clock=evaluation_time)
                                report['consultant']=exchange(native_review_dir,(),{},as_of=evaluation_time(),
                                    previous=report['consultant'],cached=True)
                                report['consultant']['native_collector']=receipt
                                if receipt['status']=='NATIVE_RECEIPT_COLLECTED':
                                    report['llm_calls']=receipt['observed_model_attempts']
                            except (ContractError,OSError,sqlite3.Error,ValueError,TypeError,KeyError,RecursionError):
                                report['consultant']['native_collector']={'status':'NATIVE_RECEIPT_UNAVAILABLE_DETERMINISTIC_FALLBACK'}
                            mark_stage('owner_and_native_wait_and_answer_import')
                            # Actual time advances during a native turn; point
                            # quotes/depth must be independently refreshed.
                            cards,depths,point_faults,as_of=refresh_selected(cards,facts,references,api,inventory,
                                completion['economics'],clock=evaluation_time,max_depth=0)
                            report['source_faults'].extend(point_faults)
                            reviews=[review_card(c,facts,[r for r in references if r.native_symbol==c.native_symbol],as_of=as_of) for c in cards]
                    revoked_tfs={p['timeframe'] for p in report['causal_packs'] if p['qualification']=='REVOKED_SELECTED_ORACLE_MISMATCH'}
                    for r in reviews:
                        if r['reference']['timeframe'] in revoked_tfs and r['stage'] in {'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'}:
                            r['stage']='UNKNOWN';r['reason_code']='REMOTE_CAUSAL_ORACLE_MISMATCH'
                            r['missing_necessary_inputs'].append('REQUALIFIED_REMOTE_CAUSAL_SOURCE')
                    if report.get('clock_anomalies'):
                        for r in reviews:
                            if r['stage'] in {'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'}:
                                r['stage']='UNKNOWN';r['reason_code']='CLOCK_COHERENCE_UNQUALIFIED'
                                r['missing_necessary_inputs'].append('CLOCK_COHERENCE')
                    reviewed=shortlist(reviews,coverage=report['coverage'])
                    for field in ('shortlist','near_misses','invalidations'):report[field]=reviewed[field]
                    report['late']=reviewed['late']
                    report['empty_shortlist_reason']=reviewed['empty_shortlist_reason']
                    watch_rows={}
                    for r in reviewed['watches']:
                        ref=r['reference'];wid=ref['id'];prior=prior_watches.get(wid)
                        if wid in watch_rows:
                            w=watch_rows[wid]
                            w['families']=tuple(sorted(set(w['families'])|set(r['family_ids'])))
                            w['interpretations'].append({'card_id':r['card_id'],'family':r['primary_family'],
                                'stage':r['stage'],'reason':r['reason_code'],'next_question':r['next_deep_analyst_question']})
                            continue
                        watch_rows[wid]={'id':wid,'native_symbol':r['instrument'],'timeframe':ref['timeframe'],
                            'families':r['family_ids'],'identity_hash':identity[r['instrument']],
                            'first_seen':prior['first_seen'] if prior else as_of,'last_checked':as_of,
                            'last_verified_cutoff':cutoffs[ref['timeframe']],
                            'reference':ref,'stage':r['stage'],'review':r,'next_review':r['trigger_to_investigate'],
                            'interpretations':[{'card_id':r['card_id'],'family':r['primary_family'],
                                'stage':r['stage'],'reason':r['reason_code'],'next_question':r['next_deep_analyst_question']}],
                            'gap_status':'GAP_UNOBSERVED' if any(g['status']=='GAP_UNOBSERVED' and r['instrument'] in g['symbols']
                                for g in report['time_gaps']) else None}
                    report['watches'].extend(watch_rows.values())
                    known={w['id'] for w in report['watches']}|{r['reference']['id'] for r in report['invalidations']}
                    for w in prior_watches.values():
                        if w['id'] in known:continue
                        reason=('DELISTED_OR_CHANGED_CONTRACT_IDENTITY' if w['native_symbol'] not in identity or
                            identity[w['native_symbol']]!=w['identity_hash'] else 'REFERENCE_EXPIRED' if
                            utc(w['reference']['valid_until'])<utc(as_of) else None)
                        if reason:
                            report['invalidations'].append({'watch_id':w['id'],'reason':reason,'last_viable_reference':w['reference']})
                            raw={k:v for k,v in w['reference'].items() if k!='id'}
                            for k in ('lo','hi','atr','tick'):raw[k]=D(str(raw[k]))
                            raw['source_ids']=tuple(raw['source_ids'])
                            ref=Reference(**raw)
                            if ref.id not in {t[0].id for t in terminals}:
                                terminals.append((ref,'EXPIRED' if reason=='REFERENCE_EXPIRED' else 'INVALIDATED',as_of))
                        else:report['watches'].append({**w,'stage':'UNKNOWN','last_checked':as_of,
                            'gap_status':'GAP_UNOBSERVED','next_review':'Original reference not covered by this bounded selected history; reassess current validity'})
                    report['context_order_study']=matched_budget_study(cards,context,min(len(cards),4))
                    report['cache_reusable']=all(p['evaluated']>0 and not p['truncated_attempts'] for p in report['packs'])
                    report['coverage']['targeted_symbol_timeframes']=len(selected)
                    report['coverage']['targeted_causal_references']=len(cards)
                    report['coverage']['price_precursors_by_timeframe']={p['timeframe']:{
                        **{k:p[k] for k in ('requested','evaluated','returned','missing','failed','unsupported')},
                        'eligible':len(members),'columns':len(p['column_ids']),
                            'quiet_percentile_at_most_025':sum(r['values'].get('quiet_percentile') is not None and
                                D(str(r['values']['quiet_percentile']))<=D('.25') for r in p['measurements'].values())}
                        for p in report['packs']}
                    report['coverage']['methods_by_timeframe']={tf:{m['id']:{'eligible':len(members),'remote_evaluated':0,
                        'remote_requested':0,'remote_returned':0,'remote_missing':0,'remote_failed':0,
                        'targeted_only':len({c.native_symbol for c in cards if c.timeframe==tf and m['id'] in c.method_ids}),
                        'unsupported_or_unqualified':len(members),'remote_evaluable':None,
                        'qualified_remote_evaluated':0,'full_method_unqualified':len(members),
                        'remote_unsupported':len(members),'excluded_contracts':len(inventory.excluded),
                        'reason':m['remote_qualification']} for m in report['method_coverage']['methods']} for tf in ('1h','15m','4h')}
                    for cp in report['causal_packs']:
                        for mid in ('M03','M05'):
                            cov=report['coverage']['methods_by_timeframe'][cp['timeframe']][mid]
                            cov.update(remote_requested=cp['requested'],remote_evaluated=cp['evaluated'],
                                remote_returned=cp['returned'],remote_failed=cp['failed'],remote_missing=cp['missing'],
                                remote_evaluable=cp['evaluated'],qualified_remote_evaluated=cp['qualified_method_predicates_evaluated'],
                                remote_unsupported=cp['unsupported'],qualification=cp['qualification'],
                                unsupported_or_unqualified=cp['unsupported'],complete_method_evaluated=0,
                                predicate_scope='SOURCE_QUALIFIED_FIXED_AGE_BOUNDARY_F2_LOWER_F4_F5_NOMINATION_SUBCLASS',
                                reason='FULL_METHOD_NOT_CLAIMED; F2_UPPER_POSITIVE_UNQUALIFIED; TARGETED_TICK_AND_INITIATIVE_CHECKS_REQUIRED')
                    report['coverage']['production_remote_method_evaluated']=sum(p['qualified_method_predicates_evaluated'] for p in report['causal_packs'])
                    report['coverage']['families_by_timeframe']={tf:{f'F{i}':{
                        'eligible':len(members),'remote_predicate_requested':next((p['requested'] for p in report['causal_packs'] if p['timeframe']==tf),0) if i in (2,4,5) else 0,
                        'remote_predicate_evaluated':next((p['evaluated'] for p in report['causal_packs'] if p['timeframe']==tf),0) if i in (2,4,5) else 0,
                        'complete_family_evaluated':0,'status':'NARROW_CAUSAL_NOMINATION' if i in (2,4,5) and tf=='1h' and report['causal_packs'] else 'TARGETED_OR_UNQUALIFIED'}
                        for i in range(1,10)} for tf in ('1h','15m','4h')}
                    # Selected algorithm execution and qualified formation are
                    # distinct from broad coverage, including valid no-events.
                    from .engine_capabilities import manifest as analytical_manifest
                    capabilities=analytical_manifest(config)
                    report['research_coverage']={'version':'research-coverage-6b.1',
                        'scope':'SELECTED_HISTORY_ALGORITHM_EXECUTION; REMOTE_LEDGER_HAS_SEPARATE_SCOPE','by_timeframe':{}}
                    for tf in ('1h','15m','4h'):
                        engines=[s for s in report['selected_research'] if s['timeframe']==tf]
                        rows={}
                        for kind,ids in [('families',[f'F{i}' for i in range(1,10)]),
                                         ('methods',[f'M{i:02d}' for i in range(1,32)])]:
                            rows[kind]={}
                            for mid in ids:
                                results=[(s['native_symbol'],r) for s in engines for r in s['analytical_engine'][kind]
                                    if r.get('family',r.get('method_id'))==mid]
                                evaluated={n for n,r in results if r['status'] in {'COMPUTED','NO_EVENT_IN_COMPLETE_WINDOW'}}
                                positive={n for n,r in results if bool(r.get('timeline')) or r.get('value') not in (None,[],{})}
                                supported={n for n in evaluated if mid in sources.qualified(n,tf,cutoffs[tf],
                                    field=kind,as_of=as_of)}
                                state=next(r['status'] for r in capabilities[kind] if r['id']==mid)
                                rows[kind][mid]={'eligible':ir['eligible_contracts'],
                                    'scope_inventory':len(members),'requested':len({n for n,r in results}),
                                    'evaluated':len(evaluated),'returned':len(evaluated),'positive_or_nonempty_result':len(positive),
                                    'source_qualified_selected':len(supported),'source_unqualified_selected':len(evaluated-supported),
                                    'unsupported':len(members) if state in {'SOURCE_CAPABILITY_REQUIRED','DEFINITION_PENDING'} and not supported else 0,
                                    'not_evaluated_budget':len({x['native_symbol'] for x in report['not_reviewed_budget'] if x['timeframe']==tf}),
                                    'failed_or_history_unknown':[{'symbol':n,'status':r['status']} for n,r in results
                                        if r['status'] not in {'COMPUTED','NO_EVENT_IN_COMPLETE_WINDOW'}],
                                    'code_state':state,'live_eligible_universe_coverage':False,
                                    'empirical_discovery_usefulness':'UNMEASURED'}
                        report['research_coverage']['by_timeframe'][tf]=rows
                    report['route_coverage']={route:{'eligible':ir['eligible_contracts'],
                        'unit':'UNIQUE_SYMBOL_TIMEFRAME',
                        'requested':len({(x['native_symbol'],x['timeframe']) for x in union.values() if any(r.startswith(route+'_') for r in x['routes'])}),
                        'evaluated':len({(n,tf) for n,tf in selected if (n,tf) in union
                            and any(r.startswith(route+'_') for r in union[n,tf]['routes'])}),
                        'returned':len({(n,tf) for n,tf in selected if (n,tf) in union
                            and any(r.startswith(route+'_') for r in union[n,tf]['routes'])}),
                        'hypothesis_card_records':len({c.id for c in cards if any(r.startswith(route+'_') for r in c.origins)}),
                        'not_evaluated_budget':len([x for x in report['not_reviewed_budget'] if any(r.startswith(route+'_') for r in x['routes'])]),
                        'unsupported':len(members) if route=='B' and not independent else 0,
                        'failed':len(specialist_faults) if route=='B' else 0} for route in ('A','B','C')}
                    report['research_comparisons']=reviewed['pairwise_comparison']
                    report['family_fronts']=reviewed['family_fronts'];report['exposure_groups']=reviewed['exposure_groups']
                    # Detectors execute in full; reports retain decisions and
                    # content hashes rather than replicate each method's large
                    # shared reference/event graph dozens of times.
                    for s in report['selected_research']:
                        analytical=s['analytical_engine']
                        analytical['methods']=[{k:v for k,v in m.items() if k!='value'} |
                            {'value_sha256':digest(encode(m['value']).encode())} for m in analytical['methods']]
                        analytical['families']=[{k:v for k,v in h.items() if k not in {'timeline','reference'}} |
                            {'ordered_event_ids':[e['id'] for e in h['timeline']]} for h in analytical['families']]
                    def compact_disposition(row):
                        return {k:v for k,v in row.items() if k not in {'formation_contract','source_coverage','events'}} | {
                            'ordered_event_ids':[e['id'] for e in row.get('events',())],
                            'last_event':{k:v for k,v in row['events'][-1].items() if k in
                                {'id','kind','known_at','available_at','source_ids'}} if row.get('events') else None,
                            'source_hashes':sorted({v['response_hash'] for v in row.get('source_coverage',{}).values()}),
                            'source_graph':'ATOMIC_RESEARCH_LEDGER; ORIGINAL_SELECTED_SOURCE_HASHES'}
                    for field in ('invalidations','near_misses','late'):
                        report[field]=[compact_disposition(r) for r in report.get(field,())]
                    for w in report['watches']:
                        if 'review' in w:w['review']=compact_disposition(w['review'])
            except (ContractError,KeyError,TypeError,ValueError,IndexError) as e:
                report['source_faults'].append({'phase':'scan','code':safe_error(e)})
                report['cache_reusable']=False
                report['shortlist']=[]
                report['operating_mode']='CONTEXT_ONLY_DEGRADED' if 'inventory' in report else 'PAUSE_UNQUALIFIED'
                if previous:
                    report['watches']=[{**w,'stage':'UNKNOWN','gap_status':'GAP_UNOBSERVED',
                        'next_review':'Source recovery required; retain last viable frozen reference'} for w in previous['watches']]
            receipts=[*api.http.receipts,*client.http.receipts];durations=sorted(r['elapsed_ms'] for r in receipts)
            report['request_receipts']=receipts;report['completed_at_utc']=evaluation_time()
            if report['shortlist'] and cards:
                # Admission evidence may age while the remaining cards are
                # reviewed. Validate the exported shortlist at completion too.
                by_card={c.id:c for c in cards};fresh_handoffs=[]
                for old in report['shortlist']:
                    checked=review_card(by_card[old['card_id']],facts,
                        [r for r in references if r.native_symbol==old['instrument']],as_of=report['completed_at_utc'])
                    if checked['stage'] in {'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'}:fresh_handoffs.append(checked)
                    else:report['near_misses'].append({**checked,'admission_reason':'SOURCE_OR_CUTOFF_AGED_BEFORE_EXPORT'})
                report['shortlist']=fresh_handoffs
            if previous and previous.get('prospective_audit'):
                current={o['native_symbol']:o for p in pulse if p['kind']=='ticker' for o in p['observations']} if 'pulse' in locals() else {}
                follow=[]
                for sample in previous['prospective_audit']['sample']:
                    old=sample.get('first_price_observation');new=current.get(sample['symbol'])
                    if old and new and report.get('inventory',{}).get('identity_hashes',{}).get(sample['symbol'])==sample['identity_hash']:
                        follow.append({'symbol':sample['symbol'],'from':old['received_at_utc'],'to':new['received_at_utc'],
                            'observed_gross_return':D(str(new['values']['lastPrice']))/D(str(old['values']['lastPrice']))-1,
                            'interpretation':'SHORT_ELAPSED_POINT_OBSERVATIONS; NOT_PROFITABILITY_OR_FULL_UNIVERSE_RECALL'})
                report['prospective_follow_up']=follow
            from .handoff import make_export,consult_changed_cards
            if not cached and report.get('native_review_phase'):
                report['llm_status']=report['consultant']['status']
            elif recovery and native_review_dir is not None:
                # A source failure before the pre-admission phase cannot fall
                # through to the old post-admission request publisher.
                report['consultant']={**consult_changed_cards(cards),
                    'status':'NATIVE_PRE_ADMISSION_UNAVAILABLE_OR_UNCHANGED; NO_POST_ADMISSION_FALLBACK'}
            elif native_review_dir is None:
                report['consultant']=consult_changed_cards(cards)
            else:
                from .agent_review import exchange
                native_cards=() if cached and same_source_admission else cards
                report['consultant']=exchange(native_review_dir,native_cards,facts,as_of=report['completed_at_utc'],
                    context=report.get('context'),reviews=reviews,cached=cached,
                    previous=previous.get('consultant') if previous else None,max_cards=native_max_cards)
                if native_audit_config and report['consultant']['status'] in {'AWAITING_NATIVE_APP_RESPONSE','NATIVE_REPLY_UNAUDITED_DETERMINISTIC_FALLBACK'}:
                    import sqlite3
                    try:
                        from .native_app import wait_for_reply
                        receipt=wait_for_reply(native_review_dir,report['consultant']['material_sha256'],
                            native_audit_config,wait_seconds=native_wait_seconds,clock=evaluation_time)
                        report['completed_at_utc']=evaluation_time()
                        report['consultant']=exchange(native_review_dir,(),{},as_of=report['completed_at_utc'],
                            previous=report['consultant'],cached=True)
                        report['consultant']['native_collector']=receipt
                        if receipt['status']=='NATIVE_RECEIPT_COLLECTED':
                            report['llm_calls']=receipt['observed_model_attempts']
                    except (ContractError,OSError,sqlite3.Error,ValueError,TypeError,KeyError,RecursionError):
                        report['consultant']['native_collector']={'status':'NATIVE_RECEIPT_UNAVAILABLE_DETERMINISTIC_FALLBACK'}
                    report['completed_at_utc']=evaluation_time()
                    # Native waiting never freezes an earlier economic admission.
                    current=[]
                    for old in report['shortlist']:
                        c=next(c for c in cards if c.id==old['card_id'])
                        checked=review_card(c,facts,[r for r in references if r.native_symbol==c.native_symbol],
                            as_of=report['completed_at_utc'])
                        if checked['stage'] in {'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'}:current.append(checked)
                        else:report['near_misses'].append({**checked,'admission_reason':'EVIDENCE_AGED_DURING_NATIVE_REVIEW'})
                    report['shortlist']=current
                report['llm_status']=report['consultant']['status']
            report['time_integrity_status']='CLOCK_UNCERTAINTY; NO_READY' if report.get('clock_anomalies') else 'NORMAL'
            if report.get('clock_anomalies') and report['shortlist']:
                for r in report['shortlist']:
                    report['near_misses'].append({**r,'stage':'UNKNOWN','reason_code':'CLOCK_COHERENCE_UNQUALIFIED'})
                report['shortlist']=[]
            if recovery:
                from .candidate_review import conditional_research,active_coin_watches
                current_reviews=[review_card(c,facts,[r for r in references if r.native_symbol==c.native_symbol],
                    as_of=report['completed_at_utc']) for c in cards]
                report['active_coin_watchlist']=active_coin_watches(current_reviews,as_of=report['completed_at_utc'])
                if cached:
                    from .candidate_review import refresh_cached_watches
                    report['active_coin_watchlist'],report['cached_watch_source_gaps']=refresh_cached_watches(
                        prior_active_coins,pulse,as_of=report['completed_at_utc'])
                report['watch_counts']={'active_unique_coins':len(report['active_coin_watchlist']),
                    'historical_reference_records':len(report['watches']),
                    'historical_unique_coins':len({w['native_symbol'] for w in report['watches']}),
                    'semantics':'ACTIVE_CURRENT_COIN_HYPOTHESES_SEPARATE_FROM_REFERENCE_ARCHIVE'}
                candidates,dispositions=conditional_research(current_reviews,cards,facts,references,
                    as_of=report['completed_at_utc']) if recovery.get('conditional_research_enabled') and not report.get('clock_anomalies') else ([],[])
                from .candidate_review import apply_native_research_advice
                candidates,dispositions,native_comparison=apply_native_research_advice(candidates,dispositions,
                    report.get('consultant',{}),as_of=report['completed_at_utc'])
                report['native_control_comparison']=native_comparison
                report['conditional_research_candidates']=candidates
                report['conditional_research_dispositions']=dispositions
                report['conditional_research_policy']={'owner_approved':True,'blueprint_sections':['1.1','11.3','11.4'],
                    'strict_ready_gates_changed':False,'full_method_qualification_changed':False,
                    'trade_authorization':False,'deep_analyst_connected':False}
                report['conditional_research_export']=make_export({**report,'shortlist':candidates},cards,facts,references)
                report['coverage']['price_observed_symbols']=sorted({n for p in report['packs'] for n in p['evaluated_symbols']})
                report['coverage']['observed_symbols']=sorted({n for p in [*report['packs'],*report['causal_packs']]
                    for n in p['evaluated_symbols']})
                report['coverage']['observed_symbols_scope']='AT_LEAST_ONE_TIME_ACCEPTED_REGISTERED_REMOTE_PRICE_OR_NARROW_CAUSAL_PACK; NOT_FULL_CORE'
                report['coverage']['unobserved_symbols']=sorted(set(report.get('inventory',{}).get('identity_hashes',{}))-
                    set(report['coverage']['observed_symbols']))
                report['coverage']['remote_family_ledger_scope']='REMOTE_FIXED_AGE_NOMINATION_PREDICATES_ONLY'
                report['invalidation_counts']={kind:sum(r.get('invalidation_kind')==kind or
                    r.get('reason')==('REFERENCE_EXPIRED' if kind=='EXPIRY' else 'DELISTED_OR_CHANGED_CONTRACT_IDENTITY')
                    for r in report['invalidations']) for kind in ('EXPIRY','CAUSAL_CONTRADICTION','IDENTITY')}
                report['invalidation_counts']['interpretation']='REFERENCE_OR_HYPOTHESIS_RECORDS; NOT_TRADES_OR_LOSSES'
                from collections import Counter
                report['historical_case_disposition_counts']=dict(Counter(
                    r['disposition'] for r in report.get('historical_case_dispositions',())))
                report['invalidation_counts']['archived_expiry_records']=report['historical_case_disposition_counts'].get('REFERENCE_EXPIRED',0)
                report['invalidation_counts']['archived_contradiction_records']=report['historical_case_disposition_counts'].get('PRIMARY_CAUSAL_CONTRADICTION',0)
            if not cached or cards:report['handoff_export']=make_export(report,cards,facts,references)
            elif not report['shortlist']:
                report['handoff_export']=make_export(report,(),{},())
            mark_stage('final_review_exports_and_report')
            native=report.get('consultant',{}).get('native_receipt',{})
            native_start=native.get('native_started_at_utc');native_end=native.get('native_completed_at_utc')
            native_trace=(utc(native_end)-utc(native_start)).total_seconds() if native_start and native_end else None
            native_wait=stage_times.get('owner_and_native_wait_and_answer_import',0)
            report['costs']={'http_requests':len(receipts),'response_bytes':sum(r.get('response_bytes') or 0 for r in receipts),
                'request_body_bytes':sum(r.get('request_body_bytes') or 0 for r in receipts),
                'request_url_bytes':sum(r.get('request_url_bytes') or 0 for r in receipts),
                'request_header_bytes':'NOT_MEASURED; PRIVATE_HEADERS_NOT_RETAINED',
                'wall_ms':round((time.monotonic()-wall)*1000),'sum_latency_ms':sum(durations),
                'p50_ms':durations[(len(durations)-1)//2] if durations else None,
                'p95_ms':durations[math.ceil(.95*len(durations))-1] if durations else None,
                'basis_charged_units':None,'quota':'UNKNOWN','sustainable_cadence':'UNQUALIFIED','llm_calls':report['llm_calls'],
                'llm_call_semantics':'COMPLETED_NATIVE_PROVIDER_ASSISTANT_ATTEMPTS_OBSERVED_DURING_OPT_IN_REVIEW; INCOMPLETE_NATIVE_TURNS_UNKNOWN',
                'cached_snapshot_reused':cached,'targeted_kline_calls':api.sample_calls}
            report['costs']['wall_breakdown_seconds']=dict(stage_times)
            report['costs']['deterministic_market_seconds_excluding_interactive_wait']=round(time.monotonic()-wall-native_wait,6)
            report['costs']['native_execution_seconds']=native_trace
            report['costs']['owner_wait_before_native_seconds']=max(0,(utc(native_start)-utc(
                report['consultant']['request_created_at_utc'])).total_seconds()) if native_start else None
            report['costs']['timing_scope']='PERSISTENCE_AND_CLI_PRINT_MEASURED_SEPARATELY; API_LATENCY_IS_INCLUDED_IN_STAGES'
            cpu=os.times()
            report['costs']['process_resources']={'scan_cpu_user_seconds':cpu.user-cpu_start.user,
                'scan_cpu_system_seconds':cpu.system-cpu_start.system,'process_peak_rss_kib':None,
                'scope':'PORTABLE_PROCESS_CPU; PEAK_RSS_NOT_MEASURED'}
            report['costs']['by_provider']={name:{'http_requests':len(rows),
                'response_bytes':sum(r.get('response_bytes') or 0 for r in rows),
                'request_body_bytes':sum(r.get('request_body_bytes') or 0 for r in rows),
                'request_url_bytes':sum(r.get('request_url_bytes') or 0 for r in rows),
                'p50_ms':sorted(r['elapsed_ms'] for r in rows)[(len(rows)-1)//2] if rows else None,
                'p95_ms':sorted(r['elapsed_ms'] for r in rows)[math.ceil(.95*len(rows))-1] if rows else None}
                for name,rows in [('binance',api.http.receipts),('basis',client.http.receipts)]}
            report['last_verified_observation_cutoffs']=old_cutoffs
            report['run_key']=digest(encode([report.get('cache_key'),report['completed_at_utc'],report['costs']]).encode())
            # Merge event DAG fragments before a single chronological ledger
            # upsert; sibling families must not append earlier events later.
            grouped={}
            for ref,events,hypotheses in bundles:
                item=grouped.setdefault(ref.id,[ref,{},{}])
                for e in events:item[1][e['id']]=e
                for h in hypotheses:item[2][h['id']]=h
            merged_bundles=[(ref,sorted(events.values(),key=lambda e:(utc(e['known_at']),e['id'])),list(hs.values()))
                for ref,events,hs in grouped.values()]
            report['run_id']=report['run_key'];report['as_of_utc']=report['completed_at_utc']
            report['parameter_versions']={'interpretation':'6b.1','resource_plan':'6b.1','family_engine':'6a.1',
                'recovery':recovery.get('version'),'current_episode_selection':bool(recovery)}
            body={'schema_version':report['research_shortlist_version'],'run_id':report['run_id'],
                'as_of_utc':report['as_of_utc'],'mode':report['evidence_mode'],
                'source_revisions':{'inventory':report.get('inventory',{}).get('content_sha256'),
                    'capability':report['capability_revision'],'manifest_sha256':digest(MANIFEST.read_bytes()),
                    'source_provenance':report['offline_source_provenance']},'parameter_versions':report['parameter_versions'],
                **{k:report.get(k) for k in ('shortlist','near_misses','invalidations','late',
                    'not_reviewed_budget','context','research_coverage','route_coverage','resource_plan',
                    'source_faults','clock_anomalies','time_gaps','question_audit','consumed_obstacles','costs')},
                **{k:report.get(k) for k in ('conditional_research_candidates','conditional_research_policy',
                    'active_coin_watchlist','watch_counts','investigation_funnel','nominee_dispositions','invalidation_counts')},
                'research_advice':report['consultant'],
                'watches':[{k:v for k,v in w.items() if k!='review'} for w in report['watches']],
                'trade_authorization':False,'new_orders_created':0}
            report['research_shortlist']={**body,'payload_sha256':digest(encode(body).encode())}
            persistence_started=time.monotonic()
            ledger.finish(attempt,report['run_key'],report,bundles=merged_bundles if not cached else (),verified=verified,
                terminals=terminals,crash_hook=crash_hook)
        report['persistence']=ledger.metrics();report['last_verified_observation_cutoffs']=ledger.cutoffs()
        report['persistence']['wall_seconds']=round(time.monotonic()-persistence_started,6)
        report['persistence']['total_wall_seconds']=round(time.monotonic()-wall,6)
        report['output_payload_sha256']=digest(encode({k:v for k,v in report.items() if k not in {'persistence','output_payload_sha256'}}).encode())
        return report
    finally:ledger.close()


def research_summary(report):
    """Small operator view; full source citations remain in JSON/SQLite."""
    from .contracts import number
    lines=[f"OpenBot Market Researcher — {report['release_status']} ({report['mode']})",
        f"Eligible contracts: {report['coverage']['eligible_contracts']}; strict handoffs: {len(report['shortlist'])}; conditional research candidates: {len(report.get('conditional_research_candidates',()))}"]
    if report.get('completed_at_utc'):lines[0]+=' | As of '+report['completed_at_utc']
    for p in report['packs']:
        lines.append(f"{p['timeframe']}: {len(p['column_ids'])} remote precursors; requested {p['requested']}, price evaluated {p['evaluated']}, returned {p['returned']}, missing {p['missing']}, failed {p['failed']}")
        if 'quote_rvol32' in p['per_formula']:
            q=p['per_formula']['quote_rvol32'];lines.append(f"  Quote RVOL {'NOT_REQUESTED' if not q['requested'] else 'REQUESTED'}; evaluated {q['evaluated']}/{q['requested']} requested ({q['eligible']} eligible); deferred {q.get('not_requested',0)}, unavailable {q.get('unavailable',0)}, requested failures {q['failed'] if q['requested'] else 0}")
    for p in report.get('causal_packs',()):
        lines.append(f"{p['timeframe']} causal nomination templates: evaluated {p['evaluated']}/{p['requested']} requested ({p['eligible_contracts']} eligible); requested-but-absent {p['missing']}; deferred {len(p.get('not_requested_symbols',()))}; full-method coverage remains partial")
    lines.append(f"Active watch coins: {len(report.get('active_coin_watchlist',()))}; historical watch reference records: {len(report['watches'])}; near misses: {len(report['near_misses'])}; expired/contradicted records: {len(report['invalidations'])}; not reviewed within budget: {len(report['not_reviewed_budget'])}")
    if report.get('investigation_funnel'):
        lines.append(f"Structurally investigated non-context coins: {report['investigation_funnel']['actual_non_context_alt_count']}; protected audit and operational capacity are separate.")
    lines.append(f"Unobserved gaps: {len(report['time_gaps'])}; HTTP calls: {report['costs']['http_requests']}; bytes: {report['costs']['response_bytes']}; wall: {report['costs']['wall_ms']/1000:.1f}s")
    if report.get('consultant',{}).get('status') not in {None,'LLM_DISABLED_NO_APPROVED_PROVIDER'}:
        lines.append(f"Native review: {report['consultant']['status']}; validated cards: {report['consultant'].get('accepted',0)}; observed model attempts this scan: {report.get('llm_calls',0)}.")
    for r in report.get('conditional_research_candidates',()):
        ref=r['reference'];room=r['research_room']
        lines.append(f"#{r.get('rank','?')} {r['instrument']} {r['side_hypothesis']} {ref['timeframe']} / {r['primary_family']} — CONDITIONAL_RESEARCH_ONLY")
        lines.append(f"  Zone {ref['lo']}–{ref['hi']}; distance {number(r['distance_atr_at_verification']):.2f} ATR; {room['status']}"+
            (f" ({number(room['room_bps']):.1f} bps to {room['level']})" if room.get('room_bps') is not None else f": {room['reason']}"))
        rival=r['strongest_rival'];rival=rival.get('family','UNKNOWN') if isinstance(rival,dict) else rival
        questions={'SOURCE_GAP':'Resolve the named missing inputs before strengthening this thesis',
            'FIRST_OBSTACLE':'Verify the first same-coin opposing obstacle and its lifecycle',
            'NEXT_CLOSED_RESPONSE':'Check the next completed candle against this frozen zone',
            'SAME_REFERENCE_RIVAL':'Discriminate the supplied rivals at the original reference'}
        lines.append(f"  Rival: {rival}; next: {questions.get(r['analyst_question'],r['analyst_question'])}")
        if r.get('current_price'):
            lines.append(f"  Price {r['current_price']['value']} at {r['current_price']['source_time']}; spread {number(r['current_spread_bps']['value']):.2f} bps.")
        event_ids=set(r.get('necessary_sequence_event_ids',()))
        events=[e for e in r.get('events',()) if not event_ids or e['id'] in event_ids]
        if events:lines.append('  Sequence: '+' → '.join(e['kind']+'@'+e['known_at'] for e in events[-3:]))
        lines.append('  Evidence: '+', '.join(r['supporting_evidence_ids'][:2])+f"; reference expires {r['expiry']}; trade_authorization=false")
        lines.append('  Missing: '+', '.join(r.get('missing_evidence',())[:5]))
    if report.get('active_coin_watchlist'):
        lines.append('Active coins: '+', '.join(w['native_symbol'] for w in report['active_coin_watchlist']))
    timing=report.get('costs',{})
    if timing.get('deterministic_market_seconds_excluding_interactive_wait') is not None:
        lines.append(f"Market/analysis: {timing['deterministic_market_seconds_excluding_interactive_wait']:.1f}s; owner/native wait+import: {timing['wall_breakdown_seconds'].get('owner_and_native_wait_and_answer_import',0):.1f}s; native execution: {timing.get('native_execution_seconds')}s.")
    if report.get('reuse'):lines.append('Reused unchanged closed-bar evidence; refreshed official inventory and current economics.')
    if not report['shortlist'] and not report.get('conditional_research_candidates'):lines.append('No research handoff under the observed evidence and gates. This does not establish that no opportunities exist.')
    lines.append('Full CORE/all-method coverage remains unqualified; narrow causal templates and selected public depth/OI are separate. Read-only; no orders or scheduling.')
    if report['source_faults']:lines.append('Source faults: '+', '.join(f['code'] for f in report['source_faults']))
    return '\n'.join(lines)


def watch_summary(report):
    from .contracts import number
    lines=[f"Active watch coins — as of {report['completed_at_utc']}; trade_authorization=false"]
    for w in report.get('active_coin_watchlist',()):
        p=w['primary'];ref=p['reference']
        lines.append(f"#{w['rank']} {w['native_symbol']} {p['side_hypothesis']} {ref['timeframe']} {p['primary_family']} / {p['stage']}; {number(p['distance_atr_at_verification']):.2f} ATR from {ref['lo']}–{ref['hi']}; next: {p['trigger_to_investigate']}")
    lines.append(f"{len(report.get('active_coin_watchlist',()))} active unique coins; {len(report['watches'])} archived reference records.")
    return '\n'.join(lines)


def coverage_summary(report):
    from collections import Counter
    lines=[f"Coverage — {report['completed_at_utc']}; eligible {report['coverage']['eligible_contracts']}"]
    for p in report['packs']:
        lines.append(f"{p['timeframe']} cutoff {p['cutoff_utc']}: considered {p.get('selected_for_current_screen_count')}; requested {p['requested']}; returned {p['returned']}; timestamp-qualified/evaluated {p['evaluated']}; requested absent {p['missing']}; deferred {p.get('not_requested',0)}; rejected {p['failed']}; unsupported {len(p.get('unsupported_symbols',()))}")
    lines.append('Nominees: '+str(dict(Counter(x['disposition'] for x in report.get('nominee_dispositions',())))))
    lines.append(f"Investigated alts {report.get('investigation_funnel',{}).get('actual_non_context_alt_count',0)}; conditional {len(report.get('conditional_research_candidates',()))}; strict READY {len(report['shortlist'])}.")
    lines.append('All F1–F9/M01–M31 retained. M14/M15 definition-pending; true profile/footprint/executed absorption/liquidations, dated sectors and catalysts require actual sources. Full per-method results: show coverage --json.')
    return '\n'.join(lines)
