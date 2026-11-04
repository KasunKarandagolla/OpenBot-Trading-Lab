"""Run relevant existing suites; preserve and separate the documented parent failure."""
import contextlib
import io
import unittest
from integrated_common import *
sys.path.insert(0,str(ROOT/'tests'))

def run():
    # Explicit fixture-input binding, without pretending to restore old private metadata.
    # Candles have already matched all 56 original source hashes; current contract
    # metadata is used ONLY by isolated native mechanics fixtures with mocked books.
    import test_setup,test_session4
    binding=WORK/'test-source-binding'
    root=binding/'development/gate/futures';root.mkdir(parents=True,exist_ok=True)
    import os
    for item in read(OUT/'data.json')['files']:
        if item['timeframe']=='5m': continue
        target=root/Path(item['path']).name
        if not target.exists(): os.link(ROOT/item['path'],target)
        if sha(target)!=item['prior_sealed_sha256']: raise ValueError('test candle binding differs from original')
    test_setup.DATA=binding
    test_session4.DATA=DATA/'gate'
    modules=['test_setup','test_setup_fixes','test_policy','test_session3_structure','test_intelligence','test_session4','test_integrated']
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in modules)
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (OUT/'regression.txt').write_text(stream.getvalue())
    errors=[dict(test=t.id(),traceback=e) for t,e in result.errors]
    known=[e for e in errors if (e['test']=='test_policy.ConfigTests.test_baseline_and_native_emergency_settings_do_not_inherit_vwap_overrides' and 'registered v3 source changed; record explicit amendment' in e['traceback']) or (e['test']=='test_session4.ReviewedGuard.test_exact_modes_and_credentials_exposure_and_override_rejection' and 'frozen strategy/config/protocol changed: research/session3/causal_structure.py' in e['traceback'])]
    unexpected=[e for e in errors if e not in known]
    data=dict(modules=modules,run=result.testsRun,passed=result.testsRun-len(result.errors)-len(result.failures)-len(result.skipped),
        failures=[dict(test=t.id(),traceback=e) for t,e in result.failures],known_parent_errors=known,unexpected_errors=unexpected,
        skipped=[dict(test=t.id(),reason=e) for t,e in result.skipped],native_lifecycle_fixtures='SYNTHETIC_MECHANICS_ONLY',
        fixture_bindings=dict(candles='56 byte-identical sealed source files; test module DATA bound to isolated hardlink tree',native_contract_metadata='Current public snapshot bound to test_session4.DATA; controlled mock books; no old snapshot restoration claimed'))
    write(OUT/'regression.json',data)
    print('Regression',data['run'],'run',data['passed'],'passed',len(known),'known parent errors',len(unexpected),'unexpected errors',flush=True)
    if result.failures or unexpected: raise SystemExit(1)

if __name__=='__main__': run()
