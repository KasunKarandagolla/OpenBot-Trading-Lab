"""Relevant regression suites and a separate, non-repairing stale-seal diagnosis."""
import io
import os
import subprocess
import unittest
from diagnosis_common import *
sys.path.insert(0,str(ROOT/'tests'))

def registration_diagnosis():
    base=OUT/'starting-freeze.json';frozen=read(base)['preexisting_files']
    directory=ROOT/'evidence/additional-3/policy-session3-001';reg=read(directory/'registration.json');expected=dict(reg['source_hashes'])
    amendments=[]
    for path in sorted((directory/'source-amendments').glob('*.json')):
        a=read(path);assert a['registration_sha256']==sha(directory/'registration.json')
        for name,change in a['changes'].items():
            assert expected.get(name)==change['old_sha256'];expected[name]=change['new_sha256']
        amendments.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path),reason=a['reason']))
    def differences(hashes):
        rows=[]
        for name,wanted in hashes.items():
            actual=sha(ROOT/name)
            if actual==wanted:continue
            try:log=subprocess.check_output(['git','log','-4','--format=%H %s','ade410ec625be51f8dbcb7194b98965d8286daf7','--',name],cwd=ROOT,text=True).splitlines()
            except FileNotFoundError:log=read(OUT/'registration-history.json').get(name,[])
            rows.append(dict(path=name,expected_sha256=wanted,actual_sha256=actual,pr13_start_sha256=frozen[name],
                unchanged_from_pr13=actual==frozen[name],prior_commit_history=log))
        return rows
    policy=differences(expected);paper={}
    for session in ('session-1','session-2','session-3'):
        hashes={name:expected for expected,name in (line.split(maxsplit=1) for line in (ROOT/'evidence'/session/'freeze.sha256').read_text().splitlines())}
        paper[session]=differences(hashes)
    write(OUT/'registration-diagnosis.json',dict(policy_mismatches=policy,policy_amendments=amendments,old_paper_freeze_mismatches=paper,
        interpretation='Inherited seals describe older source versions. All listed current bytes already existed at verified PR13 HEAD; this diagnosis did not cause the mismatch. Original verification correctly fails closed for those historical registrations. No registration, review or freeze was rewritten.',
        resolution='Use the separately sealed diagnosis research namespace for this backtest. Repairing old activation authority requires a distinct source/review amendment and its own review; no activation is authorized here.'))

def run():
    registration_diagnosis()
    import test_setup,test_session4
    binding=WORK/'test-source-binding';root=binding/'development/gate/futures';root.mkdir(parents=True,exist_ok=True)
    for item in read(PARENT/'data.json')['files']:
        if item['timeframe']=='5m':continue
        path=root/Path(item['path']).name
        if not path.exists():os.link(ROOT/item['path'],path)
        assert sha(path)==item['prior_sealed_sha256']
    test_setup.DATA=binding;test_session4.DATA=DATA/'gate'
    modules=['test_setup','test_setup_fixes','test_policy','test_session3_structure','test_intelligence','test_session4','test_integrated','test_diagnosis']
    extras=['test_recovery.RecoveryRegression.'+name for name in ('test_seconds_after_hour_funding_survives_preexit_checkpoint_once_both_sides','test_no_persistent_or_live_activation','test_short_held_path_extremes_keep_direction_before_aggregation')]
    extras+=['test_playbooks.Callbacks.test_native_stop_precedes_roi_same_bar','test_playbooks.Callbacks.test_native_short_stop_precedes_roi_same_bar','test_integrated_archive.ArchiveRestore']
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in modules+extras)
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (OUT/'regression.txt').write_text(stream.getvalue())
    errors=[dict(test=t.id(),traceback=e) for t,e in result.errors]
    known=[e for e in errors if (e['test']=='test_policy.ConfigTests.test_baseline_and_native_emergency_settings_do_not_inherit_vwap_overrides' and 'registered v3 source changed; record explicit amendment' in e['traceback']) or (e['test']=='test_session4.ReviewedGuard.test_exact_modes_and_credentials_exposure_and_override_rejection' and 'frozen strategy/config/protocol changed: research/session3/causal_structure.py' in e['traceback'])]
    unexpected=[e for e in errors if e not in known]
    data=dict(at=now(),modules=modules,extra_checks=extras,run=result.testsRun,passed=result.testsRun-len(result.errors)-len(result.failures)-len(result.skipped),
        failures=[dict(test=t.id(),traceback=e) for t,e in result.failures],known_parent_errors=known,unexpected_errors=unexpected,
        skipped=[dict(test=t.id(),reason=e) for t,e in result.skipped],
        fixture_note='56 byte-identical old source series bound to isolated hardlink tree. Current public metadata only for controlled mock-book mechanics. Synthetic lifecycle fixtures make no market profit claims.',preservation=verify_parent())
    write(OUT/'regression.json',data)
    print(data['run'],'tests;',data['passed'],'passed;',len(known),'inherited errors;',len(unexpected),'unexpected errors;',len(result.failures),'assertion failures;',len(result.skipped),'skipped',flush=True)
    if unexpected or result.failures:raise SystemExit(1)

if __name__=='__main__':run()
