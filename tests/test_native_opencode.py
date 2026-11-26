"""OpenCode 2.4.1 session/part adapter regressions. Fixtures only; no model.

Every provider row here is synthetic. The tests replay the retained parent and
child shapes without copying any real session identifier, text or account data.
"""
import json
import sqlite3
import unittest
import zipfile
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from researcher import ai_core
from researcher.agent_review import AGENT, REPLY, _material
from researcher.contracts import ContractError, digest, encode, utc
from researcher.native_codex import review_brief
from researcher.native_handoff import (
    COMPACT_PAGES, COMPACT_SUBMISSION_POLICY, packet, wsl_root,
)
from researcher.native_identity import active_identity, parent_binding, ref
from researcher.native_opencode import (
    LEGACY_SESSION_VERSIONS, SCHEMA, _page_command, _page_output, assert_session_identity, attest, attest_smoke_discovery,
    attest_start_command, attest_turn_model, collect, delivery_proof,
    observe_submission, parse_execute, session_record,
)
from researcher.native_runtime import integration_preflight
from researcher.settings import ROOT
from test_session4 import case


MODEL = 'opencode/deepseek-v4.1-flash-free'
VARIANT = 'high'
JOB = '20260101T000000Z-' + 'a' * 32
CHILD_THREAD = 'CHILD_THREAD_FIXTURE'
CHILD_SESSION = 'CHILD_SESSION_FIXTURE'
CHILD_EXTERNAL = 'CHILD_EXTERNAL_FIXTURE'
CHILD_TURN = 'CHILD_TURN_FIXTURE'
PARENT_THREAD = 'PARENT_THREAD_FIXTURE'
PARENT_SESSION = 'PARENT_SESSION_FIXTURE'
PARENT_EXTERNAL = 'PARENT_EXTERNAL_FIXTURE'
PARENT_TURN = 'PARENT_TURN_FIXTURE'
DELIVERY_TURN = 'DELIVERY_TURN_FIXTURE'


def _model(variant=VARIANT):
    return {'id': 'deepseek-v4.1-flash-free', 'providerID': 'opencode',
            'variant': variant}


def _schema_start():
    return {'type': 'object', 'additionalProperties': False,
            'properties': {'title': {'type': 'string'}, 'brief': {'type': 'string'}},
            'required': ['title', 'brief']}


def _schema_attach():
    return {'type': 'object', 'additionalProperties': False,
            'properties': {'paths': {'type': 'array', 'items': {'type': 'string'}},
                           'folder': {'type': 'string'}},
            'required': ['paths']}


def _discovery_json():
    return encode({'call': 'tools.openbot.tool_describe',
                   'guidance': ['Read the exact schemas before submitting.'],
                   'tools': [
                       {'name': 'openbot.start_task', 'description': 'Start one task.',
                        'inputSchema': _schema_start()},
                       {'name': 'openbot.attach_files_to_response',
                        'description': 'Attach one file.',
                        'inputSchema': _schema_attach()}]})


def _describe_script(names=('openbot.start_task', 'openbot.attach_files_to_response')):
    return ('const r = await tools.openbot.tool_describe('
            + json.dumps({'names': list(names)}) + '); return r;')


def _start_script(args):
    return ('const r = await tools.openbot.tool_call('
            + json.dumps({'name': 'openbot.start_task', 'arguments': args})
            + '); return r;')


def _attach_script(path):
    return ('const r = await tools.openbot.tool_call('
            + json.dumps({'name': 'openbot.attach_files_to_response',
                          'arguments': {'paths': [str(path)]}}) + '); return r;')


class OpenCodeFixture(unittest.TestCase):
    def setUp(self):
        (ROOT / 'work').mkdir(exist_ok=True)
        self.tmp = TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / 'agent'
        self.workspace.mkdir()
        skill = self.workspace / '.agents/skills/market-research-review/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_bytes((ROOT / '.agents/skills/market-research-review/SKILL.md').read_bytes())
        self.config = {'openbot_db': str(self.root / 'app.sqlite'),
                       'provider_db': str(self.root / 'opencode.sqlite'),
                       'agent_workspace': str(self.workspace)}
        self.card, self.facts, _, bars = case(family='F4')
        self.at = bars[-1].end
        self.parent_seq = 0
        self.child_seq = 0
        self._projection_schema()
        self._provider_schema()
        self._parent_rows()
        self.identity = active_identity(self.config)
        self.assertEqual(self.identity['adapter'], SCHEMA)
        self.assertEqual(self.identity['effort'], VARIANT)
        self.request = self._ai_request()
        self.reply = {'schema_version': ai_core.REPLY,
                      'material_sha256': self.request['material_sha256'],
                      'stage': ai_core.DISCOVERY, 'trade_authorization': False,
                      'rows': [{'row_id': 'SYN-ROW', 'family': 'F5', 'method': 'M05',
                                'direction': 'BULLISH', 'stage': 'EARLY',
                                'support': ['SYN-E1'], 'contradiction': [],
                                'rival': 'NULL', 'question': 'VERIFY_METHOD_SEQUENCE',
                                'expiry': 'WITHIN_RESEARCH_HORIZON'}]}
        self.raw = encode(self.reply)
        self.inline_request = self._inline_request()
        self.inline_reply = {'schema_version': REPLY,
                             'material_sha256': self.inline_request['material_sha256'],
                             'trade_authorization': False, 'interpretations': [{
                                 'card_id': 'SYN-CARD', 'interpretation': 'F5',
                                 'supporting_evidence_ids': ['SYN-E1'],
                                 'contradicting_ids': [],
                                 'strongest_rival': 'F4', 'null_hypothesis': False,
                                 'missed_traps': [], 'falsifying_question': 'FIRST_OBSTACLE',
                                 'priority': 'WATCH', 'claims': []}]}
        self.directory = self.root / 'jobs' / JOB / 'review'
        self.directory.mkdir(parents=True)

    def _ai_request(self):
        skill = (ROOT / '.agents/skills/market-research-review/SKILL.md').read_bytes()
        guidance = (ROOT / '.agents/skills/market-research-review/ai-core.md').read_bytes()
        request = {
            'schema_version': ai_core.REQUEST, 'agent_name': AGENT,
            'stage': ai_core.DISCOVERY, 'evidence_as_of_utc': self.at,
            'mode': 'BOUNDED_EVIDENCE_REVIEW',
            'evidence': [{'id': 'SYN-ROW', 'native_symbol': 'SYNTHETICUSDT',
                          'methods': ['M05'],
                          'citations': {'SYN-E1': 'A synthetic boundary was crossed and reclaimed.'}}],
            'skill_sha256': digest(skill), 'guidance_sha256': digest(guidance),
            'max_input_bytes': ai_core.MAX_BRIEF_BYTES, 'model': MODEL,
            'dispatch_reservation_policy': COMPACT_SUBMISSION_POLICY,
            'question_limit': 6, 'card_limit': 10, 'horizon_hours': 15,
            'closed_history_methods': sorted(ai_core.CLOSED_METHODS),
            'registry': [], 'families': [], 'trade_authorization': False,
            'native_identity': self.identity,
            'context': {'fixture': 'x' * 26000}, 'as_of_utc': self.at}
        request['material_sha256'] = digest(encode(_material(request)).encode())
        return request

    def _inline_request(self):
        skill = (ROOT / '.agents/skills/market-research-review/SKILL.md').read_bytes()
        request = {
            'schema_version': 'openbot.research-review.request.v1', 'agent_name': AGENT,
            'model': MODEL, 'as_of_utc': self.at, 'skill_sha256': digest(skill),
            'cards': [{'card_id': 'SYN-CARD', 'families': ['F5'],
                       'rivals': [{'family': 'F4'}],
                       'events': [{'id': 'SYN-EVENT'}],
                       'evidence': {'SYN-E1': {
                           'value': 1, 'units': 'count', 'native_symbol': 'SYNTHETICUSDT',
                           'timeframe': '1h', 'known_at': self.at}}}],
            'native_identity': self.identity}
        request['material_sha256'] = digest(encode(_material(request)).encode())
        return request

    def time(self, seconds):
        return (utc(self.at) + timedelta(seconds=seconds)).isoformat()

    def ms(self, value):
        return int(utc(value).timestamp() * 1000)

    def _projection_schema(self):
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.executescript('''CREATE TABLE projection_agents(agent_id,thread_id,model,agent_json);
              CREATE TABLE projection_threads(thread_id,agent_id,active_turn_id);
              CREATE TABLE projection_turns(turn_id,thread_id,provider_session_id,status,started_at,completed_at);
              CREATE TABLE projection_provider_sessions(id,thread_id,provider,external_session_id,model,state,effort);
              CREATE TABLE projection_agent_threads(thread_id,agent_id,origin,title,created_at);
              CREATE TABLE projection_thread_messages(thread_id,turn_id,author,item_type,status,created_at,ordinal,message_json);''')

    def _provider_schema(self):
        with sqlite3.connect(self.config['provider_db']) as db:
            db.executescript('''CREATE TABLE session_v2(id,parent_id,version,model);
              CREATE TABLE session_message(id,session_id,type,seq,time_created,time_updated,data);
              CREATE TABLE session_part(session_id,message_id,ordinal,type,call_id,time_created,time_updated,data);''')

    def _parent_rows(self):
        agent = {'name': AGENT, 'model': MODEL, 'provider': 'opencode',
                 'reasoningEffort': VARIANT, 'workspacePath': str(self.workspace)}
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute('INSERT INTO projection_agents VALUES(?,?,?,?)',
                       ('AGENT', PARENT_THREAD, MODEL, encode(agent)))
            db.execute('INSERT INTO projection_threads VALUES(?,?,?)',
                       (PARENT_THREAD, 'AGENT', PARENT_TURN))
            db.execute('INSERT INTO projection_provider_sessions VALUES(?,?,?,?,?,?,?)',
                       (PARENT_SESSION, PARENT_THREAD, 'opencode', PARENT_EXTERNAL,
                        MODEL, 'active', VARIANT))
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',
                       (PARENT_TURN, PARENT_THREAD, PARENT_SESSION, 'running',
                        self.time(-10), None))
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('INSERT INTO session_v2 VALUES(?,?,?,?)',
                       (PARENT_EXTERNAL, None, '2.4.1', encode(_model())))
        self._user(PARENT_EXTERNAL, self.time(-9), 'Current parent turn fixture.')

    def _message(self, session, mid, kind, seq, created, data):
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('''INSERT INTO session_message
                (id,session_id,type,seq,time_created,time_updated,data) VALUES(?,?,?,?,?,?,?)''',
                (mid, session, kind, seq, self.ms(created), self.ms(created) + 1,
                 encode(data)))
        return mid

    def _part(self, session, mid, ordinal, kind, call_id, created, data):
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('''INSERT INTO session_part
                (session_id,message_id,ordinal,type,call_id,time_created,time_updated,data)
                VALUES(?,?,?,?,?,?,?,?)''',
                (session, mid, ordinal, kind, call_id, self.ms(created),
                 self.ms(created) + 1, encode(data)))

    def _next_seq(self, session):
        if session == PARENT_EXTERNAL:
            seq = self.parent_seq
            self.parent_seq += 1
        else:
            seq = self.child_seq
            self.child_seq += 1
        return seq

    def _assistant(self, session, at, *, finish='tool-calls', variant=VARIANT):
        seq = self._next_seq(session)
        mid = f'msg_{session}_{seq}'
        data = {'agent': 'build', 'model': _model(variant), 'content': [],
                'finish': finish, 'rawFinish': finish,
                'time': {'created': self.ms(at), 'completed': self.ms(at) + 1},
                'tokens': {'input': 1, 'output': 1}, 'cost': 0}
        self._message(session, mid, 'assistant', seq, at, data)
        return mid

    def _user(self, session, at, text):
        seq = self._next_seq(session)
        mid = f'msg_{session}_{seq}'
        data = {'time': {'created': self.ms(at)}, 'text': text, 'files': []}
        self._message(session, mid, 'user', seq, at, data)
        return mid

    def _execute(self, session, mid, at, script, *, tool, call_input, result,
                 status='completed', call_status='completed', metadata_extra=None,
                 ordinal=0):
        metadata = {'toolCalls': [{'tool': tool, 'status': call_status,
                                   'input': call_input}], 'truncated': False}
        if metadata_extra:
            metadata.update(metadata_extra)
        part = {'type': 'tool', 'id': f'prt_{mid}', 'name': 'execute', 'executed': False,
                'state': {'status': status, 'input': {'code': script},
                          'content': [{'type': 'text', 'text': result}],
                          'metadata': metadata},
                'time': {'created': self.ms(at), 'completed': self.ms(at) + 1}}
        self._part(session, mid, ordinal, 'tool', part['id'], at, part)

    def _shell(self, session, mid, at, command, output, *, exit=0,
               status='completed', truncated=False, ordinal=0):
        part = {'type': 'tool', 'id': f'prt_{mid}_{ordinal}', 'name': 'shell',
                'executed': True,
                'state': {'status': status, 'input': {'command': command},
                          'content': [{'type': 'text', 'text': output}],
                          'metadata': {'status': status, 'truncated': truncated,
                                       'exit': exit}},
                'time': {'created': self.ms(at), 'completed': self.ms(at) + 1}}
        self._part(session, mid, ordinal, 'tool', part['id'], at, part)

    def _text(self, session, mid, at, text, *, ordinal=0):
        self._part(session, mid, ordinal, 'text', None, at,
                   {'type': 'text', 'text': text})

    def _discovery(self, at=None, *, names=None, result=None, status='completed',
                   call_status='completed'):
        at = at or self.time(1)
        names = list(names or ('openbot.start_task', 'openbot.attach_files_to_response'))
        mid = self._assistant(PARENT_EXTERNAL, at)
        self._execute(PARENT_EXTERNAL, mid, at, _describe_script(names),
                      tool='openbot.tool_describe', call_input={'names': names},
                      result=result or _discovery_json(), status=status,
                      call_status=call_status)
        return mid

    def _submission(self, at, args, *, ack=None, status='completed',
                    call_status='completed'):
        mid = self._assistant(PARENT_EXTERNAL, at)
        response = ack if ack is not None else {'taskId': CHILD_THREAD,
                                                'title': args['title']}
        self._execute(PARENT_EXTERNAL, mid, at, _start_script(args),
                      tool='openbot.tool_call',
                      call_input={'name': 'openbot.start_task', 'arguments': args},
                      result=encode(response), status=status, call_status=call_status)
        return mid

    def _child_session(self, *, variant=VARIANT):
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('INSERT INTO session_v2 VALUES(?,?,?,?)',
                       (CHILD_EXTERNAL, None, '2.4.1', encode(_model(variant))))

    def _child_projection(self, brief, raw, created, start, end, *, variant=VARIANT,
                          model=MODEL, material=None):
        material = material or self.request['material_sha256']
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute('INSERT INTO projection_agent_threads VALUES(?,?,?,?,?)',
                       (CHILD_THREAD, 'AGENT', 'agent',
                        'OPENBOT-RESEARCH-' + material, created))
            db.execute('INSERT INTO projection_provider_sessions VALUES(?,?,?,?,?,?,?)',
                       (CHILD_SESSION, CHILD_THREAD, 'opencode', CHILD_EXTERNAL,
                        model, 'active', variant))
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',
                       (CHILD_TURN, CHILD_THREAD, CHILD_SESSION, 'completed', start, end))
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',
                       (CHILD_THREAD, CHILD_TURN, 'agent', None, 'completed', created, 0,
                        encode({'text': brief})))
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',
                       (CHILD_THREAD, CHILD_TURN, 'assistant', 'final_answer', 'completed',
                        end, 1, encode({'text': raw})))

    def _child_messages(self, brief, raw, start, end, commands=(), *, user_text=None):
        self._user(CHILD_EXTERNAL, start, user_text if user_text is not None else brief)
        at = utc(start)
        for index, (command, output) in enumerate(commands, 1):
            moment = (at + timedelta(seconds=index)).isoformat()
            mid = self._assistant(CHILD_EXTERNAL, moment)
            self._shell(CHILD_EXTERNAL, mid, moment, command, output)
        final = self._assistant(CHILD_EXTERNAL, end, finish='stop')
        self._text(CHILD_EXTERNAL, final, end, raw)
        return final

    def page_commands(self, pages, outputs=None):
        commands = []
        for number, page in enumerate(pages, 1):
            output = page if outputs is None else outputs[number - 1]
            commands.append(self.page_command(number, output))
        return commands

    def page_command(self, number, output):
        return (_page_command(self.directory, self.request['material_sha256'], number),
                output)

    def _reset_child(self):
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('DELETE FROM session_part WHERE session_id=?', (CHILD_EXTERNAL,))
            db.execute('DELETE FROM session_message WHERE session_id=?', (CHILD_EXTERNAL,))
        self.child_seq = 0

    def _zip(self, target):
        entries = {'manifest.json': b'{"fixture":true}\n'}
        entries['SHA256SUMS.json'] = (encode({name: digest(raw)
                                             for name, raw in entries.items()})
                                      + '\n').encode()
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, 'w') as archive:
            for name, raw in entries.items():
                archive.writestr(name, raw)
        return target.read_bytes()

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        self.assertEqual(str(caught.exception), code)
        return caught.exception


class ParserContract(unittest.TestCase):
    def test_only_the_exact_literal_wrapper_is_decoded(self):
        valid = _describe_script(('openbot.start_task',))
        self.assertEqual(parse_execute(valid),
                         {'method': 'tool_describe',
                          'argument': {'names': ['openbot.start_task']}})
        start = _start_script({'title': 'T', 'brief': 'B'})
        self.assertEqual(parse_execute(start)['argument']['arguments'],
                         {'title': 'T', 'brief': 'B'})
        for script in (
                valid.replace('return r', 'console.log(r); return r'),
                'const r = await tools.openbot.tool_describe({"names": "x", "names": ["openbot.start_task"]}); return r;',
                valid.replace('await tools.openbot.tool_describe', 'await eval("x")'),
                valid.replace('return r;', 'return r; extra();'),
                valid[:-1] + ', r);',
                'const r = await tools.openbot.tool_describe({names:[`x`]}); return r;',
                'const r = await tools.openbot.tool_describe({names:["a"+"b"]}); return r;'):
            with self.subTest(script=script):
                with self.assertRaises(ContractError) as caught:
                    parse_execute(script)
                self.assertEqual(str(caught.exception), 'NATIVE_UNAUTHORIZED_TOOL')
        for value in ('x' * 32769, 1, ''):
            with self.assertRaises(ContractError):
                parse_execute(value)


class RecordContract(OpenCodeFixture):
    def test_session_identity_is_exact_and_effort_bound(self):
        info = session_record(self.config, PARENT_EXTERNAL)
        self.assertEqual(info['model'], MODEL)
        self.assertEqual(info['effort'], VARIANT)
        self.assertEqual(assert_session_identity(
            self.config, PARENT_EXTERNAL, model=MODEL, provider='opencode',
            effort=VARIANT)['effort'], VARIANT)
        self.assert_code('NATIVE_MODEL_SWITCHED', assert_session_identity, self.config,
                         PARENT_EXTERNAL, model='opencode/other', provider='opencode')
        self.assert_code('NATIVE_MODEL_SWITCHED', assert_session_identity, self.config,
                         PARENT_EXTERNAL, model=MODEL, provider='opencode',
                         effort='medium')
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute("UPDATE session_v2 SET version='9.9.9'")
        self.assert_code('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', session_record,
                         self.config, PARENT_EXTERNAL)

    def test_legacy_parent_binding_preserves_only_observed_session_versions(self):
        identity={**self.identity,'adapter':'OPENCODE_V2_SESSION_MESSAGE'}
        for version in sorted(LEGACY_SESSION_VERSIONS):
            with self.subTest(version=version):
                with sqlite3.connect(self.config['provider_db']) as db:
                    db.execute('UPDATE session_v2 SET version=? WHERE id=?',
                               (version,PARENT_EXTERNAL))
                bound=parent_binding(identity,self.config,require_configured_model=False,
                                     as_of=self.time(5))
                self.assertEqual(bound['external'],PARENT_EXTERNAL)
                self.assert_code('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED',session_record,
                                 self.config,PARENT_EXTERNAL)
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute("UPDATE session_v2 SET version='9.9.9' WHERE id=?",(PARENT_EXTERNAL,))
        self.assert_code('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED',parent_binding,identity,
                         self.config,require_configured_model=False,as_of=self.time(5))

    def test_shell_output_normalization_accepts_only_one_platform_line_ending(self):
        page='FRAME-END'
        self.assertTrue(_page_output(page,page))
        self.assertTrue(_page_output(page+'\n',page))
        self.assertTrue(_page_output(page+'\r\n',page))
        for output in (page+'\n\n',page+'\r\n\r\n',page+'\r',page+'\nextra'):
            with self.subTest(output=repr(output)):
                self.assertFalse(_page_output(output,page))

    def test_duplicate_message_order_fails_closed(self):
        self._user(PARENT_EXTERNAL, self.time(2), 'second user')
        with sqlite3.connect(self.config['provider_db']) as db:
            first = db.execute('SELECT id,time_created,seq FROM session_message '
                               'ORDER BY time_created,seq LIMIT 1').fetchone()
            db.execute('UPDATE session_message SET time_created=?,seq=? WHERE id=?',
                       (first[1], first[2], 'msg_%s_1' % PARENT_EXTERNAL))
        self.assert_code('NATIVE_REVIEW_INCOMPLETE', attest_turn_model, self.config,
                         PARENT_EXTERNAL, PARENT_TURN, MODEL, self.workspace,
                         start=self.time(-10), end=self.time(5), backend='opencode')

    def test_unknown_execute_tool_is_not_a_discovery(self):
        mid = self._assistant(PARENT_EXTERNAL, self.time(1))
        self._execute(PARENT_EXTERNAL, mid, self.time(1), _describe_script(),
                      tool='openbot.unknown',
                      call_input={'names': ['openbot.start_task',
                                            'openbot.attach_files_to_response']},
                      result=_discovery_json())
        self.assert_code('NATIVE_UNAUTHORIZED_TOOL', attest_smoke_discovery,
                         self.identity, self.config, as_of=self.time(5))


class DiscoveryContract(OpenCodeFixture):
    def test_exactly_one_successful_discovery_is_required(self):
        self._discovery()
        proof = attest_smoke_discovery(self.identity, self.config, as_of=self.time(5))
        self.assertEqual(proof['tools'], ['openbot.attach_files_to_response',
                                          'openbot.start_task'])
        self._discovery(self.time(2))
        error = self.assert_code('NATIVE_TOOL_DISCOVERY_UNVERIFIED',
                                 attest_smoke_discovery, self.identity, self.config,
                                 as_of=self.time(5))
        self.assertEqual(error.diagnostic['check'], 'DUPLICATE_CALL')

    def test_incomplete_or_modified_schema_is_not_a_discovery(self):
        broken = json.loads(_discovery_json())
        broken['tools'][1]['inputSchema']['properties'].pop('folder')
        self._discovery(result=encode(broken))
        error = self.assert_code('NATIVE_TOOL_DISCOVERY_UNVERIFIED',
                                 attest_smoke_discovery, self.identity, self.config,
                                 as_of=self.time(5))
        self.assertEqual(error.diagnostic['check'], 'SCHEMA_MISMATCH')

    def test_failed_nested_wrapper_is_tolerated(self):
        mid = self._assistant(PARENT_EXTERNAL, self.time(1))
        script = ('const r = await tools.openbot.tool_call('
                  + json.dumps({'name': 'openbot.tool_describe',
                                'arguments': {'names': ['openbot.start_task']}})
                  + '); return r;')
        self._execute(PARENT_EXTERNAL, mid, self.time(1), script,
                      tool='openbot.tool_call',
                      call_input={'name': 'openbot.tool_describe',
                                  'arguments': {'names': ['openbot.start_task']}},
                      result='{}', status='error', call_status='error')
        self._discovery(self.time(2))
        attest_smoke_discovery(self.identity, self.config, as_of=self.time(5))

    def test_direct_shell_is_not_a_substitute_for_discovery(self):
        mid = self._assistant(PARENT_EXTERNAL, self.time(1))
        self._shell(PARENT_EXTERNAL, mid, self.time(1), 'echo x', 'x')
        error = self.assert_code('NATIVE_TOOL_DISCOVERY_UNVERIFIED',
                                 attest_smoke_discovery, self.identity, self.config,
                                 as_of=self.time(5))
        self.assertEqual(error.diagnostic['check'], 'NO_CALL')


class SubmissionContract(OpenCodeFixture):
    def args(self):
        return {'title': 'OPENBOT-RESEARCH-' + self.request['material_sha256'],
                'brief': 'exact brief'}

    def test_one_exact_acknowledged_start_task_is_bound(self):
        args = self.args()
        self._submission(self.time(1), args)
        observed = observe_submission(self.config, self.identity, self.at, args,
                                      as_of=self.time(5))
        self.assertEqual(observed['submission_state'], 'ACKNOWLEDGED')
        self.assertEqual(observed['submission_attempts'], 1)
        self.assertEqual(observed['acknowledged_task_ref'], ref(CHILD_THREAD))

    def test_pre_request_call_is_ignored(self):
        args = self.args()
        self._submission(self.time(-2), args)
        observed = observe_submission(self.config, self.identity, self.at, args,
                                      as_of=self.time(5))
        self.assertEqual(observed['submission_state'], 'NOT_OBSERVED')
        self.assertEqual(observed['submission_attempts'], 0)

    def test_duplicate_submission_is_ambiguous(self):
        args = self.args()
        self._submission(self.time(1), args)
        self._submission(self.time(2), args)
        self.assert_code('NATIVE_HANDOFF_UNATTESTED', observe_submission, self.config,
                         self.identity, self.at, args, as_of=self.time(5))

    def test_wrong_arguments_never_bind(self):
        args = self.args()
        self._submission(self.time(1), {**args, 'brief': 'other'})
        self.assert_code('NATIVE_HANDOFF_UNATTESTED', observe_submission, self.config,
                         self.identity, self.at, args, as_of=self.time(5))

    def test_wrong_acknowledgment_never_binds(self):
        args = self.args()
        self._submission(self.time(1), args,
                         ack={'taskId': CHILD_THREAD, 'title': 'wrong'})
        self.assert_code('NATIVE_HANDOFF_UNATTESTED', observe_submission, self.config,
                         self.identity, self.at, args, as_of=self.time(5))

    def test_rejected_submission_is_reported_without_acknowledgment(self):
        args = self.args()
        self._submission(self.time(1), args, status='error', call_status='error')
        observed = observe_submission(self.config, self.identity, self.at, args,
                                      as_of=self.time(5))
        self.assertEqual(observed['submission_state'], 'REJECTED')
        self.assertEqual(observed['submission_error'], 'NATIVE_TOOL_REJECTED')


class ChildContract(OpenCodeFixture):
    def setUp(self):
        super().setUp()
        self.request['input_transport'] = COMPACT_PAGES
        self.request['dispatch_reservation_policy'] = COMPACT_SUBMISSION_POLICY
        self.request['material_sha256'] = digest(encode(_material(self.request)).encode())
        self.reply['material_sha256'] = self.request['material_sha256']
        self.raw = encode(self.reply)
        self.args, self.fingerprint, self.pages = packet(self.request, self.directory)
        self._child_session()
        self.start = self.time(3)
        self.end = self.time(8)

    def child(self, *, commands=None, brief=None, raw=None, user_text=None):
        if commands is None:
            commands = self.page_commands(self.pages)
        return self._child_messages(brief or self.args['brief'], raw or self.raw,
                                    self.start, self.end, commands, user_text=user_text)

    def proof(self):
        return attest(self.config, CHILD_EXTERNAL, CHILD_TURN, model=MODEL,
                      workspace=self.config['agent_workspace'], start=self.start,
                      end=self.end, expected_input=self.args['brief'],
                      expected_reply=self.raw, backend='opencode',
                      evidence=(self.directory, self.request['material_sha256'],
                                self.pages), effort=VARIANT)

    def test_exact_ordered_pages_and_final_text_are_attested(self):
        self.child()
        proof = self.proof()
        self.assertEqual(proof['provider_schema'], SCHEMA)
        self.assertEqual(proof['model_requests'], len(self.pages) + 1)
        self.assertEqual(proof['tool_operations'], ['READ_SKILL', 'READ_REQUEST'])

    def test_one_trailing_line_terminator_is_the_only_page_tolerance(self):
        outputs = list(self.pages)
        outputs[0] = outputs[0] + '\r\n'
        self.child(commands=self.page_commands(self.pages, outputs))
        self.proof()

    def test_modified_truncated_missing_duplicate_and_reordered_pages_fail(self):
        self.assertGreaterEqual(len(self.pages), 3)
        modified = list(self.pages)
        modified[0] = modified[0].replace('"page":1', '"page":2', 1)
        truncated = list(self.pages)
        truncated[-1] = truncated[-1][:-10]
        tail = [self.page_command(number, self.pages[number - 1])
                for number in range(2, len(self.pages) + 1)]
        duplicate = [self.page_command(1, self.pages[0]),
                     self.page_command(1, self.pages[0]), *tail]
        reordered = [self.page_command(2, self.pages[1]),
                     self.page_command(1, self.pages[0]),
                     *[self.page_command(number, self.pages[number - 1])
                       for number in range(3, len(self.pages) + 1)]]
        cases = [
            ('NATIVE_READ_INCOMPLETE', self.page_commands(self.pages, modified)),
            ('NATIVE_READ_INCOMPLETE', self.page_commands(self.pages, truncated)),
            ('NATIVE_READ_INCOMPLETE', self.page_commands(self.pages[:-1])),
            ('NATIVE_UNAUTHORIZED_TOOL', duplicate),
            ('NATIVE_UNAUTHORIZED_TOOL', reordered),
        ]
        for expected, commands in cases:
            with self.subTest(expected=expected):
                self._reset_child()
                self.child(commands=commands)
                self.assert_code(expected, self.proof)

    def test_extra_shell_or_unapproved_tool_is_rejected(self):
        self.child()
        mid = self._assistant(CHILD_EXTERNAL, self.time(7))
        self._shell(CHILD_EXTERNAL, mid, self.time(7), 'cat /etc/passwd', 'x')
        self.assert_code('NATIVE_UNAUTHORIZED_TOOL', self.proof)

    def test_unapproved_execute_tool_is_rejected(self):
        self.child()
        mid = self._assistant(CHILD_EXTERNAL, self.time(7))
        self._execute(CHILD_EXTERNAL, mid, self.time(7), _describe_script(),
                      tool='openbot.tool_describe',
                      call_input={'names': ['openbot.start_task']},
                      result=_discovery_json())
        self.assert_code('NATIVE_UNAUTHORIZED_TOOL', self.proof)

    def test_child_session_variant_switch_fails(self):
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('UPDATE session_v2 SET model=? WHERE id=?',
                       (encode(_model('medium')), CHILD_EXTERNAL))
        self.child()
        self.assert_code('NATIVE_MODEL_SWITCHED', self.proof)

    def test_child_assistant_variant_switch_fails(self):
        self.child()
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute("UPDATE session_message SET data=replace(data, '\"variant\": \"high\"', "
                       "'\"variant\": \"medium\"') WHERE type='assistant'")
        self.assert_code('NATIVE_MODEL_SWITCHED', self.proof)

    def test_wrong_final_text_fails(self):
        self.child(raw='forged')
        self.assert_code('NATIVE_REPLY_PROVENANCE', self.proof)

    def test_extra_final_text_part_fails(self):
        final = self.child()
        self._text(CHILD_EXTERNAL, final, self.end, 'extra', ordinal=1)
        self.assert_code('NATIVE_REPLY_PROVENANCE', self.proof)

    def test_missing_or_duplicated_input_fails(self):
        self.child(user_text=self.args['brief'][:-10])
        self.assert_code('NATIVE_READ_INCOMPLETE', self.proof)
        self._reset_child()
        self.child(user_text=self.args['brief'] + self.args['brief'])
        self.assert_code('NATIVE_READ_INCOMPLETE', self.proof)


class CollectContract(OpenCodeFixture):
    def inline(self):
        request = self.inline_request
        raw = encode(self.inline_reply)
        brief = review_brief(request)
        start, end = self.time(3), self.time(8)
        self._child_session()
        self._child_messages(brief, raw, start, end)
        self._child_projection(brief, raw, self.time(2), start, end,
                               material=request['material_sha256'])
        args = {'title': 'OPENBOT-RESEARCH-' + request['material_sha256'],
                'brief': brief}
        self._submission(self.time(1), args)
        return request, raw

    def compact(self):
        self.request['input_transport'] = COMPACT_PAGES
        self.request['dispatch_reservation_policy'] = COMPACT_SUBMISSION_POLICY
        self.request['material_sha256'] = digest(encode(_material(self.request)).encode())
        self.reply['material_sha256'] = self.request['material_sha256']
        self.raw = encode(self.reply)
        args, fingerprint, pages = packet(self.request, self.directory)
        ticket = {'material_sha256': self.request['material_sha256'],
                  'arguments_sha256': digest(encode(args).encode()),
                  'packet_sha256': fingerprint,
                  'evidence_pages': len(pages),
                  'submission_policy': COMPACT_SUBMISSION_POLICY,
                  'published_at_utc': self.time(5),
                  'reserved_at_utc': self.time(6)}
        (self.directory / (self.request['material_sha256'] + '.review-task.json')).write_text(
            encode(args), encoding='utf-8')
        (self.directory / (self.request['material_sha256'] + '.dispatch.json')).write_text(
            encode(ticket), encoding='utf-8')
        start = self.time(8)
        end = self.time(8 + len(pages) + 1)
        self._child_session()
        self._child_messages(args['brief'], self.raw, start, end,
                             self.page_commands(pages))
        self._child_projection(args['brief'], self.raw, self.time(7), start, end)
        self._submission(self.time(7), args)
        return args, fingerprint, pages, ticket

    def test_full_inline_collect_validates_reply_and_child(self):
        request, raw = self.inline()
        checked, audit = collect(request, self.config, as_of=self.time(10))
        self.assertEqual(checked, raw)
        self.assertEqual(audit['validated_rows'], 1)
        self.assertEqual(audit['native_invocation_verified'], True)
        self.assertEqual(audit['provider_schema'], SCHEMA)
        self.assertFalse(audit['trade_authorization'])

    def test_forged_child_text_is_not_a_receipt(self):
        request, raw = self.inline()
        with sqlite3.connect(self.config['provider_db']) as db:
            rows = db.execute("SELECT message_id,ordinal,data FROM session_part "
                              "WHERE session_id=? AND type='text'",
                              (CHILD_EXTERNAL,)).fetchall()
            self.assertEqual(len(rows), 1)
            mid, ordinal, data = rows[0]
            payload = json.loads(data)
            payload['text'] = 'forged'
            db.execute('UPDATE session_part SET data=? WHERE session_id=? '
                       'AND message_id=? AND ordinal=?',
                       (encode(payload), CHILD_EXTERNAL, mid, ordinal))
        self.assert_code('NATIVE_REPLY_PROVENANCE', collect, request,
                         self.config, as_of=self.time(10))

    def test_configured_model_change_after_start_is_rejected(self):
        request, raw = self.inline()
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute('UPDATE projection_provider_sessions SET model=? WHERE id=?',
                       ('opencode/other', CHILD_SESSION))
        self.assert_code('NATIVE_MODEL_SWITCHED', collect, request, self.config,
                         as_of=self.time(10), require_configured_model=True)

    def test_missing_parent_submission_never_becomes_a_receipt(self):
        request = self.inline_request
        raw = encode(self.inline_reply)
        brief = review_brief(request)
        start, end = self.time(3), self.time(8)
        self._child_session()
        self._child_messages(brief, raw, start, end)
        self._child_projection(brief, raw, self.time(2), start, end,
                               material=request['material_sha256'])
        mid = self._assistant(PARENT_EXTERNAL, self.time(1))
        self._text(PARENT_EXTERNAL, mid, self.time(1), 'no task was submitted')
        self.assert_code('NATIVE_HANDOFF_UNATTESTED', collect, request,
                         self.config, as_of=self.time(10))

    def test_compact_ticket_pages_and_acknowledgment_are_bound(self):
        _, _, pages, _ = self.compact()
        raw, audit = collect(self.request, self.config, as_of=self.time(30),
                             directory=self.directory)
        self.assertEqual(raw, self.raw)
        self.assertEqual(audit['verified_evidence_pages'], len(pages))
        self.assertEqual(audit['parent_delivery'],
                         'EXACT_TASK_ARGUMENTS_IN_PROVIDER_RECORD')

    def test_compact_ticket_with_wrong_packet_fails(self):
        args, _, pages, ticket = self.compact()
        ticket['packet_sha256'] = '0' * 64
        (self.directory / (self.request['material_sha256'] + '.dispatch.json')).write_text(
            encode(ticket), encoding='utf-8')
        self.assert_code('NATIVE_HANDOFF_UNATTESTED', collect, self.request,
                         self.config, as_of=self.time(30), directory=self.directory)

    def test_compact_modified_page_fails(self):
        self.request['input_transport'] = COMPACT_PAGES
        self.request['dispatch_reservation_policy'] = COMPACT_SUBMISSION_POLICY
        self.request['material_sha256'] = digest(encode(_material(self.request)).encode())
        self.reply['material_sha256'] = self.request['material_sha256']
        self.raw = encode(self.reply)
        args, fingerprint, pages = packet(self.request, self.directory)
        ticket = {'material_sha256': self.request['material_sha256'],
                  'arguments_sha256': digest(encode(args).encode()),
                  'packet_sha256': fingerprint,
                  'evidence_pages': len(pages),
                  'submission_policy': COMPACT_SUBMISSION_POLICY,
                  'published_at_utc': self.time(5),
                  'reserved_at_utc': self.time(6)}
        (self.directory / (self.request['material_sha256'] + '.review-task.json')).write_text(
            encode(args), encoding='utf-8')
        (self.directory / (self.request['material_sha256'] + '.dispatch.json')).write_text(
            encode(ticket), encoding='utf-8')
        outputs = list(pages)
        outputs[0] = outputs[0][:-5]
        start = self.time(8)
        end = self.time(8 + len(pages) + 1)
        self._child_session()
        self._child_messages(args['brief'], self.raw, start, end,
                             self.page_commands(pages, outputs))
        self._child_projection(args['brief'], self.raw, self.time(7), start, end)
        self._submission(self.time(7), args)
        self.assert_code('NATIVE_READ_INCOMPLETE', collect, self.request,
                         self.config, as_of=self.time(30), directory=self.directory)


class StartAndPreflightContract(OpenCodeFixture):
    def test_start_command_requires_the_exact_shell_execution(self):
        root = wsl_root().replace("'", "''")
        command = (f"wsl.exe --cd '{root}' -- python3 -m researcher.openbot_runner "
                   f"start --request-id {'a' * 32}")
        mid = self._assistant(PARENT_EXTERNAL, self.time(1))
        self._shell(PARENT_EXTERNAL, mid, self.time(1), command, 'ok')
        proof = attest_start_command(self.identity, self.config,
                                     {'request_id': 'a' * 32})
        self.assertEqual(proof['status'], 'VERIFIED_OPENBOT_AGENT_COMMAND')
        self.assertEqual(proof['source'], 'OPENCODE_PROVIDER_SHELL_EXECUTION')

    def test_preflight_reads_the_current_parent_turn_and_both_skills(self):
        expected = (ROOT / 'integration/openbot-market-research/SKILL.md').read_text(
            encoding='utf-8').replace('@@RESEARCH_ROOT@@', wsl_root()).encode()
        installed = self.workspace / '.agents/skills/openbot-market-research/SKILL.md'
        installed.parent.mkdir(parents=True)
        installed.write_bytes(expected)
        self._discovery()
        result = integration_preflight(self.config, as_of=self.time(5))
        self.assertEqual(result['provider_schema'], SCHEMA)
        self.assertEqual(result['identity']['provider'], 'opencode')
        self.assertFalse(result['native_execution_verified'])

    def test_preflight_rejects_a_changed_installed_skill(self):
        expected = (ROOT / 'integration/openbot-market-research/SKILL.md').read_text(
            encoding='utf-8').replace('@@RESEARCH_ROOT@@', wsl_root()).encode()
        installed = self.workspace / '.agents/skills/openbot-market-research/SKILL.md'
        installed.parent.mkdir(parents=True)
        installed.write_bytes(expected + b'changed')
        self._discovery()
        self.assert_code('AGENT_SKILL_HASH', integration_preflight, self.config,
                         as_of=self.time(5))

    def test_active_parent_incomplete_assistant_records_do_not_block_preflight_or_command_poll(self):
        expected=(ROOT/'integration/openbot-market-research/SKILL.md').read_text(
            encoding='utf-8').replace('@@RESEARCH_ROOT@@',wsl_root()).encode()
        installed=self.workspace/'.agents/skills/openbot-market-research/SKILL.md'
        installed.parent.mkdir(parents=True);installed.write_bytes(expected)
        self._discovery()
        root=wsl_root().replace("'","''")
        command=(f"wsl.exe --cd '{root}' -- python3 -m researcher.openbot_runner "
                 f"start --request-id {'a'*32}")
        mid=self._assistant(PARENT_EXTERNAL,self.time(2))
        self._shell(PARENT_EXTERNAL,mid,self.time(2),command,'{\"state\":\"STARTING\"}\r\n')
        with sqlite3.connect(self.config['provider_db']) as db:
            row=db.execute('SELECT data FROM session_message WHERE id=?',(mid,)).fetchone()
            data=json.loads(row[0]);data['time']['completed']=None;data['finish']=None;data['rawFinish']=None
            db.execute('UPDATE session_message SET data=? WHERE id=?',(encode(data),mid))
        preflight=integration_preflight(self.config,as_of=self.time(5))
        self.assertEqual(preflight['provider_schema'],SCHEMA)
        proof=attest_start_command(self.identity,self.config,{'request_id':'a'*32})
        self.assertEqual(proof['status'],'VERIFIED_OPENBOT_AGENT_COMMAND')

    def test_active_incomplete_assistant_record_is_ignored_until_its_part_completes(self):
        mid=self._assistant(PARENT_EXTERNAL,self.time(1))
        with sqlite3.connect(self.config['provider_db']) as db:
            row=db.execute('SELECT data FROM session_message WHERE id=?',(mid,)).fetchone()
            data=json.loads(row[0]);data['time']['completed']=None;data['finish']=None;data['rawFinish']=None
            db.execute('UPDATE session_message SET data=? WHERE id=?',(encode(data),mid))
        self.assert_code('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED',attest_turn_model,self.config,
            PARENT_EXTERNAL,PARENT_TURN,MODEL,self.workspace,start=self.time(-10),end=self.time(5),
            backend='opencode',allow_incomplete=False)
        self.assertEqual(attest_turn_model(self.config,PARENT_EXTERNAL,PARENT_TURN,MODEL,
            self.workspace,start=self.time(-10),end=self.time(5),backend='opencode',
            allow_incomplete=True)['model'],MODEL)

    def test_submission_poll_observes_a_completed_call_inside_an_active_parent_turn(self):
        args={'title':'OPENBOT-RESEARCH-FIXTURE','brief':'exact fixture brief\n'}
        mid=self._submission(self.time(2),args)
        with sqlite3.connect(self.config['provider_db']) as db:
            row=db.execute('SELECT data FROM session_message WHERE id=?',(mid,)).fetchone()
            data=json.loads(row[0]);data['time']['completed']=None;data['finish']=None;data['rawFinish']=None
            db.execute('UPDATE session_message SET data=? WHERE id=?',(encode(data),mid))
        result=observe_submission(self.config,self.identity,self.time(1),args,
                                  as_of=self.time(5),reserved_at=self.time(1))
        self.assertEqual(result['submission_state'],'ACKNOWLEDGED')
        self.assertEqual(result['submission_attempts'],1)


class DeliveryContract(OpenCodeFixture):
    def setUp(self):
        super().setUp()
        self._child_session()
        self.start, self.end = self.time(3), self.time(8)
        brief = review_brief(self.request)
        self._child_messages(brief, self.raw, self.start, self.end)
        self._child_projection(brief, self.raw, self.time(2), self.start, self.end)
        self.job = '20260101T000000Z-' + 'b' * 32
        self.target = self.workspace / 'market-research-results' / (self.job + '.zip')
        self.zip_bytes = self._zip(self.target)
        self.sha = digest(self.zip_bytes)
        self.state = {'native_identity': self.identity,
                      'artifact': {'attachment_path': str(self.target),
                                   'sha256': self.sha},
                      'job_id': self.job,
                      'material_sha256': self.request['material_sha256'],
                      'request_prepared_at_utc': self.at}
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute("UPDATE projection_turns SET status='completed',completed_at=? "
                       "WHERE turn_id=?", (self.time(20), PARENT_TURN))

    def delivery_turn(self, *, text=None, size=None, exchange=True, attach=True):
        text = text or f"Job {self.job} complete. Artifact SHA-256 {self.sha}."
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',
                       (DELIVERY_TURN, PARENT_THREAD, PARENT_SESSION, 'completed',
                        self.time(30), self.time(31)))
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',
                       (PARENT_THREAD, DELIVERY_TURN, 'user', None, 'completed',
                        self.time(30), 0,
                        encode({'text': 'Task report from OpenBot: done'})))
            attachments = [{'name': self.target.name,
                            'size': size or len(self.zip_bytes)}]
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',
                       (PARENT_THREAD, DELIVERY_TURN, 'assistant', 'final_answer',
                        'completed', self.time(31), 1,
                        encode({'text': text, 'attachments': attachments})))
            if exchange:
                db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',
                           (PARENT_THREAD, DELIVERY_TURN, 'agent', 'agent-exchange',
                            'completed', self.time(31), 2,
                            encode({'text': self.raw,
                                    'exchange': {'senderTaskId': CHILD_THREAD}})))
        self._user(PARENT_EXTERNAL, self.time(30), 'Task report from OpenBot: done')
        mid = self._assistant(PARENT_EXTERNAL, self.time(31), finish='stop')
        if attach:
            self._execute(PARENT_EXTERNAL, mid, self.time(31),
                          _attach_script(self.target), tool='openbot.tool_call',
                          call_input={'name': 'openbot.attach_files_to_response',
                                      'arguments': {'paths': [str(self.target)]}},
                          result=encode({'attached': 1}), ordinal=0)
        self._text(PARENT_EXTERNAL, mid, self.time(31), text,
                   ordinal=1 if attach else 0)

    def test_exact_parent_delivery_and_child_exchange_are_bound(self):
        self.delivery_turn()
        proof = delivery_proof(self.state, self.config)
        self.assertEqual(proof['status'], 'VERIFIED_OPENBOT_FINAL_DELIVERY')
        self.assertEqual(proof['zip_sha256'], self.sha)
        self.assertFalse(proof['trade_authorization'])

    def test_wrong_attachment_size_fails(self):
        self.delivery_turn(size=1)
        self.assert_code('NATIVE_REPLY_PROVENANCE', delivery_proof, self.state,
                         self.config)

    def test_missing_child_exchange_fails(self):
        self.delivery_turn(exchange=False)
        self.assert_code('NATIVE_HANDOFF_UNATTESTED', delivery_proof, self.state,
                         self.config)

    def test_provider_text_that_does_not_match_projection_is_not_delivery(self):
        self.delivery_turn()
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute("UPDATE projection_thread_messages SET message_json=? "
                       "WHERE item_type='final_answer' AND thread_id=?",
                       (encode({'text': 'different', 'attachments': [
                           {'name': self.target.name, 'size': len(self.zip_bytes)}]}),
                        PARENT_THREAD))
        self.assertIsNone(delivery_proof(self.state, self.config))


if __name__ == '__main__':
    unittest.main()
