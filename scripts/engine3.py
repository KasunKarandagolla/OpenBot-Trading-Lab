"""Fixed research actions only. No arbitrary engine args, mode, configs or paths."""
import argparse,os
from session3_common import *
def arguments(action,cid,name):
 sanitized_env();stage(); c=cohort(cid)
 cfg=config(cid,name);path=ROOT/'work/session3-configs'/cid/(name+'.json');write(path,cfg)
 args=[action,'--config',str(path),'--datadir',str(datadir(cid))]
 if action in ('detail-coarse','detail-fine'):
  from detail3 import spec,verify_detail,detail_dir
  p=spec();verify_detail()
  if cid!=p['cohort_id'] or name not in p['strategies']:raise ValueError('unregistered detail experiment')
  result=ROOT/'user_data/backtest_results/session-3/detail'/(name+'-'+('fine' if action=='detail-fine' else 'coarse'))
  result.mkdir(parents=True,exist_ok=True)
  args=['backtesting','--config',str(path),'--datadir',str(detail_dir()),'--timerange',p['evaluation_timerange'],'--fee','0.0006','--enable-protections','--cache','none','--export','trades','--backtest-directory',str(result)]
  if action=='detail-fine':args+=['--timeframe-detail','5m']
  return args
 if action=='download-data':
  if any(datadir(cid).rglob('*.feather')):raise ValueError('existing source files must be preserved')
  return args+['--trading-mode','futures','--timeframes','15m','1h','--timerange',c['download_timerange']]
 if action=='list-strategies':return args
 if action not in ('backtesting','lookahead-analysis','recursive-analysis'):raise ValueError('research actions only')
 from data_session3 import verify
 verify(cid)
 args+=['--timerange',c['evaluation_timerange']]
 if action!='recursive-analysis':args+=['--fee','0.0006']
 if action=='backtesting':
  result=ROOT/'user_data/backtest_results/session-3'/cid/name
  result.mkdir(parents=True,exist_ok=True)
  args+=['--enable-protections','--cache','none','--export','trades','--backtest-directory',str(result)]
 elif action=='lookahead-analysis':
  out=destination(cid)/'lookahead.csv'
  if out.exists():raise ValueError('lookahead output exists; preserve before rerun')
  args+=['--minimum-trade-amount','3','--targeted-trade-amount','20','--lookahead-analysis-exportfilename',str(out)]
 else:args+=['--startup-candle','120','240','480']
 return args
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['download-data','backtesting','lookahead-analysis','recursive-analysis','list-strategies','detail-coarse','detail-fine']);p.add_argument('cohort');p.add_argument('strategy',choices=NAMES);a=p.parse_args()
 args=arguments(a.action,a.cohort,a.strategy)
 env=sanitized_env();os.environ.clear();os.environ.update(env)
 from freqtrade.main import main as native
 return native(args)
if __name__=='__main__':raise SystemExit(main())
