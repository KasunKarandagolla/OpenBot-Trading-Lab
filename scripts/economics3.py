"""Deterministic comparison of recorded native exports; no source-data or engine access."""
import csv
from collections import Counter
import numpy as np
import pandas as pd
from session3_common import *
from report import summarize

def weekly(trades,weeks):
 values={k:0. for k in weeks}
 for t in trades:
  at=pd.Timestamp(t['close_date']);key=(at-pd.Timedelta(days=at.weekday())).strftime('%Y-%m-%d')
  if key in values:values[key]+=t['profit_abs']
 return np.array(list(values.values()),dtype=float)

def blocked_interval(values):
 if len(values)<4:return None
 rng=np.random.default_rng(3103)
 # Weeks are resampled jointly across correlated markets; calendar zeros included.
 sums=values[rng.integers(0,len(values),size=(2000,len(values)))].sum(axis=1)
 return {'low_usdt':float(np.quantile(sums,.025)),'high_usdt':float(np.quantile(sums,.975)),'weeks':len(values),'draws':2000,'seed':3103,'method':'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}

def metric(trades,result,tags,weeks):
 m=summarize(trades);net=sum(t['profit_abs'] for t in trades)
 fees=sum(t['amount']*(t['open_rate']*t['fee_open']+t['close_rate']*t['fee_close']) for t in trades)
 funding=sum(t.get('funding_fees',0) or 0 for t in trades)
 gross=sum(t['amount']*(t['close_rate']-t['open_rate'])*(-1 if t['is_short'] else 1) for t in trades)
 turnover=sum(t['amount']*(t['open_rate']+t['close_rate']) for t in trades)
 exposure=sum(t['stake_amount']*t['trade_duration']/60 for t in trades)
 ordered=sorted(trades,key=lambda t:(t['close_date'],t['pair']))
 streak=maximum=0
 for t in ordered:
  streak=streak+1 if t['profit_abs']<0 else 0;maximum=max(maximum,streak)
 m.update(net_usdt=net,fees_usdt=fees,funding_signed_usdt=funding,gross_price_pnl_usdt=gross,reconciliation_residual_usdt=net-(gross-fees+funding),turnover_usdt=turnover,exposure_notional_hours=exposure,net_per_notional_hour=net/exposure if exposure>0 else None,break_even_extra_bps_per_side=net/turnover*10000 if turnover else None,max_drawdown_usdt=result.get('max_drawdown_abs'),max_drawdown_account=result.get('max_drawdown_account'),longest_loss_streak=maximum,native_rejected_signals=result.get('rejected_signals'),native_canceled_entry_orders=result.get('canceled_entry_orders'),native_timedout_entry_orders=result.get('timedout_entry_orders'))
 m['directions']={s:{'trades':len([t for t in trades if t['is_short']==short]),'net_usdt':sum(t['profit_abs'] for t in trades if t['is_short']==short)} for s,short in [('long',False),('short',True)]}
 m['friction']=[]
 for bp in [0,5,10,20]:
  profits=[t['profit_abs']-t['amount']*(t['open_rate']+t['close_rate'])*bp/10000 for t in ordered]
  equity=np.r_[0.,np.cumsum(profits)];dd=float((np.maximum.accumulate(equity)-equity).max())
  m['friction'].append({'extra_bps_per_side':bp,'net_usdt':sum(profits),'closed_equity_drawdown_usdt':dd,'fills_changed':False})
 m['net_without_top3_usdt']=net-sum(sorted([t['profit_abs'] for t in trades],reverse=True)[:3])
 forced=[t for t in trades if t['exit_reason']=='force_exit']
 m['forced_end_exits']={'trades':len(forced),'net_usdt':sum(t['profit_abs'] for t in forced),'net_excluding_forced_usdt':net-sum(t['profit_abs'] for t in forced)}
 m['regimes']={key:{'trades':sum(t['regime']==key for t in tags),'net_usdt':sum(t['profit_abs'] for t in tags if t['regime']==key)} for key in sorted({t['regime'] for t in tags})}
 risk=[t['net_R'] for t in tags if t.get('net_R') is not None]
 m['net_R_quantiles']={str(q):float(np.quantile(risk,q)) for q in [0,.25,.5,.75,1]} if risk else None
 m['weekly_block_net_interval']=blocked_interval(weekly(trades,weeks))
 ci=m['weekly_block_net_interval']
 m['evidence_classification']=('REJECTED UNDER TESTED ASSUMPTIONS' if net<=0 and trades else 'INSUFFICIENT EVIDENCE' if not ci or ci['low_usdt']<=0 or m['trading_days']<10 else 'UNQUALIFIED DEVELOPMENT RESULT')
 m['decision']='NO_PROMOTION'
 return m

def compare(cid):
 c=cohort(cid);out=destination(cid);records={};raw={};provenance={}
 start=pd.to_datetime(c['evaluation_timerange'].split('-')[0],format='%Y%m%d',utc=True);end=pd.to_datetime(c['evaluation_timerange'].split('-')[1],format='%Y%m%d',utc=True)
 first=(start-pd.Timedelta(days=start.weekday())).normalize();weeks=pd.date_range(first,end-pd.Timedelta(seconds=1),freq='7D').strftime('%Y-%m-%d').tolist()
 for name in NAMES:
  p=out/'native-results'/(name+'.json');prov=read(out/'native-results'/(name+'-provenance.json'))
  if sha(p)!=prov['native_result_sha256']:raise ValueError('recorded result hash mismatch')
  if sha(ROOT/'research/cohorts'/(cid+'.json'))!=prov['cohort_sha256']:raise ValueError('cohort definition changed since recorded run')
  result=read(p)['strategy'][name];trades=result['trades'];raw[name]=trades
  tags=read(out/'trade-ledgers'/(name+'-tags.json'))
  if sha(out/'trade-ledgers'/(name+'-tags.json'))!=prov['tags_sha256']:raise ValueError('causal tags changed')
  records[name]=metric(trades,result,tags,weeks);provenance[name]=prov
 parent=records['LiquiditySweepReversalV1'];new=records['StructureAwareSweepV1']
 delta=weekly(raw['StructureAwareSweepV1'],weeks)-weekly(raw['LiquiditySweepReversalV1'],weeks)
 obj={'schema_version':1,'environment':'RESEARCH_ONLY','cohort_id':cid,'cohort_classification':c['classification'],'evaluation_timerange':c['evaluation_timerange'],'pairs':c['pairs'],'source':'recorded native Freqtrade2026.10 results and causal entry tags','strategies':records,'provenance':provenance,'parent_challenger':{'net_delta_usdt':new['net_usdt']-parent['net_usdt'],'paired_weekly_delta_interval':blocked_interval(delta),'exposure_aware_comparison':{n:records[n]['net_per_notional_hour'] for n in ['LiquiditySweepReversalV1','StructureAwareSweepV1','SweepThinningControlV1']},'control_interpretation':'Predeclared deterministic half-thinning control, same parent/risk/cost/window. Exposure-normalized, not count-matched; differing exits and capacity mean no causal alpha estimate.'},'costs':{'native_fee_per_side':.0006,'funding':'actual validated Gate observations included natively; signed once','extra_friction':'5/10/20bps each turnover side; posthoc, no refills','account_drawdown':'native mark/candle model; friction closed-equity drawdown is separate'},'limitations':['Inspected DEVELOPMENT or shared-calendar TRANSFER, no untouched holdout.','Calendar week resampling assumes exchangeable weeks; few dependent blocks, no statistical qualification.','15m requested-price fills, no queue/partial fills/historical spreads.','UTC realized-loss halt excludes unrealized losses; full account daily halt NOT ENFORCED.','Prospective evidence requires code/data freezes before outcomes; no automatic promotion.']}
 write(out/'economic-comparison.json',obj)
 report='# Session3 economic comparison — '+c['classification']+'\n\n'+c['evaluation_timerange']+' UTC, end exclusive. Native fee0.06% per side, actual funding, wallet1000, stake<=25,1x,max2.\n\n'
 report+='| Strategy | Trades | Net USDT | PF | DD USDT | Fees | Funding | +5bp | +10bp | +20bp | Status |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|\n'
 for n,m in records.items():
  pf='undefined' if m['profit_factor'] is None else f"{m['profit_factor']:.4f}"
  report+=f"|{n}|{m['trades']}|{m['net_usdt']:.6f}|{pf}|{m['max_drawdown_usdt'] or 0:.6f}|{m['fees_usdt']:.6f}|{m['funding_signed_usdt']:.6f}|{m['friction'][1]['net_usdt']:.6f}|{m['friction'][2]['net_usdt']:.6f}|{m['friction'][3]['net_usdt']:.6f}|{m['evidence_classification']}|\n"
 report+='\nParent/challenger net delta: '+str(obj['parent_challenger'])+'\n'
 for n,m in records.items():
  report+=f"\n## {n}\n\nExpectancy {m['expectancy_usdt']}; distinct active days {m['trading_days']}; loss streak {m['longest_loss_streak']}; exposure {m['exposure_notional_hours']:.6f} USDT-hours; turnover {m['turnover_usdt']:.6f}; break-even extra bps/side {m['break_even_extra_bps_per_side']}; net excluding best3 {m['net_without_top3_usdt']:.6f}.\n\nPairs {m.get('per_pair_usdt',{})}; directions {m['directions']}; causal hourly regimes {m['regimes']}; hold-minute quantiles {m['hold_minutes']}; net R {m['net_R_quantiles']}; forced-end exits {m['forced_end_exits']}.\n\nWeekly block interval {m['weekly_block_net_interval']}. Gross {m['gross_price_pnl_usdt']:.8f} minus fees plus funding reconciles to net with residual {m['reconciliation_residual_usdt']:.10f}.\n"
 report+='\n'+ '\n'.join('- '+x for x in obj['limitations'])+'\n'
 (out/'economic-report.md').write_text(report)
 return obj
