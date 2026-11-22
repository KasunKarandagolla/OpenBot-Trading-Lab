"""Isolated Windows path tests that model a reader without long-path opt-in."""
import errno
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

from researcher import native_app, native_codex, native_handoff, native_host, native_identity, settings
from researcher.agent_review import _material
from researcher.contracts import ContractError, digest, encode
from researcher.settings import ROOT
import test_native_runtime as runtime_fixture


class WindowsPathFixture(PureWindowsPath):
    """Map validated drive paths to real isolated files on the test host."""
    mount = None
    prefix = '\\\\?\\'

    def absolute(self):
        return self

    def backing_file(self):
        raw = str(self)
        ordinary = raw.removeprefix(self.prefix)
        if len(ordinary) >= 260 and raw == ordinary:
            raise FileNotFoundError(errno.ENOENT, 'simulated ordinary Win32 path limit')
        return self.mount.joinpath(*PureWindowsPath(ordinary).parts[1:])

    def lstat(self):
        return self.backing_file().lstat()

    def is_symlink(self):
        try:
            return self.backing_file().is_symlink()
        except FileNotFoundError:
            return False

    def stat(self):
        return self.backing_file().stat()

    def exists(self):
        return self.backing_file().exists()

    def is_file(self):
        return self.backing_file().is_file()

    def is_dir(self):
        return self.backing_file().is_dir()

    def read_bytes(self):
        return self.backing_file().read_bytes()

    def read_text(self, *, encoding=None):
        return self.backing_file().read_text(encoding=encoding)


class NativeWindowsPaths(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True)
        tmp = tempfile.TemporaryDirectory(dir=ROOT/'work')
        self.addCleanup(tmp.cleanup)
        self.mount = Path(tmp.name)
        self.checkout = WindowsPathFixture('C:/OpenBot/Checkout')
        suffix = WindowsPathFixture('jobs/20260101T000000Z-'+'1'*32+'/review')
        base = self.checkout/'work'
        name = 'a'*64+'.request.json'
        padding = 272-len(str(base/suffix/name))-1
        self.review = base/('x'*padding)/suffix
        self.path = self.review/name
        self.request_bytes = b'{"synthetic":"isolated long Windows request"}'
        self.write(self.path, self.request_bytes)

    def write(self, path, raw):
        actual = self.mount.joinpath(*path.parts[1:])
        actual.parent.mkdir(parents=True, exist_ok=True)
        actual.write_bytes(raw)
        return actual

    @contextmanager
    def windows(self):
        with patch.object(os, 'name', 'nt'), patch.object(WindowsPathFixture, 'mount', self.mount), \
                patch.object(native_identity, 'Path', WindowsPathFixture), patch.object(native_identity, 'ROOT', self.checkout):
            yield

    def test_long_windows_request_is_read_through_existing_native_reader(self):
        self.assertEqual(len(str(self.path)), 272)
        with self.windows():
            with self.assertRaises(FileNotFoundError):
                self.path.read_bytes()
            for value in (self.path, WindowsPathFixture.prefix+str(self.path),
                          '/mnt/c/'+self.path.as_posix()[3:]):
                with self.subTest(form=type(value)):
                    self.assertEqual(native_handoff.read_object(value), json.loads(self.request_bytes))
                    path = native_identity.under_work(value)
                    self.assertEqual(str(path), WindowsPathFixture.prefix+str(self.path))

    def test_short_paths_and_genuinely_missing_long_files(self):
        short = self.checkout/'work'/'short.json'
        self.write(short, b'{"short":true}')
        missing = self.path.with_name('b'*64+'.request.json')
        self.assertGreater(len(str(missing)),260)
        with self.windows():
            self.assertEqual(native_handoff.read_object(short), {'short': True})
            with self.assertRaises(FileNotFoundError) as failure:
                native_handoff.read_object(missing)
            self.assertEqual(native_identity.storage_fault(failure.exception,'READER')[1]['classification'],
                             'MISSING_FILE')

    def test_rejects_invalid_or_out_of_scope_paths_before_filesystem_lookup(self):
        invalid = (self.checkout/'work'/'..'/'outside.json', self.checkout/'work-other'/'x.json',
                   str(self.path)+':stream', str(self.path)+'.', 'C:work\\file.json',
                   r'\\.\C:\OpenBot\Checkout\work\short.json',
                   r'\\?\GLOBALROOT\Device\HarddiskVolume1\private.json')
        with self.windows(), patch.object(WindowsPathFixture,'lstat') as lookup:
            for value in invalid:
                with self.subTest(value=value), self.assertRaisesRegex(ContractError,'MUST_BE_UNDER_WORK'):
                    native_handoff.read_object(value)
            lookup.assert_not_called()

    def test_rejects_symlink_at_long_filename_and_at_long_ancestor(self):
        real_request = self.mount.joinpath(*self.path.parts[1:])
        elsewhere = self.mount/'outside'
        elsewhere.mkdir()
        (elsewhere/real_request.name).write_bytes(self.request_bytes)
        link_file = real_request.with_name('b'*64+'.request.json')
        link_file.symlink_to(elsewhere/real_request.name)
        link_directory = real_request.parent/('d'*90)
        link_directory.symlink_to(elsewhere,target_is_directory=True)
        with self.windows():
            for path in (self.path.with_name(link_file.name), self.review/link_directory.name/real_request.name):
                self.assertGreater(len(str(path)),260)
                with self.assertRaisesRegex(ContractError,'MUST_BE_UNDER_WORK'):
                    native_handoff.read_object(path)

    def test_drive_and_extended_drive_map_to_same_wsl_path(self):
        if os.name=='nt':
            self.assertEqual(native_identity.local_path(self.path), native_identity.local_path(
                WindowsPathFixture.prefix+str(self.path)))
            return
        expected = Path('/mnt/c', *self.path.parts[1:])
        self.assertEqual(native_identity.local_path(self.path), expected)
        self.assertEqual(native_identity.local_path(WindowsPathFixture.prefix+str(self.path)), expected)
        self.assertEqual(native_identity.path_key(self.path),native_identity.path_key(expected))

    def test_windows_bridge_reads_long_request_and_binds_ten_canonical_pages(self):
        skill = '.agents/skills/market-research-review/SKILL.md'
        self.write(self.checkout/skill,(ROOT/skill).read_bytes())
        request = {'as_of_utc':'2026-01-01T00:00:00+00:00','native_identity':{'provider':'codex','agent_id':'FIXTURE'},
                   'context':{'synthetic_padding':''},'material_sha256':'a'*64}
        request['context']['synthetic_padding']='x'*(95_000-len(native_codex.review_brief(request)))
        material = digest(encode(_material(request)).encode())
        request['material_sha256']=material
        saved = self.write(self.review/(material+'.request.json'), encode(request).encode())
        with patch.object(native_handoff,'ROOT',self.checkout):
            args,fingerprint,pages = native_handoff.packet(request,self.review)
        with patch.object(native_handoff,'ROOT',WindowsPathFixture.prefix+str(self.checkout)):
            self.assertEqual(native_handoff.packet(request,self.review),(args,fingerprint,pages))
        self.assertEqual(len(pages),10)
        self.assertEqual(digest(''.join(json.loads(p)['text'] for p in pages).encode()),fingerprint)
        args_file = self.write(self.review/(material+'.review-task.json'), encode(args).encode())
        stamp = request['as_of_utc']
        ticket = {'material_sha256':material,'arguments_sha256':digest(encode(args).encode()),
                  'packet_sha256':fingerprint,'evidence_pages':10,'published_at_utc':stamp,'reserved_at_utc':stamp,
                  'submission_policy':'EXACTLY_ONE_TICKET; NEVER_AUTOMATICALLY_RESUBMIT'}
        ticket_file=self.write(self.review/(material+'.dispatch.json'),encode(ticket).encode())
        private = self.review/('p'*90+'.json')
        files = {'openbot_db':self.review/'fixture-app.sqlite','provider_db':self.review/'fixture-provider.sqlite',
                 'agent_workspace':self.checkout/'work'}
        for name in ('openbot_db','provider_db'):
            self.write(files[name],b'not opened by this mocked receipt source')
        self.write(private,encode({k:str(v) for k,v in files.items()}).encode())
        reader_input = self.review/('i'*90+'.json')
        self.write(reader_input,encode({'config_file':str(private),'values':{'directory':str(self.review),
            'material':material,'identity':request['native_identity'],'as_of':stamp}}).encode())
        with self.windows(), patch.object(settings,'ROOT',self.checkout), patch.object(native_handoff,'ROOT',self.checkout), \
                patch.object(native_identity,'assert_parent'), patch.object(native_codex,'observe_submission',
                    return_value={'submission_attempts':0,'submission_state':'NOT_OBSERVED'}), \
                patch.object(native_app,'task_observation',return_value={'count':0}):
            verified = native_host.execute('observe_handoff',str(reader_input))
            self.assertEqual(verified['reserved_at_utc'],stamp)
            self.assertEqual(native_handoff.load_dispatch(self.review,request,as_of=stamp)[1:3],(fingerprint,pages))
        for path,raw,code in ((saved,encode({**request,'context':{}}),'REVIEW_REQUEST_HASH'),
                              (args_file,encode({**args,'brief':args['brief']+'!'}),'HANDOFF_UNATTESTED'),
                              (ticket_file,encode({**ticket,'submission_policy':native_handoff.RESERVED_SUBMISSION_POLICY,
                                  'reserved_monotonic':1}),'HANDOFF_UNATTESTED')):
            original = path.read_bytes()
            path.write_text(raw,encoding='utf-8')
            try:
                with self.windows(), patch.object(settings,'ROOT',self.checkout), patch.object(native_handoff,'ROOT',self.checkout), \
                        patch.object(native_identity,'assert_parent'):
                    with self.assertRaisesRegex(ContractError,code):
                        native_host.execute('observe_handoff',str(reader_input))
            finally:
                path.write_bytes(original)


class NativeModelComparison(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixture.CodexRuntimeFixtures()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def check_rejection(self, action, check):
        with self.assertRaisesRegex(ContractError,'^NATIVE_MODEL_SWITCHED$') as failure:
            action()
        self.assertEqual(native_identity.safe_diagnostic(failure.exception.diagnostic)['check'],check)

    def test_configured_agent_change_is_distinct_from_historical_parent_model(self):
        f = self.fixture
        model = 'different-model'
        with sqlite3.connect(f.config['openbot_db']) as db:
            db.execute('UPDATE projection_agents SET model=?,agent_json=?',(model,encode({**f.agent,'model':model})))
        self.check_rejection(lambda:native_identity.parent_binding(f.identity,f.config,
            require_configured_model=True),'CONFIGURED_MODEL')

    def test_app_parent_provider_session_keeps_exact_captured_model(self):
        f = self.fixture
        with sqlite3.connect(f.config['openbot_db']) as db:
            db.execute("UPDATE projection_provider_sessions SET model=? WHERE id='PARENT_SESSION'",
                       ('openai/'+f.identity['model'],))
        self.check_rejection(lambda:native_identity.parent_binding(f.identity,f.config),'APP_PARENT_MODEL')

    def test_codex_parent_thread_model_mismatch_is_reported_before_rollout(self):
        f = self.fixture
        with sqlite3.connect(f.config['provider_db']) as db:
            db.execute("UPDATE threads SET model=NULL WHERE id='PARENT'")
        self.check_rejection(lambda:native_identity.parent_binding(f.identity,f.config),'CODEX_PARENT_THREAD_MODEL')

    def test_historical_rollout_context_rejects_alias_missing_or_different_models(self):
        f = self.fixture
        args = {'title':'OPENBOT-RESEARCH-'+f.key,'brief':f.brief}
        for model in (f.identity['model'].upper(), None, 'different-model'):
            with self.subTest(model=model):
                f.parent[1]['payload']['model']=model
                f.write()
                self.check_rejection(lambda:native_codex.observe_submission(f.config,f.identity,
                    f.at,args,as_of=f.time(5)),'ROLLOUT_TURN_CONTEXT_MODEL')
        f.parent[1]['payload']['model']=f.identity['model']
        f.write()
        receipt=f.get()[1]
        self.assertTrue(receipt['native_invocation_verified'])
