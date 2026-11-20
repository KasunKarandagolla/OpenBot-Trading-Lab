"""Restricted finite compiler for narrow, chronological remote nominations.

This is a registered price-geometry subclass, not universal SMC coverage. Three
fixed-age confirmed pivots are frozen before any event. All offsets are positive;
zero is spelled as the current field (Basis high[0] is not current high).
"""
from dataclasses import dataclass, asdict
from decimal import Decimal as D
from .contracts import ContractError, digest, encode
from .precursors import TR
from .numerics import validate_bars, wilder_atr

VERSION = 'method-structure-5.5.0'
AGES = (8, 12, 16)
BITS = {1: ('F2', 1), 2: ('F2', -1), 4: ('F4', 1),
        8: ('F4', -1), 16: ('F5', 1), 32: ('F5', -1)}


def lag(field, age):
    if field not in {'open','high','low','close'} or type(age) is not int or not 0<=age<=20:
        raise ContractError('UNREGISTERED_FORMULA')
    return field if age==0 else f'{field}[{age}]'


def conjunction(terms):
    out='1'
    for term in reversed(terms): out=f'if({term},{out},0)'
    return out


@dataclass(frozen=True)
class Detector:
    pivot_age: int
    def __post_init__(self):
        if type(self.pivot_age) is not int or self.pivot_age not in AGES:
            raise ContractError('UNREGISTERED_FORMULA')

    @property
    def expression(self):
        k=self.pivot_age
        prefix=(f'let a=rma({TR},14)[{k-2}]; let b=0.15*a; '
                f'let u=high[{k}]; let l=low[{k}]; ')
        predicates=[]
        for side,level,extreme,other,cmp,opposite in (
                (1,'u','high','low','>','<'),(-1,'l','low','high','<','>')):
            edge=level+(' + b' if side==1 else ' - b')
            inside=level+(' - b' if side==1 else ' + b')
            fn='highest' if side==1 else 'lowest'
            pivot=[f'{level}{cmp}{fn}({extreme}[{k+1}],2)',
                   f'{level}{cmp}={fn}({extreme}[{k-2}],2)', 'a>0']
            outside=lambda j:f'{lag("close",j)}{cmp}{edge}'
            within=lambda j:f'{lag("close",j)}{opposite}{inside}'
            pierced=lambda j:f'{lag(extreme,j)}{cmp}{edge}'
            touch=lambda j:[f'{lag("high",j)}>=u-b',f'{lag("low",j)}<=u+b'] if side==1 else [f'{lag("high",j)}>=l-b',f'{lag("low",j)}<=l+b']
            # Two predetermined distinct episodes with an intervening retreat.
            pressure=[*touch(5),*touch(3),f'{lag(extreme,4)}{opposite}{level}'+(' - 0.5*a' if side==1 else ' + 0.5*a'),
                      f'{fn}({extreme}[3],{k-4})'+('<=' if side==1 else '>=')+edge]
            f2=conjunction(pivot+pressure+[outside(2),outside(1),outside(0)])
            # Reclaim and drive occupy distinct completed bars; no OHLC path guess.
            f4=conjunction(pivot+[pierced(3),within(2),within(1),within(0),
                f'{lag("close",1)}{opposite}{lag("close",2)}',
                f'{lag("close",0)}{opposite}{lag("close",1)}'])
            f5=conjunction(pivot+[pierced(5),within(4),within(3),
                f'{lag("close",3)}{opposite}{lag("close",4)}',outside(2),outside(1),outside(0)])
            predicates.extend([(1 if side==1 else 2,f2),(4 if side==1 else 8,f4),(16 if side==1 else 32,f5)])
        return prefix+'+'.join(f'{bit}*({p})' for bit,p in predicates)


DETECTORS={f'boundary_{age}':Detector(age) for age in AGES}
EXPRESSIONS={d.expression for d in DETECTORS.values()}


def reduction_expression(label, offset):
    """Bounded historical scalar oracle reduction, never arbitrary as-of scan."""
    if label not in DETECTORS or type(offset) is not int or not 0<=offset<=260:
        raise ContractError('UNREGISTERED_FORMULA')
    prefix,_,last=DETECTORS[label].expression.rpartition(';')
    return prefix+'; let result='+last+'; '+('result' if offset==0 else f'result[{offset}]')


def registered(expression):
    return expression in EXPRESSIONS or any(expression==reduction_expression(k,j)
        for k in DETECTORS for j in range(261))


def manifest():
    return {'version':VERSION,'columns':{k:{**asdict(d),'expression':d.expression,
        'sha256':digest(d.expression.encode()),'history':d.pivot_age+15,
        'units':'INTEGER_EVENT_MASK_0_TO_63','no_event':0,'unknown':'ROW_FAULT_NOT_ZERO',
        'pivot':'strict left 2, non-strict right 2; known at right confirmation close',
        'buffer':'0.15 * ATR at confirmation; tick floor verified in targeted final review',
        'significance':'CONFIRMED_PIVOT_ONLY; NOT_AUTOMATIC_HIGH_SIGNIFICANCE',
        'event_offsets':{'F2':[5,4,3,2,1,0],'F4':[3,2,1,0],'F5':[5,4,3,2,1,0]},
        'fidelity':'OHLC_PRICE_GEOMETRY; NO_INTRABAR_PATH_OR_HIDDEN_FLOW'} for k,d in DETECTORS.items()},
        'bits':BITS,'dependencies':['closed OHLC','explicit TR/rma14','highest/lowest','positive lag','nested if'],
        'source_cutoff':'LAST_CLOSED_BAR; SOURCE_ADVANCEMENT_REJECTED',
        'scope':'FIXED_AGE_PIVOT_EVENT_TEMPLATES; NOT_EXHAUSTIVE_FAMILY_DETECTION'}


def oracle_masks(bars):
    """Independent Decimal reference, only selected bounded oracle histories."""
    validate_bars(bars)
    if len(bars)<15:return {label:None for label in DETECTORS}
    atr=wilder_atr(bars);out={}
    for label,d in DETECTORS.items():
        k=d.pivot_age
        if len(bars)<k+15:out[label]=None;continue
        b=lambda age:bars[-1-age]
        a=atr[-1-(k-2)]
        if a is None:out[label]=None;continue
        mask=0;buffer=D('.15')*a
        if not a:out[label]=0;continue
        for side in (1,-1):
            level=b(k).high if side==1 else b(k).low
            x=lambda age:b(age).high if side==1 else -b(age).low
            z=side*level
            if not (z>max(x(k+1),x(k+2)) and z>=max(x(k-1),x(k-2))):continue
            c=lambda age:side*b(age).close
            touch=lambda age:b(age).high>=level-buffer and b(age).low<=level+buffer
            f2=(touch(5) and touch(3) and x(4)<z-D('.5')*a
                and max(x(j) for j in range(3,k-1))<=z+buffer
                and all(c(j)>z+buffer for j in (2,1,0)))
            f4=(x(3)>z+buffer and all(c(j)<z-buffer for j in (2,1,0)) and c(0)<c(1)<c(2))
            f5=(x(5)>z+buffer and c(3)<c(4)<z-buffer and all(c(j)>z+buffer for j in (2,1,0)))
            if f2:mask+=1 if side==1 else 2
            if f4:mask+=4 if side==1 else 8
            if f5:mask+=16 if side==1 else 32
        out[label]=D(mask)
    return out


def make_pack(tf,names):
    from .screening import RemotePack
    from .core import CORE,export_expression
    if tf not in {'1h','15m'}:raise ContractError('UNREGISTERED_FORMULA')
    first=next(iter(DETECTORS))
    return RemotePack('METHOD_STRUCTURE_'+tf,VERSION,tf,DETECTORS[first].expression,
        first,'INTEGER_EVENT_MASK',31,'0',tuple(names),columns=tuple(
        (k,d.expression,'INTEGER_EVENT_MASK',d.pivot_age+15) for k,d in DETECTORS.items())+
        (('close',export_expression(CORE['close'].expression),'USDT_PER_BASE',1),))


def scan_registered(engine,inventory,tf,cutoff,qualified_bits):
    """Reuse the existing partition engine; retain only positive event metadata."""
    pack=make_pack(tf,inventory.eligible_symbols)
    result=engine.run(inventory,pack,cutoff);observations=result.pop('observations')
    rows={}
    for o in observations:
        label=o['measurement_id']
        if label not in DETECTORS:continue
        mask=o['value']
        if mask!=int(mask) or not 0<=mask<=63:raise ContractError('INVALID_READING_SEMANTICS')
        n=o['instrument']['native_symbol']
        if mask:
            rows.setdefault(n,[]).append({'column':label,'pivot_age':DETECTORS[label].pivot_age,
                'mask':int(mask),'qualified_mask':int(mask)&sum(qualified_bits),'evidence_id':o['id'],
                'source_response_hash':o['source_response_hash'],'known_by':o['received_at_utc']})
    result['positive_observations']=rows
    result['requested']=len(result['requested_symbols']);result['evaluated']=len(result['evaluated_symbols'])
    result['returned']=len(result['returned_symbols']);result['failed']=len(result['failed_symbols'])
    result['missing']=len(result['missing_symbols']);result['unsupported']=len(result['not_requested_symbols'])
    result['qualified_method_predicates_evaluated']=result['evaluated']
    result['full_method_semantics_complete']=False
    result['qualification']='SOURCE_QUALIFIED_NARROW_CAUSAL_NOMINATION_TEMPLATES'
    result['per_column']={k:{'requested':result['requested'],'evaluated':result['evaluated'],
        'returned':result['returned'],'failed':result['failed'],'missing':result['missing'],
        'unsupported':result['unsupported'],'positive':sum(any(x['column']==k for x in v) for v in rows.values())}
        for k in DETECTORS}
    return result
