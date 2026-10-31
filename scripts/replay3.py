"""Native challenger replay without replacing the retained primary experiment."""
import subprocess,sys,zipfile,hashlib
from session3_common import *

def replay(cid):
 name='StructureAwareSweepV1';out=destination(cid);recorded=read(out/'native-results'/(name+'.json'))['strategy'][name]['trades']
 args=[sys.executable,str(ROOT/'scripts/engine3.py'),'backtesting',cid,name]
 with (out/'native-replay-output.txt').open('w') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=sanitized_env())
 if r.returncode:raise ValueError('native replay failed')
 folder=ROOT/'user_data/backtest_results/session-3'/cid/name;archive=folder/read(folder/'.last_result.json')['latest_backtest']
 with zipfile.ZipFile(archive) as z:
  raw=z.read(next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n))
 trades=json.loads(raw)['strategy'][name]['trades']
 digest=lambda rows:hashlib.sha256(json.dumps(rows,sort_keys=True,allow_nan=False).encode()).hexdigest()
 obj={'schema_version':1,'cohort_id':cid,'strategy':name,'primary_trade_count':len(recorded),'replay_trade_count':len(trades),'all_native_trade_fields_identical':trades==recorded,'primary_trades_sha256':digest(recorded),'replay_trades_sha256':digest(trades),'replay_native_json_sha256':hashlib.sha256(raw).hexdigest(),'exit_code':r.returncode,'primary_artifacts_overwritten':False}
 write(out/'native-replay-verification.json',obj)
 print(json.dumps(obj,indent=2))
 if trades!=recorded:raise ValueError('native replay differs; investigate before qualification')
