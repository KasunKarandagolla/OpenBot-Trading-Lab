"""Evidence-bound planning and comparison for the two required AI stages."""
from dataclasses import asdict, dataclass
from collections import defaultdict, deque
from time import monotonic

from .agent_review import AGENT, _material, parse_reply
from .contracts import ContractError, digest, encode, utc
from .handoff import ALLOWED_QUESTIONS
from .native_handoff import COMPACT_PAGES, MAX_EVIDENCE_PAGES, COMPACT_SUBMISSION_POLICY
from .research import fact_id
from .settings import ROOT

REQUEST = 'openbot.ai-research.request.v1'
REPLY = 'openbot.ai-research.reply.v1'
INLINE = 'INLINE_AI_CORE_V1'
MAX_BRIEF_BYTES = 42000
DISCOVERY = 'DISCOVERY'
FINAL = 'SHORTLIST'
GUIDANCE = ROOT / '.agents/skills/market-research-review/ai-core.md'
# These are approved questions about a method's evidence. The registry still
# determines implementation/fidelity and no method obtains a live certificate.
METHOD_FAMILIES = {
    'M01': '12345689', 'M02': '124589', 'M03': '124567', 'M04': '2456',
    'M05': '4569', 'M06': '1459', 'M07': '145', 'M08': '1379', 'M09': '459',
    'M10': '1467', 'M11': '17', 'M12': '2456', 'M13': '2456',
    'M14': '245', 'M15': '145', 'M16': '2467', 'M17': '2467', 'M18': '2467',
    'M19': '1678', 'M20': '67', 'M21': '2345789', 'M22': '2345679',
    'M23': '245679', 'M24': '45679', 'M25': '23456789', 'M26': '2389',
    'M27': '789', 'M28': '49', 'M29': '189', 'M30': '123689', 'M31': '389',
}
CLOSED_METHODS = frozenset(f'M{i:02d}' for i in (*range(1, 14), 16, 19, 20, 21, 29, 30))
STAGES = frozenset({'EARLY', 'DEVELOPING', 'APPROACHING_DECISION', 'READY_FOR_DEEP',
    'FAST_WITH_ROOM', 'LATE', 'INVALIDATED', 'UNKNOWN'})
DIRECTIONS = frozenset({'BULLISH', 'BEARISH', 'NEUTRAL'})
EXPIRY = frozenset({'NEXT_CLOSED_RESPONSE', 'WITHIN_RESEARCH_HORIZON', 'UNRESOLVED'})
DEEP = frozenset({'READY_FOR_DEEP', 'FAST_WITH_ROOM', 'CONDITIONAL_FOR_DEEP'})


@dataclass(frozen=True)
class Limits:
    max_native_tasks: int = 2
    max_provider_attempts: int = 2 * (MAX_EVIDENCE_PAGES + 1)
    max_input_bytes: int = MAX_BRIEF_BYTES
    max_broad_rows: int = 36
    max_questions: int = 6
    max_cards: int = 10
    deadline_seconds: int = 600
    freshness_seconds: int = 600

    def __post_init__(self):
        maximum = (2, 2 * (MAX_EVIDENCE_PAGES + 1), MAX_BRIEF_BYTES, 100, 12, 12, 600, 600)
        if any(type(v) is not int or not 0 < v <= cap
               for v,cap in zip(asdict(self).values(),maximum,strict=True)):
            raise ContractError('AGENT_INPUT_SIZE')


@dataclass(frozen=True)
class Opportunity:
    row_id: str
    family: str
    method: str
    direction: str
    stage: str
    support: tuple[str, ...]
    contradiction: tuple[str, ...]
    rival: str
    question: str
    expiry: str


def _need(test, code='AGENT_REPLY_CONTRACT'):
    if not test:
        raise ContractError(code)


def _choice(value, choices, code='AGENT_REPLY_ADVICE'):
    _need(isinstance(value, str) and value in choices, code)


def _citations(support, contradiction, available):
    for ids in (support, contradiction):
        _need(isinstance(ids, list) and len(ids) <= 4 and all(isinstance(x, str) for x in ids),
              'AGENT_REPLY_CITATION')
        _need(len(set(ids)) == len(ids) and set(ids) <= available, 'AGENT_REPLY_CITATION')
    _need(bool(support) and not set(support).intersection(contradiction), 'AGENT_REPLY_CITATION')


def validate(reply, request):
    keys = {'schema_version', 'material_sha256', 'stage', 'rows', 'trade_authorization'}
    if request['stage'] == FINAL:
        keys.add('assessment')
    _need(isinstance(reply, dict) and set(reply) == keys
        and reply['schema_version'] == REPLY and reply['stage'] == request['stage']
        and reply['material_sha256'] == request['material_sha256']
        and reply['trade_authorization'] is False and isinstance(reply['rows'], list))
    supplied = {row['id']: row for row in request['evidence']}
    previous = set()
    if request['stage'] == DISCOVERY:
        _need(len(reply['rows']) <= request['question_limit'])
        for row in reply['rows']:
            _need(isinstance(row, dict) and set(row) == set(Opportunity.__dataclass_fields__))
            _choice(row['row_id'], supplied, 'AGENT_REPLY_CARD')
            _choice(row['method'], METHOD_FAMILIES)
            _choice(row['family'], {'F' + f for f in METHOD_FAMILIES[row['method']]})
            _choice(row['direction'], DIRECTIONS)
            _choice(row['stage'], STAGES - {'READY_FOR_DEEP', 'FAST_WITH_ROOM'})
            _choice(row['rival'], {'F' + str(i) for i in range(1, 10)} | {'NULL', 'UNKNOWN'})
            _choice(row['question'], {'VERIFY_METHOD_SEQUENCE'} if row['method'] in CLOSED_METHODS
                    else {'CHECK_SOURCE_FIDELITY'})
            _choice(row['expiry'], EXPIRY)
            key = (row['row_id'], row['family'], row['method'], row['direction'])
            _need(key not in previous, 'AGENT_REPLY_ADVICE')
            previous.add(key)
            _citations(row['support'], row['contradiction'], set(supplied[row['row_id']]['citations']))
    else:
        _need(len(reply['rows']) == len(supplied) and len(reply['rows']) <= request['card_limit'])
        selected = 0
        for row in reply['rows']:
            _need(isinstance(row, dict) and set(row) == {
                'id', 'interpretation', 'rival', 'stage', 'decision', 'support', 'contradiction', 'next_question',
                'deciding_factor'})
            _choice(row['id'], supplied, 'AGENT_REPLY_CARD')
            _need(row['id'] not in previous, 'AGENT_REPLY_CARD')
            previous.add(row['id'])
            card = supplied[row['id']]
            alternatives=card.get('qualified_alternatives',{})
            _need(isinstance(alternatives,dict), 'AGENT_REPLY_CONTRACT')
            _choice(row['interpretation'], set(card['families']) | set(alternatives) | {'NULL', 'UNKNOWN'})
            _choice(row['rival'], set(card['families']) | {'NULL', 'UNKNOWN'})
            _choice(row['stage'], STAGES)
            _choice(row['decision'], {'HANDOFF', 'WATCH', 'DECLINE', 'UNKNOWN'})
            _choice(row['next_question'], ALLOWED_QUESTIONS)
            _choice(row['deciding_factor'], {'ORDERED_CONFIRMATION', 'EARLY_SEQUENCE', 'RIVAL_STRONGER',
                'CONTRADICTION', 'SOURCE_GAP', 'EXPIRED_OR_NO_ROOM', 'FRICTION', 'SHARED_EXPOSURE',
                'NO_SUPPORTED_FORMATION'})
            _citations(row['support'], row['contradiction'], set(card['citations']))
            if row['decision'] == 'HANDOFF':
                target=card
                if row['interpretation'] != card['primary_family']:
                    target=supplied.get(alternatives.get(row['interpretation']))
                    _need(isinstance(target,dict) and target['primary_family']==row['interpretation']
                        and target.get('qualification')=='QUALIFIED'
                        and target['native_symbol']==card['native_symbol']
                        and target['timeframe']==card['timeframe']
                        and target['reference']['id']==card['reference']['id'], 'AGENT_REPLY_ADVICE')
                    _need(any(c in row['support'] and c in card['citations'] and
                        card['citations'][c]==target['citations'].get(c) for c in target['formation_citations']),
                        'AGENT_REPLY_CITATION')
                _need(row['stage'] in {'READY_FOR_DEEP', 'FAST_WITH_ROOM'} and target['eligible'],
                      'AGENT_REPLY_ADVICE')
                _need(bool(set(row['support']).intersection(target['formation_citations'])),
                      'AGENT_REPLY_CITATION')
                selected += 1
        _need(selected <= 5, 'AGENT_REPLY_ADVICE')
        assessment = reply['assessment']
        _need(isinstance(assessment, dict) and set(assessment) == {'finding', 'citations'})
        _choice(assessment['finding'], {'RESEARCH_HANDOFFS'} if selected else {
            'NO_SUPPORTED_OPPORTUNITY', 'WATCH_ONLY', 'SOURCE_OR_COVERAGE_GAP'})
        overall = set(request['assessment_evidence'])
        overall.update(i for card in supplied.values() for i in card['citations'])
        _citations(assessment['citations'], [], overall)
    return {'reply': reply, 'accepted': len(reply['rows'])}


def _ordered_rows(rows, nominations, at):
    buckets = defaultdict(deque)
    for (name, tf), evidence in sorted(rows.items(), key=lambda item: fact_id(at, *item[0])):
        routes = nominations.get((name, tf), {}).get('routes', ())
        route = min(routes, key=lambda r: ('BCA'.index(r[0]), r)) if routes else 'OBSERVED_WITHOUT_NOMINATION'
        buckets[route, tf].append(evidence)
    # Respect the exact research routes, with a chance for independently
    # observed cases and both intervals before any bucket gets a second row.
    while buckets:
        for key in sorted(buckets):
            yield buckets[key].popleft()
            if not buckets[key]:
                del buckets[key]


def _projection(f):
    row = {k: getattr(f, k) for k in ('measurement', 'value', 'units', 'timeframe', 'window_end',
        'known_at', 'available_at', 'received_at', 'response_hash', 'source_id', 'qualification',
        'fidelity', 'cluster', 'complete', 'verdict', 'reason')}
    limit = 2800 if f.measurement.startswith('AI_METHOD_') else 1500
    if len(encode(f.value, compact=True)) > limit:
        row.update(value=None, value_sha256=digest(encode(f.value).encode()),
                   value_status='MODEL_INPUT_OMISSION')
    return row


class AIResearch:
    def __init__(self, *, gateway=None, identity=None, limits=None, clock=None):
        self.gateway = gateway
        self.identity = identity
        self.limits = limits or Limits()
        self.clock = clock
        self.started = monotonic()
        self.status = {'state': 'AI_DISCOVERY_NOT_STARTED', 'stages': {}, 'investigations': [],
            'limits': asdict(self.limits), 'current_market_interpretation': False,
            'trade_authorization': False, 'model_tasks': 0, 'provider_attempts': 0}

    def _request(self, stage, evidence, *, at, mode, extra, config):
        from .agent_review import _bounded_context
        from .engine_capabilities import manifest
        capabilities = {m['id']:m['status'] for m in manifest(config)['methods']}
        method_fields = ('necessary_evidence', 'temporal_sequence', 'false_positive_traps',
                         'competing_explanations', 'invalidation_conditions', 'fidelity')
        context = _bounded_context(extra.get('context', {}))
        active_methods = {m for row in evidence for m in row.get('methods', ())}
        active_methods.update(i['hypothesis']['method'] for i in extra.get('investigations', ()))
        registry = [{'id': m['id'], 'name': m['name'], 'status': capabilities[m['id']],
            'families': ['F' + family for family in METHOD_FAMILIES[m['id']]],
            **{k: m['implementation'][k] for k in method_fields}} for m in config['methods']
            if stage == DISCOVERY or m['id'] in active_methods]
        body = {'schema_version': REQUEST, 'agent_name': AGENT,
            'stage': stage, 'evidence_as_of_utc': at, 'mode': mode, 'evidence': evidence,
            'skill_sha256': digest((ROOT / '.agents/skills/market-research-review/SKILL.md').read_bytes()),
            'guidance_sha256': digest(GUIDANCE.read_bytes()), 'input_transport': COMPACT_PAGES,
            'max_input_bytes': self.limits.max_input_bytes,
            'model': self.identity['model'] if self.identity else None,
            'dispatch_reservation_policy': COMPACT_SUBMISSION_POLICY,
            'question_limit': self.limits.max_questions, 'card_limit': self.limits.max_cards,
            'horizon_hours': 15, 'closed_history_methods': sorted(CLOSED_METHODS), 'registry': registry,
            'families': [{k:f[k] for k in ('id','name')} for f in config['families']],
            'trade_authorization': False, **extra,
            'context': context}
        if self.identity:
            body['native_identity'] = self.identity
        body['as_of_utc'] = self.clock() if self.clock else at
        body['material_sha256'] = digest(encode(_material(body)).encode())
        return body

    def _run(self, stage, evidence, *, at, mode, extra, config):
        from .native_codex import review_brief
        pending = 'AI_DISCOVERY_PENDING' if stage == DISCOVERY else 'AI_SHORTLIST_PENDING'
        detail = {'status': pending}
        self.status['state'] = pending
        self.status['stages'][stage] = detail
        if self.gateway is None:
            detail.update(status='AI_PROVIDER_UNAVAILABLE', reason='NO_NATIVE_GATEWAY')
        elif (self.status['model_tasks'] >= self.limits.max_native_tasks
                or self.status['provider_attempts'] >= self.limits.max_provider_attempts
                or monotonic() - self.started >= self.limits.deadline_seconds):
            detail.update(status='AI_PROVIDER_UNAVAILABLE', reason='NATIVE_TASK_OR_TIME_BUDGET_EXHAUSTED')
        else:
            try:
                chosen = list(evidence)
                while True:
                    request = self._request(stage, chosen, at=at, mode=mode, extra={
                        **extra, 'omitted_count': extra.get('omitted_count', 0) + len(evidence) - len(chosen)},
                        config=config)
                    try:
                        review_brief(request)
                        break
                    except ContractError as error:
                        if str(error) != 'AGENT_INPUT_SIZE' or not chosen:
                            raise
                        chosen.pop()
                if evidence and not chosen:
                    raise ContractError('AGENT_INPUT_SIZE')
                detail.update(material_sha256=request['material_sha256'],
                    supplied_ids=[e['id'] for e in chosen], omitted_count=request['omitted_count'],
                    request_evidence_as_of_utc=at, request_created_at_utc=request['as_of_utc'],
                    packet_bytes=len(review_brief(request).encode()),
                    input_sha256=digest(review_brief(request).encode()))
                if stage==FINAL:
                    detail['primary_families']={e['id']:e['primary_family'] for e in request['evidence']}
                    detail['qualified_alternatives']={e['id']:e.get('qualified_alternatives',{})
                        for e in request['evidence'] if e.get('qualified_alternatives')}
                self.status['model_tasks'] += 1
                collected = self.gateway(request, max(0, int(self.limits.deadline_seconds - (monotonic() - self.started))))
                collector = collected['collector']
                detail['native_collector'] = collector
                receipt = collected.get('receipt')
                self.status['provider_attempts'] += collector.get('observed_model_attempts', 0)
                if receipt is None:
                    reason = (collector.get('terminal_error') or {}).get('code', collector['status'])
                    detail.update(status=_failed_state(reason), reason=reason)
                else:
                    raw = collected['raw']
                    _need(receipt.get('native_invocation_verified') is True and
                        receipt.get('skill_and_request_read_completely') is True and
                        receipt.get('unauthorized_tool_operations') == 0 and
                        receipt.get('native_identity') == self.identity and
                        (self.identity is None or receipt.get('packet_sha256') == detail['input_sha256']) and
                        (self.identity is None or receipt.get('native_turn_ref') not in {
                            s.get('receipt', {}).get('native_turn_ref') for s in self.status['stages'].values()}) and
                        receipt.get('material_sha256') == request['material_sha256'] and
                        receipt.get('reply_sha256') == digest(raw.encode()) and
                        type(receipt.get('model_requests')) is int and receipt['model_requests'] > 0 and
                        receipt['model_requests'] == collector.get('observed_model_attempts'),
                        'NATIVE_AGENT_RECEIPT_REQUIRED')
                    detail['receipt'] = receipt
                    if self.status['provider_attempts'] > self.limits.max_provider_attempts:
                        raise ContractError('NATIVE_PROVIDER_ATTEMPT_BUDGET')
                    checked = validate(parse_reply(raw), request)
                    verified = 'AI_DISCOVERY_VERIFIED' if stage == DISCOVERY else 'AI_SHORTLIST_VERIFIED'
                    detail.update(status=verified, reply=checked['reply'], accepted=checked['accepted'])
                    self.status['state'] = verified
                    return checked['reply']['rows']
            except ContractError as error:
                detail.update(status=_failed_state(str(error)), reason=str(error))
        self.status['state'] = detail['status']
        return None

    def discover(self, rows_by_tf, nominations, *, at, cutoffs, mode, facts, references, context, config):
        if self.gateway is None:
            return self._run(DISCOVERY, [], at=at, mode=mode, extra={}, config=config)
        rows = {}
        source_records = defaultdict(dict)
        for f in facts.values():
            if f.timeframe in cutoffs and f.usable(as_of=at, cutoff=cutoffs[f.timeframe]):
                if f.cluster != 'PRICE_PATH':
                    source_records[f.instrument.native_symbol, f.timeframe][f.id] = _projection(f)
        for tf, broad in rows_by_tf.items():
            for symbol, row in broad.items():
                if utc(row['received_at']) <= utc(at) and 0 <= (utc(at) - utc(cutoffs[tf])).total_seconds() < 7200:
                    values = {k:v for k,v in row['values'].items() if k != 'quote_rvol32'}
                    source_records[symbol, tf][row['evidence_ids'][0]] = {'values': values,
                        'source_hashes': row['source_hashes'], 'received_at': row['received_at'],
                        'cutoff': cutoffs[tf], 'scope': 'BASIS_PRICE_PRECURSOR'}
        for key, nomination in nominations.items():
            for r in nomination.get('remote_causal_evidence', ())[:2]:
                if utc(r['known_by']) <= utc(at):
                    source_records[key][r['evidence_id']] = {**r, 'scope': 'REGISTERED_REMOTE_MASK_PRECURSOR'}
            specialist = nomination.get('specialist_source')
            if specialist:
                envelope = specialist['source_envelope']
                if utc(envelope['received_at']) <= utc(at):
                    source_records[key][specialist['evidence_ids'][0]] = {
                        'method': specialist['specialist_method'], 'source_envelope': envelope,
                        'scope': 'QUALIFIED_SPECIALIST_NOMINATION'}
        for ref in references:
            key = ref.native_symbol, ref.timeframe
            if key in source_records and utc(ref.available_at) <= utc(at) <= utc(ref.valid_until):
                if len(source_records[key]) < 4:
                    source_records[key][ref.id] = {'reference': asdict(ref), 'scope': 'FROZEN_REFERENCE'}
        for (symbol, tf), citations in source_records.items():
            nomination = nominations.get((symbol, tf), {})
            rows[symbol, tf] = {'id': fact_id(symbol, tf, cutoffs[tf]), 'native_symbol': symbol,
                'timeframe': tf, 'cutoff': cutoffs[tf], 'citations': citations,
                'routes': nomination.get('routes', ()), 'prior_families': nomination.get('families', ())}
        ordered = list(_ordered_rows(rows, nominations, cutoffs))
        self.status['broad_coverage']={'observed_symbol_timeframes':len(rows),
            'nominated_symbol_timeframes':len(nominations),
            'nominations_without_citable_row':len(set(nominations)-set(rows))}
        self.discovery_rows = {r['id']: r for r in ordered}
        if not rows:
            self.status['state'] = 'AI_INPUT_INVALID'
            self.status['stages'][DISCOVERY] = {'status': 'AI_INPUT_INVALID', 'reason': 'NO_SOURCE_CITED_BROAD_EVIDENCE'}
            return None
        return self._run(DISCOVERY, ordered[:self.limits.max_broad_rows], at=at, mode=mode,
            extra={'context': context, 'omitted_count': max(0, len(rows) - self.limits.max_broad_rows),
                   'cutoffs': cutoffs, 'closed_history_question_budget': self.limits.max_questions}, config=config)

    def shortlist(self, cards, reviews, facts, *, at, mode, context, config, conditional, shadow_selected=()):
        by_review = {r['card_id']: r for r in reviews}
        admissible = {row['card_id'] for row in conditional}
        evidence = []
        per_symbol = defaultdict(deque)
        for card in cards:
            review = by_review[card.id]
            primary = next(h for h in card.hypotheses if h.family == card.primary_family)
            required = set(primary.supporting_ids + primary.contradicting_ids)
            event_ids = {e['id'] for e in card.events[-6:]}
            event_ids.update(e['id'] for e in [e for e in card.events if e['id'] in required][-6:])
            events = {e['id']: {k:e[k] for k in ('kind', 'known_at', 'available_at')}
                      | {'source_ids_sha256':digest(encode(e['source_ids']).encode())}
                      for e in card.events if e['id'] in event_ids}
            catalog = {i: facts[i] for i in card.evidence_ids if i in facts and utc(facts[i].received_at) <= utc(at)}
            # Keep full causal and numeric evidence in the ledger. The packet
            # names its projections and only transmitted IDs can be cited.
            useful = {'RESEARCH_PRICE','SPREAD_BPS','DEPTH_USDT_WITHIN_ROOM','ROUND_TRIP_FEE_BPS',
                'FUNDING_BOUND_BPS','SLIPPAGE_BOUND_BPS','REFERENCE_SIGNIFICANCE','CAUSAL_SEQUENCE','HORIZON_RELEVANT'}
            salient = sorted(catalog, key=lambda i: (catalog[i].measurement not in useful,
                                                      catalog[i].measurement, i))[:8]
            values = {**{i: _projection(catalog[i]) for i in salient}, **events}
            # Retained/synthetic comparisons may inspect the same source-bar
            # roots as the shadow methods. Live admission remains unaffected.
            shadow_rows=[]
            if mode in {'SYNTHETIC','AUTHENTIC_REPLAY'}:
                for selected in shadow_selected:
                    if (selected.get('native_symbol')!=card.native_symbol or
                            selected.get('timeframe')!=card.timeframe):
                        continue
                    for method in selected.get('analytical_engine',{}).get('shadow_methods',()):
                        shadow_rows.append({k:method[k] for k in ('id','variant_id','state','mode','rank_eligible')})
                        for observation in method.get('events',())[-2:]:
                            if utc(observation['available_at'])<=utc(at):
                                values.setdefault(observation['event_root_id'],{
                                    'method':method['id'],'variant':method['variant_id'],
                                    'scope':'SHADOW_ONLY_UNQUALIFIED','observation':observation})
            if not values:
                continue
            formation_ids = sorted(required.intersection(events))
            if not formation_ids:
                formation_ids = [i for i in salient if catalog[i].qualification == 'QUALIFIED'
                                 and catalog[i].measurement == 'CAUSAL_SEQUENCE']
            room = review.get('research_room', review['room'])
            ref = {k:v for k,v in asdict(card.reference).items() if k != 'source_ids'}
            rivals = [{'family': h.family, 'direction': h.direction, 'verdict': h.verdict,
                'supporting_ids': [i for i in h.supporting_ids if i in values],
                'contradicting_ids': [i for i in h.contradicting_ids if i in values]} for h in card.hypotheses]
            per_symbol[card.native_symbol].append({'id': card.id, 'native_symbol': card.native_symbol,
                'timeframe': card.timeframe, 'reference': {'id':card.reference.id,**ref},
                'side': primary.direction,
                'families': card.family_ids, 'primary_family': card.primary_family, 'methods': card.method_ids,
                'stage': review['stage'], 'eligible': review['stage'] in DEEP or card.id in admissible,
                'citations': values, 'formation_citations': formation_ids,
                'event_order': list(events), 'omitted_facts': len(catalog) - len(salient),
                'omitted_events': len(card.events) - len(events), 'qualification': card.qualification,
                'rivals': rivals, 'missing': review['missing_necessary_inputs'],
                **({'shadow_methods':shadow_rows} if shadow_rows else {}),
                'room': {k:v for k,v in room.items() if k not in {'evidence_ids','missing_source_ids'}},
                'economics': {k:v for k,v in review['economics'].items() if k not in {'evidence_ids','assumption_evidence_ids'}},
                'exposure_cluster': review['exposure_cluster']})
        for group in per_symbol.values():
            ordered = sorted(group, key=lambda row: not row['eligible'])
            group.clear()
            group.extend(ordered)
        investigated = {r['native_symbol'] for r in self.status['investigations']}
        while per_symbol:
            for key in sorted(per_symbol, key=lambda n: (not per_symbol[n][0]['eligible'], n not in investigated, n)):
                evidence.append(per_symbol[key].popleft())
                if not per_symbol[key]:
                    del per_symbol[key]
        evidence=evidence[:self.limits.max_cards]
        # A rival can replace a provisional family only if a separate card for
        # the same reference already passed its own qualification and review.
        for current in evidence:
            alternatives={}
            for other in evidence:
                family=other['primary_family']
                if (other['id']==current['id'] or family==current['primary_family'] or family in alternatives
                        or not other['eligible'] or other['qualification']!='QUALIFIED'
                        or not other['formation_citations'] or other['native_symbol']!=current['native_symbol']
                        or other['timeframe']!=current['timeframe']
                        or other['reference']['id']!=current['reference']['id']):
                    continue
                if any(citation in current['citations'] and
                        current['citations'][citation]!=other['citations'].get(citation)
                        for citation in other['formation_citations']):
                    continue
                alternatives[family]=other['id']
                for citation in other['formation_citations']:
                    if citation in other['citations']:
                        current['citations'].setdefault(citation,other['citations'][citation])
            if alternatives:current['qualified_alternatives']=alternatives
        # Give a zero-card comparison a source-cited observation to interpret.
        baseline = next(r for r in self.discovery_rows.values()
                        if r['id'] in self.status['stages'][DISCOVERY]['supplied_ids'])
        baseline_id = next(iter(baseline['citations']))
        assessment_evidence = {baseline_id: baseline['citations'][baseline_id]}
        for investigation in self.status['investigations']:
            if investigation.get('evidence_id'):
                assessment_evidence[investigation['evidence_id']] = {
                    'hypothesis': investigation['hypothesis'], 'status': investigation['status']}
        return self._run(FINAL, evidence, at=at, mode=mode, extra={
            'context': context, 'assessment_evidence': assessment_evidence, 'omitted_count': len(cards) - min(len(evidence), self.limits.max_cards),
            'discovery_material_sha256': self.status['stages'][DISCOVERY]['material_sha256'],
            'investigations': self.status['investigations']}, config=config)


def _failed_state(reason):
    if any(key in reason for key in ('STALE', 'FUTURE', 'CLOCK_INVALID', 'AFTER_SNAPSHOT')):
        return 'AI_EVIDENCE_STALE'
    if any(key in reason for key in ('QUOTA', 'RATE_LIMIT', 'PROVIDER_UNSUPPORTED', 'TASK_FAILED', 'ATTEMPT_BUDGET')):
        return 'AI_PROVIDER_UNAVAILABLE'
    if reason.startswith('AGENT_') or reason == 'NATIVE_REVIEW_REQUEST_HASH':
        return 'AI_INPUT_INVALID'
    return 'AI_RECEIPT_UNVERIFIED'


def research_with_native(directory, *, audit_config, identity, clock, progress=None, wait_seconds=600):
    """Build a gateway to the existing one-shot native dispatcher and verifier."""
    import os
    import sqlite3
    from .agent_review import request_file_text
    from .native_app import failure, wait_for_reply
    from .native_identity import local_path, under_work

    def gateway(request, remaining):
        result = {}
        material = request['material_sha256']
        try:
            if not identity or identity['provider'] != 'codex':
                raise ContractError('NATIVE_PROVIDER_UNSUPPORTED')
            folder = under_work(local_path(directory))
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / (material + '.request.json')
            with target.open('x', encoding='utf-8', newline='') as stream:
                stream.write(request_file_text(request))
                stream.flush()
                os.fsync(stream.fileno())

            def notify(state, **fields):
                if progress:
                    progress(state, ai_stage=request['stage'], **fields)

            result['collector'] = wait_for_reply(folder, material, audit_config,
                wait_seconds=min(wait_seconds, remaining), clock=clock, progress=notify,
                verified_identity=identity, return_verified=result)
        except (ContractError, OSError, ValueError, TypeError, KeyError, sqlite3.Error) as error:
            if isinstance(error, FileExistsError):
                error = ContractError('NATIVE_REVIEW_REQUEST_COLLISION')
            fault = failure(error, 'REQUEST_PREPARATION')
            result['collector'] = {'status': fault['code'], 'terminal_error': fault}
        return result

    from .settings import load_config
    return AIResearch(gateway=gateway, identity=identity, clock=clock,
                      limits=Limits(**load_config().get('ai_core',{})))


def reconcile(report, research, decisions, reviews, conditional, *, as_of):
    """Intersect the model's ordered decisions with the current admission gates."""
    strict = {r['card_id']: r for r in reviews if r['stage'] in DEEP}
    qualified_conditional = {r['card_id']: r for r in conditional}
    selected = []
    conditional_selected = []
    seen = set()
    reconciled = []
    status = research.status
    final = status['stages'].get(FINAL, {})
    if decisions is not None and report.get('mode') == 'LIVE':
        lag = (utc(as_of) - utc(final['request_evidence_as_of_utc'])).total_seconds()
        from .screening import closed_cutoff
        advanced = any(closed_cutoff(as_of,tf) != cutoff for tf,cutoff in report['frozen_cutoffs'].items())
        if report.get('clock_anomalies') or advanced or not 0 <= lag <= research.limits.freshness_seconds:
            status['state'] = 'AI_EVIDENCE_STALE'
            decisions = None
    if decisions is not None and not status.get('investigation_complete', True):
        status['state'] = 'AI_INVESTIGATION_INCOMPLETE'
        decisions = None
    if decisions is not None:
        status['state'] = 'AI_RESEARCH_COMPLETE'
        status['current_market_interpretation'] = report['mode'] == 'LIVE'
        for decision in decisions:
            cid = decision['id']
            reason = decision['decision']
            if reason == 'HANDOFF':
                primary=final.get('primary_families',{}).get(cid)
                target=(cid if decision['interpretation']==primary else
                    final.get('qualified_alternatives',{}).get(cid,{}).get(decision['interpretation']))
                if target not in final.get('supplied_ids',[]):
                    target=cid if target==cid else None
                row = strict.get(target) or qualified_conditional.get(target)
                if row is None:
                    reason = 'CURRENT_ADMISSION_GATE'
                elif row['instrument'] in seen:
                    reason = 'SHARED_NATIVE_CONTRACT'
                else:
                    seen.add(row['instrument'])
                    chosen = {**row, 'rank': len(seen), 'ai_reasoning': decision,
                              'reasoning_status': 'VERIFIED_AI_SHORTLIST'}
                    if target in strict:
                        chosen['next_deep_analyst_question'] = decision['next_question']
                        selected.append(chosen)
                    else:
                        chosen['analyst_question'] = decision['next_question']
                        conditional_selected.append(chosen)
                    reason = 'SELECTED'
            reconciled.append({'card_id': cid, 'disposition': reason, 'reasoning': decision})
    omitted = set(r['card_id'] for r in reviews) - {r['card_id'] for r in reconciled}
    reconciled.extend({'card_id': cid, 'disposition': 'NOT_REVIEWED_BY_VERIFIED_AI'} for cid in sorted(omitted))
    status['reconciliation'] = reconciled
    review_by_id={r['card_id']:r for r in reviews}
    status['watches'] = [{'card_id':row['card_id'], 'native_symbol':review_by_id[row['card_id']]['instrument'],
        'stage':row['reasoning']['stage'], 'next_question':row['reasoning']['next_question']}
        for row in reconciled if row['disposition']=='WATCH' and row['card_id'] in review_by_id
        and review_by_id[row['card_id']]['stage'] not in {'LATE','INVALIDATED'}]
    report['shortlist'] = selected
    report['conditional_research_candidates'] = conditional_selected
    report['llm_calls'] = status['provider_attempts']
    report['llm_status'] = status['state']
    report['empty_shortlist_reason'] = (None if selected or conditional_selected else
        'AI_NO_QUALIFIED_HANDOFF_IN_REVIEWED_EVIDENCE' if status['state'] == 'AI_RESEARCH_COMPLETE'
        else status['state'])
    report['ai_research'] = status
    if status['state'] != 'AI_RESEARCH_COMPLETE' and report['operation_status'] != 'BLOCKED_OR_UNQUALIFIED':
        report['operation_status'] = 'AI_REQUIRED_INCOMPLETE'


def _method_projection(value):
    """Send a bounded excerpt with explicit omissions and the full value hash."""
    if len(encode(value, compact=True)) <= 2400:
        return {'value': value, 'scope': 'COMPLETE_SELECTED_METHOD_VALUE'}
    def excerpt(item, depth):
        if hasattr(item, '__dataclass_fields__'):
            item = asdict(item)
        if isinstance(item, dict):
            if depth >= 4:
                return {k:v for k,v in item.items() if k in {'kind','stage','known_at','direction','lo','hi'}}
            return {k: excerpt(v, depth + 1) for k, v in item.items()
                    if k not in {'source_ids','defining_ids','unknowns','evidence_ids'}}
        if isinstance(item, (list, tuple)):
            significant = [v for v in item if isinstance(v, dict) and (v.get('timeline') or v.get('events'))]
            return [excerpt(v, depth + 1) for v in (significant or item)[-2:]]
        return item
    result = excerpt(value, 0)
    if len(encode(result, compact=True)) > 2400:
        if isinstance(result, list):
            result = result[-1:]
        if isinstance(result, dict):
            result = {k:v for k,v in result.items() if len(encode(v, compact=True)) <= 500}
    return {'value': result if len(encode(result, compact=True)) <= 2400 else None,
            'scope': 'RECENT_METHOD_EXCERPT', 'value_sha256': digest(encode(value).encode())}


def investigate_opportunities(research, hypotheses, *, capacity, fetch_selected, selected,
                              members, facts, clock, mode):
    from datetime import timedelta
    from .method_engine import evaluate_methods
    from .observations import WIDTHS
    from .query_planner import QueryPlanner
    from .research import Fact
    from .structures import equal_level_references, swing_references

    planner = QueryPlanner(budgets={'broad': 0, 'targeted': research.limits.max_questions,
                                   'exception': 0, 'watch': 0},
                           byte_budget=65536 * research.limits.max_questions)
    history = set()
    method_results = {}
    selected_names = []

    def calculate(query):
        key = query.native_symbol, query.timeframe
        name, tf = key
        fetch_selected((name,), requested_tf=tf)
        if key not in selected:
            raise ContractError('OFFLINE_SOURCE_UNAVAILABLE')
        bars, source = selected[key]
        if len(bars) < 34 or bars[0].open_ms > int(utc(query.start).timestamp()*1000):
            raise ContractError('INSUFFICIENT_HISTORY')
        if key not in method_results:
            benchmark = selected.get(('BTCUSDT', tf))
            tick = members[name].tick_size
            at = clock()
            refs = [*swing_references(bars, tick, as_of=at), *equal_level_references(bars, tick, as_of=at)]
            bundle = evaluate_methods(bars, tick, cutoff=query.end, as_of=at, references=refs,
                                      benchmark=benchmark[0] if benchmark else None)
            method_results[key] = {m['method_id']: m for m in bundle}
        method = method_results[key][query.fact.removeprefix('AI_METHOD_')]
        stamp = source['receipt']['received_at_utc']
        response_hash = source['source_response_sha256']
        qualified = method['status'] == 'COMPUTED'
        summary = {**_method_projection(method['value']), 'method_status': method['status'],
                   'reason': method['reason'], 'formation_qualification': 'SELECTED_OBSERVATIONS_ONLY'}
        return Fact(fact_id(query.key, response_hash), members[name], query.fact, summary, query.units,
                    tf, query.end, stamp, stamp, stamp, query.source_id, response_hash,
                    'EXACT_REPORTED', qualified, 'QUALIFIED' if qualified else 'UNQUALIFIED',
                    mode, 2 * WIDTHS[tf])

    # Round one lets each proposed symbol ask once. Additional opposing
    # hypotheses can reuse the same source window or enter the residual budget.
    ordered = sorted(enumerate(hypotheses), key=lambda item: (
        sum(research.discovery_rows[h['row_id']]['native_symbol'] ==
            research.discovery_rows[item[1]['row_id']]['native_symbol'] for h in hypotheses[:item[0]]),
        item[0]))
    for _, hypothesis in ordered:
        origin = research.discovery_rows[hypothesis['row_id']]
        name, tf, cutoff = (origin[k] for k in ('native_symbol', 'timeframe', 'cutoff'))
        key = name, tf
        within_time = monotonic() - research.started < research.limits.deadline_seconds
        closed = hypothesis['question'] == 'VERIFY_METHOD_SEQUENCE'
        new_history = closed and key not in selected and key not in history
        if not within_time or (new_history and len(history) >= capacity):
            answer = {'status': 'NOT_REVIEWED_BUDGET', 'reason': 'TARGETED_HISTORY_OR_WALL_BUDGET'}
        else:
            if new_history:
                history.add(key)
            start = (utc(cutoff) - timedelta(seconds=34 * WIDTHS[tf])).isoformat()
            answer = planner.opportunity(hypothesis, origin, start=start, as_of=clock(),
                                         adapter=calculate, clock=clock)
        entry = {'hypothesis': asdict(Opportunity(**{**hypothesis, 'support': tuple(hypothesis['support']),
                 'contradiction': tuple(hypothesis['contradiction'])})),
                 'native_symbol': name, 'timeframe': tf, 'cutoff': cutoff,
                 'origin_citations': {i: origin['citations'][i] for i in
                                      [*hypothesis['support'], *hypothesis['contradiction']]},
                 'status': answer['status'], 'reason': answer.get('reason')}
        if answer.get('fact'):
            fact = answer['fact']
            facts[fact.id] = fact
            entry.update(evidence_id=fact.id, observation=_projection(fact), cache_reused=answer['cache_reused'])
        if key in selected and name not in selected_names and name not in {'BTCUSDT', 'ETHUSDT'}:
            selected_names.append(name)
        research.status['investigations'].append(entry)
    research.status['planner_audit'] = planner.audit
    closed = [item for item in research.status['investigations']
              if item['hypothesis']['question'] == 'VERIFY_METHOD_SEQUENCE']
    research.status['investigation_complete'] = not closed or any(
        r['status'] == 'VERIFIED_SOURCE_OBSERVATION' for r in closed)
    return selected_names
