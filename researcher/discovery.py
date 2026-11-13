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
                         mode='LIVE',crash_hook=None):
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
    from .candidate_review import boundary_card,review_card,shortlist
    from .method_registry import capability_coverage
    from .observations import WIDTHS
    from .persistence import RunLedger
    from .query_planner import QueryPlanner,Question
    from .research import Fact,fact_id
    from .settings import ROOT,validate_config
    from .screening import BasisScreenSource,PartitionEngine,RequestBudget,closed_cutoff,safe_error
    from .structures import Reference,swing_references,equal_level_references,boundary_events,selected_family_facts,gap_lifecycle
    from .transport import PublicHTTP
    if mode not in {'LIVE','SYNTHETIC'}:raise ContractError('FACT_PROVENANCE')
    wall=time.monotonic();start=clock();config=config or load_config();validate_config(config)
    spec=config['session5'];cutoffs={tf:closed_cutoff(start,tf) for tf in ('1h','15m','4h')}
    api=api or OfficialResearchAPI()
    client=client or BasisMCP(PublicHTTP(max_requests=spec['max_http_requests']),qualification=True,session5=True)
    ledger=RunLedger(ledger_path or ROOT/'work/research-metadata.sqlite')
    report={'schema_version':'openbot.market-research.v5','environment':'CODEX_LOCAL','mode':mode,
        'created_at_utc':start,'frozen_cutoffs':cutoffs,'operation_status':'BLOCKED_OR_UNQUALIFIED',
        'release_status':'PARTIAL','operating_mode':'PAUSE_UNQUALIFIED','shortlist':[],'watches':[],
        'near_misses':[],'invalidations':[],'not_reviewed_budget':[],'time_gaps':[],
        'source_health':[],'packs':[],'nominations':[],'selected_research':[],'planner':[],
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
                if inventory.mode!='VERIFIED_INVENTORY':raise ContractError('LIVE_INVENTORY_PARTIAL')
                identity={n:digest(encode([i.venue,n,i.contract_type,i.quote,i.settlement,i.onboard_at_utc,
                    i.contract_multiplier,i.tick_size,i.quantity_rules]).encode()) for n,i in members.items()}
                report['inventory']['identity_hashes']=identity
                quarantined={w['native_symbol'] for w in prior_watches.values()
                    if w['native_symbol'] in identity and w['identity_hash']!=identity[w['native_symbol']]}
                report['identity_quarantine']=sorted(quarantined)
                pulse=api.pulse(inventory,partial=True)
                report['source_health']=[{**{k:v for k,v in p.items() if k!='observations'},
                    'accepted':len(p['observations']),'eligible':len(members)} for p in pulse]
                report['operation_status']='PARTIAL';report['operating_mode']='REMOTE_WIDE_PARTIAL'
                key=digest(encode([cutoffs,identity,spec,mode]).encode())
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
                    if report['shortlist']:raise ContractError('STALE_OR_INCOMPLETE_BAR_TAIL')
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
                                'after':last,'before_current':cutoffs[tf],'symbols':[w['native_symbol']],
                                'last_viable_reference':w['reference'],
                                'reason':'CURRENT_PRICE_RECONSTRUCTION_CANNOT_PROVE_TIMELY_HISTORICAL_ACTIONABILITY',
                                'current_reconstruction_repairs_prospective_gap':False})
                    client.connect();budget=RequestBudget(spec['max_screen_requests'],retry_calls=2)
                    engine=PartitionEngine(BasisScreenSource(client),budget)
                    rows_by_tf={}
                    for tf in ('15m','1h'):
                        pack=make_pack(tf,inventory.eligible_symbols,spec['qualified_price_columns'])
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
                        result['measurements']=rows;result['column_ids']=list(spec['qualified_price_columns'])
                        result['operating_scope']='QUALIFIED_SAMPLED_PRICE_PRECURSORS; NOT_FULL_CORE_OR_METHODS'
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
                            'unsupported':0,'units':CORE[f].units} for f in spec['qualified_price_columns']}
                        report['packs'].append(result);rows_by_tf[tf]=rows
                        if rows:verified.append(('PRICE_PRECURSORS:'+tf,cutoffs[tf],tuple(rows)))
                    report['broad_budget']=budget.report()
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
                        k=(n,tf);r=rows_by_tf.get(tf,{}).get(n)
                        x=union.setdefault(k,{'native_symbol':n,'timeframe':tf,'routes':[], 'families':[],
                            'questions':[],'evidence_ids':r['evidence_ids'] if r else [],'cutoff':cutoffs[tf],
                            'stage':'PREMATURE','formation_supported':False})
                        x['routes']=list(dict.fromkeys(x['routes']+[route]));x['families']=list(dict.fromkeys(x['families']+list(families)))
                        x['questions'].append(question)
                    for tf,rows in rows_by_tf.items():
                        btc=rows.get('BTCUSDT',{}).get('values',{}).get('progress16')
                        for n,r in rows.items():
                            v=r['values'];quiet=D(str(v['quiet_percentile']))<=D('.25')
                            if quiet:nominate(n,tf,'C_QUIET',('F2','F3','F6'),'Does historical quiet attach to a pre-known decision reference?')
                            if v['pressure_upper'] or v['pressure_lower']:
                                nominate(n,tf,'A_FIXED_WINDOW_PRESSURE_PRECURSOR',('F2','F4','F5','F6'),'Verify separated retreats and the same frozen reference chronology')
                            if D(str(v['displacement']))>=3:
                                nominate(n,tf,'A_POST_SHOCK_PRECURSOR',('F9',),'Has this price shock stabilized or made another extreme? No liquidation assertion.')
                            if btc is not None and abs(D(str(v['progress16']))/D(str(btc))-1)>=D('.015'):
                                nominate(n,tf,'C_RELATIVE_EXCEPTION',('F8','F1'),'Does lag-trained relative evidence survive local structure and peer checks?')
                    for w in prior_watches.values():
                        n=w['native_symbol'];tf=w['timeframe']
                        if n in members and w['identity_hash']==identity[n]:nominate(n,tf,'C_SAVED_WATCH',w['families'],'Reassess original frozen reference without inventing missed events')
                    for n,i in members.items():
                        if i.onboard_at_utc and 0<=(utc(clock())-utc(i.onboard_at_utc)).total_seconds()<=30*86400:
                            nominate(n,'15m','C_NEW_LISTING',('F2','F3','F9'),
                                'Which shorter-history price structure is sourceable? Missing long baseline stays UNKNOWN.')
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
                    alt=[];allocations=[]
                    for route,predicate in [('watch',lambda n:'C_SAVED_WATCH' in n['routes']),
                        ('exception',lambda n:bool({'C_QUIET','C_NEW_LISTING'}&set(n['routes']))),
                        ('targeted',lambda n:any(r.startswith('A_') for r in n['routes']))]:
                        prior_selected={(s['native_symbol'],s['timeframe']) for s in previous.get('selected_research',())} if previous else set()
                        choices=sorted((n for n in union.values() if predicate(n) and n['native_symbol'] not in {'BTCUSDT','ETHUSDT'}),
                            key=lambda n:(not bool(set(n['families'])&set(context.agenda)),
                                (n['native_symbol'],n['timeframe']) in prior_selected,
                                digest(encode([cutoffs[n['timeframe']],n['native_symbol'],n['timeframe']]).encode())))
                        for n in choices:
                            name=n['native_symbol']
                            if name not in alt and len(alt)<spec['max_targeted_alt_symbols']:
                                alt.append(name);allocations.append({'pool':route,'symbol':name});break
                    report['targeted_allocation']=allocations
                    report['not_reviewed_budget']=[{**n,'reason':'NOT_REVIEWED_BUDGET'} for n in union.values()
                        if n['native_symbol'] not in {*alt,'BTCUSDT','ETHUSDT'}]
                    fetch_selected(alt)
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
                        proposed=[*swing_references(bars,members[n].tick_size,as_of=as_of)[-4:],
                            *equal_level_references(bars,members[n].tick_size,as_of=as_of)[-2:]]
                        refs=[ledger.freeze_reference(r) for r in proposed if r.id not in terminal_ids]
                        references.extend(refs)
                        for ref in refs:
                            result=boundary_events(ref,bars,as_of=as_of)
                            bundles.append((ref,result['events'],result['hypotheses']))
                            primary=max((h for h in result['hypotheses'] if h['family'] in {'F2','F4','F5'}),
                                key=lambda h:(h['current_formation_verdict']=='SUPPORTED',len(h['supporting_ids']),h['family']))['family']
                            fid=fact_id(ref.id,cutoffs[tf],'CAUSAL')
                            facts[fid]=Fact(fid,members[n],'CAUSAL_SEQUENCE',True,'BOOLEAN',tf,cutoffs[tf],
                                source['receipt']['received_at_utc'],source['receipt']['received_at_utc'],source['receipt']['received_at_utc'],
                                'TARGETED_CAUSAL_RECONSTRUCTION',source['source_response_sha256'],
                                'SYNCHRONIZED_REMOTE_RECONSTRUCTION',True,'TRIAL',mode,2*WIDTHS[tf])
                            card=boundary_card(ref,result,cutoff=cutoffs[tf],evidence_ids=(fid,*econ_ids.get(n,())),primary_family=primary,
                                mode=mode,origins=('C_TARGETED_SOURCE_BACKED_CAUSAL_WATCH',))
                            if ref.origin.startswith('EQH_EQL:'):card=replace(card,method_ids=('M04','M05'))
                            cards.append(card)
                            plan=planner.next(card,(Question('REFERENCE_SIGNIFICANCE',0,'ORDINAL',('WATCH','ADMISSION')),
                                Question('DEPTH_USDT_WITHIN_ROOM',1,'USDT',('ECONOMICS_UNKNOWN','ECONOMICS_OBSERVED'))),(),facts,as_of=as_of)
                            report['planner'].append({'card_id':card.id,'status':plan['status'],'next_fact':plan.get('question').fact if plan.get('question') else None,
                                'reason':'NO_QUALIFIED_SOURCE_FOR_NECESSARY_ADMISSION_FACT; STOP_UNRELATED_QUERIES'})
                    reviews=[review_card(c,facts,[r for r in references if r.native_symbol==c.native_symbol],as_of=as_of) for c in cards]
                    if report.get('clock_anomalies'):
                        for r in reviews:
                            if r['stage'] in {'READY_FOR_DEEP','FAST_WITH_ROOM'}:
                                r['stage']='UNKNOWN';r['reason_code']='CLOCK_COHERENCE_UNQUALIFIED'
                                r['missing_necessary_inputs'].append('CLOCK_COHERENCE')
                    reviewed=shortlist(reviews,coverage=report['coverage'])
                    for field in ('shortlist','near_misses','invalidations'):report[field]=reviewed[field]
                    report['empty_shortlist_reason']=reviewed['empty_shortlist_reason']
                    for r in reviewed['watches']:
                        ref=r['reference'];wid=ref['id'];prior=prior_watches.get(wid)
                        report['watches'].append({'id':wid,'native_symbol':r['instrument'],'timeframe':ref['timeframe'],
                            'families':r['family_ids'],'identity_hash':identity[r['instrument']],
                            'first_seen':prior['first_seen'] if prior else as_of,'last_checked':as_of,
                            'last_verified_cutoff':cutoffs[ref['timeframe']],
                            'reference':ref,'stage':r['stage'],'review':r,'next_review':r['trigger_to_investigate'],
                            'gap_status':'GAP_UNOBSERVED' if report['time_gaps'] else None})
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
                            terminals.append((Reference(**raw),'EXPIRED' if reason=='REFERENCE_EXPIRED' else 'INVALIDATED',as_of))
                        else:report['watches'].append({**w,'stage':'UNKNOWN','last_checked':as_of,
                            'gap_status':'GAP_UNOBSERVED','next_review':'Original reference not covered by this bounded selected history; reassess current validity'})
                    report['context_order_study']=matched_budget_study(cards,context,min(len(cards),4))
                    report['cache_reusable']=all(p['evaluated']>0 and not p['truncated_attempts'] for p in report['packs'])
                    report['coverage']['targeted_symbol_timeframes']=len(selected)
                    report['coverage']['targeted_causal_references']=len(cards)
                    report['coverage']['price_precursors_by_timeframe']={p['timeframe']:{
                        **{k:p[k] for k in ('requested','evaluated','returned','missing','failed','unsupported')},
                        'eligible':len(members),'columns':len(p['column_ids']),
                        'quiet_percentile_at_most_025':sum(D(str(r['values']['quiet_percentile']))<=D('.25') for r in p['measurements'].values())}
                        for p in report['packs']}
                    report['coverage']['methods_by_timeframe']={tf:{m['id']:{'eligible':len(members),'remote_evaluated':0,
                        'remote_requested':0,'remote_returned':0,'remote_missing':0,'remote_failed':0,
                        'targeted_only':len({c.native_symbol for c in cards if c.timeframe==tf and m['id'] in c.method_ids}),
                        'unsupported_or_unqualified':len(members),'reason':m['remote_qualification']} for m in report['method_coverage']['methods']} for tf in ('1h','15m','4h')}
            except (ContractError,KeyError,TypeError,ValueError,IndexError) as e:
                report['source_faults'].append({'phase':'scan','code':safe_error(e)})
                report['cache_reusable']=False
                report['operating_mode']='CONTEXT_ONLY_DEGRADED' if 'inventory' in report else 'PAUSE_UNQUALIFIED'
                if previous:
                    report['watches']=[{**w,'stage':'UNKNOWN','gap_status':'GAP_UNOBSERVED',
                        'next_review':'Source recovery required; retain last viable frozen reference'} for w in previous['watches']]
            receipts=[*api.http.receipts,*client.http.receipts];durations=sorted(r['elapsed_ms'] for r in receipts)
            report['request_receipts']=receipts;report['completed_at_utc']=evaluation_time()
            report['time_integrity_status']='CLOCK_UNCERTAINTY; NO_READY' if report.get('clock_anomalies') else 'NORMAL'
            if report.get('clock_anomalies') and report['shortlist']:
                for r in report['shortlist']:
                    report['near_misses'].append({**r,'stage':'UNKNOWN','reason_code':'CLOCK_COHERENCE_UNQUALIFIED'})
                report['shortlist']=[]
            report['costs']={'http_requests':len(receipts),'response_bytes':sum(r.get('response_bytes') or 0 for r in receipts),
                'request_body_bytes':sum(r.get('request_body_bytes') or 0 for r in receipts),
                'request_url_bytes':sum(r.get('request_url_bytes') or 0 for r in receipts),
                'request_header_bytes':'NOT_MEASURED; PRIVATE_HEADERS_NOT_RETAINED',
                'wall_ms':round((time.monotonic()-wall)*1000),'sum_latency_ms':sum(durations),
                'p50_ms':durations[(len(durations)-1)//2] if durations else None,
                'p95_ms':durations[math.ceil(.95*len(durations))-1] if durations else None,
                'basis_charged_units':None,'quota':'UNKNOWN','sustainable_cadence':'UNQUALIFIED','llm_calls':0,
                'cached_snapshot_reused':cached,'targeted_kline_calls':api.sample_calls}
            report['last_verified_observation_cutoffs']=old_cutoffs
            report['run_key']=digest(encode([report.get('cache_key'),report['completed_at_utc'],report['costs']]).encode())
            ledger.finish(attempt,report['run_key'],report,bundles=bundles if not cached else (),verified=verified,
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
    lines.append(f"Watches: {len(report['watches'])}; near misses: {len(report['near_misses'])}; invalidations: {len(report['invalidations'])}; not reviewed within budget: {len(report['not_reviewed_budget'])}")
    lines.append(f"Unobserved gaps: {len(report['time_gaps'])}; HTTP calls: {report['costs']['http_requests']}; bytes: {report['costs']['response_bytes']}; wall: {report['costs']['wall_ms']/1000:.1f}s")
    if report.get('reuse'):lines.append('Reused unchanged closed-bar evidence; refreshed official inventory and current economics.')
    if not report['shortlist']:lines.append('No qualified handoff: causal/admission coverage is incomplete. This does not establish that no opportunities exist.')
    lines.append('Full CORE, broad family detectors and true specialists remain unqualified. Read-only; no orders or scheduling.')
    if report['source_faults']:lines.append('Source faults: '+', '.join(f['code'] for f in report['source_faults']))
    return '\n'.join(lines)
