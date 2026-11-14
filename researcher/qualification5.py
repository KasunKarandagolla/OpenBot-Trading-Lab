"""Bounded live qualification; selected oracle history, never an all-coin engine."""
from dataclasses import asdict
from decimal import Decimal as D
import time
from .basis import BasisMCP
from .binance import OfficialResearchAPI
from .contracts import ContractError, digest, encode, now_utc, number, utc
from .core import CORE, OPTIONAL, compare_tail, make_pack, oracle_value, manifest
from .screening import BasisScreenSource, normalize_screen, closed_cutoff, safe_error
from .transport import PublicHTTP, ProviderError


def qualify_core(*,api=None,client=None):
    started=time.monotonic();at=now_utc();api=api or OfficialResearchAPI()
    client=client or BasisMCP(PublicHTTP(max_requests=80),qualification=True,session4=True,session5=True)
    result={'schema_version':'openbot.core-qualification.v5','mode':'LIVE','environment':'CODEX_LOCAL',
        'started_at':at,'checks':[],'screens':[],'failures':[],'formula_manifest':manifest(),
        'native_atr_status':'REJECTED_SEED_SEMANTICS','full_core_qualified':False,
        'provider_quota_and_sustained_rights':'UNKNOWN','trade_authorization':False}
    def failure(phase,e,**scope):
        result['failures'].append({'phase':phase,**scope,'code':safe_error(e),
            'receipt':getattr(e,'receipt',None) or (client.http.receipts[-1] if client.http.receipts else None)})
        if str(e) in {'HTTP_403','HTTP_451','HTTP_429','ROUTE_DISABLED','REQUEST_BUDGET_EXHAUSTED'}:raise e
    try:
        inventory=api.inventory();result['inventory']=inventory.report();pulse=api.pulse(inventory)
        result['pulse_summary']=[{k:v for k,v in p.items() if k!='observations'} for p in pulse]
        members={i.native_symbol:i for i in inventory.instruments}
        volumes={o['native_symbol']:number(o['values']['quoteVolume']) for o in pulse[0]['observations']}
        ranked=sorted(volumes,key=lambda n:(volumes[n],n));quiet=next(n for n in ranked if n.isascii() and not n[0].isdigit())
        names=list(dict.fromkeys(['BTCUSDT','ETHUSDT','1000PEPEUSDT',quiet,'我踏马来了USDT']))
        result['selected_plan']={'symbols':names,'quote_turnover_ranks':{n:ranked.index(n)+1 if n in ranked else None for n in names},
            'verified_multiplier_facts':[n for n in names if members[n].contract_multiplier is not None],
            'native_prefix_is_not_multiplier_evidence':True,'oracle_max_symbols':5,'oracle_max_klines_calls':10}
        cutoffs={tf:closed_cutoff(at,tf) for tf in ('1h','15m')};result['cutoffs']=cutoffs
        client.connect();samples={}
        for n in names:
            for tf in ('1h','15m'):
                try:
                    bars,source=api.klines(members[n],timeframe=tf,cutoff=cutoffs[tf],bars=300)
                    samples[n,tf]=bars
                    result.setdefault('independent_selected_bars',[]).append({'source':source,'bars':[asdict(b) for b in bars]})
                    data=client.call('market_candles',{'exchange':'binance','market':'futures','symbol':n,'timeframe':tf,'bars':300,'withDerivatives':False})
                    same=[b for b in bars if data['from']<=b.open_ms//1000<=data['to']]
                    if not same or same[-1].end!=cutoffs[tf]:raise ContractError('ORACLE_SOURCE_CUTOFF_MISMATCH')
                    for label in ('atr_explicit','pressure_upper','pressure_lower'):
                        value=client.call('formula_evaluate',{'ref':data['ref'],'expression':CORE[label].expression,'reduce':'tail','includeForming':False})
                        result['checks'].append({**compare_tail(label,value,same),'kind':'LONG_IDENTICAL_START',
                            'remote_data':value,'receipt':client.http.receipts[-1]})
                    short=client.call('market_candles',{'exchange':'binance','market':'futures','symbol':n,'timeframe':tf,'bars':21,'withDerivatives':False})
                    same=[b for b in bars if short['from']<=b.open_ms//1000<=short['to']]
                    value=client.call('formula_evaluate',{'ref':short['ref'],'expression':CORE['atr_explicit'].expression,'reduce':'tail','includeForming':False})
                    result['checks'].append({**compare_tail('atr_explicit',value,same),'kind':'EXACT_SEED_AND_INITIAL_NULLS',
                        'remote_data':value,'receipt':client.http.receipts[-1]})
                except (ContractError,KeyError,TypeError,ValueError) as e:failure('selected_oracle',e,native_symbol=n,timeframe=tf)
        source=BasisScreenSource(client)
        for tf in ('1h','15m'):
            try:
                pack=make_pack(tf,names,CORE);data,meta=source.screen(tuple(names),pack)
                receipt,obs=normalize_screen(tuple(names),data,meta,pack=pack,instruments=members,cutoff=cutoffs[tf])
                checks=[]
                for o in obs:
                    n=o['instrument']['native_symbol'];label=o['measurement_id'];bars=samples.get((n,tf))
                    if not bars:continue
                    # Screen lookback is 300 including the current forming bar,
                    # so the common independent closed input has 299 bars.
                    e=oracle_value(label,bars[-299:]);a=number(o['value']) if o['value'] is not None else None;tol=max(D('1e-10'),abs(e)*D('1e-10')) if e is not None else None
                    checks.append({'native_symbol':n,'timeframe':tf,'feature':label,'actual':a,'independent':e,
                        'tolerance':tol,'passed':a is None if e is None else a is not None and abs(a-e)<=tol,'source_start':bars[-299].open_ms//1000})
                result['screens'].append({'timeframe':tf,'receipt':asdict(receipt),'oracle_checks':checks,'data':data,'transport':meta})
            except (ContractError,KeyError,TypeError,ValueError) as e:failure('multi_column_screen',e,timeframe=tf)
        # Isolate optional quote field from the finite price pack.
        try:
            handle=client.call('market_candles',{'exchange':'binance','market':'futures','symbol':'BTCUSDT','timeframe':'1h','bars':300,'withDerivatives':False})
            data=client.call('formula_evaluate',{'ref':handle['ref'],
                'expression':OPTIONAL['quote_rvol32'].expression,'reduce':'tail','includeForming':False})
            result['optional_quote_field']={'data':data,'receipt':client.http.receipts[-1],'status':'UNQUALIFIED_PENDING_ORACLE'}
        except (ContractError,KeyError,TypeError,ValueError) as e:failure('optional_quote_field',e)
    except (ContractError,KeyError,TypeError,ValueError) as e:
        result['failures'].append({'phase':'qualification_stopped','code':safe_error(e),'receipt':getattr(e,'receipt',None)})
    result['receipts']=[*api.http.receipts,*client.http.receipts]
    result['operation_status']='PARTIAL' if result['checks'] or result['screens'] else 'BLOCKED_OR_UNQUALIFIED'
    result['production_enabled']=False
    result['wall_ms']=round((time.monotonic()-started)*1000);result['completed_at']=now_utc()
    return result
