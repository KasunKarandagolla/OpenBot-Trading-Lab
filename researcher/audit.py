"""Bounded prospective sampling and equal-budget schedules; no recall claims."""
from .contracts import digest,encode,utc
from decimal import Decimal as D


def lottery(names,seed):
    return sorted(set(names),key=lambda n:(digest(encode([seed,n]).encode()),n))


def allocate(nominations,context,cutoffs,*,limit=2):
    """One causal slot plus one protected rotating lane, same total history cap.

    The old watch→quiet→structure loop filled both slots before reaching A.
    Grouping by symbol avoids paying twice for timeframe/family duplicates.
    Inclusion fractions assume a uniform hash seed across future invocations;
    deterministic within a cutoff, not an empirical recall estimate.
    """
    by={}
    for n in nominations:
        if n['native_symbol'] in {'BTCUSDT','ETHUSDT'}:continue
        x=by.setdefault(n['native_symbol'],{'families':set(),'routes':set()})
        x['families'].update(n['families']);x['routes'].update(n['routes'])
    agenda=set(context.agenda);seed=cutoffs['15m'];epoch=int(utc(seed).timestamp())//900
    pools={'causal':[n for n,x in by.items() if 'A_REMOTE_CAUSAL' in x['routes']],
        'specialist':[n for n,x in by.items() if any(r.startswith('B_') for r in x['routes'])],
        'watch':[n for n,x in by.items() if 'C_SAVED_WATCH' in x['routes']],
        'quiet_contrary':[n for n,x in by.items() if {'C_QUIET','C_NEW_LISTING','C_RELATIVE_EXCEPTION'}&x['routes']],
        'audit':[n for n,x in by.items() if 'C_STRATIFIED_AUDIT' in x['routes']],
        'fallback':list(by)}
    protected=(('specialist','watch','quiet_contrary','audit') if pools['specialist'] else
        ('watch','quiet_contrary','audit'))[epoch%(4 if pools['specialist'] else 3)]
    lanes=['causal',protected]
    # Empty lanes pass to the next protected pool; no trend approval or veto.
    lanes+=['specialist','audit','watch','quiet_contrary','causal','fallback','fallback']
    def schedule(prioritized):
        picked=[];receipts=[]
        for lane in lanes:
            choices=[n for n in pools[lane] if n not in picked]
            if not choices or len(picked)>=limit:continue
            ranked=lottery(choices,[seed,lane])
            if prioritized:
                ranked.sort(key=lambda n:not bool(by[n]['families']&agenda))
            n=ranked[0];picked.append(n)
            receipts.append({'symbol':n,'pool':lane,'pool_size':len(choices),
                'neutral_inclusion_probability':1/len(choices),
                'context_inclusion_probability':'PRIORITY_STRATUM_DEPENDENT; NOT_UNIFORM' if prioritized else 1/len(choices)})
        return picked,receipts
    neutral,nr=schedule(False);ordered,cr=schedule(True)
    # Actual allocation is neutral protected sampling until prospective outcomes
    # demonstrate that context ordering adds value at equal source cost.
    return neutral,nr,{'seed_cutoff':seed,'history_symbol_budget':limit,'neutral':neutral,'context':ordered,
        'neutral_allocation':nr,'context_allocation':cr,'pool_sizes':{k:len(v) for k,v in pools.items()},
        'unique_nominated_symbols':len(by),'raw_symbol_timeframe_questions':len(nominations),
        'not_reviewed_unique_symbols':len(set(by)-set(neutral)),
        'actual_schedule':'NEUTRAL_WITH_PROTECTED_LANES','causal_lane_starvation_fixed':True,
        'scope':'PROSPECTIVE_SELECTION_PLAN; OUTCOMES_AND_DISCOVERY_LIFT_INSUFFICIENT',
        'zero_inclusion_this_run_pools':[p for p in pools if p not in {r['pool'] for r in nr}]}


def investigate(nominations,context,cutoffs,rows_by_tf,tickers,*,protected=2,capacity=18):
    """Protect the old audit allocation, then rank a separate operational lane.

    Ranking is an investigation heuristic, never a detector or admission gate.
    Distance, quiet, fresh causal nominations, liquidity and symmetric relative
    exceptions contribute separately; BTC direction cannot exclude a name.
    """
    audit,receipts,study=allocate(nominations,context,cutoffs,limit=protected)
    by={}
    for row in nominations:
        n=row['native_symbol']
        if n in {'BTCUSDT','ETHUSDT'}:continue
        x=by.setdefault(n,{'routes':set(),'families':set(),'evidence_ids':set(),'distances':[],'score':D(0)})
        x['routes'].update(row['routes']);x['families'].update(row['families']);x['evidence_ids'].update(row['evidence_ids'])
        v=rows_by_tf.get(row['timeframe'],{}).get(n,{}).get('values',{})
        atr=D(str(v.get('atr_explicit') or 0));close=D(str(v.get('close') or 0))
        if atr>0 and close>0:
            distances=[D(str(v[k]))*close/atr for k in ('upper_distance','lower_distance') if v.get(k) is not None]
            if distances:x['distances'].append(min(distances))
        pressure=max(D(str(v.get(k) or 0)) for k in ('pressure_upper','pressure_lower'))
        quiet=D(str(v['quiet_percentile'])) if v.get('quiet_percentile') is not None else None
        # Max across TFs avoids rewarding duplicated representations of one fact.
        score=min(pressure,D(3))+(D(1) if quiet is not None and quiet<=D('.25') else D(0))
        if x['distances']:score+=max(D(0),D(3)-min(x['distances']))
        x['score']=max(x['score'],score)
    for n,x in by.items():
        r=x['routes']
        x['score']+=4*int('A_REMOTE_CAUSAL' in r)+2*int(any(s.startswith('B_') for s in r))
        x['score']+=int('C_SAVED_WATCH' in r)+int('C_RELATIVE_EXCEPTION' in r)
        values=tickers.get(n,{}).get('values',{})
        x['turnover']=D(str(values.get('quoteVolume') or 0))
    seed=cutoffs['15m'];picked=list(audit)
    pools={
        'causal':[n for n,x in by.items() if any(r.startswith(('A_','B_')) for r in x['routes'])],
        'watch':[n for n,x in by.items() if 'C_SAVED_WATCH' in x['routes']],
        'quiet':[n for n,x in by.items() if {'C_QUIET','C_NEW_LISTING'}&x['routes']],
        'contrary_relative':[n for n,x in by.items() if 'C_RELATIVE_EXCEPTION' in x['routes']],
        'remaining':list(by)}
    def take(lane):
        choices=[n for n in pools[lane] if n not in picked]
        if not choices or len(picked)>=protected+capacity:return False
        # Liquidity is a late tiebreak; quiet/causal/contrary have reserved turns.
        n=min(choices,key=lambda n:(-by[n]['score'],-by[n]['turnover'],digest(encode([seed,n]).encode())))
        picked.append(n);receipts.append({'symbol':n,'pool':'operational_'+lane,'score':by[n]['score'],
            'distance_to_rolling_boundary_atr':min(by[n]['distances']) if by[n]['distances'] else None,
            'evidence_ids':sorted(by[n]['evidence_ids']),'selection':'SOURCE_AWARE_RANK; NOT_PROBABILITY_OR_METHOD_QUALIFICATION'})
        return True
    # Reserved first turns survive a large causal/volume pool. Remaining capacity
    # follows quality; actual I/O later adapts to measured time/request cost.
    for lane in ('causal','watch','quiet','contrary_relative'):take(lane)
    while take('remaining'):pass
    study.update(protected_audit_symbol_budget=protected,operational_capacity=capacity,
        total_planned_alt_capacity=protected+capacity,selected_alt_symbols=picked,
        actual_schedule='PROTECTED_AUDIT_PLUS_SOURCE_AWARE_OPERATIONAL',
        not_reviewed_unique_symbols=len(set(by)-set(picked)),
        priority_heuristic='DISTANCE_PRESSURE_QUIET_CAUSAL_WATCH_SYMMETRIC_RELATIVE; NOT_CALIBRATED',
        context_direction_veto=False)
    return picked,receipts,study
