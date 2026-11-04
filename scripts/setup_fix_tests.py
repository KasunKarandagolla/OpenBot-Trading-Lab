"""One focused repository verification pass with the known parent error separate."""
import sys,unittest
from setup_common import *
sys.path.insert(0,str(ROOT/'tests'))

def run():
    loader=unittest.TestLoader();suite=loader.discover(str(ROOT/'tests'),pattern='test_setup*.py')
    for module in ['test_session3_structure','test_intelligence','test_policy']:suite.addTests(loader.loadTestsFromName(module))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    known=[];unexpected=[]
    for test,error in result.errors:
        if test.id()=='test_policy.ConfigTests.test_baseline_and_native_emergency_settings_do_not_inherit_vwap_overrides' and 'registered v3 source changed; record explicit amendment' in error:
            known.append(dict(test=test.id(),reason='Same frozen-registration error documented on untouched PR11 parent',parent_evidence='evidence/setup/run-002/parent-regression-policy.txt'))
        else:unexpected.append(dict(test=test.id(),traceback=error))
    report=dict(tests_run=result.testsRun,passed=result.testsRun-len(result.errors)-len(result.failures)-len(result.skipped),
        known_parent_errors=known,unexpected_errors=unexpected,failures=[dict(test=t.id(),traceback=e) for t,e in result.failures],skipped=[dict(test=t.id(),reason=e) for t,e in result.skipped])
    write(OUT/'verification.json',report)
    if result.failures or unexpected:raise SystemExit(1)
if __name__=='__main__':run()
