"""Independent reconciliation assertions: cited fixtures never imply live calls."""
import copy
import unittest
from datetime import timedelta
from unittest.mock import patch
from researcher.contracts import utc
from researcher.candidate_review import review_card,conditional_research,apply_native_research_advice,native_review_selection
from researcher.agent_review import make_request
from researcher.settings import ROOT
from researcher.contracts import digest
from test_session4 import case


class ReconciliationRecovery(unittest.TestCase):
    def setUp(self):
        self.c,self.f,self.refs,self.b=case(qualification='TRIAL',current=100)
        self.at=self.b[-1].end;self.r=review_card(self.c,self.f,self.refs,as_of=self.at)
        self.candidates,self.decisions=conditional_research([self.r],[self.c],self.f,self.refs,as_of=self.at)
        self.row={'card_id':self.c.id,'priority':'INVESTIGATE','interpretation':'F4','strongest_rival':'NULL',
            'falsifying_question':'FIRST_OBSTACLE','supporting_evidence_ids':['seq'],'contradicting_ids':[],
            'missed_traps':['SHARED_PRICE_EVIDENCE'],'null_hypothesis':False}
        self.advice={'status':'NATIVE_REVIEW_INCOMPLETE','material_sha256':'a'*64,
            'request_created_at_utc':self.at,'reviewed_card_ids':[self.c.id],
            'card_review_provenance':{self.c.id:{'material_sha256':'b'*64,'request_created_at_utc':self.at,
                'validation_status':'VALIDATED_ADVISORY_ONLY'}},'reply':{'interpretations':[self.row]}}

    def test_valid_batch_survives_an_independent_rejected_batch(self):
        result,_,comparison=apply_native_research_advice(self.candidates,self.decisions,self.advice,as_of=self.at)
        self.assertEqual(result[0]['reasoning_status'],'NATIVE_REVIEWED')
        self.assertFalse(result[0]['native_review_coverage_complete'])
        self.assertEqual(result[0]['native_challenge']['material_sha256'],'b'*64)
        self.assertTrue(comparison['accepted_current_advice']);self.assertFalse(comparison['hard_gates_changed'])

    def test_unvalidated_or_expired_partial_rows_cannot_influence_reconciliation(self):
        for change in ('unvalidated','unlisted','expired'):
            advice=copy.deepcopy(self.advice);at=self.at
            if change=='unvalidated':advice['card_review_provenance'][self.c.id]['validation_status']='REJECTED'
            if change=='unlisted':advice['reviewed_card_ids']=[]
            if change=='expired':at=(utc(at)+timedelta(seconds=601)).isoformat()
            with self.subTest(change=change):
                result,_,comparison=apply_native_research_advice(self.candidates,[],advice,as_of=at)
                self.assertEqual(result[0]['reasoning_status'],'DETERMINISTIC_ONLY')
                self.assertFalse(comparison['accepted_current_advice'])

    def test_33_current_watches_do_not_force_twelve_native_tasks(self):
        ids=['watch-'+str(i) for i in range(33)]
        from dataclasses import replace
        cards=[case(qualification='TRIAL',current=100,name='WATCH'+str(i)+'USDT')[0] for i in range(33)]
        watches=[{'native_symbol':c.native_symbol,'primary':{'card_id':c.id}} for c in cards]
        with patch('researcher.candidate_review.conditional_research',return_value=([],[])),\
                patch('researcher.candidate_review.active_coin_watches',return_value=watches):
            selected,coverage=native_review_selection([],cards,{},[],as_of=self.at)
        self.assertLessEqual(len(selected),4)
        self.assertEqual(set(selected)|set(coverage['deferred_watch_card_ids']),{c.id for c in cards})
        self.assertEqual(coverage['omitted_finalists'],[])

    def test_every_viable_finalist_is_preserved_even_beyond_watch_budget(self):
        from dataclasses import replace
        cards=[case(qualification='TRIAL',current=100,name='FINAL'+str(i)+'USDT')[0] for i in range(12)]
        finalists=[{'card_id':c.id} for c in cards]
        with patch('researcher.candidate_review.conditional_research',return_value=(finalists,[])),\
                patch('researcher.candidate_review.active_coin_watches',return_value=[]):
            selected,coverage=native_review_selection([],cards,{},[],as_of=self.at)
        self.assertEqual(set(selected),{c.id for c in cards});self.assertEqual(coverage['omitted_finalists'],[])

    def test_model_receives_all_registry_states_and_shared_source_dependencies(self):
        request=make_request([self.c],self.f,as_of=self.at,
            skill_sha256=digest((ROOT/'.agents/skills/market-research-review/SKILL.md').read_bytes()))
        self.assertEqual(len(request['analytical_registry']['families']),9)
        self.assertEqual(len(request['analytical_registry']['methods']),31)
        methods={m['id']:m for m in request['analytical_registry']['methods']}
        self.assertEqual(methods['M15']['status'],'DEFINITION_PENDING')
        self.assertEqual(methods['M17']['status'],'SOURCE_CAPABILITY_REQUIRED')
        evidence=request['cards'][0]['evidence']
        for key,fact in evidence.items():
            self.assertEqual(fact['cluster'],self.f[key].cluster)
            self.assertEqual(fact['source_id'],self.f[key].source_id)
        self.assertTrue(all(not m['production_enabled'] for m in methods.values()))
