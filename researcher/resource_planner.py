"""Versioned serial pack plan. Estimates never establish provider entitlement."""
from math import ceil
from .contracts import ContractError, digest, encode
from .screening import partitions

VERSION = 'research-resources-6b.1'


def plan_resources(names, *, cap=26, qualified_packs=(), partition_size=50,
                   remaining_quota=None, retry_reserve=0, samples=(),fallback_qualified=False):
    if (type(cap) is not int or not 0 <= cap <= 40 or type(retry_reserve) is not int
            or not 0 <= retry_reserve <= cap or remaining_quota is not None
            and (type(remaining_quota) is not int or remaining_quota < 0)):
        raise ContractError('RESOURCE_PLAN_CONTRACT')
    parts=partitions(names,partition_size); n=len(names); p=len(parts)
    allowance=min(cap,remaining_quota) if remaining_quota is not None else cap
    left=max(0,allowance-retry_reserve); rows=[]
    # Required breadth goes before all optional operations; TFs share capacity.
    for layer,required in [('CORE',True),('PARTICIPATION',False),('METHOD_STRUCTURE',False),
                           ('METHOD_QUIET_LOCATION',False),('METHOD_TREND_CORRECTION',False)]:
        for tf,label in [('15m','15M'),('1h','1H')]:
            pid=layer+'_'+label; qualified=pid in qualified_packs
            count=min(left,p) if qualified else 0
            selected=parts[:count];left-=count
            rows.append({'pack_id':pid,'timeframe':tf,'required':required,
                'eligible':n,'logical_calls_required':p,'logical_calls_planned':count,
                'selected_partitions':[list(v) for v in selected],
                'requested_symbols':[v for part in selected for v in part],
                'not_evaluated_budget':[v for part in parts[count:] for v in part] if qualified else [],
                'unsupported_symbols':list(names) if not qualified else [],
                'status':'UNQUALIFIED_SOURCE' if not qualified else
                    'FULL_BREADTH_PLANNED' if count==p else 'PARTIAL_BUDGET',
                'consequence':'PRECURSOR_ONLY; FORMATION_REQUIRES_CAUSAL_SOURCE',
                'warmup':'REGISTERED_PACK_300_CLOSED_BARS; EXACT_FROZEN_CUTOFF'})
    fallback=[]
    if fallback_qualified and not qualified_packs:
        available=allowance-retry_reserve
        for layer in ('LEGACY_PRICE_PRECURSORS','LEGACY_PARTICIPATION'):
            for tf in ('15m','1h'):
                count=min(p,max(0,available));available-=count
                fallback.append({'pack':layer,'timeframe':tf,'calls':count,
                    'partitions':[list(v) for v in parts[:count]],
                    'not_evaluated_budget':[v for part in parts[count:] for v in part],
                    'full_core_certified':False})
    measured=[r for r in samples if r.get('response_bytes') is not None and r.get('elapsed_ms') is not None]
    durations=sorted(r['elapsed_ms'] for r in measured)
    mean_bytes=sum(r['response_bytes'] for r in measured)/len(measured) if measured else None
    calls=sum(r['logical_calls_planned'] for r in rows) or sum(r['calls'] for r in fallback)
    body={'version':VERSION,'eligible_set_hash':digest(encode(sorted(names)).encode()),
        'eligible':n,'partition_size':partition_size,'partitions':p,'packs':rows,
        'mandatory_core_calls':2*p,'participation_extra_calls':2*p,'approach_extra_calls':2*p,
        'effective_degraded_plan':fallback,
        'actual_fallback':'QUALIFIED_LEGACY_PRICE_SCALARS' if fallback else None,
        'three_layers_calls':6*p,'configured_cap':cap,'effective_allowance':allowance,
        'retry_reserve':retry_reserve,'remaining_unallocated':left,
        'full_core_planned':all(r['status']=='FULL_BREADTH_PLANNED' for r in rows if r['required']),
        'coverage_certified':False,'quota':remaining_quota,'quota_status':'UNKNOWN' if remaining_quota is None else 'DECLARED_REMAINING',
        'estimates':{'classification':'EXTRAPOLATION_FROM_RETAINED_RECEIPTS; NOT_LIVE',
            'sample_receipts':len(measured),'logical_calls':calls,
            'response_bytes':round(mean_bytes*calls) if measured else None,
            'serial_latency_ms':round(sum(durations)/len(durations)*calls) if measured else None,
            'sample_p50_ms':durations[(len(durations)-1)//2] if durations else None,
            'sample_p95_ms':durations[ceil(.95*len(durations))-1] if durations else None,
            'request_bytes':'UNKNOWN_UNTIL_COMPILED_PARTITION_REQUEST',
            'cpu_disk':'MEASURE_CURRENT_RUN; NO_FULL_MARKET_HISTORY'},
        'selected_reserves':{'watch_exception_audit':'PROTECTED_ROTATING_REVIEW_LANE',
            'specialist':'SEPARATE_DECLARED_READ_ONLY_OPERATIONS','retries':'BOUNDED_NO_DENIAL_RETRY'},
        'operation_envelope':{'basis_transport_ceiling_including_handshake':40,
            'retained_observed_handshake_http':3,'legacy_causal_required_calls_one_timeframe':p,
            'legacy_causal_configured_ceiling':14,'causal_actual_ceiling':'MIN_CONFIGURED_AND_REMAINING_TRANSPORT_AFTER_BROAD',
            'selected_klines':{'symbols':5,'calls':10,'bars_per_call':300},
            'selected_depth_max_calls':2,'selected_oi_max_calls':2,
            'public_inventory_calls':1,'initial_aggregate_pulse_calls':3,'final_quote_premium_calls':2,
            'historical_asof_api':'UNQUALIFIED; NEVER_ASSUMED',
            'protected_review':'ONE_OF_TWO_ALT_SLOTS_ROTATES_WATCH_QUIET_CONTRARY_AUDIT_SPECIALIST',
            'unallocated_questions':'NOT_REVIEWED_BUDGET; NEVER_NO_OPPORTUNITY'},
        'family_method_consequences':{'families':{f'F{i}':'SELECTED_CAUSAL_SOURCE_REQUIRED; CORE_ALONE_IS_NOT_FORMATION' for i in range(1,10)},
            'methods':{f'M{i:02d}':'DEFINITION_PENDING' if i in (14,15) else
                'INDEPENDENT_SOURCE_AND_FORMATION_CERTIFICATE_REQUIRED' for i in range(1,32)}},
        'local_recommendation':{'A':'QUALIFY_BOTH_CORE_PACKS_THEN_SERIAL_EXACT_PARTITIONS',
            'B':'ONLY_QUALIFIED_PRICE_SCALARS_PLUS_WATCH_EXCEPTION_AUDIT; PARTIAL_COVERAGE',
            'quota_action':'MEASURE_COLD_WARM_P50_P95_429_CHARGES_AND_RIGHTS_ON_LOCAL'},
        'scheduling_enabled':False}
    return {**body,'plan_sha256':digest(encode(body).encode())}
