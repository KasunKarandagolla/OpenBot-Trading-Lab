"""Compact transport security regressions; all provider records are fixtures."""
import copy
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from researcher import openbot_runner as runner
from researcher.agent_review import _material
from researcher.contracts import ContractError, digest, encode
from researcher.native_app import observe_handoff, prepare
from researcher.native_handoff import COMPACT_PAGES, COMPACT_SUBMISSION_POLICY
from researcher.native_runtime import collect
import test_native_dispatch_confirmation as historical


class CompactNative(unittest.TestCase):
    def setUp(self):
        self.h = historical.ConfirmedDispatch()
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        h = self.h
        h.pin_request()
        request = h.request
        request['input_transport'] = COMPACT_PAGES
        request['dispatch_reservation_policy'] = COMPACT_SUBMISSION_POLICY
        request['evidence'] = [{'id':'SYN-ROW','native_symbol':'SYNTHETICUSDT','methods':['M05'],
            'citations':{'SYN-E1':'A synthetic boundary was crossed and reclaimed.'}}]
        h.material = request['material_sha256'] = digest(encode(_material(request)).encode())
        h.lease = h.directory/(h.material+'.dispatch.json')
        (h.directory/(h.material+'.request.json')).write_text(encode(request),encoding='utf-8')
        prepare(h.directory,h.material,h.j.private,verified_identity=h.f.identity,as_of=h.clock())
        runner._transition(h.folder,'REVIEW_READY',review_transport=COMPACT_PAGES,material_sha256=h.material,
            request_prepared_at_utc=h.clock(),request_expires_monotonic=600,submission_expires_monotonic=600)

    def issue(self):
        h=self.h
        frame=runner.status(h.job)
        self.assertEqual(frame['begin_frame'],'OPENBOT_COMPACT_DISPATCH_V1')
        self.assertEqual(frame['end_frame'],'END_OPENBOT_COMPACT_DISPATCH_V1')
        self.assertTrue(frame['submission_permitted'])
        self.assertLessEqual(len((encode(frame,compact=True)+'\n').encode()),4096)
        second=runner.status(h.job)
        self.assertFalse(second['submission_permitted'])
        self.assertNotIn('start_task_arguments',second)
        return frame['start_task_arguments'],second['dispatch_receipt']

    def completed(self):
        h=self.h
        args,ticket=self.issue()
        self.assertTrue(h.app.dispatch_once(args,h.job,ticket))
        h.sleep(2)
        h.app.complete_due()
        return args,ticket

    def read(self):
        h=self.h
        return collect(h.request,h.f.config,as_of=h.clock(),directory=h.directory)

    def test_compact_exact_task_and_pages_are_bound(self):
        self.completed()
        raw,audit=self.read()
        self.assertGreater(audit['verified_evidence_pages'],1)
        self.assertEqual(audit['parent_delivery'],'EXACT_TASK_ARGUMENTS_IN_PROVIDER_RECORD')
        self.assertEqual(audit['reply_sha256'],digest(raw.encode()))
        self.assertEqual(audit['reply_validation_status'],'VALIDATED')
        self.assertEqual(audit['unauthorized_tool_operations'],0)

    def test_no_publication_countdown_but_request_expiry_remains(self):
        self.h.sleep(181)
        self.issue()
        self.h.sleep(420)
        with self.assertRaises(ContractError):
            runner.review_page(self.h.job,self.h.material,None,1)

    def test_identity_check_cannot_publish_after_request_expiry(self):
        with patch('researcher.openbot_runner.assert_parent',side_effect=lambda *a,**k:self.h.sleep(601)):
            with self.assertRaises(ContractError): runner.status(self.h.job)
        self.assertFalse(self.h.lease.exists())

    def test_internal_start_status_does_not_consume_dispatch(self):
        status=runner.status(self.h.job,_allow_compact_dispatch=False)
        self.assertNotIn('start_task_arguments',status)
        self.assertFalse(self.h.lease.exists())
        self.issue()

    def test_uncertain_or_duplicate_submission_never_reissues_permission(self):
        h=self.h
        args,ticket=self.issue()
        wrapper={'name':'openbot.start_task','arguments':args}
        h.f.parent.append(h.f.record(h.seconds,'response_item',{'type':'function_call',
            'name':'tool_call','namespace':'openbot','call_id':'FIRST_CALL','arguments':json.dumps(wrapper)}))
        h.app.write('PARENT',h.f.parent)
        observation=observe_handoff(h.f.config,identity=h.f.identity,directory=h.directory,material=h.material,as_of=h.clock())
        self.assertEqual(observation['submission_state'],'ATTEMPTED')
        self.assertNotIn('start_task_arguments',runner.status(h.job))
        h.f.parent.append(h.f.record(h.seconds,'response_item',{'type':'function_call',
            'name':'tool_call','namespace':'openbot','call_id':'ANOTHER_CALL','arguments':json.dumps(wrapper)}))
        h.app.write('PARENT',h.f.parent)
        with self.assertRaises(ContractError):
            observe_handoff(h.f.config,identity=h.f.identity,directory=h.directory,material=h.material,as_of=h.clock())
        self.assertNotIn('start_task_arguments',runner.status(h.job))

    def test_concurrent_polls_issue_only_one_permission(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:runner.status(self.h.job),range(4)))
        self.assertEqual(sum(r.get('submission_permitted') is True for r in results),1)
        self.assertEqual(sum('start_task_arguments' in r for r in results),1)

    def test_wrong_acknowledged_task_cannot_bind_child(self):
        self.completed()
        h=self.h
        for row in h.f.parent:
            item=row['payload'].get('item',{})
            if item.get('tool')=='tool_call' and item.get('success') is True:
                item['content_items'][0]['text']=json.dumps({'taskId':'WRONG_TASK','title':next(iter(h.app.submitted))})
        h.app.write('PARENT',h.f.parent)
        with self.assertRaises(ContractError): self.read()

    def test_missing_duplicate_reordered_modified_and_unapproved_pages_fail(self):
        self.completed()
        path=self.h.f.root/'sessions/REVIEW_1.jsonl'
        original=[json.loads(line) for line in path.read_text().splitlines()]
        calls=[i for i,r in enumerate(original) if r['type']=='response_item' and r['payload'].get('name')=='exec_command']
        outputs=[i for i,r in enumerate(original) if r['type']=='response_item' and r['payload'].get('type')=='function_call_output']
        self.assertGreaterEqual(len(calls),2)
        variants={}
        rows=copy.deepcopy(original); rows.pop(outputs[0]); variants['missing']=rows
        rows=copy.deepcopy(original); rows.insert(calls[0]+1,copy.deepcopy(rows[calls[0]])); variants['duplicate']=rows
        rows=copy.deepcopy(original); rows[calls[0]],rows[calls[1]]=rows[calls[1]],rows[calls[0]]; variants['reordered']=rows
        rows=copy.deepcopy(original); rows[outputs[0]]['payload']['output']+='tampered'; variants['modified']=rows
        rows=copy.deepcopy(original); rows.insert(calls[0],{'timestamp':rows[calls[0]]['timestamp'],'type':'response_item',
            'payload':{'type':'function_call','name':'unexpected_tool','call_id':'OTHER','arguments':'{}'}}); variants['unauthorized']=rows
        for label,rows in variants.items():
            with self.subTest(label=label):
                self.h.app.write('REVIEW_1',rows)
                with self.assertRaises(ContractError): self.read()

    def test_changed_child_model_and_invalid_citation_fail(self):
        self.completed()
        path=self.h.f.root/'sessions/REVIEW_1.jsonl'
        original=[json.loads(line) for line in path.read_text().splitlines()]
        changed=copy.deepcopy(original)
        next(r for r in changed if r['type']=='turn_context')['payload']['model']='different-model'
        self.h.app.write('REVIEW_1',changed)
        with self.assertRaises(ContractError): self.read()
        self.h.app.write('REVIEW_1',original)
        from researcher.ai_core import validate
        raw,_=self.read()
        reply=json.loads(raw); reply['rows'][0]['support']=['NOT-TRANSMITTED']
        with self.assertRaises(ContractError): validate(reply,self.h.request)

    def test_unsupported_provider_gateway_fails_before_publication(self):
        from researcher.ai_core import research_with_native
        identity={**self.h.f.identity,'provider':'unsupported'}
        research=research_with_native(self.h.directory,audit_config=self.h.j.private,
            identity=identity,clock=self.h.clock)
        result=research.gateway(self.h.request,60)
        self.assertNotIn('receipt',result)
        self.assertEqual(result['collector']['terminal_error']['code'],'NATIVE_PROVIDER_UNSUPPORTED')
