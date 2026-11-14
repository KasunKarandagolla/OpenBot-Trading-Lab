"""Session 6A code/source/coverage flags, independent of legacy live gates."""
from .contracts import ContractError
from .pack_contracts import contracts, scenario_budget

OFFLINE='IMPLEMENTED_AND_INDEPENDENTLY_ORACLE_TESTED_OFFLINE'
SOURCE='SOURCE_CAPABILITY_REQUIRED'
PENDING='DEFINITION_PENDING'
METHOD_PATHS={
    'M01':'numerics.confirmed_swings/swing_ladder','M02':'method_engine.evaluate_methods/swing_breaks',
    'M03':'method_engine.evaluate_methods/order_blocks','M04':'structures.equal_level_references',
    'M05':'family_engine.boundary_family','M06':'method_engine.order_blocks',
    'M07':'method_engine.zone_lifecycle','M08':'structures.gap_lifecycle',
    'M09':'structures.gap_lifecycle','M10':'method_engine.zone_lifecycle','M11':'method_engine.ote',
    'M12':'method_engine.crt','M13':'method_engine.amd','M14':'method_engine.timed_subclass',
    'M15':None,'M16':'method_engine.auction','M17':'specialists.true_profile',
    'M18':'specialists.profile_nodes/first_profile_revisit','M19':'numerics.anchored_value',
    'M20':'measurements.value_extension/family_engine.value_reversion',
    'M21':'measurements.flow_divergence','M22':'specialists.footprint',
    'M23':'specialists.aggression_attempts','M24':'specialists.aggression_attempts',
    'M25':'method_engine.depth_walls','M26':'measurements.oi_decomposition',
    'M27':'measurements.funding_basis','M28':'specialists.liquidations',
    'M29':'measurements.persistent_residual/sector_strength',
    'M30':'numerics.compression/context.build_context','M31':'measurements.catalyst'}
FAMILY_PATHS={'F1':'continuation','F2':'boundary_family','F3':'compression_family',
    'F4':'boundary_family','F5':'boundary_family','F6':'boundary_family/balance_references',
    'F7':'value_reversion','F8':'relative_family','F9':'shock_family'}


def manifest(config):
    from .method_engine import DEPENDENCIES
    methods=[]
    for m in config['methods']:
        mid=m['id'];pending=mid in {'M14','M15'};dependent=mid in DEPENDENCIES and not pending
        methods.append({'id':mid,'name':m['name'],'code_path':METHOD_PATHS[mid],
            'status':PENDING if pending else SOURCE if dependent else OFFLINE,
            'implemented_code':mid!='M15','source_supported':False,
            'algorithm_oracle_tested':mid!='M15','method_formation_verified':False,
            'whole_universe_coverage':False,'empirically_useful':False,
            'production_enabled':False,'required_source':DEPENDENCIES.get(mid,'CLOSED_SOURCE_ALIGNED_SELECTED_OHLCQV'),
            'test_oracle':'tests/test_session6a.py + inherited authentic regression suites',
            'live_qualification':'SESSION_3_LOCAL_REQUIRED; NOT_ESTABLISHED_BY_CLOUD_FIXTURES'})
    return {'version':'analytical-capabilities-6a.1','methods':methods,
        'families':[{'id':f,'code_path':'researcher.family_engine.'+p,'status':OFFLINE,
            'implemented_code':True,'source_supported':False,'method_formation_verified':False,
            'whole_universe_coverage':False,'empirically_useful':False,'production_enabled':False}
            for f,p in FAMILY_PATHS.items()],
        'remote_packs':contracts(),'budget_scenario':scenario_budget(),
        'qualification_policy':'OFFLINE_ALGORITHMS_DO_NOT_PROMOTE_LIVE_SOURCE_GATES'}


def analyze_selected(bars,tick,*,cutoff,as_of,benchmark=None,references=(),inputs=None):
    from .family_engine import evaluate_families
    from .method_engine import evaluate_methods
    families=evaluate_families(bars,tick,cutoff=cutoff,as_of=as_of,benchmark=benchmark,references=references)
    methods=evaluate_methods(bars,tick,cutoff=cutoff,as_of=as_of,benchmark=benchmark,
        references=references,families=families,inputs=inputs)
    return {'families':families,'methods':methods,'execution_scope':'BOUNDED_SELECTED_ORACLE_RECONSTRUCTION',
        'mode':'OFFLINE_OR_SOURCE_RECONSTRUCTION; NOT_PROSPECTIVE_LIVE_QUALIFICATION',
        'production_enabled':False,'new_orders_created':0,'remote_requests':0}


def qualified_route_a(bundle,capability,*,native_symbol,timeframe,cutoff):
    """Exact source-qualified adapter. Offline results cannot nominate via A."""
    if not capability or capability.get('production_enabled') is not True:return []
    if (capability.get('qualification')!='QUALIFIED' or capability.get('venue')!='BINANCE_USDM'
            or native_symbol not in capability.get('exact_contracts',())
            or timeframe not in capability.get('timeframes',()) or cutoff!=capability.get('cutoff')
            or capability.get('formula_version')!='families-6a.1'
            or not capability.get('source_oracle_receipt_hash')):
        raise ContractError('UNQUALIFIED_ANALYTICAL_ROUTE_A')
    return [{'route':'REMOTE_STRUCTURE','family':h['family'],'reference_id':h['reference_id'],
        'native_symbol':native_symbol,'stage':h['stage'],'evidence_ids':[e['id'] for e in h['timeline']],
        'source_oracle_receipt_hash':capability['source_oracle_receipt_hash']}
        for h in bundle['families'] if h['family'] in capability.get('families',())
        and h['stage'] in {'EARLY','DEVELOPING','APPROACHING_DECISION'} and h['reference_id']]
