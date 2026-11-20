"""Finite remote precursor experiments; never production CORE certification.

No broad local history. Oracle arithmetic accepts a bounded selected sample only.
Quiet ratio uses 128 prior windows, excluding the entire measured 16-bar window;
it is explicitly not a percentile, significant frozen boundary, or detector.
"""
from dataclasses import dataclass
from decimal import Decimal as D
from statistics import median
from .contracts import ContractError, number, digest, encode, utc
from .numerics import validate_bars, normalized_width, efficiency, true_ranges, wilder_atr


@dataclass(frozen=True)
class Feature:
    expression: str
    units: str
    history: int
    role: str


TR = 'max(high-low,max(abs(high-close[1]),abs(low-close[1])))'
QUIET = 'let w=(highest(high,16)-lowest(low,16))/close; (' + '+'.join(
    f'if(w[{j}]<w,1,if(w[{j}]==w,0.5,0))' for j in range(16,144)) + ')/128'
FEATURES = {
    'width16': Feature('(highest(high,16)-lowest(low,16))/close', 'FRACTION', 16, 'QUIET_GEOMETRY'),
    'quiet_ratio': Feature('let w=(highest(high,16)-lowest(low,16))/close; w/median(w[16],128)', 'RATIO', 159, 'PAST_ONLY_QUIET_BASELINE'),
    'quiet_percentile': Feature(QUIET, 'PERCENTILE_FRACTION', 159, 'PAST_ONLY_QUIET_BASELINE'),
    'prior_high16': Feature('highest(high[1],16)', 'USDT_PER_BASE', 17, 'ROLLING_BOUNDARY_PROXY'),
    'prior_low16': Feature('lowest(low[1],16)', 'USDT_PER_BASE', 17, 'ROLLING_BOUNDARY_PROXY'),
    'upper_distance': Feature('abs(highest(high[1],16)-close)/close', 'FRACTION', 17, 'UNFROZEN_LEVEL_DISTANCE_PROXY'),
    'lower_distance': Feature('abs(close-lowest(low[1],16))/close', 'FRACTION', 17, 'UNFROZEN_LEVEL_DISTANCE_PROXY'),
    'efficiency16': Feature('efficiency_ratio(close,16)', 'RATIO', 17, 'TREND_CHURN_PRECURSOR'),
    'progress16': Feature('close/close[16]', 'GROSS_PRICE_RATIO', 17, 'DIRECTIONAL_PROGRESS_PRECURSOR'),
    'base_rvol32': Feature('volume/median(volume[1],32)', 'BASE_VOLUME_RATIO', 33, 'PARTICIPATION_NOT_QUOTE_RVOL'),
    'tr_fraction': Feature(TR+'/close[1]', 'FRACTION', 2, 'DISPLACEMENT_SHOCK_PRECURSOR'),
    'atr_explicit': Feature('rma('+TR+',14)', 'USDT_PER_BASE', 15, 'ATR_SEED_EXPERIMENT'),
}


def expected_feature(label, bars):
    validate_bars(bars)
    f = FEATURES[label]
    if len(bars) < f.history:
        raise ContractError('INSUFFICIENT_HISTORY')
    b = bars[-1]
    high = max(x.high for x in bars[-17:-1])
    low = min(x.low for x in bars[-17:-1])
    if label == 'width16': return normalized_width(bars, 16)
    if label == 'quiet_ratio':
        stop = len(bars)-16
        baseline = [normalized_width(bars[:i],16) for i in range(stop-127,stop+1)]
        m = median(baseline)
        return normalized_width(bars,16)/m if m else None
    if label == 'quiet_percentile':
        from .numerics import compression
        return compression(bars)['past_percentile']
    if label == 'prior_high16': return high
    if label == 'prior_low16': return low
    if label == 'upper_distance': return abs(high-b.close)/b.close
    if label == 'lower_distance': return abs(b.close-low)/b.close
    if label == 'efficiency16': return efficiency(bars)
    if label == 'progress16': return b.close/bars[-17].close
    if label == 'base_rvol32':
        m = median(x.base_volume for x in bars[-33:-1])
        return b.base_volume/m if m else None
    if label == 'tr_fraction': return true_ranges(bars[-2:])[-1]/bars[-2].close
    if label == 'atr_explicit': return wilder_atr(bars)[-1]
    raise ContractError('UNREGISTERED_FORMULA')


def compare_feature(label, data, bars):
    """Strict short remote tail vs independent same-start closed sample."""
    from .observations import WIDTHS
    validate_bars(bars)
    if (data.get('symbol') != bars[0].native_symbol or data.get('exchange') != 'binance'
            or data.get('market') != 'futures' or data.get('timeframe') != bars[0].timeframe
            or ('expression' in data and data['expression'] != FEATURES[label].expression)
            or data.get('bars') != len(bars)):
        raise ContractError('ORACLE_SOURCE_IDENTITY')
    times, values = data.get('tailTimes', []), data.get('tail', [])
    if (not 1 <= len(times) <= 20 or len(times) != len(values)
            or times[-1] != bars[-1].open_ms//1000 or any(type(t) is not int for t in times)
            or any(b-a != WIDTHS[bars[0].timeframe] for a,b in zip(times,times[1:]))):
        raise ContractError('ORACLE_TAIL_CLOCK')
    by_time = {b.open_ms//1000:i for i,b in enumerate(bars)}
    comparisons=[]
    for t,v in zip(times,values):
        if t not in by_time: raise ContractError('ORACLE_UNALIGNED_TAIL')
        expected = expected_feature(label,bars[:by_time[t]+1])
        actual = number(v) if v is not None else None
        tolerance = max(D('1e-10'),abs(expected)*D('1e-10')) if expected is not None else None
        comparisons.append({'open_seconds':t,'actual':actual,'independent':expected,
            'passed':actual is None if expected is None else actual is not None and abs(actual-expected)<=tolerance,
            'tolerance':tolerance})
    return {'feature':label,'units':FEATURES[label].units,'comparisons':comparisons,
            'passed':all(c['passed'] for c in comparisons),'production_enabled':False}


def reproduce_atr_failures(report):
    """Recheck retained authentic scalar pairs, not a fresh raw-series rerun."""
    failures=[]
    for o in report['oracles']:
        for check in o['outcomes']:
            if check['formula'] != 'atr': continue
            rows=[]
            for c in check['comparisons']:
                error=abs(number(c['actual'])-number(c['independent']))
                rows.append({**c,'recomputed_absolute_error':error,
                             'recomputed_passed':error<=number(c['tolerance'])})
            failures.append({'native_symbol':o['native_symbol'],'timeframe':o['timeframe'],
                'provider_window_from':o['provider_window_from'],'provider_window_to':o['provider_window_to'],
                'closed_bars':o['closed_bars'],'comparisons':rows,
                'first_bar_hl_seed_passed':check['first_bar_hl_seed_passed'],
                'conditional_recurrence_passed':check['conditional_recurrence_passed'],
                'source_response_sha256':check['receipt']['response_sha256'],
                'status':'ATR_REMOTE_UNQUALIFIED'})
    return {'classification':'AUTHENTIC_RECORDED_SCALAR_COMPARISON_REPLAY',
            'source_report_canonical_object_sha256':digest(encode(report).encode()),'failures':failures,
            'raw_initial_seed_bars_retained':False,'fresh_independent_reconstruction':'BLOCKED_CLOUD_HTTP_451'}


def verify_retained_precursors(report, outcomes):
    """Live remote tails vs already captured independent Binance values.

    Only exact intersecting timestamps are compared. Retained 20-value raw
    tails cannot qualify a 32-volume baseline or a 128-window median. ATR with
    a changed history start is explicitly convergence evidence, not seed proof.
    """
    from .observations import WIDTHS
    raw={}
    for o in report['oracles']:
        raw[(o['native_symbol'],o['timeframe'])]={c['formula']:{r['open_seconds']:number(r['independent'])
            for r in c['comparisons']} for c in o['outcomes']}
    selected={(s['source']['native_symbol'],s['source']['timeframe']):s for s in report['selected_samples']}
    checks=[]
    for o in outcomes:
        if 'data' not in o:continue
        label=o['feature'];data=o['data'];name=data.get('symbol');tf=o['timeframe']
        f=FEATURES[label];values=data.get('tail',[]);times=data.get('tailTimes',[])
        if (tf not in WIDTHS or data.get('timeframe')!=tf or data.get('exchange')!='binance'
                or data.get('market')!='futures' or not 1<=len(times)<=20 or len(values)!=len(times)
                or any(type(t) is not int for t in times)
                or any(b-a!=WIDTHS[tf] for a,b in zip(times,times[1:]))):
            raise ContractError('ORACLE_TAIL_CLOCK')
        expected={};fields=raw.get((name,tf),{});c=fields.get('close',{});h=fields.get('high',{});l=fields.get('low',{})
        for t in times:
            width=WIDTHS[tf];prior=[t-j*width for j in range(16,-1,-1)]
            if label=='tr_fraction' and t in h and t in l and t-width in c:
                expected[t]=max(h[t]-l[t],abs(h[t]-c[t-width]),abs(l[t]-c[t-width]))/c[t-width]
            if not all(p in c for p in prior):continue
            if label=='efficiency16':
                path=sum((abs(c[b]-c[a]) for a,b in zip(prior,prior[1:])),D(0))
                expected[t]=abs(c[t]-c[prior[0]])/path if path else None
            if label=='progress16':expected[t]=c[t]/c[prior[0]]
            if label=='width16' and all(p in h and p in l for p in prior[1:]):
                expected[t]=(max(h[p] for p in prior[1:])-min(l[p] for p in prior[1:]))/c[t]
            if label in {'prior_high16','upper_distance'} and all(p in h for p in prior[:-1]):
                hi=max(h[p] for p in prior[:-1]);expected[t]=hi if label=='prior_high16' else abs(hi-c[t])/c[t]
            if label in {'prior_low16','lower_distance'} and all(p in l for p in prior[:-1]):
                lo=min(l[p] for p in prior[:-1]);expected[t]=lo if label=='prior_low16' else abs(c[t]-lo)/c[t]
        s=selected.get((name,tf))
        if s:
            t=int(utc(s['source']['cutoff']).timestamp())-WIDTHS[tf]
            key={'width16':'width16','quiet_percentile':'compression16_128',
                 'efficiency16':'efficiency16','atr_explicit':'atr14'}.get(label)
            if key and s['measurements'][key]['status']=='COMPUTED' and t in times:
                value=s['measurements'][key]['value']
                expected[t]=number(value['past_percentile'] if label=='quiet_percentile' else value)
        comparisons=[]
        for t,v in zip(times,values):
            if t not in expected:continue
            e=expected[t];a=number(v) if v is not None else None
            tol=max(D('1e-10'),abs(e)*D('1e-10')) if e is not None else None
            comparisons.append({'open_seconds':t,'actual':a,'independent':e,'tolerance':tol,
                'passed':a is None if e is None else a is not None and abs(a-e)<=tol})
        checks.append({'feature':label,'native_symbol':name,'timeframe':tf,'comparisons':comparisons,
            'status':'MATCHED_RETAINED_INDEPENDENT_SAMPLE' if comparisons and all(c['passed'] for c in comparisons)
                else 'FAILED_INDEPENDENT_SAMPLE' if comparisons else 'NO_RETAINED_INDEPENDENT_INPUTS',
            'qualification_limit':'LONG_WARMUP_CONVERGENCE; CHANGED_START; NOT_SEED_EQUIVALENCE' if label=='atr_explicit'
                else 'EXACT_RETAINED_TIMESTAMPS_ONLY; NOT_LIVE_INDEPENDENT_FETCH',
            'source_receipt':s['source']['receipt'] if s else None,'production_enabled':False})
    return checks


def precursor_questions(scans):
    """Independent quiet questions, not qualified formation/admission signals.

    The registered .25 trial band is chosen before reading the observations.
    Neither BTC direction, mover rank nor RVOL is an eligibility input.
    """
    from .nominations import Nomination
    questions=[]
    for scan in scans:
        if scan.get('feature')!='quiet_percentile':continue
        for o in scan.get('observations',()):
            if number(o['value'])>D('.25'):continue
            n=Nomination(o['instrument']['native_symbol'],'QUIET_TAIL',('F2','F3'),('M30',),
                o['provider'],(o['id'],),o['window_end_utc'],o['known_at_utc'],o['received_at_utc'],
                o['fidelity'],'PROXY_ONLY',
                'Is this below-usual width attached to a pre-known decision reference, or ordinary noise?',
                stage='PREMATURE',competing_hypotheses=('F2_BREAK','F3_EXPANSION','F4_FAILED_BREAK',
                    'F6_CONTINUED_BALANCE','NULL_NO_OPPORTUNITY'))
            questions.append({'nomination':n,'classification':'TRIAL_PRECURSOR_QUESTION_ONLY',
                'coverage_gate':'CURRENT_ELIGIBILITY_AND_FULL_HISTORY_NOT_REVALIDATED',
                'disposition':'UNKNOWN','reason':'NO_QUALIFIED_FROZEN_REFERENCE_METHOD_SOURCE',
                'source_value':o['value'],'units':o['units'],'formation_supported':False})
    return questions


def verify_seed_capture(check):
    """Independent HLC oracle: previous close + 14 TRs, then recurrence.

    HLC is all ATR needs; no invented open/volume or full candle is constructed.
    Native first-bar-HL alternative is verified separately and never substituted.
    """
    from .observations import WIDTHS
    rows=check['independent_hlc'];tf=check['timeframe'];width=WIDTHS[tf];window=check['source_window']
    if (check['native_symbol']!='BTCUSDT' or len(rows)!=20 or window['from']!=rows[0]['open_seconds']
            or window['from']+(window['closedBars']-1)*width!=window['to']
            or any(b['open_seconds']-a['open_seconds']!=width for a,b in zip(rows,rows[1:]))):
        raise ContractError('ORACLE_INCOMPLETE_INDEPENDENT_WINDOW')
    hlc=[{k:number(r[k],positive=True) for k in ('high','low','close')} for r in rows]
    if any(r['low']>r['close'] or r['high']<r['close'] or r['low']>r['high'] for r in hlc):
        raise ContractError('OHLC_INCONSISTENT')
    tr=[None]+[max(b['high']-b['low'],abs(b['high']-p['close']),abs(b['low']-p['close'])) for p,b in zip(hlc,hlc[1:])]
    blueprint=[None]*20;alternative=[None]*20
    blueprint[14]=sum(tr[1:15],D(0))/14
    alternative[13]=(hlc[0]['high']-hlc[0]['low']+sum(tr[1:14],D(0)))/14
    for j in range(14,20):
        alternative[j]=(13*alternative[j-1]+tr[j])/14
        if j>14:blueprint[j]=(13*blueprint[j-1]+tr[j])/14
    results=[]
    for f in check['formulas']:
        data=f['data'];label=f['label'];expression=FEATURES['atr_explicit'].expression if label=='explicit_tr_rma' else 'atr(14)'
        if (label not in {'explicit_tr_rma','native_atr'} or f['expression']!=expression
                or data.get('symbol')!='BTCUSDT' or data.get('exchange')!='binance' or data.get('market')!='futures'
                or data.get('timeframe')!=tf or data.get('bars')!=window['closedBars']
                or len(data.get('tailTimes',()))!=len(data.get('tail',()))
                or not data.get('tailTimes') or data['tailTimes'][-1]!=window['to']):
            raise ContractError('ORACLE_SOURCE_IDENTITY')
        values=dict(zip(data['tailTimes'],data['tail']));comparisons=[]
        for j in range(14,20):
            t=rows[j]['open_seconds']
            if t not in values:continue
            a=number(values[t]);e=blueprint[j];tol=max(D('1e-10'),abs(e)*D('1e-10'))
            comparisons.append({'open_seconds':t,'actual':a,'independent':e,'tolerance':tol,
                'passed':abs(a-e)<=tol,'seed_point':j==14,
                'alternative_first_hl_seed_passed':abs(a-alternative[j])<=tol})
        results.append({'label':label,'comparisons':comparisons,
            'passed':len(comparisons)==6 and all(r['passed'] for r in comparisons),
            'scope':'EXACT_START_BTC_RETAINED_HLC_20_ONLY','production_enabled':False})
    return results


def seed_experiment(client, report):
    """Six bounded calls maximum, no arbitrary historical-asof API claim."""
    from .observations import WIDTHS
    from .screening import closed_cutoff
    from .contracts import now_utc
    checks=[]
    for tf in ('1h','15m'):
        o=next(o for o in report['oracles'] if o['native_symbol']=='BTCUSDT' and o['timeframe']==tf)
        fields={x['formula']:{r['open_seconds']:number(r['independent']) for r in x['comparisons']} for x in o['outcomes']}
        times=sorted(set(fields['close'])&set(fields['high'])&set(fields['low']));width=WIDTHS[tf]
        size=(int(utc(closed_cutoff(now_utc(),tf)).timestamp())-times[0])//width+1
        if not 21<=size<=65:
            checks.append({'timeframe':tf,'status':'OUTSIDE_BOUNDED_RETAINED_WINDOW','bars':size});continue
        data=client.call('market_candles',{'exchange':'binance','market':'futures','symbol':'BTCUSDT',
            'timeframe':tf,'bars':size,'withDerivatives':False})
        if data.get('from')!=times[0]:raise ContractError('ORACLE_SOURCE_CUTOFF_MISMATCH')
        check={'native_symbol':'BTCUSDT','timeframe':tf,'status':'EXACT_START_MATCH',
            'source_window':{k:data[k] for k in ('from','to','closedBars','evidence')},
            'independent_hlc':[{'open_seconds':t,**{k:fields[k][t] for k in ('high','low','close')}} for t in times],
            'independent_source_receipt':next(s['source']['receipt'] for s in report['selected_samples']
                if s['source']['native_symbol']=='BTCUSDT' and s['source']['timeframe']==tf),'formulas':[]}
        for label,expression in (('explicit_tr_rma',FEATURES['atr_explicit'].expression),('native_atr','atr(14)')):
            value=client.call('formula_evaluate',{'ref':data['ref'],'expression':expression,
                'reduce':'tail','includeForming':False})
            check['formulas'].append({'label':label,'expression':expression,'data':value,'receipt':client.http.receipts[-1]})
        check['verification']=verify_seed_capture(check);checks.append(check)
    return checks
