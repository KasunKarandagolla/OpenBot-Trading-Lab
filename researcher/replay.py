"""Explicit network-free sources for the ordinary scan, never LIVE substitutes.

Retained projections preserve original values/receipts/availability. Synthetic
controls generate declared source observations, not prebuilt decisions/cards.
"""
import copy
import json
from dataclasses import replace
from decimal import Decimal as D
from types import SimpleNamespace
from .contracts import ContractError, Instrument, digest, encode, utc
from .inventory import InventorySnapshot
from .numerics import Bar
from .observations import WIDTHS, iso_seconds
from .query_planner import ResearchSources
from .settings import ROOT

FIELDS={'open','high','low','close','base_volume','quote_volume','buy_base','buy_quote'}


def decode_bars(rows):
    return [Bar(**{k:D(v) if k in FIELDS else v for k,v in r.items()}) for r in rows]


class OfflineHTTP:
    def __init__(self, api):self.api=api;self.receipts=[]

    def request(self, endpoint, *, query=None):
        if self.api.mode!='SYNTHETIC' or endpoint!='binance_depth':
            raise ContractError('OFFLINE_SOURCE_UNAVAILABLE')
        n=query['symbol'];p=self.api.prices[n];at=self.api.at
        raw={'T':int(utc(at).timestamp()*1000),'bids':[[str(p-D('.01')),'10000']],
             'asks':[[str(p+D('.01')),'10000']]}
        body=encode(raw).encode();receipt={'requested_query':query,'received_at_utc':at,
            'response_sha256':digest(body),'elapsed_ms':0,'response_bytes':len(body),
            'http_status':200,'classification':'SYNTHETIC; ZERO_HTTP'}
        return SimpleNamespace(body=body,receipt=receipt)


class OfflineClient:
    def __init__(self):self.http=SimpleNamespace(receipts=[]);self.tools={}
    def connect(self):return {}


class ReplayAPI:
    def __init__(self, *, at, mode, instruments, samples, inventory_hash, original_inventory=None):
        self.at=at;self.mode=mode;self.instruments=tuple(instruments);self.samples=samples
        self.inventory_hash=inventory_hash;self.original_inventory=original_inventory
        self.http=OfflineHTTP(self);self.sample_calls=0
        self.prices={n:series[-1].close for (n,tf),(series,s) in samples.items() if tf=='1h'}

    def inventory(self):
        return InventorySnapshot(self.mode+'_SOURCE_SUBSET','OFFLINE_RETAINED_OR_CONTROLLED',
            max(i.captured_at_utc for i in self.instruments),self.at,self.inventory_hash,self.instruments,
            'PARTIAL_INVENTORY' if self.original_inventory else 'VERIFIED_INVENTORY',
            eligible_symbols=tuple(i.native_symbol for i in self.instruments),
            complete_source_snapshot=not bool(self.original_inventory),freshness='FRESH')

    def pulse(self, inventory, *, partial=False, kinds=('ticker','book','premium')):
        result=[]
        for k in kinds:
            obs=[]
            if self.mode=='SYNTHETIC' and k=='book':
                for n,p in self.prices.items():
                    obs.append({'native_symbol':n,'values':{'bid':p-D('.01'),'ask':p+D('.01'),
                        'spread_bps':D('.02')/p*10000},'source_response_sha256':digest(encode([n,p,self.at]).encode()),
                        'source_time_utc':self.at,'received_at_utc':self.at})
            result.append({'kind':k,'observations':obs,'status':'SYNTHETIC' if obs else 'UNAVAILABLE_RETAINED_SOURCE',
                'reason':None if obs else 'NO_QUOTE_OR_BENCHMARK_FABRICATION'})
        return result

    def klines(self, instrument, *, timeframe, cutoff, bars=300):
        key=(instrument.native_symbol,timeframe)
        if key not in self.samples:raise ContractError('OFFLINE_SOURCE_UNAVAILABLE')
        series,source=self.samples[key]
        if series[-1].end!=cutoff:raise ContractError('ORACLE_SOURCE_CUTOFF_MISMATCH')
        self.sample_calls+=1
        return series[-bars:],source


class RetainedScreen:
    def __init__(self, proof):self.proof=proof
    def screen(self, names, pack):
        screen=next(s for s in self.proof['screens'] if s['timeframe']==pack.timeframe)
        data=copy.deepcopy(screen['data']);metadata=dict(screen['transport'])
        expressions=[r['left']['expression'] for r in data['rules']]
        wanted=[c[1] for c in pack.columns]
        if not set(wanted)<=set(expressions):raise ContractError('OFFLINE_SOURCE_UNAVAILABLE')
        indices=[expressions.index(e) for e in wanted]
        data['rules']=[data['rules'][j] for j in indices]
        for row in data['results']:
            row['values']=[row['values'][j] for j in indices]
            row['matchedRules']=str(len(indices))+'/'+str(len(indices))
        # This is a read-only column projection of a retained original response,
        # not an additional provider request or a newly observed receipt.
        return data,metadata


def retained_session5():
    path=ROOT/'evidence/external-first/session5/core-qualification.json'
    proof=json.loads(path.read_text());raw=proof['inventory']
    instruments=[Instrument(**{**r,'tick_size':D(r['tick_size'])}) for r in raw['selected_instruments']]
    samples={}
    for s in proof['independent_selected_bars']:
        rows=[{**s['bar_common'],**dict(zip(s['bar_columns'],v))} for v in s['bars']]
        series=decode_bars(rows);samples[series[0].native_symbol,series[0].timeframe]=(series,s['source'])
    at=proof['completed_at']
    api=ReplayAPI(at=at,mode='AUTHENTIC_REPLAY',instruments=instruments,samples=samples,
        inventory_hash=raw['content_sha256'],original_inventory=raw)
    sources=ResearchSources(mode='AUTHENTIC_REPLAY',screen_source=RetainedScreen(proof))
    sources.retained_receipts=[r for r in proof['receipts'] if 'basischarts.com' in r.get('endpoint','')]
    provenance={'artifact':str(path.relative_to(ROOT)),
        'sha256':digest(path.read_bytes()),'historical_eligible_denominator':raw['eligible_contracts'],
        'exact_selected_contracts':list(api.prices),'scope':'RETAINED_FIVE; NO_CURRENT_OR_FULL_UNIVERSE_CLAIM',
        'projection':'EXACT_COLUMNS_FROM_RETAINED_RESPONSE; ORIGINAL_HASH_PRESERVED','network_requests':0}
    sources.provenance=provenance
    return api,OfflineClient(),sources,at,provenance


class SyntheticScreen:
    def __init__(self,api):self.api=api
    def screen(self,names,pack):
        from .core import oracle_value,CORE
        from .pack_contracts import evaluate_core,CORE_COLUMNS,OPTIONAL_COLUMNS
        rows=[]
        for n in names:
            bars,source=self.api.samples[n,pack.timeframe];values=[]
            for label,expression,units,history in pack.columns:
                if label in CORE:value=oracle_value(label,bars)
                else:value=evaluate_core(bars,optional=label=='quote_rvol32')[label]['value']
                if value is None:encoded=0
                else:
                    column=next((c for c in (*CORE_COLUMNS,*OPTIONAL_COLUMNS) if c.id==label and expression=='('+c.expression+')*100000000'),None)
                    encoded=(value+1 if column and column.encoding=='POSITIVE_MINUS_ONE' or label=='quote_rvol32' else value)*100000000
                values.append({'left':encoded,'right':0,'matched':True,'ruleId':label})
            rows.append({'symbol':n,'observationTime':bars[-1].open_ms//1000,
                'last':bars[-1].close,'values':values,'matchedRules':str(len(values))+'/'+str(len(values))})
        data={'exchange':'binance','market':'futures','quote':'USDT','timeframe':pack.timeframe,
            'lookback':300,'logic':'all','limit':60,'truncated':False,'screened':len(names),'evaluated':len(names),
            'matched':len(names),'returned':len(names),'couldNotEvaluate':0,'results':rows,
            'rules':[{'id':c[0],'left':{'kind':'formula','expression':c[1]},'operator':'atOrAbove',
                'right':{'kind':'constant','value':0}} for c in pack.columns]}
        return data,{'received_at_utc':self.api.at,'response_sha256':digest(encode(data).encode()),
            'schema_sha256':'SYNTHETIC','response_bytes':len(encode(data).encode()),'elapsed_ms':0}


def synthetic_6b():
    """A real positive control through engine/source/room/economics/ledger, no cards injected."""
    end=1794650400;at=iso_seconds(end+10);samples={};instruments=[]
    for n in ('BTCUSDT','ETHUSDT','CONTROLUSDT'):
        instruments.append(Instrument(n,'BINANCE_USDM',quote='USDT',settlement='USDT',contract_type='PERPETUAL',
            tick_size=D('.01'),quantity_rules={'LOT_SIZE':{'minQty':'.01','maxQty':'100000','stepSize':'.01'}},
            exchange_rules=({'filterType':'MIN_NOTIONAL','notional':'5'},),metadata_hash='SYNTHETIC_6B',
            identity_status='EXCHANGE_VERIFIED',trading_status='TRADING',underlying_class='CRYPTO',
            source_id='SYNTHETIC_6B',captured_at_utc=at,onboard_at_utc='2025-01-01T00:00:00+00:00'))
        for tf in ('1h','15m','4h') if n!='CONTROLUSDT' else ('1h','15m'):
            width=WIDTHS[tf];cutoff=end-end%width;series=[]
            rows=[(100,101,99,100)]*200
            if n=='CONTROLUSDT':
                rows[-20]=(100,101,95,100)
                rows[-10:]=[(100,101,99,100),(109,110,108,109),(100,101,99,100),
                    (100,101,99,100),(100,101,99,100),(100,101,99,100),
                    (100,101,99,100),(110,112,109,111),(108,109,107,108),(108,108,104,104.5)]
            for j,(o,h,l,c) in enumerate(rows):
                b_end=iso_seconds(cutoff-(len(rows)-j-1)*width)
                series.append(Bar(n,tf,(cutoff-(len(rows)-j)*width)*1000,*map(lambda v:D(str(v)),(o,h,l,c)),
                    D(1000),D(str(c))*1000,D(500),D(str(c))*500,100,'SYNTHETIC_CONTROL_6B',b_end,available_at=b_end))
            source={'native_symbol':n,'timeframe':tf,'cutoff':iso_seconds(cutoff),
                'source_response_sha256':digest(encode(series).encode()),
                'receipt':{'received_at_utc':at,'response_sha256':digest(encode(series).encode())}}
            samples[n,tf]=(series,source)
    api=ReplayAPI(at=at,mode='SYNTHETIC',instruments=instruments,samples=samples,inventory_hash='SYNTHETIC_6B')
    certificate={'mode':'SYNTHETIC','venue':'BINANCE_USDM','authorized_read_only':True,'rights_verified':True,
        'oracle_receipt_hash':'SYNTHETIC_OFFLINE_CONTROL_6B','source_id':'SYNTHETIC_6B',
        'exact_contracts':['CONTROLUSDT'],'timeframes':['1h','15m'],'families':[f'F{i}' for i in range(1,10)],
        'methods':[],'packs':[],'formation_causality_verified':True,
        'valid_from':iso_seconds(end-86400),'valid_until':iso_seconds(end+86400)}
    sources=ResearchSources(mode='SYNTHETIC',certificates=[certificate],screen_source=SyntheticScreen(api))
    provenance={'classification':'SYNTHETIC_TEST','network_requests':0,
        'source_qualification':'CONTROLLED_OFFLINE_ONLY; DOES_NOT_ENABLE_REAL_PROVIDER'}
    sources.provenance=provenance
    return api,OfflineClient(),sources,at,provenance
