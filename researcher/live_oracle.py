"""Independent Binance-vs-Basis formula verification, five symbols maximum.

A passing sample does not qualify broad CORE, source replay or sustainable quota.
ATR seed equivalence is tested separately from conditional recurrence.
"""
from decimal import Decimal as D
from .contracts import ContractError, number, utc
from .observations import WIDTHS, candle_observation
from .numerics import normalized_width,wilder_atr,bar_delta
from .settings import load_config


def compare_formula(data,bars,*,label,window_from,window_to,expected_count,tick):
    if (data.get("symbol")!=bars[0].native_symbol or data.get("exchange")!="binance"
            or data.get("market")!="futures" or data.get("timeframe")!=bars[0].timeframe):
        raise ContractError("ORACLE_SOURCE_IDENTITY")
    times=data.get("tailTimes",[]);values=data.get("tail",[])
    if (not isinstance(times,list) or not isinstance(values,list) or len(times)!=len(values)
            or not 1<=len(times)<=20 or any(type(t) is not int for t in times)
            or any(b-a!=WIDTHS[bars[0].timeframe] for a,b in zip(times,times[1:]))):
        raise ContractError("ORACLE_TAIL_CLOCK")
    by_time={b.open_ms//1000:(i,b) for i,b in enumerate(bars)}
    if any(t not in by_time for t in times) or times[-1]!=window_to:
        raise ContractError("ORACLE_UNALIGNED_TAIL")
    if type(data.get("bars")) is not int or data["bars"]!=expected_count:
        raise ContractError("ORACLE_FORMULA_WINDOW_CHANGED")
    window=[b for b in bars if window_from<=b.open_ms//1000<=window_to]
    if len(window)!=expected_count:raise ContractError("ORACLE_INCOMPLETE_INDEPENDENT_WINDOW")
    local_atr=wilder_atr(window) if len(window)>=15 else []
    full_atr=wilder_atr(bars) if len(bars)>=15 else []
    comparisons=[]
    for t,raw in zip(times,values):
        idx,b=by_time[t];local_index=(t-window_from)//WIDTHS[b.timeframe]
        actual=number(raw);expected=None
        if label in {"close","high","low"}:expected=getattr(b,label)
        elif label=="volume":expected=b.base_volume
        elif label=="buy_volume":expected=b.buy_base
        elif label=="delta":expected=bar_delta(b)["delta_base"]
        elif label=="width":expected=normalized_width(bars[:idx+1],3,tick)
        elif label=="prior_high":expected=max(x.high for x in bars[idx-3:idx])
        elif label=="prior_low":expected=min(x.low for x in bars[idx-3:idx])
        elif label=="lag":expected=bars[idx-1].close
        elif label in {"median","quantile"}:expected=sorted(x.close for x in bars[idx-2:idx+1])[1]
        elif label=="atr":expected=local_atr[local_index]
        else:raise ContractError("ORACLE_FORMULA_NOT_IMPLEMENTED")
        if expected is None:raise ContractError("ORACLE_INSUFFICIENT_WARMUP")
        # Formula output is full precision; tiny relative tolerance handles binary floats.
        tolerance=max(D('1e-10'),abs(expected)*D('1e-10'))
        error=abs(actual-expected)
        comparisons.append({"open_seconds":t,"actual":actual,"independent":expected,
                            "absolute_error":error,"tolerance":tolerance,"passed":error<=tolerance})
    result={"formula":label,"comparisons":comparisons,"passed":all(x["passed"] for x in comparisons),
            "classification":"INDEPENDENT_OFFICIAL_BINANCE_REFERENCE","scope":"SAMPLED_ONLY"}
    if label=="atr":
        # Also test first-TR=H-L and n-bar seed convention observed by some providers.
        from .numerics import true_ranges
        tr=true_ranges(window);alternate=[None]*len(window)
        if len(window)>=14:
            alternate[13]=sum([window[0].high-window[0].low,*tr[1:14]],D(0))/14
            for j in range(14,len(window)):alternate[j]=(13*alternate[j-1]+tr[j])/14
        alt=[];recurrence=[]
        for j,(t,raw) in enumerate(zip(times,values)):
            idx,b=by_time[t];wi=(t-window_from)//WIDTHS[b.timeframe]
            seed=alternate[wi]
            tolerance=max(D('1e-10'),abs(number(raw))*D('1e-10'))
            alt.append(seed is not None and abs(number(raw)-seed)<=tolerance)
            if j:
                tr_now=max(b.high-b.low,abs(b.high-bars[idx-1].close),abs(b.low-bars[idx-1].close))
                predicted=(13*number(values[j-1])+tr_now)/14
                recurrence.append(abs(number(raw)-predicted)<=tolerance)
        result['first_bar_hl_seed_passed']=bool(alt) and all(alt)
        result['conditional_recurrence_passed']=bool(recurrence) and all(recurrence)
        result['seed_semantics']='PREVIOUS_CLOSE_REQUIRED' if result['passed'] else 'FIRST_BAR_HL_SEED' if all(alt) else 'UNQUALIFIED'
        result['blueprint_seed_equivalent']=result['passed']
        result['longer_history_atr_last']=full_atr[-1] if full_atr else None
        result['remote_production_enabled']=False
    return result


def verify_sample(client,bars,instrument,*,labels):
    config=load_config();name=instrument.native_symbol;tf=bars[0].timeframe
    data=client.call('market_candles',{'exchange':'binance','market':'futures','symbol':name,
            'timeframe':tf,'bars':65,'withDerivatives':False})
    receipt=client.http.receipts[-1]
    from .contracts import digest,encode
    observation=candle_observation(data,requested_symbol=name,timeframe=tf,
        received_at=receipt['received_at_utc'],schema_hash=digest(encode(client.tools['market_candles']['inputSchema']).encode()),
        response_hash=receipt['response_sha256'])
    if utc(observation.window_end_utc)!=utc(bars[-1].end):raise ContractError('ORACLE_SOURCE_CUTOFF_MISMATCH')
    outcomes=[]
    for label in labels:
        value=client.call('formula_evaluate',{'ref':data['ref'],'expression':config['qualification_formulas'][label]['expression'],
                         'reduce':'tail','includeForming':False})
        outcome=compare_formula(value,bars,label=label,window_from=data['from'],window_to=data['to'],
                                expected_count=data['closedBars'],tick=instrument.tick_size)
        outcome['receipt']=client.http.receipts[-1]
        outcomes.append(outcome)
    return {'native_symbol':name,'timeframe':tf,'cutoff':bars[-1].end,
            'provider_window_from':data['from'],'provider_window_to':data['to'],
            'closed_bars':data['closedBars'],'candle_receipt':receipt,'outcomes':outcomes,
            'all_blueprint_formula_checks_passed':all(o['passed'] for o in outcomes)}
