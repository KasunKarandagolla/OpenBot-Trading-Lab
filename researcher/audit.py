"""Bounded prospective sampling and equal-budget schedules; no recall claims."""
from .contracts import digest,encode,utc


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
