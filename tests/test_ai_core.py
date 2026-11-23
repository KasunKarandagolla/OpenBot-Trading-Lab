"""Independent source fixtures with scripted native responses and fault cases."""
from copy import deepcopy
from datetime import timedelta
import unittest

from researcher.ai_core import AIResearch, DISCOVERY, FINAL, Limits, REPLY, reconcile, validate
from researcher.contracts import ContractError, digest, encode, utc
from researcher.discovery import scan_market_research
from researcher.native_codex import review_brief
from researcher.replay import synthetic_6b
from researcher.settings import load_config


def envelope(request, rows, *, finding=None):
    result = {'schema_version': REPLY, 'stage': request['stage'], 'material_sha256': request['material_sha256'],
              'trade_authorization': False, 'rows': rows}
    if finding:
        result['assessment'] = {'finding': finding, 'citations': [next(iter(request['assessment_evidence']))]}
    return result


def opportunity(row, method='M08', family='F3', direction='BULLISH', question='VERIFY_METHOD_SEQUENCE'):
    return {'row_id': row['id'], 'method': method, 'family': family, 'direction': direction,
        'stage': 'EARLY', 'support': [next(iter(row['citations']))], 'contradiction': [],
        'rival': 'NULL', 'question': question, 'expiry': 'NEXT_CLOSED_RESPONSE'}


class FixtureGateway:
    def __init__(self, discovery, *, finish='NO_SUPPORTED_OPPORTUNITY', failure=None):
        self.discovery = discovery
        self.finish = finish
        self.failure = failure
        self.requests = []

    def __call__(self, request, _remaining):
        self.requests.append(request)
        if self.failure:
            return {'collector': {'status': self.failure, 'observed_model_attempts': 0}}
        if request['stage'] == DISCOVERY:
            reply = envelope(request, self.discovery(request))
        else:
            reply = envelope(request, [{'id': c['id'], 'support': [next(iter(c['citations']))],
                        'contradiction': [], 'stage': 'UNKNOWN', 'interpretation': 'NULL', 'rival': 'NULL',
                        'decision': 'DECLINE','next_question': 'SOURCE_GAP','deciding_factor': 'NO_SUPPORTED_FORMATION'}
                        for c in request['evidence']], finding=self.finish)
        raw = encode(reply)
        return {'raw': raw, 'collector': {'status': 'FIXTURE', 'observed_model_attempts': 1},
                'receipt': {'native_invocation_verified': True, 'skill_and_request_read_completely': True,
                'unauthorized_tool_operations': 0, 'native_identity': request.get('native_identity'),
                'packet_sha256': digest(review_brief(request).encode()),
                'native_turn_ref': 'fixture-' + request['stage'],
                'material_sha256': request['material_sha256'], 'reply_sha256': digest(raw.encode()), 'model_requests': 1}}


class AICore(unittest.TestCase):
    def run_scan(self, gateway, *, limits=None):
        api, client, sources, at, _ = synthetic_6b()
        research = AIResearch(gateway=gateway, limits=limits)
        report = scan_market_research(api=api, client=client, sources=sources, clock=lambda: at,
                mode=sources.mode, ledger_path=':memory:', route_ablation=('B',), ai_research=research)
        return report, at

    def test_nonnominated_gap_and_opposing_hypotheses_guide_investigation(self):
        def propose(request):
            row = next(c for c in request['evidence'] if c['native_symbol'] == 'CONTROLUSDT')
            self.assertEqual(list(row['routes']), [])
            return [opportunity(row), opportunity(row, direction='BEARISH'),
                opportunity(row, 'M16', 'F6'), opportunity(row, 'M22', 'F4', question='CHECK_SOURCE_FIDELITY')]
        gateway = FixtureGateway(propose, finish='SOURCE_OR_COVERAGE_GAP')
        report, _ = self.run_scan(gateway, limits=Limits(max_questions=4))
        ai = report['ai_research']
        self.assertEqual(ai['state'], 'AI_RESEARCH_COMPLETE', {k:v.get('reason') for k,v in ai['stages'].items()})
        self.assertFalse(report['nominations'])
        self.assertIn('CONTROLUSDT', report['investigation_funnel']['actual_alt_symbols'])
        gap, rival, auction, footprint = ai['investigations']
        self.assertEqual(gap['status'], 'VERIFIED_SOURCE_OBSERVATION')
        self.assertIsNotNone(gap['observation']['value']['value'])
        self.assertEqual(gap['evidence_id'], rival['evidence_id'])
        self.assertTrue(rival['cache_reused'])
        self.assertEqual(auction['status'], 'VERIFIED_SOURCE_OBSERVATION')
        self.assertEqual(footprint['status'], 'UNKNOWN')
        self.assertEqual(footprint['reason'], 'QUALIFIED_SPECIALIST_INPUT_OR_DEFINITION_REQUIRED')
        self.assertEqual(gateway.requests[1]['investigations'][0]['evidence_id'], gap['evidence_id'])
        self.assertEqual(report['shortlist'], [])
        self.assertFalse(report['trade_authorization'])

    def test_provider_quota_preserves_broad_evidence_and_prevents_completion(self):
        report, _ = self.run_scan(FixtureGateway(lambda _: [], failure='PROVIDER_QUOTA_EXHAUSTED'))
        self.assertEqual(report['ai_research']['state'], 'AI_PROVIDER_UNAVAILABLE')
        self.assertEqual(list(report['ai_research']['stages']), [DISCOVERY])
        self.assertEqual(report['shortlist'], [])
        self.assertGreater(sum(p['evaluated'] for p in report['packs']), 0)

    def test_no_reply_or_native_receipt_cannot_complete(self):
        for gateway, state in ((None,'AI_PROVIDER_UNAVAILABLE'),
                               (lambda *_: {'collector':{'status':'NATIVE_PROVIDER_RESPONSE_NOT_OBSERVED'}},
                                'AI_RECEIPT_UNVERIFIED')):
            with self.subTest(state=state):
                report, _ = self.run_scan(gateway)
                self.assertEqual(report['ai_research']['state'], state)
                self.assertEqual(report['shortlist'], [])
                self.assertEqual(report['handoff_export']['research_handoffs'], [])

    def test_unsupported_query_and_invented_claims_reject_before_io(self):
        request = {'stage': DISCOVERY, 'material_sha256': 'material', 'question_limit': 3,
                   'evidence': [{'id':'row','citations':{'cited':{'close':'100'}}}]}
        base = opportunity(request['evidence'][0])
        for edits, reason in (({'question':'SHELL'},'AGENT_REPLY_ADVICE'),
                              ({'support':['invented']},'AGENT_REPLY_CITATION'),
                              ({'claim':{'close':200}},'AGENT_REPLY_CONTRACT'),
                              ({'family':'F2'},'AGENT_REPLY_ADVICE')):
            with self.subTest(edits=edits), self.assertRaisesRegex(ContractError, reason):
                validate(envelope(request, [{**base, **edits}]), request)

    def test_second_call_budget_stops_completion(self):
        gateway = FixtureGateway(lambda _: [])
        report, _ = self.run_scan(gateway, limits=Limits(max_native_tasks=1))
        self.assertEqual(len(gateway.requests), 1)
        self.assertEqual(report['ai_research']['state'], 'AI_PROVIDER_UNAVAILABLE')
        self.assertEqual(report['shortlist'], [])

    def test_inline_packet_is_trim_stable_and_fails_closed_at_size_boundary(self):
        gateway = FixtureGateway(lambda _: [])
        self.run_scan(gateway)
        request = deepcopy(gateway.requests[0])
        self.assertEqual(review_brief(request), review_brief(request).strip())
        request['max_input_bytes'] = 100
        with self.assertRaisesRegex(ContractError, 'AGENT_INPUT_SIZE'):
            review_brief(request)
        request['guidance_sha256']='0'*64
        with self.assertRaisesRegex(ContractError, 'AGENT_SKILL_HASH'):
            review_brief(request)

    def test_reconciliation_blocks_old_result_at_next_closed_cutoff(self):
        api, _, _, at, _ = synthetic_6b()
        from researcher.screening import closed_cutoff
        research = AIResearch()
        research.status['stages'][FINAL] = {'request_evidence_as_of_utc':at}
        report = {'mode':'LIVE','operation_status':'PARTIAL',
                  'frozen_cutoffs':{tf:closed_cutoff(api.at,tf) for tf in ('15m','1h')}}
        reconcile(report,research,[],[],[],as_of=(utc(at)+timedelta(hours=1)).isoformat())
        self.assertEqual(report['ai_research']['state'],'AI_EVIDENCE_STALE')
        self.assertEqual(report['shortlist'], [])

    def test_wrong_provider_attestation_cannot_be_reused_after_model_switch(self):
        trustworthy_fixture = FixtureGateway(lambda _: [])
        def wrong_model(request, remaining):
            result = trustworthy_fixture(request, remaining)
            result['receipt']['native_identity']={'model':'old'}
            return result
        research = AIResearch(gateway=wrong_model,identity={'model':'current'})
        decision = research._run(DISCOVERY,[{'id':'row','citations':{}}],at='2026-01-20T12:00:00Z',
                                 mode='AUTHENTIC_REPLAY',extra={},config=load_config())
        self.assertIsNone(decision)
        self.assertEqual(research.status['state'],'AI_RECEIPT_UNVERIFIED')


if __name__ == '__main__':
    unittest.main()
