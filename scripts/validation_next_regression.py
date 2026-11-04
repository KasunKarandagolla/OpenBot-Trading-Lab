"""Run broad inherited checks without manufacturing absent private owner inputs."""
from validation_next_common import *
import io,unittest,sys
sys.path.insert(0,str(ROOT/'tests'))
def run():
 modules=['test_setup','test_setup_fixes','test_policy','test_session3_structure','test_intelligence','test_session4','test_integrated','test_diagnosis','test_validation_next']
 extras=['test_recovery.RecoveryRegression.'+n for n in ['test_seconds_after_hour_funding_survives_preexit_checkpoint_once_both_sides','test_no_persistent_or_live_activation','test_short_held_path_extremes_keep_direction_before_aggregation']]
 extras+=['test_playbooks.Callbacks.test_native_stop_precedes_roi_same_bar','test_playbooks.Callbacks.test_native_short_stop_precedes_roi_same_bar','test_integrated_archive.ArchiveRestore']
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(x) for x in modules+extras);stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 log=OUT/'regression.txt';log.write_text(stream.getvalue());errors=[]
 for t,e in r.errors:
  cls='MISSING_PRIOR_PRIVATE_INPUT' if 'FileNotFoundError' in e and ('/work/integrated/' in e or '/user_data/data/' in e or '/work/diagnosis/' in e) else 'INHERITED_REGISTRATION' if ('registered v3 source changed; record explicit amendment' in e or 'frozen strategy/config/protocol changed: research/session3/causal_structure.py' in e) else 'UNEXPECTED'
  errors.append(dict(test=t.id(),classification=cls,traceback=e))
 out=dict(at=now(),run=r.testsRun,passed=r.testsRun-len(r.errors)-len(r.failures)-len(r.skipped),errors=errors,failures=[dict(test=t.id(),traceback=e) for t,e in r.failures],skipped=[dict(test=t.id(),reason=e) for t,e in r.skipped],exit_code=0 if r.wasSuccessful() else 1,prior_private_inputs='NOT_PROVIDED; seals source-verified, do not relabel missing input tests as passes')
 write(OUT/'regression-and-validation.json',out);print({k:out[k] for k in ['run','passed','exit_code']},[(e['classification'],e['test']) for e in errors],flush=True)
 raise SystemExit(out['exit_code'])
if __name__=='__main__':run()
