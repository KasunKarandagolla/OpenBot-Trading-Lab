"""Causal BTC/ETH context and equal-budget, non-veto research scheduling."""
from dataclasses import dataclass, asdict
from decimal import Decimal as D
from statistics import median
from .contracts import ContractError, utc
from .numerics import validate_bars, confirmed_swings, swing_ladder, wilder_atr, efficiency,compression
from .research import Fact, fact_id
from .screening import closed_cutoff


@dataclass(frozen=True)
class ContextClaim:
    name: str
    value: object
    status: str
    evidence_ids: tuple[str,...]
    eligible: int | None = None
    evaluated: int = 0
    missing: tuple[str,...] = ()
    reason: str | None = None


@dataclass(frozen=True)
class ContextCard:
    as_of: str
    claims: tuple[ContextClaim,...]
    agenda: tuple[str,...]
    policy: str = 'ADVISORY_NON_VETO'

    @property
    def id(self): return fact_id(asdict(self))


def benchmark_fact(bars, instrument, *, as_of, mode, qualification='TRIAL'):
    """Only two selected benchmarks, never ticker-derived HTF structure.

    Confirmed swing ladder is independent of the current return. Impulse and
    shock are explicit trial observations; they do not certify liquidation.
    """
    if instrument.native_symbol not in {'BTCUSDT','ETHUSDT'} or len(bars)<34:
        raise ContractError('BENCHMARK_HISTORY_REQUIRED')
    validate_bars(bars)
    bars=[b for b in bars if utc(b.end)<=utc(closed_cutoff(as_of,b.timeframe))
        and utc(b.available_at or b.received_at)<=utc(as_of) and utc(b.received_at)<=utc(as_of)]
    if len(bars)<34:raise ContractError('BENCHMARK_HISTORY_REQUIRED')
    validate_bars(bars,cutoff=closed_cutoff(as_of,bars[0].timeframe),require_current=True)
    if any(b.native_symbol!=instrument.native_symbol for b in bars):
        raise ContractError('ORACLE_SOURCE_IDENTITY')
    if utc(bars[-1].received_at)>utc(as_of): raise ContractError('FUTURE_BAR')
    swings=confirmed_swings(bars); ladder=swing_ladder(swings)
    atr=wilder_atr(bars); last=bars[-1]; prev=bars[-2]
    tr=max(last.high-last.low,abs(last.high-prev.close),abs(last.low-prev.close))
    shock=atr[-2] is not None and tr>=D(3)*atr[-2]
    er=efficiency(bars)
    state='TREND_UP' if ladder=='HH_HL' else 'TREND_DOWN' if ladder=='LH_LL' else 'TRANSITION'
    labels=[state]
    from .family_engine import balance_references
    if balance_references(bars,instrument.tick_size):labels.append('RANGE')
    quiet=compression(bars,tick=instrument.tick_size) if len(bars)>=159 else None
    if quiet and quiet['past_percentile']<=D('.2'):labels.append('COMPRESSION')
    if atr[-1] and any(abs(last.close-s['price'])<=D('2.5')*atr[-1] for s in swings[-4:]):
        labels.append('HTF_DECISION')
    if shock: labels.append('SHOCK')
    if er is not None and er>=D('.7'): labels.append('IMPULSE')
    refs=[{'id':s['id'],'price':s['price'],'known_at':s['known_at']} for s in swings[-4:]]
    return Fact(fact_id([b.id for b in bars],'CONTEXT'),instrument,'BENCHMARK_STRUCTURE',
        {'labels':labels,'ladder':ladder,'efficiency16':er,'preknown_references':refs,
            'closed_log_return_16':(last.close/bars[-17].close).ln(),
            'past_only_quiet_percentile':quiet['past_percentile'] if quiet else None},
        'STRUCTURE',last.timeframe,last.end,last.end,last.available_at or last.received_at,
        last.received_at,'OFFICIAL_BINANCE_SELECTED',last.source_hash,
        'SYNCHRONIZED_REMOTE_RECONSTRUCTION',True,qualification,mode,
        max_age_seconds=2*(last.end_ms-last.open_ms)//1000)


def build_context(facts, *, as_of, eligible_symbols=(), eligible_known=False,
                  benchmark_ids=(), return_ids=(), sector_mapping=None):
    claims=[];labels=[];bench={}
    for name in ('BTCUSDT','ETHUSDT'):
        for tf in ('4h','1h'):
            choices=[facts[i] for i in benchmark_ids if i in facts
                and facts[i].measurement=='BENCHMARK_STRUCTURE'
                and facts[i].timeframe==tf and facts[i].units=='STRUCTURE'
                and facts[i].usable(as_of=as_of,native_symbol=name,qualified=True,
                                    cutoff=closed_cutoff(as_of,tf))]
            if len(choices)>1: raise ContractError('AMBIGUOUS_CONTEXT_SOURCE')
            f=choices[0] if choices else None
            value=f.value if f else None
            if f:
                if not isinstance(value,dict) or not isinstance(value.get('labels'),list):
                    raise ContractError('CONTEXT_STRUCTURE_SCHEMA')
                if not set(value['labels'])<={'TREND_UP','TREND_DOWN','TRANSITION','RANGE','COMPRESSION','SHOCK','IMPULSE','HTF_DECISION'}:
                    raise ContractError('CONTEXT_STRUCTURE_SCHEMA')
                labels.extend(value['labels']);bench[(name,tf)]=tuple(value['labels'])
            claims.append(ContextClaim(name+'_'+tf,value,'SUPPORTED' if f else 'UNKNOWN',
                (f.id,) if f else (),reason=None if f else 'QUALIFIED_ALIGNED_HTF_HISTORY_UNAVAILABLE'))
    disagreement=any(bench.get(('BTCUSDT',tf))!=bench.get(('ETHUSDT',tf)) for tf in ('4h','1h')
        if ('BTCUSDT',tf) in bench and ('ETHUSDT',tf) in bench) if bench else False
    comparable=any(('BTCUSDT',tf) in bench and ('ETHUSDT',tf) in bench for tf in ('4h','1h'))
    claims.append(ContextClaim('BTC_ETH_DISAGREEMENT',disagreement if comparable else None,
        'SUPPORTED' if comparable else 'UNKNOWN',tuple(i for i in benchmark_ids if i in facts and facts[i].usable(as_of=as_of,qualified=True)),
        reason=None if comparable else 'ALIGNED_BENCHMARK_PAIR_UNAVAILABLE'))
    # A common start AND end window is required; rolling ticker windows cannot
    # be promoted here. Measurement name fixes a completed 16-bar log return.
    eligible=set(eligible_symbols);rows={};windows=set();used=[]
    for i in return_ids:
        f=facts.get(i)
        if (f and f.instrument.native_symbol in eligible and f.measurement=='CLOSED_LOG_RETURN_16'
                and f.timeframe=='1h' and f.usable(as_of=as_of,units='LOG_RETURN',qualified=True,
                                                cutoff=closed_cutoff(as_of,'1h'))):
            name=f.instrument.native_symbol
            if name in rows: raise ContractError('DUPLICATE_MARKET_ROW')
            rows[name]=D(str(f.value));windows.add((f.timeframe,utc(f.window_end)));used.append(i)
    if len(windows)>1: raise ContractError('INCOHERENT_TEMPORAL_JOIN')
    missing=tuple(sorted(eligible-set(rows)));values=list(rows.values())
    n=len(values);m=median(values) if values else None;btc=rows.get('BTCUSDT')
    ordered=sorted(values)
    q1=median(ordered[:n//2] or ordered) if n else None
    q3=median(ordered[(n+1)//2:] or ordered) if n else None
    stats={'up_fraction':D(sum(v>0 for v in values))/n if n else None,'median':m,
        'mad':median(abs(v-m) for v in values) if n else None,
        'iqr':q3-q1 if n else None,'quartile_definition':'MEDIAN_SPLIT_EXCLUDES_CENTRAL_ODD',
        'outperform_btc_fraction':D(sum(v>btc for name,v in rows.items() if name!='BTCUSDT'))/(n-1)
            if btc is not None and n>1 else None}
    claims.append(ContextClaim('BREADTH_1H_16',stats if n else None,'SUPPORTED' if n else 'UNKNOWN',
        tuple(used),len(eligible) if eligible_known else None,n,missing,
        'PARTIAL_CONSTITUENT_HISTORY' if missing else None if n else 'SYNCHRONIZED_HISTORY_UNAVAILABLE'))
    leadership=rows.get('ETHUSDT')-rows['BTCUSDT'] if {'ETHUSDT','BTCUSDT'}<=set(rows) else None
    leadership_ids=tuple(i for i in used if facts[i].instrument.native_symbol in {'ETHUSDT','BTCUSDT'})
    claims.append(ContextClaim('ETH_MINUS_BTC_1H_16_LOG_RETURN',leadership,
        'SUPPORTED' if leadership is not None else 'UNKNOWN',leadership_ids,
        reason=None if leadership is not None else 'ALIGNED_COMPLETED_BENCHMARK_RETURNS_UNAVAILABLE'))
    # No dated exact-perp taxonomy is installed. Supplied mappings must be
    # verified by a future registered adapter; never guess categories from text.
    claims.append(ContextClaim('SECTOR_HEAT',None,'UNKNOWN',(),len(eligible) if eligible_known else None,
        reason='DATED_EXACT_PERP_MAPPING_AND_ALIGNED_PEERS_UNAVAILABLE'))
    agenda=[]
    if any(x in labels for x in ('TREND_UP','TREND_DOWN')): agenda.append('F1')
    if 'RANGE' in labels: agenda.extend(('F6','F4'))
    if 'COMPRESSION' in labels: agenda.extend(('F2','F3'))
    if 'SHOCK' in labels: agenda.insert(0,'F9')
    return ContextCard(as_of,tuple(claims),tuple(dict.fromkeys(agenda)))


def investigation_order(cards, context, *, prioritized=True):
    """Same union, different order; no direction eligibility argument exists."""
    return sorted(cards,key=lambda c:(0 if prioritized and set(c.family_ids)&set(context.agenda) else 1,c.id))


def matched_budget_study(cards, context, budget):
    if type(budget) is not int or budget<0: raise ContractError('SCREEN_BUDGET_REQUIRED')
    ids={c.id for c in cards}
    result={'classification':'DETERMINISTIC_ORDER_STUDY_NOT_DISCOVERY_LIFT','budget':budget,
            'union_ids':sorted(ids)}
    for label,enabled in [('neutral',False),('context',True)]:
        order=investigation_order(cards,context,prioritized=enabled)
        result[label]={'reviewed':[c.id for c in order[:budget]],
            'not_reviewed':{c.id:'NOT_REVIEWED_BUDGET' for c in order[budget:]}}
    return result
