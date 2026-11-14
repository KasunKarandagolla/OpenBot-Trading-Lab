"""On-demand external observations and coverage. No detector or trading path."""
from dataclasses import asdict
from .basis import BasisMCP
from .contracts import Coverage, ContractError, ResearchReport, digest, encode, now_utc, utc
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


def scan_market_research(*,api=None,client=None,config=None,ledger_path=None,clock=now_utc,
                         mode='LIVE',crash_hook=None,sources=None,context_prioritized=True,route_ablation=None):
    """One on-demand read-only path: live sources → remote packs → saved research.

    Historical price precursors nominate questions independently. Only two
    selected alts receive causal history alongside BTC/ETH context; this cannot
    establish market-wide family detection or repair unsupported specialists.
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
    if route_ablation is not None and (mode!='SYNTHETIC' or not set(route_ablation)<={'A','B','C'}):
        raise ContractError('OFFLINE_REPLAY_SCOPE')
    sources=sources or ResearchSources(mode=mode)
    if sources.mode!=mode:raise ContractError('SOURCE_QUALIFICATION_CONTRACT')
    wall=time.monotonic();start=clock();config=config or load_config();validate_config(config)
    import resource
    cpu_start=resource.getrusage(resource.RUSAGE_SELF)
    spec=config['session5'];cutoffs={tf:closed_cutoff(start,tf) for tf in ('1h','15m','4h')}
    completion=config.get('session55',{})
    api=api or OfficialResearchAPI()
    client=client or BasisMCP(PublicHTTP(max_requests=spec['max_http_requests']),qualification=True,session5=True,session6a=True)
    ledger=RunLedger(ledger_path or ROOT/'work/research-metadata.sqlite')
    report={'schema_version':'openbot.market-research.v5','environment':'CODEX_LOCAL' if mode=='LIVE' else 'OFFLINE_REPLAY_HOST','mode':mode,
        'created_at_utc':start,'frozen_cutoffs':cutoffs,'operation_status':'BLOCKED_OR_UNQUALIFIED',
        'release_status':'PARTIAL','operating_mode':'PAUSE_UNQUALIFIED','shortlist':[],'watches':[],
        'near_misses':[],'invalidations':[],'not_reviewed_budget':[],'time_gaps':[],
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
    bundles=[];verified=[];terminals=[];facts={};cards=[];references=[];cached=False
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
                report['identity_quarantine']=sorted(quarantined)
                # Obstacle-only frozen metadata has no watch row. Delisting or
                # changed identity must retire those references as well.
                for raw in ledger.active_references(evaluation_time()):
                    if raw['native_symbol'] not in members or raw['native_symbol'] in quarantined:
                        raw={**raw}
                        for field in ('lo','hi','atr','tick'):raw[field]=D(str(raw[field]))
                        raw['source_ids']=tuple(raw['source_ids'])
                        terminals.append((Reference(**raw),'INVALIDATED',evaluation_time()))
                pulse=api.pulse(inventory,partial=True)
                report['source_health']=[{**{k:v for k,v in p.items() if k!='observations'},
                    'accepted':len(p['observations']),'eligible':len(members)} for p in pulse]
                report['operation_status']='PARTIAL';report['operating_mode']='REMOTE_WIDE_PARTIAL'
                key=digest(encode([cutoffs,identity,spec,completion,mode,sources.certificates,route_ablation,context_prioritized,'interpretation-6b.1']).encode())
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
                    if report['shortlist'] and not same_source_admission:
                        report['near_misses']=[*report['near_misses'],*[
                            {**r,'stage':'UNKNOWN','reason_code':'CACHED_HANDOFF_REQUIRES_FRESH_ADMISSION_REVIEW'} for r in report['shortlist']]]
                        report['shortlist']=[]
                        report['empty_shortlist_reason']='CACHED_HANDOFF_REQUIRES_FRESH_ADMISSION_REVIEW'
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
                    qualified_packs={pid for pid,p in pack_contracts().items() if p.get('timeframe') and all(
                        pid in sources.qualified(n,p['timeframe'],cutoffs[p['timeframe']],field='packs',as_of=evaluation_time())
                        for n in members)}
                    report['resource_plan']=plan_resources(tuple(members),cap=spec['max_screen_requests'],
                        qualified_packs=qualified_packs,samples=getattr(sources,'retained_receipts',()),fallback_qualified=True)
                    client.connect();budget=RequestBudget(spec['max_screen_requests'],retry_calls=2,
                        interval_seconds=0 if mode!='LIVE' else 1)
                    engine=PartitionEngine(sources.screen_source or BasisScreenSource(client),budget,deferred_tool_recovery=True)
                    rows_by_tf={}
                    for tf in ('15m','1h'):
                        price_columns=[c for c in spec['qualified_price_columns'] if c!='quote_rvol32']
                        from .pack_contracts import make_remote_pack
                        pack_id='CORE_'+('1H' if tf=='1h' else '15M')
                        if pack_id in qualified_packs:
                            pack=make_remote_pack(pack_id,inventory.eligible_symbols)
                            price_columns=[c[0] for c in pack.columns]
                        else:pack=make_pack(tf,inventory.eligible_symbols,price_columns)
                        result=engine.run(inventory,pack,cutoffs[tf]);rows={}
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
                            optional=engine.run(inventory,make_pack(tf,inventory.eligible_symbols,
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
                        registered=engine.run(inventory,pack,cutoffs[pack.timeframe])
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
                            retry_calls=min(completion['method_recovery_requests'],method_ceiling))
                        method_engine=PartitionEngine(sources.screen_source or BasisScreenSource(client),method_budget,deferred_tool_recovery=True)
                        for tf in completion['causal_timeframes']:
                            cp=scan_registered(method_engine,inventory,tf,cutoffs[tf],completion['qualified_bits'])
                            report['causal_packs'].append(cp)
                            if cp['evaluated_symbols']:verified.append(('METHOD_STRUCTURE:'+tf,cutoffs[tf],tuple(cp['evaluated_symbols'])))
                        report['causal_budget']=method_budget.report()
                    else:report['causal_status']='SOURCE_SCHEMA_NOT_ATTESTED; NO_CAUSAL_PROMOTION' if not causal_enabled else 'NOT_REVIEWED_BUDGET; BASIS_TRANSPORT_LIMIT'
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
                    def fetch_selected(names):
                        for n in names:
                            if n not in members:continue
                            if n in quarantined:
                                report['source_faults'].append({'phase':'contract_identity','symbol':n,'code':'CONTRACT_IDENTITY_CHANGED'})
                                continue
                            for tf in (('1h','15m','4h') if n in {'BTCUSDT','ETHUSDT'} else ('1h','15m')):
                                try:
                                    bars,source=api.klines(members[n],timeframe=tf,cutoff=cutoffs[tf])
                                    selected[n,tf]=(bars,source)
                                    observed_times.append(source['receipt']['received_at_utc'])
                                    if n in {'BTCUSDT','ETHUSDT'} and tf in {'1h','4h'}:
                                        f=benchmark_fact(bars,members[n],as_of=evaluation_time(),mode=mode,qualification='QUALIFIED')
                                        facts[f.id]=f;benchmark_ids.append(f.id)
                                except (ContractError,KeyError,ValueError,TypeError) as e:
                                    report['source_faults'].append({'phase':'targeted_history','symbol':n,'timeframe':tf,'code':safe_error(e)})
                    fetch_selected(('BTCUSDT','ETHUSDT'))
                    context=build_context(facts,as_of=evaluation_time(),eligible_symbols=inventory.eligible_symbols,
                        eligible_known=True,benchmark_ids=benchmark_ids,return_ids=return_ids)
                    report['context']=asdict(context)
                    # Separate watch, exception and structural allocations. All
                    # remaining questions retain NOT_REVIEWED_BUDGET explicitly.
                    alt,allocations,allocation_study=allocate(list(union.values()),context,cutoffs,
                        limit=spec['max_targeted_alt_symbols'])
                    report['allocation_study']=allocation_study
                    report['targeted_allocation']=allocations
                    for sample in report['prospective_audit']['sample']:
                        sample['price_history_reviewed']=sample['symbol'] in alt
                    report['not_reviewed_budget']=[{**n,'reason':'NOT_REVIEWED_BUDGET'} for n in union.values()
                        if n['native_symbol'] not in {*alt,'BTCUSDT','ETHUSDT'}]
                    fetch_selected(alt)
                    if causal_enabled or sources.certificates:
                        from .economic_sources import depth_snapshot
                        for n in alt:
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
                            if not set(old_ref.source_ids)<=set(facts):
                                report.setdefault('watch_refresh_faults',[]).append({'watch_id':w['id'],
                                    'status':'SOURCE_COVERAGE_LOST','reason':'ORIGINAL_REFERENCE_SOURCE_OUTSIDE_SELECTED_WINDOW'})
                            elif old_ref.id not in {r.id for r in all_swings}:all_swings.append(old_ref)
                        from .engine_capabilities import analyze_selected,qualified_route_a
                        report['selected_research'][-1]['analytical_engine']=analyze_selected(
                            bars,members[n].tick_size,cutoff=cutoffs[tf],as_of=as_of,
                            benchmark=bench[0] if bench and len(bench[0])==len(bars) else None,
                            references=all_swings,inputs=sources.inputs_for(n,tf,cutoffs[tf],as_of))
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
                        proposed=[*all_swings[-4:],*remote_refs,
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
                    from .context import investigation_order
                    cards=investigation_order(cards,context,prioritized=context_prioritized)
                    report['context_questions']={'actual_order':'CONTEXT_PRIORITY' if context_prioritized else 'NEUTRAL',
                        'agenda':context.agenda,'raw_nomination_set_unchanged':True,
                        'verification_allowance':dict(planner.budgets),'eligibility_or_direction_veto':False}
                    for index,c in enumerate(cards):
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
                    report['research_coverage']={'version':'research-coverage-6b.1','by_timeframe':{}}
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
                        'requested':len({(x['native_symbol'],x['timeframe']) for x in union.values() if any(r.startswith(route+'_') for r in x['routes'])}),
                        'evaluated':len({(c.native_symbol,c.timeframe) for c in cards if any(r.startswith(route+'_') for r in c.origins)}),
                        'returned':len({c.id for c in cards if any(r.startswith(route+'_') for r in c.origins)}),
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
            if report['shortlist'] and not cached:
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
            report['consultant']=consult_changed_cards(cards)
            report['time_integrity_status']='CLOCK_UNCERTAINTY; NO_READY' if report.get('clock_anomalies') else 'NORMAL'
            if report.get('clock_anomalies') and report['shortlist']:
                for r in report['shortlist']:
                    report['near_misses'].append({**r,'stage':'UNKNOWN','reason_code':'CLOCK_COHERENCE_UNQUALIFIED'})
                report['shortlist']=[]
            if not cached:report['handoff_export']=make_export(report,cards,facts,references)
            elif not report['shortlist']:
                report['handoff_export']=make_export(report,(),{},())
            report['costs']={'http_requests':len(receipts),'response_bytes':sum(r.get('response_bytes') or 0 for r in receipts),
                'request_body_bytes':sum(r.get('request_body_bytes') or 0 for r in receipts),
                'request_url_bytes':sum(r.get('request_url_bytes') or 0 for r in receipts),
                'request_header_bytes':'NOT_MEASURED; PRIVATE_HEADERS_NOT_RETAINED',
                'wall_ms':round((time.monotonic()-wall)*1000),'sum_latency_ms':sum(durations),
                'p50_ms':durations[(len(durations)-1)//2] if durations else None,
                'p95_ms':durations[math.ceil(.95*len(durations))-1] if durations else None,
                'basis_charged_units':None,'quota':'UNKNOWN','sustainable_cadence':'UNQUALIFIED','llm_calls':0,
                'cached_snapshot_reused':cached,'targeted_kline_calls':api.sample_calls}
            cpu=resource.getrusage(resource.RUSAGE_SELF)
            report['costs']['process_resources']={'scan_cpu_user_seconds':cpu.ru_utime-cpu_start.ru_utime,
                'scan_cpu_system_seconds':cpu.ru_stime-cpu_start.ru_stime,'process_peak_rss_kib':cpu.ru_maxrss,
                'scope':'LINUX_PROCESS_HIGH_WATER_RSS; CPU_DURING_SCAN_BEFORE_FINAL_SQLITE_AND_JSON_WRITE'}
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
            report['parameter_versions']={'interpretation':'6b.1','resource_plan':'6b.1','family_engine':'6a.1'}
            body={'schema_version':report['research_shortlist_version'],'run_id':report['run_id'],
                'as_of_utc':report['as_of_utc'],'mode':report['evidence_mode'],
                'source_revisions':{'inventory':report.get('inventory',{}).get('content_sha256'),
                    'capability':report['capability_revision'],'manifest_sha256':digest(MANIFEST.read_bytes()),
                    'source_provenance':report['offline_source_provenance']},'parameter_versions':report['parameter_versions'],
                **{k:report.get(k) for k in ('shortlist','near_misses','invalidations','late',
                    'not_reviewed_budget','context','research_coverage','route_coverage','resource_plan',
                    'source_faults','clock_anomalies','time_gaps','question_audit','costs')},
                'watches':[{k:v for k,v in w.items() if k!='review'} for w in report['watches']],
                'trade_authorization':False,'new_orders_created':0}
            report['research_shortlist']={**body,'payload_sha256':digest(encode(body).encode())}
            ledger.finish(attempt,report['run_key'],report,bundles=merged_bundles if not cached else (),verified=verified,
                terminals=terminals,crash_hook=crash_hook)
        report['persistence']=ledger.metrics();report['last_verified_observation_cutoffs']=ledger.cutoffs()
        report['output_payload_sha256']=digest(encode({k:v for k,v in report.items() if k not in {'persistence','output_payload_sha256'}}).encode())
        return report
    finally:ledger.close()


def research_summary(report):
    """Small operator view; full source citations remain in JSON/SQLite."""
    lines=[f"OpenBot Market Researcher — {report['release_status']} ({report['mode']})",
        f"Eligible contracts: {report['coverage']['eligible_contracts']}; research handoffs: {len(report['shortlist'])}"]
    for p in report['packs']:
        lines.append(f"{p['timeframe']}: {len(p['column_ids'])} remote precursors; requested {p['requested']}, price evaluated {p['evaluated']}, returned {p['returned']}, missing {p['missing']}, failed {p['failed']}")
        if 'quote_rvol32' in p['per_formula']:
            q=p['per_formula']['quote_rvol32'];lines.append(f"  Quote RVOL evaluated {q['evaluated']}/{q['eligible']}; unavailable {q.get('unavailable',0)}, failed {q['failed']}")
    for p in report.get('causal_packs',()):
        lines.append(f"{p['timeframe']} causal nomination templates: evaluated {p['evaluated']}/{p['eligible_contracts']}; failed {p['failed']}; positive contracts {len(p['positive_observations'])}; full-method coverage remains partial")
    lines.append(f"Watches: {len(report['watches'])}; near misses: {len(report['near_misses'])}; invalidations: {len(report['invalidations'])}; not reviewed within budget: {len(report['not_reviewed_budget'])}")
    lines.append(f"Unobserved gaps: {len(report['time_gaps'])}; HTTP calls: {report['costs']['http_requests']}; bytes: {report['costs']['response_bytes']}; wall: {report['costs']['wall_ms']/1000:.1f}s")
    if report.get('reuse'):lines.append('Reused unchanged closed-bar evidence; refreshed official inventory and current economics.')
    if not report['shortlist']:lines.append('No qualified handoff: causal/admission coverage is incomplete. This does not establish that no opportunities exist.')
    lines.append('Full CORE/all-method coverage remains unqualified; narrow causal templates and selected public depth/OI are separate. Read-only; no orders or scheduling.')
    if report['source_faults']:lines.append('Source faults: '+', '.join(f['code'] for f in report['source_faults']))
    return '\n'.join(lines)
