"""Deterministic §10.3 planner. A query must answer a disposition-changing fact.

Adapters are injected read-only callables; the default specialist registry is
empty. No agent tool entitlement is treated as a runtime Python capability.
"""
from dataclasses import dataclass
from .contracts import ContractError, utc
from .research import Fact, fact_id

OPERATIONS=frozenset({'market_candles','formula_evaluate','screener_run',
                     'binance_book','binance_premium','binance_klines','specialist_envelope'})
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
    geometry_reference_id: str | None = None
    geometry_direction: int | None = None
    geometry_obstacle_id: str | None = None

    def __post_init__(self):
        if (self.pool not in POOLS or utc(self.start)>=utc(self.end)
                or any(type(x) is not int or x<0 for x in
                       (self.quota,self.latency_ms,self.response_bytes,self.permission_level))):
            raise ContractError('QUERY_CONTRACT')

    @property
    def key(self):
        # Pools/cost estimates are scheduling metadata, not a different fact.
        return fact_id(self.source_id,self.operation,self.native_symbol,self.venue,
            self.timeframe,self.start,self.end,self.fact,self.units,self.geometry_reference_id,
            self.geometry_direction,self.geometry_obstacle_id)


class QueryPlanner:
    def __init__(self, *, budgets=None, byte_budget=2*1024*1024):
        self.budgets=dict(budgets if budgets is not None else {'broad':0,'targeted':4,'exception':1,'watch':1})
        if (set(self.budgets)!=POOLS or any(type(v) is not int or v<0 for v in self.budgets.values())
                or type(byte_budget) is not int or byte_budget<0):
            raise ContractError('QUERY_BUDGET')
        self.byte_budget=byte_budget;self.cache={};self.attempted=set();self.audit=[];self.unavailable={}

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
            relevant=[q for q in queries if q.fact==question.fact]
            # If no operation exists at all, its absence is shared even when
            # different references would require different positive answers.
            ref=card.reference.id if relevant and question.fact in {'REFERENCE_SIGNIFICANCE','HORIZON_RELEVANT','DEPTH_USDT_WITHIN_ROOM'} else None
            absence_key=fact_id(card.native_symbol,card.venue,card.timeframe,card.cutoff,ref,question.fact,question.units,
                [(q.key,q.qualified,q.authorized,q.source_current) for q in queries if q.fact==question.fact])
            if absence_key in self.unavailable:
                return {'status':'UNKNOWN_SHARED_SOURCE_GAP','question':question,'query':None,
                    'first_card_id':self.unavailable[absence_key],'source_gap_key':absence_key}
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
                elif q.fact=='DEPTH_USDT_WITHIN_ROOM' and (q.geometry_reference_id!=card.reference.id
                        or q.geometry_direction!=next(1 if h.direction=='BULLISH' else -1 for h in card.hypotheses if h.family==card.primary_family)
                        or not q.geometry_obstacle_id):
                    reason='GEOMETRY_REFERENCE_MISMATCH'
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
            if status=='UNKNOWN':self.unavailable[absence_key]=card.id
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
            if plan['status']!='QUERY':
                if plan.get('question'):
                    resolved.add(plan['question'].fact)
                    continue
                break
            q=plan['query'];self.attempted.add((card.id,q.key,card.material_hash))
            if (q.source_id,q.operation) not in adapters:
                self.audit.append({'card_id':card.id,'fact':q.fact,'status':'UNKNOWN','reason':'NO_RUNTIME_ADAPTER'})
                resolved.add(q.fact);continue
            self.budgets[q.pool]-=q.quota;self.byte_budget-=q.response_bytes
            try:
                f=adapters[(q.source_id,q.operation)](q)
                if not _answer_valid(q,f,as_of):
                    raise ContractError('QUERY_RESPONSE_SCOPE_OR_FRESHNESS')
            except (ContractError,OSError,KeyError,ValueError,TypeError):
                self.audit.append({'card_id':card.id,'fact':q.fact,'status':'UNKNOWN','reason':'SOURCE_OR_VALIDATION_FAILURE'})
                resolved.add(q.fact);continue
            self.cache[q.key]=f;facts[f.id]=f;resolved.add(q.fact)
            self.audit.append({'card_id':card.id,'status':'VALIDATED','query':q.key,'evidence_id':f.id})
        return facts,decisions


class ResearchSources:
    """Operator-owned capabilities; provider content cannot register authority.

    Default registry is empty. A selected source can independently qualify a
    family/method/TF without editing interpretation, ranking or provider prose.
    Offline certificates are unusable for a LIVE run.
    """
    def __init__(self, *, mode='LIVE', certificates=(), queries=(), adapters=None,
                 nominations=(), selected_inputs=None, screen_source=None,gap_histories=()):
        self.mode=mode;self.certificates=tuple(certificates);self.queries=tuple(queries)
        self.adapters=dict(adapters or {});self.nominations=tuple(nominations)
        self.selected_inputs=dict(selected_inputs or {});self.screen_source=screen_source
        self.gap_histories=tuple(gap_histories)
        self.normalized_facts={}
        from .pack_contracts import contracts
        packs=contracts()
        for c in self.certificates:
            if (c.get('mode')!=mode or c.get('venue')!='BINANCE_USDM'
                    or c.get('authorized_read_only') is not True or c.get('rights_verified') is not True
                    or not c.get('oracle_receipt_hash') or not c.get('source_id')
                    or not c.get('exact_contracts') or not c.get('timeframes')
                    or not set(c.get('families',()))<={f'F{i}' for i in range(1,10)}
                    or not set(c.get('methods',()))<={f'M{i:02d}' for i in range(1,32)}-{'M14','M15'}
                    or not set(c.get('packs',()))<=set(packs)
                    or c.get('formation_causality_verified') is not True):
                raise ContractError('SOURCE_QUALIFICATION_CONTRACT')
            if mode=='LIVE' and (c.get('environment')!='CODEX_LOCAL'
                    or c.get('independent_numeric_oracle') is not True
                    or c.get('source_coverage_verified') is not True):
                raise ContractError('LIVE_SOURCE_QUALIFICATION_REQUIRED')

    @classmethod
    def from_file(cls,path,*,mode='LIVE'):
        """Read an operator-reviewed, hash-bound Local qualification manifest.

        Numeric probes alone deliberately fail this gate. Formation chronology,
        exact coverage, rights and compiler identity need separate actual proof.
        No source file installs a runtime callable or an arbitrary expression.
        """
        import json
        from pathlib import Path
        from .settings import ROOT
        from .contracts import digest
        from .pack_contracts import contracts
        p=Path(path).absolute()
        if '..' in p.parts or not p.is_relative_to(ROOT/'work') or any(x.is_symlink() for x in (p,*p.parents)):
            raise ContractError('SOURCE_QUALIFICATION_CONTRACT')
        doc=json.loads(p.read_text())
        if doc.get('schema_version')!='openbot.source-qualifications.6b.1':
            raise ContractError('SOURCE_QUALIFICATION_CONTRACT')
        certificates=doc.get('certificates',[])
        for c in certificates:
            verified=[]
            for artifact in c.get('proofs',()):
                src=(ROOT/artifact['path']).absolute()
                if ('..' in src.parts or not (src.is_relative_to(ROOT/'work') or src.is_relative_to(ROOT/'evidence'))
                        or any(x.is_symlink() for x in (src,*src.parents))
                        or digest(src.read_bytes())!=artifact['sha256']):
                    raise ContractError('LIVE_SOURCE_QUALIFICATION_REQUIRED')
                verified.append(json.loads(src.read_text()))
            numeric=[v for v in verified if v.get('schema_version')=='openbot.analytical-oracle.6a'
                and v.get('environment')=='CODEX_LOCAL' and v.get('sample_passed') is True
                and not v.get('failures') and v.get('checks') and all(x['passed'] for x in v['checks'])]
            formation=[v for v in verified if v.get('schema_version')=='openbot.formation-oracle.6b.1'
                and v.get('environment')=='CODEX_LOCAL' and v.get('formation_checks')
                and all(x.get('passed') is True and x.get('source_hash') and x.get('known_at') for x in v['formation_checks'])
                and v.get('point_in_time_causality_passed') is True and v.get('source_coverage_verified') is True]
            if not numeric or not formation:raise ContractError('LIVE_SOURCE_QUALIFICATION_REQUIRED')
            for pid in c.get('packs',()):
                spec=contracts()[pid]
                if c.get('pack_contract_hashes',{}).get(pid)!=digest(encode(spec).encode()):
                    raise ContractError('LIVE_SOURCE_QUALIFICATION_REQUIRED')
            for n in c['exact_contracts']:
                for tf in c['timeframes']:
                    if not any(v['native_symbol']==n and v['timeframe']==tf for v in numeric):
                        raise ContractError('LIVE_SOURCE_QUALIFICATION_REQUIRED')
            if not all(any(set(c.get(key,()))<=set(v.get(key,())) for v in formation)
                       for key in ('families','methods')):
                raise ContractError('LIVE_SOURCE_QUALIFICATION_REQUIRED')
        return cls(mode=mode,certificates=certificates)

    def qualified(self, symbol, tf, cutoff, *, field='families', as_of=None):
        result=set()
        for c in self.certificates:
            if (symbol in c['exact_contracts'] and tf in c['timeframes']
                    and utc(c['valid_from'])<=utc(cutoff)<=utc(c['valid_until'])
                    and (as_of is None or utc(as_of)<=utc(c['valid_until']))):
                result.update(c.get(field,()))
        return result

    def questions(self,card,as_of,review=None):
        # Queries have to be independently registered and match this card.
        allowed=[]
        for q in self.queries:
            if q.native_symbol!=card.native_symbol:continue
            if q.fact=='DEPTH_USDT_WITHIN_ROOM' and (not review or
                    q.geometry_obstacle_id!=review['room'].get('first_obstacle_id')):continue
            certs=[c for c in self.certificates if c['source_id']==q.source_id
                and card.native_symbol in c['exact_contracts'] and card.timeframe in c['timeframes']
                and utc(c['valid_from'])<=utc(q.start)<utc(q.end)<=utc(c['valid_until'])
                and utc(as_of)<=utc(c['valid_until']) and q.operation in c.get('operations',())
                and c.get('facts',{}).get(q.fact)==q.units]
            if certs:allowed.append(q)
        return allowed

    def covered_gap(self,gap):
        from .numerics import validate_bars
        from .observations import WIDTHS
        names=set(gap['symbols']);tf=gap['scope'].rsplit(':',1)[-1]
        # WATCH scopes carry the actual reference's timeframe instead.
        if tf not in WIDTHS:tf=gap.get('timeframe')
        if tf not in WIDTHS:return False
        covered=set()
        for history in self.gap_histories:
            if history.get('mode')!=self.mode or history.get('timeframe')!=tf:continue
            bars=history.get('bars',())
            try:validate_bars(bars)
            except ContractError:continue
            if not bars or len(bars)>300:continue
            n=bars[0].native_symbol
            if (n not in names or not self.qualified(n,tf,gap['before_current'])
                    or utc(bars[0].end)>utc(gap['after']) or utc(bars[-1].end)<utc(gap['before_current'])
                    or any(utc(b.available_at or b.received_at)<utc(b.end) for b in bars)):
                continue
            covered.add(n)
        return names<=covered

    def independent(self, *, as_of, eligible):
        from .method_engine import analyze_specialist_envelope
        accepted=[];faults=[]
        for n in self.nominations:
            try:
                e=n['envelope'];mid=n['method_id'];fam=n['family']
                cert=next((c for c in self.certificates if c['source_id']==n['source_id']
                    and e.native_symbol in c['exact_contracts'] and n['timeframe'] in c['timeframes']
                    and mid in c.get('methods',()) and fam in c.get('families',())
                    and utc(c['valid_from'])<=utc(e.start)<utc(e.end)<=utc(c['valid_until'])
                    and utc(as_of)<=utc(c['valid_until'])),None)
                if (not cert or e.mode!=self.mode or e.native_symbol not in eligible
                        or e.coverage!='COMPLETE' or not n.get('question')):
                    raise ContractError('SPECIALIST_SOURCE_SCOPE_UNQUALIFIED')
                result=analyze_specialist_envelope(mid,e,as_of=as_of)
                if result['status']!='COMPUTED':raise ContractError('SPECIALIST_NOMINATION_UNKNOWN')
                key=(e.native_symbol,n['timeframe'])
                self.selected_inputs.setdefault(key,{})[mid]=e.payload
                if mid=='M17':
                    profile=result['value']
                    self.selected_inputs.setdefault(key,{}).setdefault('true_profiles',[]).append(profile)
                    self.selected_inputs[key][mid]=e.payload
                    self.normalized_facts[profile['id']]=Fact(profile['id'],eligible[e.native_symbol],
                        'TRUE_EXECUTED_PROFILE',profile,profile['units'],n['timeframe'],e.end,
                        e.known_at,e.available_at,e.received_at,n['source_id'],e.source_hash,
                        'SYNCHRONIZED_REMOTE_RECONSTRUCTION',True,'QUALIFIED',self.mode,86400,cluster='VALUE_LOCATION')
                accepted.append({'native_symbol':e.native_symbol,'timeframe':n['timeframe'],
                    'routes':['B_SPECIALIST'],'families':[fam],'questions':[n['question']],
                    'evidence_ids':[e.source_hash],'specialist_method':mid,
                    'source_envelope':result['source_envelope'],'vendor_score_is_not_certification':True})
            except (ContractError,KeyError,TypeError,ValueError):
                faults.append({'route':'B','status':'UNAVAILABLE_SOURCE','reason':'SPECIALIST_SOURCE_SCOPE_OR_SEMANTICS'})
        return accepted,faults

    def inputs_for(self,symbol,tf,cutoff,as_of):
        mids=self.qualified(symbol,tf,cutoff,field='methods',as_of=as_of)
        raw=self.selected_inputs.get((symbol,tf),{})
        # Caller-provided candle proxies cannot enter specialist reducers.
        return {k:v for k,v in raw.items() if k in mids or
            k=='true_profiles' and 'M17' in mids or k=='event_anchor' and 'M19' in mids or
            k=='observed_liquidation' and 'M28' in mids}


def decision_questions(review):
    """Possible answers are specified before any source operation."""
    required=[('REFERENCE_SIGNIFICANCE','ORDINAL',('LOW_SIGNIFICANCE_WATCH','SIGNIFICANT_ADMISSION_REVIEW')),
        ('RESEARCH_PRICE','USDT_PER_BASE',('ROOM_EXHAUSTED','ROOM_OBSERVED')),
        ('DEPTH_USDT_WITHIN_ROOM','USDT',('ECONOMICS_UNKNOWN','ECONOMICS_OBSERVED')),
        ('ROUND_TRIP_FEE_BPS','BPS',('ECONOMICS_UNFAVORABLE','ECONOMICS_FEASIBLE')),
        ('HORIZON_RELEVANT','BOOLEAN',('HORIZON_UNCERTAIN','WITHIN_RESEARCH_HORIZON'))]
    if review['stage'] in {'INVALIDATED','LATE'}:return ()
    return tuple(Question(k,i,u,changes) for i,(k,u,changes) in enumerate(required))
