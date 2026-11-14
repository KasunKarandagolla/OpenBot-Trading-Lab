"""Offline adversarial exchange tests; these never count as native LLM calls."""
import copy,json
from dataclasses import replace
from datetime import timedelta
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from researcher.agent_review import make_request,validate_reply,parse_reply,consume_reply,exchange,REPLY,AGENT,MODEL
from researcher.contracts import ContractError,encode,utc,digest
from researcher.settings import ROOT
from test_session4 import case


class NativeReviewContract(unittest.TestCase):
    def setUp(self):
        self.card,self.facts,_,self.bars=case(family='F4')
        self.request=make_request([self.card],self.facts,as_of=self.bars[-1].end,skill_sha256='a'*64)
        self.row={'card_id':self.card.id,'interpretation':'F4','supporting_evidence_ids':['seq'],
            'contradicting_ids':[],'strongest_rival':'NULL','null_hypothesis':False,
            'missed_traps':['SHARED_PRICE_EVIDENCE'],'falsifying_question':'FIRST_OBSTACLE',
            'priority':'WATCH','claims':[]}
        self.reply={'schema_version':REPLY,'material_sha256':self.request['material_sha256'],
            'interpretations':[self.row],'trade_authorization':False}

    def test_bounded_source_exchange_is_advice_and_does_not_admit(self):
        result=validate_reply(self.reply,self.request)
        self.assertEqual(result['accepted'],1);self.assertFalse(result['trade_authorization'])
        self.assertFalse(result['can_override_deterministic_admission'])
        self.assertEqual(self.request['cards'][0]['reference']['known_at'],self.card.reference.known_at)

    def test_fabricated_citation_and_cross_card_scope_are_rejected(self):
        self.row['supporting_evidence_ids']=['nonexistent-article-instruction']
        with self.assertRaisesRegex(ContractError,'AGENT_REPLY_CITATION'):validate_reply(self.reply,self.request)
        self.row['supporting_evidence_ids']=['seq'];self.row['card_id']='another-symbol-card'
        with self.assertRaisesRegex(ContractError,'AGENT_REPLY_CARD'):validate_reply(self.reply,self.request)

    def test_numeric_claim_must_match_identity_units_time_and_value_exactly(self):
        f=self.request['cards'][0]['evidence']['RESEARCH_PRICE']
        claim={k:f[k] for k in ('value','units','native_symbol','timeframe','known_at')}
        claim['evidence_id']='RESEARCH_PRICE';self.row['claims']=[claim]
        validate_reply(self.reply,self.request)
        for k,v in [('value','999999'),('native_symbol','BTCUSDT'),('timeframe','15m'),('known_at',self.card.reference.known_at),('units','CONTRACTS')]:
            bad=copy.deepcopy(self.reply);bad['interpretations'][0]['claims'][0][k]=v
            with self.assertRaisesRegex(ContractError,'AGENT_REPLY_CLAIM'):validate_reply(bad,self.request)

    def test_trading_and_unallowlisted_tool_requests_fail_closed(self):
        for k,v in [('order',{'buy':True}),('entry',84),('model','replacement'),('tool','shell')]:
            bad=copy.deepcopy(self.reply);bad['interpretations'][0][k]=v
            with self.assertRaises(ContractError):validate_reply(bad,self.request)
        self.row['falsifying_question']='PLACE_ORDER'
        with self.assertRaisesRegex(ContractError,'AGENT_REPLY_ADVICE'):validate_reply(self.reply,self.request)

    def test_duplicate_json_keys_nonfinite_and_oversize_are_rejected(self):
        with self.assertRaisesRegex(ContractError,'DUPLICATE_KEY'):parse_reply('{"x":1,"x":2}')
        with self.assertRaisesRegex(ContractError,'NONFINITE'):parse_reply('{"x":NaN}')
        with self.assertRaisesRegex(ContractError,'REPLY_SIZE'):parse_reply(' '*32769)
        # Actual native transport failure: unfinished prefix + full continuation.
        with self.assertRaisesRegex(ContractError,'REPLY_JSON'):
            parse_reply('{"schema_version":"unfinished\n\n'+encode(self.reply))
        with self.assertRaisesRegex(ContractError,'REPLY_JSON'):
            parse_reply('{"schema_version":"openbot.research-review\\.reply.v1"}')

    def test_future_source_or_wrong_native_identity_cannot_enter_model_input(self):
        future=replace(self.facts['seq'],received_at='2099-01-01T00:00:00+00:00',available_at='2099-01-01T00:00:00+00:00')
        with self.assertRaisesRegex(ContractError,'EVIDENCE_FUTURE'):
            make_request([self.card],{**self.facts,'seq':future},as_of=self.bars[-1].end,skill_sha256='a'*64)
        wrong=replace(self.facts['seq'],timeframe='15m')
        with self.assertRaisesRegex(ContractError,'EVIDENCE_IDENTITY'):
            make_request([self.card],{**self.facts,'seq':wrong},as_of=self.bars[-1].end,skill_sha256='a'*64)

    def test_current_point_quotes_retain_their_actual_timeframe(self):
        point=replace(self.facts['RESEARCH_PRICE'],timeframe='CURRENT')
        r=make_request([self.card],{**self.facts,'RESEARCH_PRICE':point},as_of=self.bars[-1].end,skill_sha256='a'*64)
        self.assertEqual(r['cards'][0]['evidence']['RESEARCH_PRICE']['timeframe'],'CURRENT')
        self.assertEqual(r['cards'][0]['timeframe'],'1h')
        wrong=replace(self.facts['seq'],timeframe='CURRENT')
        with self.assertRaisesRegex(ContractError,'EVIDENCE_IDENTITY'):
            make_request([self.card],{**self.facts,'seq':wrong},as_of=self.bars[-1].end,skill_sha256='a'*64)

    def test_input_budget_is_explicit_and_unchanged_time_is_not_new_material(self):
        r=make_request([self.card]*20,self.facts,as_of=self.bars[-1].end,skill_sha256='a'*64)
        self.assertLessEqual(len(r['cards']),12);self.assertTrue(r['omitted'])
        later=make_request([self.card],self.facts,as_of=(utc(self.bars[-1].end)+timedelta(seconds=1)).isoformat(),skill_sha256='a'*64)
        self.assertEqual(later['material_sha256'],self.request['material_sha256'])
        stale=make_request([self.card],self.facts,as_of='2099-01-01T00:00:00+00:00',skill_sha256='a'*64)
        self.assertNotEqual(stale['material_sha256'],self.request['material_sha256'])
        before=make_request([self.card],self.facts,as_of=self.bars[-1].end,skill_sha256='a'*64,
            context={'as_of':self.bars[-1].end,'policy':'ADVISORY_NON_VETO'})
        after=make_request([self.card],self.facts,as_of=later['as_of_utc'],skill_sha256='a'*64,
            context={'as_of':later['as_of_utc'],'policy':'ADVISORY_NON_VETO'})
        self.assertEqual(before['material_sha256'],after['material_sha256'])

    def test_fixture_json_is_not_a_native_invocation_receipt(self):
        with self.assertRaisesRegex(ContractError,'NATIVE_AGENT_RECEIPT_REQUIRED'):
            consume_reply(encode(self.reply),self.request,native_receipt={})

    def test_nested_hostile_types_are_contract_errors_not_python_crashes(self):
        for key in ('card_id','interpretation','strongest_rival','priority','falsifying_question'):
            bad=copy.deepcopy(self.reply);bad['interpretations'][0][key]={}
            with self.assertRaises(ContractError):validate_reply(bad,self.request)
        for key in ('supporting_evidence_ids','contradicting_ids','missed_traps'):
            bad=copy.deepcopy(self.reply);bad['interpretations'][0][key]=[{}]
            with self.assertRaises(ContractError):validate_reply(bad,self.request)

    def test_native_exchange_deduplicates_and_isolates_missing_invalid_and_stale_reply(self):
        # All receipts below are explicit test doubles, never runtime evidence.
        (ROOT/'work').mkdir(exist_ok=True)
        with TemporaryDirectory(dir=ROOT/'work') as tmp:
            first=exchange(tmp,[self.card],self.facts,as_of=self.bars[-1].end)
            self.assertEqual(first['status'],'AWAITING_NATIVE_APP_RESPONSE');self.assertEqual(first['calls'],0)
            path=Path(tmp)/first['request_file'];original=path.read_bytes()
            same=exchange(tmp,[self.card],self.facts,as_of=(utc(self.bars[-1].end)+timedelta(seconds=1)).isoformat())
            self.assertEqual(first['material_sha256'],same['material_sha256']);self.assertEqual(path.read_bytes(),original)
            request=json.loads(original);reply=copy.deepcopy(self.reply);reply['material_sha256']=first['material_sha256']
            raw=encode(reply);key=first['material_sha256']
            (Path(tmp)/(key+'.reply.json')).write_text(raw)
            missing=exchange(tmp,[],{},as_of=self.bars[-1].end,cached=True,previous=first)
            self.assertEqual(missing['status'],'NATIVE_REPLY_UNAUDITED_DETERMINISTIC_FALLBACK')
            audit={'schema_version':'openbot.native-review.audit.v1','audit_source':'OPENBOT_APP_SCOPED_READ_ONLY_AUDIT',
                'reply_sha256':digest(raw.encode()),'model_requests':1,'tool_operations':['READ_SKILL','READ_REQUEST'],
                'unauthorized_tool_operations':0,'agent_name':AGENT,'model':MODEL,
                'skill_sha256':request['skill_sha256'],'material_sha256':key,'native_invocation_verified':True,
                'test_double':True}
            auditfile=Path(tmp)/(key+'.audit.json');auditfile.write_text(encode(audit))
            good=exchange(tmp,[],{},as_of=self.bars[-1].end,cached=True,previous=first)
            self.assertEqual(good['accepted'],1);self.assertEqual(good['calls_this_scan'],0)
            self.assertFalse(good['can_override_deterministic_admission'])
            stale=exchange(tmp,[],{},as_of=(utc(self.bars[-1].end)+timedelta(seconds=601)).isoformat(),cached=True,previous=first)
            self.assertEqual(stale['status'],'NATIVE_REQUEST_STALE_DETERMINISTIC_FALLBACK')
            audit['unauthorized_tool_operations']=1;auditfile.write_text(encode(audit))
            rejected=exchange(tmp,[],{},as_of=self.bars[-1].end,cached=True,previous=first)
            self.assertEqual(rejected['status'],'NATIVE_REVIEW_INVALID_OR_UNAVAILABLE_DETERMINISTIC_FALLBACK')

    def test_ordinary_pipeline_optional_exchange_preserves_deterministic_shortlist(self):
        from researcher.discovery import scan_market_research
        from researcher.replay import synthetic_6b
        api,client,sources,at,_=synthetic_6b()
        with TemporaryDirectory(dir=ROOT/'work') as tmp:
            result=scan_market_research(api=api,client=client,sources=sources,clock=lambda:at,
                mode='SYNTHETIC',ledger_path=Path(tmp)/'research.sqlite',native_review_dir=Path(tmp)/'exchange')
            self.assertEqual(result['consultant']['status'],'AWAITING_NATIVE_APP_RESPONSE')
            self.assertEqual(len(result['shortlist']),2);self.assertEqual(result['llm_calls'],0)
            self.assertFalse(result['trade_authorization']);self.assertEqual(result['new_orders_created'],0)
            self.assertTrue((Path(tmp)/'exchange'/result['consultant']['request_file']).is_file())


if __name__=='__main__':unittest.main()
