"""Versioned remote precursors. These are measurements, not family detectors.

Broad history stays at Basis. Independent arithmetic is limited to selected
oracle bars. Optional/sparse fields never share the guaranteed price pack.
"""
from dataclasses import asdict
from decimal import Decimal as D
from .precursors import FEATURES, Feature, TR, expected_feature
from .contracts import ContractError, digest, encode, number, utc
from .numerics import wilder_atr, true_ranges, relative_quote_volume


def pressure_expression(upper):
    # One boundary established before all eight observation bars; no rolling
    # contemporaneous boundary substituted within the visit count.
    level = 'highest(high[8],24)' if upper else 'lowest(low[8],24)'
    lag=lambda name,j:name if j==0 else f'{name}[{j}]'
    return ('let u='+level+'; let a=rma('+TR+',14)[8]; let b=0.15*a; '+
        '+'.join(f'if({lag("high",j)}>=u-b,if({lag("low",j)}<=u+b,'
                 f'if(high[{j+1}]<u-b,1,if(low[{j+1}]>u+b,1,0)),0),0)'
                 for j in range(7)))


CORE = {k: FEATURES[k] for k in ('atr_explicit','width16','quiet_percentile',
    'efficiency16','progress16','prior_high16','prior_low16','upper_distance',
    'lower_distance','tr_fraction')}
CORE.update({
    'close': Feature('close','USDT_PER_BASE',1,'CLOSED_SOURCE_PRICE_PRECISION'),
    'displacement': Feature('let a=rma('+TR+',14); ('+TR+')/a[1]', 'RATIO', 16, 'PRIOR_ATR_DISPLACEMENT'),
    'body_fraction': Feature('if(high>low,abs(close-open)/(high-low),0)', 'RATIO', 1, 'BODY_FRACTION_ZERO_RANGE_IS_ZERO'),
    'pressure_upper': Feature(pressure_expression(True), 'EPISODE_START_COUNT', 32, 'FIXED_T_MINUS_8_BOUNDARY_VISIT_PROXY'),
    'pressure_lower': Feature(pressure_expression(False), 'EPISODE_START_COUNT', 32, 'FIXED_T_MINUS_8_BOUNDARY_VISIT_PROXY'),
    'quote_rvol32': Feature('if(median(quote_volume[1],32)>0,1+quote_volume/median(quote_volume[1],32),0)',
        'QUOTE_VOLUME_RATIO',33,'OPTIONAL_QUOTE_RVOL; ZERO_SENTINEL_UNKNOWN; POSITIVE_EXPORT_MINUS_ONE'),
})
OPTIONAL = {
    'quote_rvol32': Feature('quoteVolume/median(quoteVolume[1],32)', 'QUOTE_VOLUME_RATIO',33,'QUOTE_RVOL_FIELD_EXPERIMENT'),
    'quote_rvol32_snake': Feature('quote_volume/median(quote_volume[1],32)', 'QUOTE_VOLUME_RATIO',33,'ISOLATED_FIELD_ALIAS_EXPERIMENT'),
}
EXPORT_SCALE = D(100000000)


def export_expression(expression):
    prefix,sep,last=expression.rpartition(';')
    return (prefix+';' if sep else '')+'('+last+')*100000000'


EXPRESSIONS = {e for f in (*CORE.values(), *OPTIONAL.values())
    for e in (f.expression,export_expression(f.expression))}
REVISION = 'remote-core-5.0.0'


def oracle_value(label, bars):
    if label in FEATURES: return expected_feature(label,bars)
    if len(bars)<CORE[label].history: raise ContractError('INSUFFICIENT_HISTORY')
    b=bars[-1]
    if label=='close':return b.close
    if label=='quote_rvol32':return relative_quote_volume(bars)
    if label=='displacement': return true_ranges(bars)[-1]/wilder_atr(bars)[-2]
    if label=='body_fraction': return abs(b.close-b.open)/(b.high-b.low) if b.high>b.low else D(0)
    if label.startswith('pressure_'):
        old=bars[:-8];u=(max(x.high for x in old[-24:]) if label=='pressure_upper'
            else min(x.low for x in old[-24:]));a=wilder_atr(old)[-1];buffer=D('.15')*a
        touch=lambda x: x.high>=u-buffer and x.low<=u+buffer
        return D(sum(touch(bars[-1-j]) and not touch(bars[-2-j]) for j in range(7)))
    raise ContractError('UNREGISTERED_FORMULA')


def compare_tail(label, data, bars):
    """Includes exact seed/initial NULLs; no warm-up convergence substitution."""
    from .observations import WIDTHS
    f=CORE[label]
    if (not bars or data.get('symbol')!=bars[0].native_symbol
            or data.get('exchange')!='binance' or data.get('market')!='futures'
            or data.get('timeframe')!=bars[0].timeframe or data.get('bars')!=len(bars)
            or data.get('expression',f.expression)!=f.expression):
        raise ContractError('ORACLE_SOURCE_IDENTITY')
    times,values=data.get('tailTimes',[]),data.get('tail',[])
    if (not 1<=len(times)<=20 or len(times)!=len(values)
            or times[-1]!=bars[-1].open_ms//1000 or len(set(times))!=len(times)
            or any(type(t)is not int for t in times)
            or any(b-a!=WIDTHS[bars[0].timeframe] for a,b in zip(times,times[1:]))):
        raise ContractError('ORACLE_TAIL_CLOCK')
    indexes={b.open_ms//1000:i for i,b in enumerate(bars)};rows=[]
    for t,v in zip(times,values):
        if t not in indexes: raise ContractError('ORACLE_UNALIGNED_TAIL')
        prefix=bars[:indexes[t]+1]
        e=oracle_value(label,prefix) if len(prefix)>=f.history else None
        a=number(v) if v is not None else None
        if label=='quote_rvol32' and a is not None:a=a-1 if a>0 else None
        tol=max(D('1e-10'),abs(e)*D('1e-10')) if e is not None else None
        rows.append({'open_seconds':t,'actual':a,'independent':e,'tolerance':tol,
            'passed':a is None if e is None else a is not None and abs(a-e)<=tol})
    return {'feature':label,'native_symbol':bars[0].native_symbol,'timeframe':bars[0].timeframe,
        'source_start':bars[0].open_ms//1000,'cutoff':bars[-1].end,'units':f.units,
        'comparisons':rows,'passed':all(r['passed'] for r in rows),
        'independent_response_hash':bars[-1].source_hash,'scope':'SELECTED_IDENTICAL_START_AND_CUTOFF'}


def manifest():
    return {k:{**asdict(f),'version':REVISION,'screen_export_scale':EXPORT_SCALE,
        'screen_export_expression':export_expression(f.expression),'null':'INSUFFICIENT_HISTORY_OR_ZERO_DENOMINATOR',
        'cutoff':'LAST_CLOSED_BAR',**({'null_encoding':'ZERO_IS_UNKNOWN; POSITIVE_MINUS_ONE'} if k=='quote_rvol32' else {}),
        'ordinal_ties':'HALF_WEIGHT' if k=='quiet_percentile' else 'NOT_APPLICABLE',
        'history_scope':'PROVIDER_LOADED_WINDOW; ATR_SEED_RESTARTS_AT_WINDOW_START',
        'current_exclusion':'BASELINE_ENDS_BEFORE_MEASURED_WINDOW' if k=='quiet_percentile'
            else 'PRIOR_CLOSE_OR_PRIOR_BOUNDARY' if k in {'tr_fraction','displacement','prior_high16','prior_low16'}
            else 'DECLARED_EXPRESSION', 'family_detector':False} for k,f in CORE.items()}


def make_pack(tf,names,labels):
    from .screening import RemotePack
    labels=tuple(labels)
    if not labels or not set(labels)<=set(CORE):raise ContractError('UNREGISTERED_FORMULA')
    return RemotePack('CORE_PRECURSORS_'+tf,REVISION,tf,CORE[labels[0]].expression,
        labels[0],CORE[labels[0]].units,max(CORE[x].history for x in labels),'1e-10',tuple(names),
        columns=tuple((x,export_expression(CORE[x].expression),CORE[x].units,CORE[x].history) for x in labels))
