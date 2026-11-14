"""Restricted finite expression DAG and source-gated remote pack contracts.

Only registered expressions compile to Basis. The local evaluator is a bounded
selected oracle, never a universe scanner. New expressions require Local source
oracle qualification before the operational registry can dispatch them.
"""
from dataclasses import dataclass, asdict
from decimal import Decimal as D
from statistics import median
from .contracts import ContractError, digest, encode, number
from .numerics import validate_bars, wilder_atr, compression

VERSION='packs-6a.1'
SCHEMA='evidence/external-first/session55/provider-schema.json'


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple


def node(op,*args):return Expr(op,args)
def field(name):return node('field',name)
def const(n):return node('constant',str(n))
def lag(x,n):return node('lag',x,n)
def add(a,b):return node('+',a,b)
def sub(a,b):return node('-',a,b)
def mul(a,b):return node('*',a,b)
def div(a,b):return node('/',a,b)
def choose(c,a,b):return node('if',c,a,b)
def maximum(a,b):return node('max',a,b)
def absolute(x):return node('abs',x)
def window(op,x,n):return node(op,x,n)
def positive_ratio(a,b):return choose(node('>',b,const(0)),add(const(1),div(a,b)),const(0))


def compile_expr(e):
    if not isinstance(e,Expr):raise ContractError('REGISTERED_DSL_NODE_REQUIRED')
    op,a=e.op,e.args
    arities={'field':1,'constant':1,'lag':2,'+':2,'-':2,'*':2,'/':2,'>':2,'<':2,
        '==':2,'>=':2,'<=':2,'highest':2,'lowest':2,'median':2,'sum':2,'rma':2,
        'if':3,'max':2,'abs':1}
    if op not in arities or len(a)!=arities[op]:raise ContractError('UNREGISTERED_DSL_OPERATION')
    if op=='field':
        if a[0] not in {'open','high','low','close','quote_volume'}:raise ContractError('DSL_FIELD')
        return a[0]
    if op=='constant':return str(number(a[0]))
    if op=='lag':
        if type(a[1]) is not int or not 1<=a[1]<=160:raise ContractError('DSL_POSITIVE_LAG')
        return '('+compile_expr(a[0])+')['+str(a[1])+']'
    if op in {'+','-','*','/','>','<','==','>=','<='}:
        return '('+compile_expr(a[0])+op+compile_expr(a[1])+')'
    if op in {'highest','lowest','median','sum','rma'}:
        if type(a[1]) is not int or not 1<=a[1]<=160:raise ContractError('DSL_BOUNDED_WINDOW')
        return op+'('+compile_expr(a[0])+','+str(a[1])+')'
    if op in {'if','max','abs'}:return op+'('+','.join(compile_expr(x) for x in a)+')'
    raise ContractError('UNREGISTERED_DSL_OPERATION')


def evaluate_expr(e,bars,cache=None):
    """Independent source interpretation is still required after this oracle."""
    cache={} if cache is None else cache
    if e in cache:return cache[e]
    compile_expr(e)  # Reject unknown operations even on unevaluated branches.
    op,a=e.op,e.args;n=len(bars)
    if op=='field':out=[getattr(b,a[0]) for b in bars]
    elif op=='constant':out=[number(a[0])]*n
    elif op=='lag':out=[None]*a[1]+evaluate_expr(a[0],bars,cache)[:max(0,n-a[1])];out=out[:n]
    elif op in {'highest','lowest','median','sum','rma'}:
        x=evaluate_expr(a[0],bars,cache);k=a[1];out=[None]*n
        for i in range(n):
            w=x[max(0,i-k+1):i+1]
            if op=='rma' and i and out[i-1] is not None and x[i] is not None:
                out[i]=((k-1)*out[i-1]+x[i])/k
            elif len(w)==k and all(v is not None for v in w):
                out[i]={'highest':max,'lowest':min,'median':median,'sum':sum,'rma':lambda w:sum(w,D(0))/k}[op](w)
    else:
        xs=[evaluate_expr(x,bars,cache) for x in a];out=[]
        for v in zip(*xs):
            if op=='if':out.append(v[1] if v[0] else v[2] if v[0] is not None else None);continue
            if any(x is None for x in v):out.append(None);continue
            x=v[0];y=v[1] if len(v)>1 else None
            if op=='+':z=x+y
            elif op=='-':z=x-y
            elif op=='*':z=x*y
            elif op=='/':z=x/y if y else None
            elif op=='max':z=max(v)
            elif op=='abs':z=abs(x)
            else:z=D(
                x>y if op=='>' else x<y if op=='<' else x==y if op=='==' else x>=y if op=='>=' else x<=y)
            out.append(z)
    cache[e]=out;return out


O,H,L,C,Q=map(field,('open','high','low','close','quote_volume'))
TR=maximum(sub(H,L),maximum(absolute(sub(H,lag(C,1))),absolute(sub(L,lag(C,1)))))
ATR=window('rma',TR,14)
W=div(sub(window('highest',H,16),window('lowest',L,16)),C)
PATH=window('sum',absolute(sub(C,lag(C,1))),16)
QUIET=const(0)
for j in range(16,144):
    QUIET=add(QUIET,choose(node('<',lag(W,j),W),const(1),choose(node('==',lag(W,j),W),const('.5'),const(0))))
QUIET=div(QUIET,const(128))


@dataclass(frozen=True)
class Column:
    id: str
    expr: Expr
    units: str
    history: int
    null: str='NONE_AFTER_DECLARED_WARMUP'
    encoding: str='DIRECT'
    dependencies: tuple=()

    @property
    def expression(self):return compile_expr(self.expr)


CORE_COLUMNS=(
    Column('close',C,'USDT_PER_BASE',1),Column('tr',TR,'USDT_PER_BASE',2),
    Column('atr14',ATR,'USDT_PER_BASE',15,dependencies=('tr',)),
    Column('width16',W,'FRACTION',16),Column('quiet_percentile',QUIET,'FRACTION',159,dependencies=('width16',)),
    Column('efficiency16',positive_ratio(absolute(sub(C,lag(C,16))),PATH),'RATIO',17,
        'ZERO_PATH_UNKNOWN','POSITIVE_MINUS_ONE'),
    Column('progress16',div(C,lag(C,16)),'GROSS_PRICE_RATIO',17),
    Column('prior_high16',window('highest',lag(H,1),16),'USDT_PER_BASE',17),
    Column('prior_low16',window('lowest',lag(L,1),16),'USDT_PER_BASE',17),
    Column('tr_fraction',div(TR,lag(C,1)),'FRACTION',2,dependencies=('tr',)),
    Column('displacement',positive_ratio(TR,lag(ATR,1)),'RATIO',16,
        'ZERO_PRIOR_ATR_UNKNOWN','POSITIVE_MINUS_ONE',('tr','atr14')),
    Column('body_fraction',choose(node('>',H,L),div(absolute(sub(C,O)),sub(H,L)),const(0)),'FRACTION',1))
OPTIONAL_COLUMNS=(Column('quote_rvol32',positive_ratio(Q,window('median',lag(Q,1),32)),
    'QUOTE_VOLUME_RATIO',33,'ZERO_BASELINE_UNKNOWN','POSITIVE_MINUS_ONE'),)


def compile_columns(columns):
    """Publish shared DAG in topological order; provider output is exact code."""
    ids={c.id for c in columns}
    if len(ids)!=len(columns):raise ContractError('DUPLICATE_PACK_COLUMN')
    visited=set();visiting=set();ordered=[]
    def visit(c):
        if c.id in visited:return
        if c.id in visiting:raise ContractError('PACK_DEPENDENCY_CYCLE')
        visiting.add(c.id)
        for d in c.dependencies:
            dep=next((x for x in columns if x.id==d),None)
            if dep is None:raise ContractError('PACK_DEPENDENCY_MISSING')
            visit(dep)
        visiting.remove(c.id);visited.add(c.id);ordered.append(c.id)
    for c in columns:visit(c)
    return {'dependency_order':ordered,'columns':[{**{k:v for k,v in asdict(c).items() if k!='expr'},
        'expression':c.expression,'export_expression':'('+c.expression+')*100000000',
        'formula_sha256':digest(c.expression.encode()),'output_absolute_precision':'1e-10',
        'small_price_scale':100000000} for c in columns]}


def evaluate_core(bars,*,optional=False):
    validate_bars(bars);cache={};out={}
    for c in OPTIONAL_COLUMNS if optional else CORE_COLUMNS:
        if len(bars)<c.history:out[c.id]={'status':'INSUFFICIENT_HISTORY','value':None};continue
        v=evaluate_expr(c.expr,bars,cache)[-1]
        if c.encoding=='POSITIVE_MINUS_ONE':v=v-1 if v is not None and v>0 else None
        out[c.id]={'status':'COMPUTED' if v is not None else 'SOURCE_UNKNOWN','value':v,'units':c.units}
    return out


def early_columns():
    """Fixed confirmed pivot before formation: pre-event, two signs, no lookahead.

    These nominate source-oracle questions, not complete family evaluations.
    Each output is isolated from CORE and has an explicit fixed-age reference.
    """
    from .remote_structure import conjunction, lag as price_lag
    from .precursors import TR as source_tr
    out={}
    for age in (8,12,16):
        for side in (1,-1):
            high=side==1;ext='high' if high else 'low';fn='highest' if high else 'lowest'
            cmp='>' if high else '<';sign='+' if high else '-'
            level=f'{ext}[{age}]'
            prefix=f'let u={level}; let a=rma({source_tr},14)[{age-2}]; '
            pivot=[f'u{cmp}{fn}({ext}[{age+1}],2)',f'u{cmp}={fn}({ext}[{age-2}],2)','a>0']
            # Last two observations approach from the inside; all post-confirmation
            # closes remain on the original side, hence no decisive break required.
            inside=[f'{price_lag("close",j)}'+('<' if high else '>')+'=u' for j in range(age-2)]
            near=['abs(close-u)<=2.5*a','abs(close-u)<abs(close[2]-u)']
            name=f'approach_{age}_'+('upper' if high else 'lower')
            out[name]=prefix+conjunction(pivot+inside+near)
            touch=lambda j:[f'{price_lag("high",j)}>=u-0.15*a',f'{price_lag("low",j)}<=u+0.15*a']
            retreat=f'{price_lag(ext,4)}'+('<u-0.5*a' if high else '>u+0.5*a')
            out[name.replace('approach','pressure')]=prefix+conjunction(pivot+inside+near+touch(5)+[retreat]+touch(3))
    return out


EARLY=early_columns()


def early_oracle(bars):
    """Independent Decimal oracle for the fixed-reference prebreak subclasses."""
    validate_bars(bars);out={}
    atr=wilder_atr(bars) if len(bars)>=15 else []
    for age in (8,12,16):
        for side in (1,-1):
            suffix=str(age)+'_'+('upper' if side==1 else 'lower')
            if len(bars)<age+15:
                out['approach_'+suffix]=None;out['pressure_'+suffix]=None;continue
            b=lambda j:bars[-1-j]
            level=b(age).high if side==1 else b(age).low
            x=lambda j:side*(b(j).high if side==1 else b(j).low)
            z=side*level;a=atr[-1-age+2]
            pivot=z>max(x(age+1),x(age+2)) and z>=max(x(age-1),x(age-2))
            inside=all(side*(b(j).close-level)<=0 for j in range(age-2))
            approach=bool(a and pivot and inside and abs(b(0).close-level)<=D('2.5')*a
                and abs(b(0).close-level)<abs(b(2).close-level))
            touch=lambda j:b(j).high>=level-D('.15')*a and b(j).low<=level+D('.15')*a
            pressure=approach and touch(5) and touch(3) and x(4)<z-D('.5')*a
            out['approach_'+suffix]=D(approach);out['pressure_'+suffix]=D(pressure)
    return out


def quiet_near_columns():
    from .precursors import FEATURES
    q=FEATURES['quiet_percentile'].expression
    prefix,_,last=q.rpartition(';')
    return {k.replace('approach','quiet_near'):v.rpartition(';')[0]+'; '+prefix+'; let quiet='+last+'; '
            'if(quiet<=0.2,'+v.rpartition(';')[2]+',0)'
            for k,v in EARLY.items() if k.startswith('approach')}


QUIET_NEAR=quiet_near_columns()


def correction_columns():
    from .precursors import TR as tr
    from .remote_structure import conjunction,lag as source_lag
    out={}
    for side in (1,-1):
        high=side==1;end='high' if high else 'low';start='low' if high else 'high'
        fn='highest' if high else 'lowest';op='>' if high else '<'
        otherfn='lowest' if high else 'highest';otherop='<' if high else '>'
        pivot=[]
        for field,age,f,cmp in [(end,8,fn,op),(end,16,fn,op),
                                  (start,12,otherfn,otherop),(start,20,otherfn,otherop)]:
            pivot += [f'{field}[{age}]{cmp}{f}({field}[{age+1}],2)',
                      f'{field}[{age}]{cmp}={f}({field}[{age-2}],2)']
        trend=[f'{end}[8]{op}{end}[16]',f'{start}[12]{op}{start}[20]']
        prefix=f'let a=rma({tr},14)[10]; let s={start}[12]; let e={end}[8]; let amp=abs(e-s); '
        rho='abs(e-close)/amp'
        guards=['a>0','amp>0',rho+'>=0.15',rho+'<=0.70','abs(close-s)<=2.5*a',
            'median(high-low,3)<=median((high-low)[8],4)']
        defended=[f'{source_lag("close",j)}{op}s' for j in range(6)]
        out['controlled_correction_'+('long' if high else 'short')]=prefix+conjunction(pivot+trend+guards+defended)
    return out


CORRECTIONS=correction_columns()


def correction_oracle(bars):
    validate_bars(bars)
    if len(bars)<35:return {k:None for k in CORRECTIONS}
    atr=wilder_atr(bars);out={};b=lambda j:bars[-1-j]
    for side in (1,-1):
        high=side==1
        val=lambda field,j:getattr(b(j),field)
        endpoint='high' if high else 'low';startpoint='low' if high else 'high'
        good=True
        for field,age,s in [(endpoint,8,side),(endpoint,16,side),(startpoint,12,-side),(startpoint,20,-side)]:
            p=s*val(field,age)
            good=good and p>max(s*val(field,age+1),s*val(field,age+2)) and p>=max(s*val(field,age-1),s*val(field,age-2))
        good=good and side*(val(endpoint,8)-val(endpoint,16))>0 and side*(val(startpoint,12)-val(startpoint,20))>0
        s,e=val(startpoint,12),val(endpoint,8);amp=abs(e-s);a=atr[-11]
        rho=abs(e-b(0).close)/amp if amp else None
        small=median(x.high-x.low for x in bars[-3:])<=median(b(j).high-b(j).low for j in (8,9,10,11))
        out['controlled_correction_'+('long' if high else 'short')]=D(bool(good and amp and a
            and D('.15')<=rho<=D('.70') and abs(b(0).close-s)<=D('2.5')*a and small
            and all(side*(b(j).close-s)>0 for j in range(6))))
    return out


def quiet_near_oracle(bars):
    early=early_oracle(bars)
    if len(bars)<159:return {k:None for k in QUIET_NEAR}
    quiet=compression(bars)['past_percentile']<=D('.2')
    return {k:D(bool(early[k.replace('quiet_near','approach')]) and quiet) for k in QUIET_NEAR}


def contracts():
    core=compile_columns(CORE_COLUMNS);optional=compile_columns(OPTIONAL_COLUMNS)
    base={'version':VERSION,'source':'BASIS_BINANCE_FUTURES_USDT','schema_receipt':SCHEMA,
        'lookback':300,'warmup':'ATR_FIRST_14_VALID_TRS; FIXED_PROVIDER_START',
        'cutoff':'EXACT_LAST_CLOSED_BAR_SOURCE_ADVANCEMENT_REJECTED',
        'chunk_size':50,'limit':60,'filler_policy':'EXCLUDE_FROM_REQUESTED_COUNTS',
        'source_supported':False,'full_core_qualified':False,
        'capability_status':'REMOTE_SCHEMA_VERIFIED_BUT_NEEDS_LOCAL_ORACLE',
        'provider_functions':['if','max','abs','highest','lowest','median','sum','rma','positive_lag'],
        'oracle_tests':'tests/test_session6a.py; inherited genuine source receipts',
        'failure_isolation':'FINITE_CORE_SEPARATE_OPTIONAL_COLUMNS_AND_EVENT_PACKS'}
    out={}
    for tf,label in [('1h','1H'),('15m','15M')]:
        out['CORE_'+label]={**base,**core,'timeframe':tf,'required_history':159}
        out['PARTICIPATION_'+label]={**base,**optional,'timeframe':tf,'required_history':33}
        out['METHOD_STRUCTURE_'+label]={**base,'timeframe':tf,'columns':EARLY,
            'family_eligibility':['F1','F2','F3','F4','F5','F6','F7','F8','F9'],
            'scope':'FIXED_REFERENCE_PREBREAK_APPROACH_SUBCLASS; NOT_FULL_FAMILY',
            'no_event':0,'unknown':'ROW_ERROR_OR_INSUFFICIENT_HISTORY_NEVER_ZERO',
            'reference':'PIVOT_AGE_8_12_16; CONFIRMED_AFTER_TWO_RIGHT_BARS; FROZEN_CONFIRMATION_ATR',
            'temporal_output':'SCALAR_MASK_IS_NOT_EVENT_CHRONOLOGY; SELECTED_EVENT_TAIL_REQUIRED'}
        out['METHOD_QUIET_LOCATION_'+label]={**base,'timeframe':tf,'columns':QUIET_NEAR,
            'required_history':159,'scope':'PAST_ONLY_QUIET_AT_FROZEN_CONFIRMED_PIVOT_APPROACH',
            'no_event':0,'failure_isolation':'LONG_HISTORY_OPTIONAL_NEVER_POISONS_SHORT_EARLY_PACK'}
        out['METHOD_TREND_CORRECTION_'+label]={**base,'timeframe':tf,'columns':CORRECTIONS,
            'required_history':35,'scope':'CONFIRMED_COMPARABLE_LADDER_CONTROLLED_COUNTERLEG_PRE_RESPONSE',
            'no_event':0,'frozen_reference':'DEFENDED_PIVOT_T_MINUS_12; ATR_AT_CONFIRMATION_T_MINUS_10',
            'failure_isolation':'SEPARATE_REGISTERED_FORMATION_SUBCLASS'}
    for name,needs in [('METHOD_AUCTION_VALUE',['Q_BASE_VOLUME_ANCHOR_RESET','TRUE_TAPE_FOR_PROFILE']),
                        ('RELATIONSHIP',['SYNCHRONIZED_ASSET_BENCHMARK_HISTORY','DATED_SECTOR_MEMBERSHIP']),
                        ('DERIV_SPECIALIST',['OI_MULTIPLIER_MARK','ACTUAL_FUNDING_INTERVAL','EXECUTED_FLOW_COVERAGE'])]:
        out[name]={**base,'timeframes':['15m','1h'],'required_inputs':needs,
            'capability_status':'SOURCE_CAPABILITY_REQUIRED','compilation':'STRICT_TYPED_REDUCER_ADAPTER',
            'code_path':'researcher.method_engine.specialist_method' if name=='DERIV_SPECIALIST' else 'researcher.method_engine.evaluate_methods'}
    return out


def registered(expression):
    return expression in set(EARLY.values()) | set(QUIET_NEAR.values()) | set(CORRECTIONS.values()) | {v for cols in (CORE_COLUMNS,OPTIONAL_COLUMNS)
        for c in cols for v in (c.expression,'('+c.expression+')*100000000')}


def column_by_export(expression):
    return next((c for c in (*CORE_COLUMNS,*OPTIONAL_COLUMNS)
        if expression=='('+c.expression+')*100000000'),None)


def make_remote_pack(pack_id,names):
    from .screening import RemotePack
    spec=contracts().get(pack_id)
    if spec is None or 'columns' not in spec:raise ContractError('SOURCE_CAPABILITY_REQUIRED')
    tf=spec['timeframe']
    columns=tuple((c['id'],c['export_expression'],c['units'],c['history']) for c in spec['columns']) if isinstance(spec['columns'],list) else tuple(
        (k,v,'BOOLEAN_PRECURSOR',spec.get('required_history',31)) for k,v in spec['columns'].items())
    c=columns[0]
    return RemotePack(pack_id,VERSION,tf,c[1],c[0],c[2],max(x[3] for x in columns),'1e-10',tuple(names),columns=columns)


def scenario_budget(n=519,partition=50):
    import math
    if n<0 or not 1<=partition<=50:raise ContractError('BUDGET_SCENARIO')
    p=math.ceil(n/partition)
    return {'classification':'SCENARIO_NOT_LIVE_MEASUREMENT','historical_inventory':n,'partitions':p,
        'two_timeframe_core':2*p,'optional_participation':2*p,'two_timeframe_early_structure':2*p,
        'all_three_layers':6*p,'optional_quiet_location_extra':2*p,'optional_correction_extra':2*p,
        'method_count_does_not_multiply_scans':31,
        'optional_packs_run_independently':True,'selected_history_limit':{'symbols':5,'bars':300,'calls':10},
        'quota_charges':'UNKNOWN','scheduler_enabled':False,'compulsory_broad_local_history':False}
