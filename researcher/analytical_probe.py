"""Explicit Session 3 Local probe; never invoked by ordinary Cloud tests.

One selected symbol/timeframe, 300-bar oracle, fixed registered expressions.
This records qualification evidence and cannot enable a production capability.
"""
from decimal import Decimal as D
from .basis import BasisMCP
from .binance import OfficialResearchAPI
from .contracts import ContractError, now_utc, utc, number
from .pack_contracts import (CORE_COLUMNS,OPTIONAL_COLUMNS,EARLY,QUIET_NEAR,CORRECTIONS,
    evaluate_expr,early_oracle,quiet_near_oracle,correction_oracle,VERSION)
from .screening import closed_cutoff,safe_error
from .transport import PublicHTTP


def qualify_selected(*,environment,native_symbol='BTCUSDT',timeframe='1h',api=None,client=None,clock=now_utc):
    if environment!='CODEX_LOCAL':raise ContractError('LOCAL_ONLY_ANALYTICAL_PROBE')
    if timeframe not in {'1h','15m'}:raise ContractError('TIMEFRAME_UNSUPPORTED')
    at=clock();cutoff=closed_cutoff(at,timeframe)
    report={'schema_version':'openbot.analytical-oracle.6a','environment':environment,
        'native_symbol':native_symbol,'timeframe':timeframe,'cutoff':cutoff,'version':VERSION,
        'checks':[],'failures':[],'production_enabled':False,'full_universe_qualified':False,
        'interpretation':'SELECTED_SOURCE_SEMANTICS_ONLY; NOT_PROSPECTIVE_SHORTLIST_OR_QUOTA_PROOF'}
    api=api or OfficialResearchAPI()
    client=client or BasisMCP(PublicHTTP(max_requests=45),qualification=True,session6a=True)
    try:
        inventory=api.inventory();members={i.native_symbol:i for i in inventory.instruments}
        if native_symbol not in members:raise ContractError('EXACT_ELIGIBLE_CONTRACT_REQUIRED')
        bars,source=api.klines(members[native_symbol],timeframe=timeframe,cutoff=cutoff,bars=300)
        report['independent_source']=source
        client.connect()
        data=client.call('market_candles',{'exchange':'binance','market':'futures','symbol':native_symbol,
            'timeframe':timeframe,'bars':300,'withDerivatives':False})
        same=[b for b in bars if data['from']<=b.open_ms//1000<=data['to']]
        if (not same or same[-1].end!=cutoff or same[0].open_ms//1000!=data['from']
                or len(same)!=data['closedBars']):raise ContractError('ORACLE_SOURCE_CUTOFF_MISMATCH')
        report['source_window']={k:data[k] for k in ('from','to','closedBars')}
        by={b.open_ms//1000:i for i,b in enumerate(same)}
        columns={c.id:c for c in (*CORE_COLUMNS,*OPTIONAL_COLUMNS)}
        expressions={k:c.expression for k,c in columns.items()}|EARLY|QUIET_NEAR|CORRECTIONS
        for label,expression in expressions.items():
            value=client.call('formula_evaluate',{'ref':data['ref'],'expression':expression,
                'reduce':'tail','includeForming':False})
            if (value.get('symbol')!=native_symbol or value.get('exchange')!='binance'
                    or value.get('market')!='futures' or value.get('timeframe')!=timeframe
                    or value.get('bars')!=len(same)
                    or not 1<=len(value.get('tailTimes',[]))<=20
                    or len(value['tailTimes'])!=len(value.get('tail',[]))
                    or value['tailTimes'][-1]!=same[-1].open_ms//1000
                    or len(set(value['tailTimes']))!=len(value['tailTimes'])):
                raise ContractError('ORACLE_SOURCE_IDENTITY')
            from .observations import WIDTHS
            if any(b-a!=WIDTHS[timeframe] for a,b in zip(value['tailTimes'],value['tailTimes'][1:])):
                raise ContractError('ORACLE_TAIL_CLOCK')
            checks=[]
            for t,v in zip(value['tailTimes'],value['tail']):
                if t not in by:raise ContractError('ORACLE_UNALIGNED_TAIL')
                prefix=same[:by[t]+1]
                expected=evaluate_expr(columns[label].expr,prefix)[-1] if label in columns else (
                    early_oracle(prefix)[label] if label in EARLY else
                    quiet_near_oracle(prefix)[label] if label in QUIET_NEAR else correction_oracle(prefix)[label])
                actual=number(v) if v is not None else None
                tolerance=max(D('1e-10'),abs(expected)*D('1e-10')) if expected is not None else None
                checks.append({'open_seconds':t,'actual':actual,'expected_encoded':expected,
                    'tolerance':tolerance,'passed':actual is None if expected is None else
                        actual is not None and abs(actual-expected)<=tolerance})
            report['checks'].append({'column':label,'comparisons':checks,'passed':all(c['passed'] for c in checks),
                'receipt':client.http.receipts[-1]})
    except (ContractError,KeyError,TypeError,ValueError) as e:
        report['failures'].append({'code':safe_error(e),'phase':'STOPPED_NO_DENIAL_RETRY',
            'receipt':getattr(e,'receipt',None)})
    report['receipts']=[*api.http.receipts,*client.http.receipts]
    report['operation_status']='PARTIAL' if report['checks'] else 'BLOCKED_OR_UNQUALIFIED'
    report['sample_passed']=bool(report['checks']) and not report['failures'] and all(c['passed'] for c in report['checks'])
    return report
