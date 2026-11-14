"""Bounded Local numerical qualification, with per-column failure isolation.

This command records source evidence. It cannot enable a production capability.
"""
from decimal import Decimal as D
from .basis import BasisMCP
from .binance import OfficialResearchAPI
from .contracts import ContractError, now_utc, number, digest, encode
from .pack_contracts import (CORE_COLUMNS,OPTIONAL_COLUMNS,EARLY,QUIET_NEAR,CORRECTIONS,
    early_oracle,quiet_near_oracle,correction_oracle,VERSION)
from .screening import closed_cutoff,safe_error
from .transport import PublicHTTP


def independent_column(label,bars):
    """Reference arithmetic does not execute the compiler's expression DAG."""
    from .numerics import (true_ranges,wilder_atr,normalized_width,compression,
        efficiency,relative_quote_volume)
    b=bars[-1];tr=true_ranges(bars)[-1]
    if label=='close':return b.close
    if label=='tr':return tr
    if label=='atr14':return wilder_atr(bars)[-1]
    if label=='width16':return normalized_width(bars,16,tick=D('1e-100'))
    if label=='quiet_percentile':return compression(bars,tick=D('1e-100'))['past_percentile']
    if label=='efficiency16':
        v=efficiency(bars);return 1+v if v is not None else D(0)
    if label=='progress16':return b.close/bars[-17].close
    if label=='prior_high16':return max(x.high for x in bars[-17:-1])
    if label=='prior_low16':return min(x.low for x in bars[-17:-1])
    if label=='tr_fraction':return tr/bars[-2].close
    if label=='displacement':
        a=wilder_atr(bars)[-2];return 1+tr/a if a else D(0)
    if label=='body_fraction':return abs(b.close-b.open)/(b.high-b.low) if b.high>b.low else D(0)
    if label=='quote_rvol32':
        v=relative_quote_volume(bars);return 1+v if v is not None else D(0)
    if label in EARLY:return early_oracle(bars)[label]
    if label in QUIET_NEAR:return quiet_near_oracle(bars)[label]
    if label in CORRECTIONS:return correction_oracle(bars)[label]
    raise ContractError('ORACLE_FORMULA_NOT_IMPLEMENTED')


def qualify_selected(*,environment,native_symbol='BTCUSDT',timeframe='1h',api=None,client=None,clock=now_utc):
    if environment!='CODEX_LOCAL':raise ContractError('LOCAL_ONLY_ANALYTICAL_PROBE')
    if timeframe not in {'1h','15m'}:raise ContractError('TIMEFRAME_UNSUPPORTED')
    at=clock();cutoff=closed_cutoff(at,timeframe)
    columns={c.id:c for c in (*CORE_COLUMNS,*OPTIONAL_COLUMNS)}
    expressions={k:c.expression for k,c in columns.items()}|EARLY|QUIET_NEAR|CORRECTIONS
    report={'schema_version':'openbot.analytical-oracle.6a','environment':environment,
        'native_symbol':native_symbol,'timeframe':timeframe,'cutoff':cutoff,'version':VERSION,
        'started_at_utc':at,'checks':[],'failures':[],'production_enabled':False,'full_universe_qualified':False,
        'expected_columns':list(expressions),'not_evaluated_columns':list(expressions),
        'reference_arithmetic':'INDEPENDENT_NUMERICS_NOT_COMPILED_DAG',
        'interpretation':'SELECTED_SOURCE_SEMANTICS_ONLY; NOT_PROSPECTIVE_SHORTLIST_OR_QUOTA_PROOF'}
    api=api or OfficialResearchAPI()
    client=client or BasisMCP(PublicHTTP(max_requests=45),qualification=True,session6a=True)
    try:
        inventory=api.inventory();members={i.native_symbol:i for i in inventory.instruments}
        report['inventory']={'content_sha256':inventory.content_sha256,'eligible_contracts':len(inventory.eligible_symbols),
            'mode':inventory.mode,'captured_at_utc':inventory.captured_at_utc}
        if native_symbol not in members:raise ContractError('EXACT_ELIGIBLE_CONTRACT_REQUIRED')
        report['instrument']=members[native_symbol]
        bars,source=api.klines(members[native_symbol],timeframe=timeframe,cutoff=cutoff,bars=300)
        report['independent_source']=source
        client.connect()
        data=client.call('market_candles',{'exchange':'binance','market':'futures','symbol':native_symbol,
            'timeframe':timeframe,'bars':300,'withDerivatives':False})
        # Preserve diagnostic source clocks even when an advancing/stale bar fails.
        report['source_window']={k:data.get(k) for k in ('from','to','closedBars','evidence','symbol','timeframe')}
        from .observations import candle_observation,WIDTHS
        try:
            candle_observation(data,requested_symbol=native_symbol,timeframe=timeframe,
                max_bars=300,
                received_at=client.http.receipts[-1]['received_at_utc'],
                schema_hash=digest(encode(client.tools['market_candles']['inputSchema']).encode()),
                response_hash=client.http.receipts[-1]['response_sha256'])
            report['time_integrity']='VERIFIED_SELECTED_SOURCE_RECEIPT'
        except ContractError as error:
            # A clock discrepancy must block qualification, but need not hide
            # arithmetic on independently aligned already-closed source bars.
            if str(error)!='CLOSED_BAR_CUTOFF_MISMATCH':raise
            report['time_integrity']='UNQUALIFIED_NO_CAUSAL_OR_LIVE_PROMOTION'
            report['failures'].append({'code':safe_error(error),'phase':'TEMPORAL_VALIDATION',
                'receipt':client.http.receipts[-1]})
        same=[b for b in bars if data['from']<=b.open_ms//1000<=data['to']]
        if (not same or same[-1].end!=cutoff or same[0].open_ms//1000!=data['from']
                or len(same)!=data['closedBars']):raise ContractError('ORACLE_SOURCE_CUTOFF_MISMATCH')
        by={b.open_ms//1000:i for i,b in enumerate(same)}
        for label,expression in expressions.items():
            try:
                value=client.call('formula_evaluate',{'ref':data['ref'],'expression':expression,
                    'reduce':'tail','includeForming':False})
                if (value.get('symbol')!=native_symbol or value.get('exchange')!='binance'
                        or value.get('market')!='futures' or value.get('timeframe')!=timeframe
                        or value.get('bars')!=len(same)
                        or not 1<=len(value.get('tailTimes',[]))<=20
                        or len(value['tailTimes'])!=len(value.get('tail',[]))
                        or value['tailTimes'][-1]!=same[-1].open_ms//1000
                        or any(type(t) is not int for t in value['tailTimes'])
                        or len(set(value['tailTimes']))!=len(value['tailTimes'])
                        or 'expression' in value and value['expression']!=expression):
                    raise ContractError('ORACLE_SOURCE_IDENTITY')
                if any(b-a!=WIDTHS[timeframe] for a,b in zip(value['tailTimes'],value['tailTimes'][1:])):
                    raise ContractError('ORACLE_TAIL_CLOCK')
                checks=[]
                for t,v in zip(value['tailTimes'],value['tail']):
                    if t not in by:raise ContractError('ORACLE_UNALIGNED_TAIL')
                    prefix=same[:by[t]+1]
                    expected=independent_column(label,prefix)
                    actual=number(v) if v is not None else None
                    tolerance=max(D('1e-10'),abs(expected)*D('1e-10')) if expected is not None else None
                    checks.append({'open_seconds':t,'actual':actual,'expected_encoded':expected,
                        'tolerance':tolerance,'passed':actual is None if expected is None else
                            actual is not None and abs(actual-expected)<=tolerance})
                report['checks'].append({'column':label,'formula_sha256':digest(expression.encode()),
                    'comparisons':checks,'passed':all(c['passed'] for c in checks),
                    'receipt':client.http.receipts[-1]})
                report['not_evaluated_columns'].remove(label)
            except (ContractError,KeyError,TypeError,ValueError) as error:
                receipt=getattr(error,'receipt',None) or (client.http.receipts[-1] if client.http.receipts else None)
                code=safe_error(error)
                report['failures'].append({'column':label,'code':code,'phase':'COLUMN',
                    'receipt':receipt,'formula_sha256':digest(expression.encode())})
                if code in {'HTTP_403','HTTP_418','HTTP_429','HTTP_451','ROUTE_DISABLED','REQUEST_BUDGET_EXHAUSTED','PROVIDER_BUSY_COOLDOWN'}:break
    except (ContractError,KeyError,TypeError,ValueError) as error:
        report['failures'].append({'code':safe_error(error),'phase':'SOURCE_WINDOW_STOPPED',
            'receipt':getattr(error,'receipt',None) or (client.http.receipts[-1] if client.http.receipts else None)})
    report['receipts']=[*api.http.receipts,*client.http.receipts]
    report['operation_status']='PARTIAL' if report['checks'] else 'BLOCKED_OR_UNQUALIFIED'
    report['sample_passed']=(bool(report['checks']) and not report['failures']
        and not report['not_evaluated_columns'] and all(c['passed'] for c in report['checks']))
    report['numeric_passed']=(bool(report['checks']) and not report['not_evaluated_columns']
        and all(c['passed'] for c in report['checks']))
    report['completed_at_utc']=clock()
    return report
