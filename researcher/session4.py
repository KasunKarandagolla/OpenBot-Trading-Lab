"""Session 4 replay and opt-in Basis qualification, separate from live scan.

Replay reads pinned authentic metadata; it is not operational market input.
Session 5 will connect these primitives to one durable on-demand workflow.
"""
from dataclasses import asdict
from decimal import Decimal as D
import json
from .contracts import ContractError, Instrument, digest, encode, now_utc, utc
from .settings import ROOT, load_config
from .structures import Reference
from .research import Fact, fact_id
from .context import build_context, matched_budget_study
from .candidate_review import boundary_card, union_cards, review_card, shortlist
from .precursors import reproduce_atr_failures, verify_retained_precursors, precursor_questions, seed_experiment, FEATURES
from .method_registry import capability_coverage
from .query_planner import QueryPlanner, Question

S3=ROOT/'evidence/external-first/session3'


def authentic_session3():
    checks=json.loads((S3/'SHA256SUMS.json').read_text())
    # Session 3 manifest maps filenames to exact SHA256, never trusts new JSON.
    for name in ('live-qualification.json','selected-causal-metadata.json'):
        raw=(S3/name).read_bytes()
        expected=checks.get('evidence/external-first/session3/'+name)
        if expected is None or digest(raw)!=expected:raise ContractError('QUALIFICATION_EVIDENCE_DRIFT')
    return (json.loads((S3/'live-qualification.json').read_text()),
            json.loads((S3/'selected-causal-metadata.json').read_text()))


def replay_session3():
    report,metadata=authentic_session3();facts={};cards=[];references=[]
    sources={(s['source']['native_symbol'],s['source']['timeframe']):s['source'] for s in report['selected_samples']}
    for bundle in metadata['bundles']:
        rd=dict(bundle['reference'])
        for k in ('lo','hi','atr','tick'):rd[k]=D(rd[k])
        rd['source_ids']=tuple(rd['source_ids']);r=Reference(**rd);references.append(r)
        src=sources[(r.native_symbol,r.timeframe)];receipt=src['receipt']
        instrument=Instrument(r.native_symbol,'BINANCE_USDM',tick_size=r.tick)
        received=receipt['received_at_utc'];end=src['cutoff']
        raw_ids=set(r.source_ids)|{i for e in bundle['events'] for i in e['source_ids']}
        for i in raw_ids:
            facts[i]=Fact(i,instrument,'RETAINED_SOURCE_ID_BINDING',i,'SOURCE_ID',r.timeframe,
                end,received,received,received,'OFFICIAL_BINANCE_SELECTED',receipt['response_sha256'],
                'INCOMPLETE_HISTORY',False,'TRIAL','AUTHENTIC_REPLAY',7*86400,
                reason='BAR_VALUES_NOT_RETAINED; ID_BOUND_TO_AUTHENTIC_SELECTED_METADATA')
        tail_id=fact_id(r.id,'RECORDED_EVENT_TAIL')
        facts[tail_id]=Fact(tail_id,instrument,'TRIAL_EVENT_TAIL',len(bundle['events']),'EVENT_COUNT',
            r.timeframe,end,received,received,received,'SESSION3_CAUSAL_TRIAL',
            digest((S3/'selected-causal-metadata.json').read_bytes()),'SYNCHRONIZED_REMOTE_RECONSTRUCTION',
            True,'TRIAL','AUTHENTIC_REPLAY',86400)
        # All retained references enter the audit union, including quiet/no-event
        # cases. This is C recorded-watch research, never qualified A screening.
        hs=[h for h in bundle['hypotheses'] if h['family'] in {'F2','F4','F5'}]
        primary=min(hs,key=lambda h:(-len(h['supporting_ids']),h['family']))['family']
        cards.append(boundary_card(r,bundle,cutoff=end,evidence_ids=(tail_id,),primary_family=primary,
                                  origins=('C_RECORDED_CAUSAL_REFERENCE_AUDIT',)))
    cards=union_cards(cards);as_of=report['completed_at_utc']
    context=build_context(facts,as_of=as_of,eligible_symbols=report['inventory']['verified_eligible_subset'],eligible_known=True)
    planner=QueryPlanner();decisions=[];reviews=[]
    for card in cards:
        questions=(Question('CAUSAL_SEQUENCE',0,'BOOLEAN',('WATCH','RESEARCH_ADMISSION')),
                   Question('RESEARCH_PRICE',1,'USDT_PER_BASE',('ROOM_UNKNOWN','ROOM_OBSERVED')))
        decision=planner.next(card,questions,(),facts,as_of=as_of)
        decisions.append({'card_id':card.id,'status':decision['status'],
            'missing_fact':decision.get('question').fact if decision.get('question') else None,
            'reason':'NO_QUALIFIED_FROZEN_ASOF_SOURCE; LIVE_QUERY_CANNOT_REPAIR_HISTORICAL_REPLAY'})
        reviews.append(review_card(card,facts,references,as_of=as_of))
    coverage={**report['coverage'],'classification':'AUTHENTIC_SESSION3_HISTORICAL_SCOPE_ONLY',
        'current_live_eligible_contracts':None,'reviewed_recorded_references':len(cards),
        'qualified_remote_core_evaluated':0,'production_method_evaluated':0,
        'route_A':'BLOCKED_REMOTE_METHOD_QUALIFICATION','route_B':'NO_QUALIFIED_SPECIALIST',
        'route_C':'RECORDED_REFERENCE_AUDIT_ONLY'}
    result=shortlist(reviews,coverage=coverage)
    return {**result,'mode':'AUTHENTIC_REPLAY','environment':'CODEX_CLOUD','as_of':as_of,
        'created_at':now_utc(),'context':asdict(context),'facts':{i:asdict(f) for i,f in facts.items()},
        'planner_decisions':decisions,'planner_audit':planner.audit,
        'context_order_study':matched_budget_study(cards,context,5),
        'method_coverage':capability_coverage(load_config()),'atr_regression':reproduce_atr_failures(report),
        'resources':{'http_requests':0,'llm_calls':0,'live_binance_fetches':0},
        'limitations':['RETROSPECTIVE_SELECTED_METADATA; NOT_PROSPECTIVE_DISCOVERY',
            '4H_BENCHMARK_HISTORY_UNAVAILABLE','SYNC_BREADTH_AND_DATED_SECTORS_UNAVAILABLE',
            'ROOM_AND_CURRENT_ECONOMICS_UNAVAILABLE','PRODUCTION_CORE_AND_METHODS_DISABLED']}


def probe_precursors(client=None):
    """Bounded live remote measurements; no Binance-denial retry or local scan.

    Uses dated authentic inventory solely to request explicit partitions. It
    cannot recertify their current exchange eligibility from provider strings.
    """
    from .basis import BasisMCP
    from .transport import PublicHTTP, ProviderError
    from .screening import BasisScreenSource,RemotePack,normalize_screen,closed_cutoff,safe_error
    report,_=authentic_session3()
    client=client or BasisMCP(PublicHTTP(max_requests=45),qualification=True,session4=True)
    created=now_utc();outcomes=[];scans=[];seed_checks=[]
    try:
        client.connect()
        for tf in ('1h','15m'):
            data=client.call('market_candles',{'exchange':'binance','market':'futures','symbol':'BTCUSDT',
                'timeframe':tf,'bars':300,'withDerivatives':False})
            expected_cutoff=closed_cutoff(created,tf)
            if (data.get('symbol')!='BTCUSDT' or data.get('exchange')!='binance' or data.get('market')!='futures'
                    or data.get('timeframe')!=tf or not 159<=data.get('closedBars',0)<=300
                    or utc(data['evidence']['asOfUtc'])!=utc(expected_cutoff)):
                raise ContractError('ORACLE_SOURCE_CUTOFF_MISMATCH')
            for name,spec in FEATURES.items():
                try:
                    value=client.call('formula_evaluate',{'ref':data['ref'],'expression':spec.expression,
                        'reduce':'tail','includeForming':False})
                    from .observations import WIDTHS
                    if (value.get('symbol')!='BTCUSDT' or value.get('exchange')!='binance'
                            or value.get('market')!='futures' or value.get('timeframe')!=tf
                            or value.get('bars')!=data['closedBars']
                            or not value.get('tailTimes') or value['tailTimes'][-1]!=data['to']
                            or data['from']+(data['closedBars']-1)*WIDTHS[tf]!=data['to']):
                        raise ContractError('ORACLE_SOURCE_CUTOFF_MISMATCH')
                    outcomes.append({'feature':name,'timeframe':tf,'status':'REMOTE_EXECUTED_UNQUALIFIED',
                        'units':spec.units,'required_history':spec.history,'data':value,
                        'request_expression_sha256':digest(spec.expression.encode()),'receipt':client.http.receipts[-1]})
                except ProviderError as e:
                    outcomes.append({'feature':name,'timeframe':tf,'status':safe_error(e),'receipt':e.receipt})
                    if str(e) in {'HTTP_403','HTTP_451','HTTP_429'}:raise
        source=BasisScreenSource(client)
        for tf in ('1h','15m'):
            for feature,names in zip(('quiet_percentile','progress16','upper_distance'),report['quiet_tail']['partitions']):
                spec=FEATURES[feature];names=tuple(names)
                pack=RemotePack('S4_'+feature,'4.0.0-trial',tf,spec.expression,feature,spec.units,spec.history,'0.0001',names)
                try:
                    data,meta=source.screen(names,pack)
                    receipt,obs=normalize_screen(names,data,meta,pack=pack,
                        instruments={n:Instrument(n,'BINANCE_USDM') for n in names},cutoff=closed_cutoff(created,tf))
                    scans.append({'feature':feature,'receipt':asdict(receipt),'observations':obs,
                        'historical_eligible_denominator':519,'current_eligible_denominator':None,
                        'current_exchange_identity':'NOT_REVALIDATED_CLOUD_HTTP_451',
                        'method_evaluated':0,'full_core_evaluated':0})
                except (ContractError,ProviderError) as e:
                    scans.append({'feature':feature,'timeframe':tf,'requested_symbols':names,'status':safe_error(e)})
                    if str(e) in {'HTTP_403','HTTP_451','HTTP_429'}:raise
        for tf in ('1h','15m'):
            data=client.call('market_candles',{'exchange':'binance','market':'futures','symbol':'ETHUSDT',
                'timeframe':tf,'bars':300,'withDerivatives':False})
            value=client.call('formula_evaluate',{'ref':data['ref'],'expression':FEATURES['atr_explicit'].expression,
                'reduce':'tail','includeForming':False})
            outcomes.append({'feature':'atr_explicit','timeframe':tf,'data':value,
                'status':'REMOTE_EXECUTED_UNQUALIFIED','receipt':client.http.receipts[-1]})
        seed_checks=seed_experiment(client,report)
    except (ContractError,ProviderError,KeyError,TypeError,ValueError) as e:
        outcomes.append({'status':'STOPPED','reason':safe_error(e)})
    return {'schema_version':'openbot.precursor-qualification.v1','mode':'LIVE_BASIS_CLOUD',
        'operation_status':'PARTIAL' if any('data' in o for o in outcomes) else 'BLOCKED_OR_UNQUALIFIED',
        'created_at':created,'completed_at':now_utc(),'outcomes':outcomes,'scans':scans,
        'production_enabled':False,'atr_status':'ATR_REMOTE_UNQUALIFIED',
        'independent_retained_comparisons':verify_retained_precursors(report,outcomes),
        'independent_source_mode':'AUTHENTIC_RETAINED_LOCAL_VALUES; NO_LIVE_BINANCE_FETCH',
        'precursor_questions':precursor_questions(scans),
        'exact_start_seed_experiment':seed_checks,
        'transport_receipts':client.http.receipts,'trade_authorization':False,'new_orders_created':0}
