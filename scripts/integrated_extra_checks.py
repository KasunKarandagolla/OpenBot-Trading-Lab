"""Direct inherited native funding/ambiguity checks and private-archive safety."""
import io
import unittest
from integrated_common import *
sys.path.insert(0,str(ROOT/'tests'))

def run():
    names=[
        'test_recovery.RecoveryRegression.test_seconds_after_hour_funding_survives_preexit_checkpoint_once_both_sides',
        'test_recovery.RecoveryRegression.test_no_persistent_or_live_activation',
        'test_recovery.RecoveryRegression.test_short_held_path_extremes_keep_direction_before_aggregation',
        'test_playbooks.Callbacks.test_native_stop_precedes_roi_same_bar',
        'test_playbooks.Callbacks.test_native_short_stop_precedes_roi_same_bar',
        'test_integrated_archive']
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in names)
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (OUT/'extra-checks.txt').write_text(stream.getvalue())
    write(OUT/'extra-checks.json',dict(run=result.testsRun,passed=result.testsRun-len(result.errors)-len(result.failures)-len(result.skipped),
        failures=[dict(test=t.id(),traceback=e) for t,e in result.failures],errors=[dict(test=t.id(),traceback=e) for t,e in result.errors],
        skipped=[dict(test=t.id(),reason=e) for t,e in result.skipped],classification='SYNTHETIC_NATIVE_MECHANICS_AND_FILESYSTEM_SAFETY'))
    print(stream.getvalue(),flush=True)
    if not result.wasSuccessful():raise SystemExit(1)

if __name__=='__main__':run()
