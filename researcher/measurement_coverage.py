"""The blueprint's 27 measurements, with executable component provenance.

Coverage describes a measured field or a disclosed source gap, never a full
method certificate. VALUE2 is extension; VALUE3 is true profile (§6.2).
"""
from collections import Counter
from .contracts import ContractError,digest,encode

MEASUREMENTS={
 'ID0':'inventory.official_snapshot','ECO1':'admission_facts.refresh_selected/candidate_review.economics',
 'VOL1':'numerics.true_ranges','VOL2':'numerics.wilder_atr','VOL3':'numerics.normalized_width',
 'VOL4':'numerics.compression','PATH1':'numerics.efficiency','PATH2':'numerics.overlap',
 'PATH3':'numerics.displacement','LVL1':'numerics.confirmed_swings','LVL2':'structures.swing_references',
 'LVL3':'candidate_review.remaining_room','LVL4':'numerics.touch_episodes','LVL5':'structures.swing_breaks',
 'VOLU1':'numerics.relative_quote_volume','FLOW1':'numerics.bar_delta','FLOW2':'measurements.flow_divergence',
 'VALUE1':'numerics.anchored_value','VALUE2':'measurements.value_extension','VALUE3':'specialists.true_profile',
 'REL1':'numerics.relative_return','REL2':'measurements.persistent_residual','REL3':'measurements.sector_strength',
 'DER1':'measurements.oi_decomposition/funding_basis','DER2':'specialists.liquidations',
 'CTX1':'context.build_context','CTX2':'measurements.catalyst'}


def selected(bars,tick,methods,refs,benchmark):
    from .numerics import selected_measurements,true_ranges,displacement,wilder_atr,relative_return
    measured=selected_measurements(bars,tick);by={m['method_id']:m for m in methods};out={}
    def record(mid,status,value=None,reason=None):
        out[mid]={'status':status,'reason':reason,'value_sha256':digest(encode(value).encode()) if value is not None else None,
            'source_response_sha256':bars[-1].source_hash,'cutoff':bars[-1].end,'code_path':MEASUREMENTS[mid],
            'qualification':'SELECTED_SOURCE_COMPONENT; NOT_FULL_METHOD_CERTIFICATION'}
    for mid in MEASUREMENTS:record(mid,'NOT_EVALUATED',reason='REQUIRES_REPORT_LEVEL_OR_INDEPENDENT_SOURCE')
    for mid,key in {'VOL2':'atr14','VOL3':'width16','VOL4':'compression16_128','PATH1':'efficiency16',
            'PATH2':'overlap','LVL1':'swings','VOLU1':'quote_rvol32','FLOW1':'delta'}.items():
        row=measured[key];value=row['value']
        record(mid,'NOT_AVAILABLE' if value is None else row['status'],value,
            'ZERO_OR_INSUFFICIENT_BASELINE' if value is None else None)
    record('VOL1','COMPUTED',true_ranges(bars)[-1])
    record('LVL2','COMPUTED' if refs else 'NO_EVENT_IN_COMPLETE_WINDOW',[r.id for r in refs])
    try:record('PATH3','COMPUTED',displacement(bars[-2],bars[-1],wilder_atr(bars)[-2],tick))
    except (ContractError,IndexError):record('PATH3','NOT_EVALUATED',reason='INSUFFICIENT_OR_ZERO_ATR')
    for mid,method in {'LVL4':'M03','LVL5':'M02','FLOW2':'M21','VALUE1':'M19','VALUE2':'M20',
            'VALUE3':'M17','REL2':'M29','DER2':'M28','CTX2':'M31'}.items():
        row=by[method];state=row['status'];value=row['value']
        if state=='SOURCE_CAPABILITY_REQUIRED':state='SOURCE_UNQUALIFIED'
        if mid=='REL2' and isinstance(value,dict):value=value.get('relative')
        record(mid,state,value,row.get('reason'))
    if benchmark is not None:
        try:record('REL1','COMPUTED',relative_return(bars,benchmark))
        except (ContractError,IndexError):record('REL1','NOT_EVALUATED',reason='BENCHMARK_ALIGNMENT_OR_HISTORY')
    sector=by['M29'].get('value')
    if isinstance(sector,dict):
        v=sector.get('sector');valid=isinstance(v,dict) and v.get('status')=='COMPUTED'
        record('REL3','COMPUTED' if valid else 'SOURCE_UNQUALIFIED',v,'DATED_EXACT_PERP_SECTORS_REQUIRED' if not valid else None)
    deriv=[by[m] for m in ('M26','M27')]
    record('DER1','COMPUTED' if all(r['status']=='COMPUTED' for r in deriv) else 'SOURCE_UNQUALIFIED',
        [{k:r[k] for k in ('method_id','status','value')} for r in deriv],
        'FULL_ALIGNED_OI_MARK_MULTIPLIER_AND_ACTUAL_FUNDING_REQUIRED')
    return out


def report_coverage(report):
    rows={}
    for mid,path in MEASUREMENTS.items():
        entries=[s.get('analytical_engine',{}).get('measurements',{}).get(mid) for s in report.get('selected_research',())]
        entries=[e for e in entries if e]
        rows[mid]={'code_path':path,'selected_symbol_timeframes':len(entries),
            'state_counts':dict(Counter(e['status'] for e in entries)),
            'qualified_complete_method':False,'whole_universe_qualified':False}
    rows['ID0'].update(report_state='COMPUTED' if report.get('inventory') else 'NOT_AVAILABLE',
        eligible=report.get('coverage',{}).get('eligible_contracts'))
    rows['ECO1'].update(report_state='SOURCE_UNQUALIFIED',
        reason='POINT_PRICE_SPREAD_AND_DISPLAYED_DEPTH_SEPARATE_FROM_UNKNOWN_ACTUAL_FEE_AND_FUTURE_FILLS')
    rows['LVL3'].update(report_state='COMPUTED_COMPONENTS',
        reason='PER_CARD_ROOM_OBSERVED_UNKNOWN_EXHAUSTED_RETAINED_WITH_ORIGINAL_OBSTACLES')
    rows['CTX1'].update(report_state='COMPUTED_COMPONENTS' if report.get('context') else 'NOT_AVAILABLE',
        reason='SEE_CONTEXT_CLAIMS_WITH_ELIGIBLE_AND_EVALUATED_DENOMINATORS')
    return rows
