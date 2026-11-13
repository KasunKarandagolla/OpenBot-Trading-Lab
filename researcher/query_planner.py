"""Deterministic §10.3 planner. A query must answer a disposition-changing fact.

Adapters are injected read-only callables; the default specialist registry is
empty. No agent tool entitlement is treated as a runtime Python capability.
"""
from dataclasses import dataclass
from .contracts import ContractError, utc
from .research import Fact, fact_id

OPERATIONS=frozenset({'market_candles','formula_evaluate','screener_run',
                     'binance_book','binance_premium','binance_klines'})
POOLS=frozenset({'broad','targeted','exception','watch'})
POINT_OPERATIONS=frozenset({'binance_book','binance_premium'})


def _answer_valid(q, f, as_of):
    point=q.operation in POINT_OPERATIONS
    return (isinstance(f,Fact) and f.source_id==q.source_id and f.measurement==q.fact
        and f.timeframe==q.timeframe and f.usable(as_of=as_of,native_symbol=q.native_symbol,
            venue=q.venue,units=q.units,qualified=True,cutoff=None if point else q.end)
        and (not point or utc(q.start)<=utc(f.window_end)<=utc(q.end)
             and (utc(as_of)-utc(f.window_end)).total_seconds()<=30))


@dataclass(frozen=True)
class Question:
    fact: str
    priority: int
    units: str
    changes: tuple[str,...]
    necessary: bool = True
    contradiction: bool = False


@dataclass(frozen=True)
class Query:
    source_id: str
    operation: str
    native_symbol: str
    venue: str
    timeframe: str
    start: str
    end: str
    fact: str
    units: str
    pool: str
    quota: int
    latency_ms: int
    response_bytes: int
    qualified: bool
    authorized: bool
    complete_window: bool
    source_current: bool
    permission_level: int = 0

    def __post_init__(self):
        if (self.pool not in POOLS or utc(self.start)>=utc(self.end)
                or any(type(x) is not int or x<0 for x in
                       (self.quota,self.latency_ms,self.response_bytes,self.permission_level))):
            raise ContractError('QUERY_CONTRACT')

    @property
    def key(self): return fact_id(self)


class QueryPlanner:
    def __init__(self, *, budgets=None, byte_budget=2*1024*1024):
        self.budgets=dict(budgets if budgets is not None else {'broad':0,'targeted':4,'exception':1,'watch':1})
        if (set(self.budgets)!=POOLS or any(type(v) is not int or v<0 for v in self.budgets.values())
                or type(byte_budget) is not int or byte_budget<0):
            raise ContractError('QUERY_BUDGET')
        self.byte_budget=byte_budget;self.cache={};self.attempted=set();self.audit=[]

    def next(self, card, questions, queries, facts, *, as_of):
        # Context changes never manufacture a missing fact or a permission.
        unresolved=[]
        for q in questions:
            if not q.changes or len(set(q.changes))<2: continue
            current=[f for f in facts.values() if f.measurement==q.fact and f.timeframe in {card.timeframe,'CURRENT'}
                and f.usable(as_of=as_of,native_symbol=card.native_symbol,units=q.units,qualified=True,
                             cutoff=None if f.timeframe=='CURRENT' else card.cutoff)
                and (f.timeframe!='CURRENT' or (utc(as_of)-utc(f.window_end)).total_seconds()<=30)]
            if not current or q.contradiction: unresolved.append(q)
        unresolved.sort(key=lambda q:(not q.necessary,not q.contradiction,q.priority,q.fact))
        for question in unresolved:
            viable=[];reasons=[]
            for q in queries:
                if q.fact!=question.fact:continue
                reason=None;point=q.operation in POINT_OPERATIONS
                if q.operation not in OPERATIONS:reason='UNSUPPORTED_OPERATION'
                elif not q.authorized:reason='UNAUTHORIZED_SOURCE'
                elif not q.qualified:reason='UNQUALIFIED_SOURCE'
                elif (q.native_symbol!=card.native_symbol or q.venue!=card.venue
                        or (not point and (q.timeframe!=card.timeframe or utc(q.end)!=utc(card.cutoff)
                            or utc(q.start)!=utc(card.window_start)))
                        or (point and (q.timeframe!='CURRENT' or utc(q.end)!=utc(as_of)
                            or not 0<(utc(q.end)-utc(q.start)).total_seconds()<=30))):reason='IDENTITY_VENUE_OR_WINDOW_MISMATCH'
                elif q.units!=question.units:reason='UNIT_MISMATCH'
                elif not q.complete_window:reason='INCOMPLETE_SOURCE_WINDOW'
                elif not q.source_current or utc(q.end)>utc(as_of):reason='STALE_OR_FUTURE_SOURCE'
                elif q.key in self.cache:
                    f=self.cache[q.key]
                    if _answer_valid(q,f,as_of):
                        return {'status':'CACHED','question':question,'query':q,'fact':f}
                    reason='STALE_CACHE'
                elif (card.id,q.key,card.material_hash) in self.attempted:reason='UNCHANGED_WATCH_ALREADY_QUERIED'
                elif q.quota>self.budgets[q.pool] or q.response_bytes>self.byte_budget:reason='NOT_REVIEWED_BUDGET'
                if reason: reasons.append({'query':q.key,'reason':reason})
                else:viable.append(q)
            if viable:
                q=min(viable,key=lambda q:(q.permission_level,q.quota,q.latency_ms,q.response_bytes,q.key))
                return {'status':'QUERY','question':question,'query':q}
            status='NOT_REVIEWED_BUDGET' if any(r['reason']=='NOT_REVIEWED_BUDGET' for r in reasons) else 'UNKNOWN'
            self.audit.append({'card_id':card.id,'fact':question.fact,'status':status,
                'rejections':reasons,'reason':None if reasons else 'NO_QUALIFIED_SOURCE'})
            # Necessary missing fact cannot be bypassed with unrelated trivia.
            if question.necessary:return {'status':status,'question':question,'query':None}
        return {'status':'STOP_NO_DECISION_CHANGING_QUERY','query':None}

    def investigate(self, card, questions, queries, facts, *, as_of, adapters, max_steps=8):
        if type(max_steps) is not int or not 0<=max_steps<=16:raise ContractError('QUERY_BUDGET')
        facts=dict(facts);resolved=set();decisions=[]
        for _ in range(max_steps):
            plan=self.next(card,[q for q in questions if q.fact not in resolved],queries,facts,as_of=as_of)
            decisions.append(plan)
            if plan['status']=='CACHED':
                f=plan['fact'];facts[f.id]=f;resolved.add(plan['question'].fact);continue
            if plan['status']!='QUERY':break
            q=plan['query'];self.attempted.add((card.id,q.key,card.material_hash))
            if (q.source_id,q.operation) not in adapters:
                self.audit.append({'card_id':card.id,'status':'UNKNOWN','reason':'NO_RUNTIME_ADAPTER'});break
            self.budgets[q.pool]-=q.quota;self.byte_budget-=q.response_bytes
            try:
                f=adapters[(q.source_id,q.operation)](q)
                if not _answer_valid(q,f,as_of):
                    raise ContractError('QUERY_RESPONSE_SCOPE_OR_FRESHNESS')
            except (ContractError,OSError):
                self.audit.append({'card_id':card.id,'status':'UNKNOWN','reason':'SOURCE_OR_VALIDATION_FAILURE'});break
            self.cache[q.key]=f;facts[f.id]=f;resolved.add(q.fact)
            self.audit.append({'card_id':card.id,'status':'VALIDATED','query':q.key,'evidence_id':f.id})
        return facts,decisions
