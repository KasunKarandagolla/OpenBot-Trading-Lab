"""Independent order/cash reconciliation and opportunity-level descriptive economics."""
from collections import Counter,defaultdict
import math,statistics
import numpy as np
import pandas as pd
from validation_next_common import *
from trade_contract import audit

def strategy(result):return next(iter(result['strategy'].values()))
def source_clock(x):return pd.Timestamp(x)
def key(t):return (t['pair'],pd.Timestamp(t['open_date']).isoformat())
def auc(rows,feature):
 pos=[r['features'][feature] for r in rows if r.get('net',0)>0 and feature in r.get('features',{})];neg=[r['features'][feature] for r in rows if r.get('net',0)<=0 and feature in r.get('features',{})]
 return dict(fills=len(pos)+len(neg),winners=len(pos),auc=float(np.mean([float(a>b)+.5*(a==b) for a in pos for b in neg])) if pos and neg else None)

def summarize(path):
 prov=read(path/'provenance.json');part=prov['partition'];variant=prov['variant'];s=strategy(read(path/'result.json'));trades=s['trades'];states=read(path/'states.json');oa=read(path/'order-audit.json');raw=read(OUT/('opportunities-'+part+'.json'));plans=read(WORK/part/'plans'/(variant+'.json'));contracts=read(OUT/'scenario-contracts.json')
 states_by={(x['pair'],pd.Timestamp(x['open_date']).isoformat()):x for x in states};bytrade={};cash=[];failures=[];amounts=[];all_events=[];ledger=[]
 for t in trades:
  st=states_by[key(t)];g=st['plan'];sign=-1 if t['is_short'] else 1;q=t['amount'];entry=t['open_rate'];exit=t['close_rate'];fees=q*(entry*t['fee_open']+exit*t['fee_close']);gross=sign*q*(exit-entry);funding=float(t.get('funding_fees',0));expected=gross-fees+funding
  funding_independent=sum((1 if t['is_short'] else -1)*x['quantity']*x['mark']*x['rate'] for x in st['funding'])
  if abs(expected-t['profit_abs'])>2e-7:failures.append(dict(type='CASH',key=key(t),expected=expected,native=t['profit_abs']))
  if abs(funding-funding_independent)>2e-8:failures.append(dict(type='FUNDING',key=key(t),expected=funding_independent,native=funding))
  # Independent source-event coverage, not merely summing the engine's own event ledger.
  source=pd.read_feather(DATA/'binance/futures'/(slug(t['pair'])+'-1h-funding_rate.feather'))
  first=pd.Timestamp(st['state'].get('first_fill',t['open_timestamp']/1000),unit='s',tz='UTC');last=pd.Timestamp(t['close_date'])
  expected_events=source.loc[(source.date>=first)&(source.date<=last)]
  if list(expected_events.date.map(lambda x:x.isoformat()))!=[x['at'] for x in st['funding']]:failures.append(dict(type='FUNDING_EVENT_COVERAGE',key=key(t),expected=expected_events.date.astype(str).tolist(),actual=[x['at'] for x in st['funding']]))
  step=contracts[t['pair']]['step_contracts']*contracts[t['pair']]['contract_size']
  if q*entry>25+1e-8 or abs(q/step-round(q/step))>1e-6 or t['leverage']!=1:failures.append(dict(type='LEGALITY',key=key(t)))
  price_risk=q*abs(entry-g['stop']);cost_risk=price_risk+q*(entry*t['fee_open']+g['stop']*t['fee_close'])
  detail=pd.read_feather(DATA/'binance/futures'/(slug(t['pair'])+'-5m-futures.feather'));closed=detail.loc[(detail.date>first)&(detail.date+pd.Timedelta(minutes=5)<=last)]
  mfe=max(0,((closed.high.max()-entry) if sign==1 else (entry-closed.low.min()))/entry) if len(closed) else None
  mae=min(0,((closed.low.min()-entry) if sign==1 else (entry-closed.high.max()))/entry) if len(closed) else None
  record=dict(pair=t['pair'],decision_id=g['decision_id'],entry_at=first.isoformat(),exit_at=last.isoformat(),entry_price=entry,exit_price=exit,quantity=q,gross=gross,fees=fees,funding=funding,net=t['profit_abs'],reconciled_net=expected,original_price_risk=price_risk,net_R_price=t['profit_abs']/price_risk if price_risk else None,net_R_cost=t['profit_abs']/cost_risk if cost_risk else None,recipe=g['recipe'],exit_reason=t['exit_reason'],turnover=q*(entry+exit),held_minutes=(last-first).total_seconds()/60,mfe_completed_nonentry_bars=mfe,mae_completed_nonentry_bars=mae,mae_mfe_timing='Exclude entry5m bar and bars not fully closed before exit label; descriptive inaccessible extrema',plan=g)
  cash.append(record);bytrade[g['decision_id']]=record
 orders=oa['orders'];entries=[o for o in orders if o['is_entry']];orders_by={o['decision_id']:o for o in entries if o['decision_id']};terminal_by={x['trade_id']:x for x in oa['terminal_events']}
 for r in raw:
  p=r['pair'];g=plans.get(p,{}).get(r['at']);original=r.get('plan');o=orders_by.get(g['decision_id']) if g else None;t=bytrade.get(g['decision_id']) if g else None;reason=r['raw_reason'];status='NO_TRADE'
  if reason=='TRADE' and not r['horizon_ok']:reason='PURGED_MAX_HOLD_AT_BLOCK_END'
  elif reason=='TRADE' and not r['selected']:reason='LIQUIDITY_OR_FROZEN_SHORTLIST'
  elif r['selected'] and g is None:reason='POLICY_PLAYBOOK_OR_GEOMETRY_REJECT'
  elif g and not o:
   status='ORDER_NOT_SUBMITTED';vs=[x.get('verdict') for x in oa['observations'] if x['event']=='RISK' and x['pair']==p and x['at']==r['at']]
   reason=next((v['reason'] for v in vs if isinstance(v,dict) and v.get('status')=='REJECT'),'NATIVE_CAPACITY_EXISTING_PAIR_LOCK_OR_SIGNAL_CONFLICT')
  elif o and not o['filled']:status='ORDER_EXPIRED' if o['trade_id'] in terminal_by else 'ORDER_UNFILLED_UNRESOLVED';reason='NATIVE_REMOVAL' if status=='ORDER_EXPIRED' else 'NO_TERMINAL_OBSERVATION'
  elif t:status='FILLED';reason=t['exit_reason']
  elif o:status='FILLED_WITHOUT_RECONCILED_TRADE';reason='ERROR';failures.append(dict(type='MISSING_TRADE',candidate=r['id']))
  exit_status=None
  if t:exit_status='STOP' if 'stop' in reason or 'protective' in reason else 'ROI' if reason in ['roi','frozen_target'] else 'TIMEOUT' if 'max_hold' in reason or reason=='force_exit' else 'THESIS_EXIT'
  ledger.append(dict(candidate_id=r['id'],pair=p,at=r['at'],recipe=r['recipe'],state=r.get('state','UNQUALIFIED'),features=r.get('features',{}),selected_original=bool(r['selected']),policy_plan=bool(g),status=status,reason=reason,exit_status=exit_status,net=t['net'] if t else 0.,order=o,terminal=terminal_by.get(o['trade_id']) if o else None,trade=t,contract=audit(g,contracts[p]['price_precision'],management='structural' if variant=='structural-transfer' else 'compatible' if variant=='thesis-compatible-transfer' else 'v4-fast') if g else r.get('contract')))
 # Reserves are half-open [order creation, expiry/position close), releases precede new reservations at ties.
 for o in entries:
  t=bytrade.get(o['decision_id']);end=pd.Timestamp(t['exit_at']) if t else pd.Timestamp(terminal_by[o['trade_id']]['terminal_at']) if o['trade_id'] in terminal_by else None
  if end is not None:all_events.extend([(pd.Timestamp(o['created_at']),1,o['price']*o['amount']),(end,-1,-o['price']*o['amount'])])
 peak=peak_n=running=n=0
 for at,d,amount in sorted(all_events,key=lambda x:(x[0],x[1])):running+=amount;n+=d;peak=max(peak,running);peak_n=max(peak_n,n)
 pnls=[t['net'] for t in cash];total=sum(pnls);wins=sum(x>0 for x in pnls);positive=sum(x for x in pnls if x>0);negative=-sum(x for x in pnls if x<0);streak=worst=0
 for t in sorted(cash,key=lambda x:x['exit_at']):streak=streak+1 if t['net']<0 else 0;worst=max(worst,streak)
 days=pd.date_range(*[pd.Timestamp(x,tz='UTC') for x in spec()['partitions'][part]],freq='D',inclusive='left');daily=pd.Series(0.,index=days)
 for t in cash:daily.loc[pd.Timestamp(t['exit_at']).floor('D')]+=t['net']
 blocks=[float(daily.iloc[i:i+7].sum()) for i in range(0,len(daily),7)];rng=np.random.default_rng(20261104);draws=rng.choice(blocks,size=(10000,len(blocks))).sum(axis=1) if blocks else np.array([0.]);ci=np.quantile(draws,[.025,.975]).tolist()
 weekly={str(days[i].date()):float(daily.iloc[i:i+7].sum()) for i in range(0,len(daily),7)}
 groups={}
 for field in ['pair','recipe','exit_reason']:
  groups[field]={k:dict(fills=sum(t[field]==k for t in cash),net=sum(t['net'] for t in cash if t[field]==k)) for k in sorted({t[field] for t in cash})}
 states={k:dict(fills=sum(r['status']=='FILLED' and r['state']==k for r in ledger),net=sum(r['net'] for r in ledger if r['state']==k)) for k in sorted({r['state'] for r in ledger})}
 largest=sorted([x for x in pnls if x>0],reverse=True);turnover=sum(t['turnover'] for t in cash);selected=sum(r['selected'] for r in raw);filled=len(cash)
 summary=dict(method=variant,venue='Binance UM offline fixture scenario',partition=part,window=spec()['partitions'][part],original_candidates=len(raw),original_selected_plans=selected,plans=sum(map(len,plans.values())),orders=len(entries),fills=filled,missed_orders=sum(not o['filled'] for o in entries),not_submitted=sum(r['status']=='ORDER_NOT_SUBMITTED' for r in ledger),net_usdt=total,net_per_original_candidate=total/len(raw) if raw else None,median_net_per_original_candidate=float(np.median([r['net'] for r in ledger])) if raw else None,net_per_selected_original_plan=total/selected if selected else None,mean_net_per_fill=total/filled if filled else None,median_net_per_fill=float(np.median(pnls)) if filled else None,median_net_R_cost=float(np.median([x['net_R_cost'] for x in cash])) if filled else None,mean_net_R_cost=float(np.mean([x['net_R_cost'] for x in cash])) if filled else None,win_percent=100*wins/filled if filled else None,profit_factor=positive/negative if negative else None,average_winner=positive/wins if wins else None,average_loss=-negative/(filled-wins) if filled>wins else None,worst_loss_streak=worst,drawdown_native_usdt=s.get('max_drawdown_abs'),largest_winner_dependence={str(n):total-sum(largest[:n]) for n in [1,3,5]},tail_interpretation='Arithmetic remove winners; not native capacity replay',turnover=turnover,extra_cost_results={str(bp):total-turnover*bp/10000 for bp in [5,10,20]},extra_cost_interpretation='Turnover sensitivity on fixed fills, no spread/queue model',week_pnl=weekly,positive_weeks=sum(x>0 for x in weekly.values()),negative_weeks=sum(x<0 for x in weekly.values()),zero_weeks=sum(x==0 for x in weekly.values()),weekly_block_interval_total_usdt=ci,weekly_block_interval_per_original_candidate=[v/len(raw) for v in ci] if raw else None,uncertainty='Descriptive7day all-pair cluster bootstrap including zero days; few blocks, not significance or durable-edge proof',peak_reserved_notional=peak,peak_reserved_positions=peak_n,return_on_peak_reserved_notional=total/peak if peak else None,wallet_peak_usage_percent=peak/10,groups=groups,states=states,status_counts=dict(Counter(r['status'] for r in ledger)),fee_per_side=prov['fee_per_side'],funding=sum(t['funding'] for t in cash),fees=sum(t['fees'] for t in cash),gross=sum(t['gross'] for t in cash),detail_5m=prov['detail_5m'],trade_through=prov['trade_through'],native_hash=sha(path/'result.json'),validation_status='PARTIAL_COST_MODEL / INSUFFICIENT_ECONOMIC_VALIDATION',reconciliation_failures=failures)
 return summary,cash,ledger

def run():
 portfolios={};ledgers={};cashbook={}
 for path in sorted((OUT/'native').glob('*/result.json')):
  if read(path.parent/'provenance.json').get('funding_clock')!='EXACT_ARCHIVE_MILLISECONDS':continue
  label=path.parent.name;s,c,l=summarize(path.parent);portfolios[label]=s;cashbook[label]=c;ledgers[label]=l
 write(OUT/'portfolio-economics.json',dict(at=now(),portfolios=portfolios,reconciliation_failures=sum(len(x['reconciliation_failures']) for x in portfolios.values()),r_definitions='NetR_price = net cash/(actual quantity * distance actual entry to original plan stop). NetR_cost adds entry fee and hypothetical stop-exit fee to denominator. Actual funding is only in numerator;38bp allowance is not debited as cash. Negative and zero/no-fill candidate outcomes remain distinct.',scenario_status='UNQUALIFIED'))
 write(OUT/'trade-cash-ledger.json',cashbook)
 write(OUT/'opportunity-lifecycle-ledger.json',ledgers)
 comparisons={};quality={};contracts={}
 for part in spec()['partitions']:
  label=lambda v:part+'-'+v+'-detail5m-touch-fee500-exactclock'
  if label('v4-transfer') not in portfolios:continue
  control={t['decision_id']:t for t in cashbook[label('v4-transfer')]};comps={}
  for v in ['passive-transfer','structural-transfer','thesis-compatible-transfer','parent-target','continuation-only-diagnostic']:
   if label(v) not in cashbook:continue
   alt={t['decision_id']:t for t in cashbook[label(v)]};shared=set(control)&set(alt);missing=set(control)-set(alt);extra=set(alt)-set(control)
   comps[v]=dict(shared_fills=len(shared),matched_net_delta=sum(alt[k]['net']-control[k]['net'] for k in shared),missing_v4_fills=[control[k] for k in sorted(missing)],missing_v4_net=sum(control[k]['net'] for k in missing),extra_fills=[alt[k] for k in sorted(extra)],all_shared=[dict(decision_id=k,entry_improvement=(1 if control[k]['plan']['side']=='long' else -1)*(control[k]['entry_price']-alt[k]['entry_price']),net_delta=alt[k]['net']-control[k]['net'],exit_changed=control[k]['exit_price']!=alt[k]['exit_price'],original=control[k],alternative=alt[k]) for k in sorted(shared)])
  comparisons[part]=comps;quality[part]={f:auc([r for r in ledgers[label('v4-transfer')] if r['status']=='FILLED'],f) for f in ['rvol','adx_1h','atr_ratio','return4h','activity']}
  raw=read(OUT/('opportunities-'+part+'.json'));contracts[part]=dict(raw_candidates=len(raw),raw_reasons=dict(Counter(r['raw_reason'] for r in raw)),selected=sum(r['selected'] for r in raw),contract_errors=[dict(id=r['id'],errors=r['contract']['errors']) for r in raw if r.get('contract',{}).get('errors')],passive_stale_stored_rr=sum((r.get('contract') or {}).get('stored_economics_stale',False) for r in ledgers[label('passive-transfer')]),target_changes=sum(g['target']!=read(WORK/part/'plans/parent-target.json')[p][at]['target'] for p,rs in read(WORK/part/'plans/v4-transfer.json').items() for at,g in rs.items()))
 write(OUT/'matched-trade-differences.json',comparisons);write(OUT/'chronological-feature-separability.json',dict(results=quality,interpretation='DESCRIPTIVE_ONLY; fixed natural feature direction, no fitted selector or threshold; filled-cohort AUC cannot score rejected opportunities'))
 write(OUT/'trade-contract-audit.json',contracts)
 ambiguities={}
 for label,s in portfolios.items():
  ambiguities[label]=dict(detail_5m=s['detail_5m'],native_timeout_minutes=5,terminal_ages=dict(Counter(str(x['age_minutes']) for x in read(OUT/'native'/label/'order-audit.json')['terminal_events'])),queue='UNKNOWN; range-touch or one-tick-through scenario, no queue/fill probability inference',intrabar='5m bar order unresolved; native stop-beforeROI conventions retained',funding='Real events and preceding hourly OPEN; exact settlement mark unknown',historical_metadata='UNKNOWN; source fixture only')
 write(OUT/'execution-ambiguities.json',ambiguities)
 primary=[(label,s) for label,s in portfolios.items() if s['detail_5m'] and not s['trade_through'] and s['fee_per_side']==.0005]
 cols=['Method','Venue','Window','Original candidates','Plans','Orders','Fills','Missed','Net USDT','Net/original candidate','Median net R','Win %','PF','Largest-winner dependence','Worst losing streak','Drawdown','Extra-cost result','Validation status']
 lines=['| '+' | '.join(cols)+' |','|'+'|'.join(['---']*len(cols))+'|']
 fmt=lambda v: 'N/A' if v is None else f'{v:.6f}'
 for label,s in primary:
  lines.append('| '+' | '.join([s['method'],'Binance scenario',s['partition']+' '+('/'.join(s['window'])),str(s['original_candidates']),str(s['plans']),str(s['orders']),str(s['fills']),str(s['missed_orders']),fmt(s['net_usdt']),fmt(s['net_per_original_candidate']),fmt(s['median_net_R_cost']),fmt(s['win_percent']),fmt(s['profit_factor']),'net ex top3 '+fmt(s['largest_winner_dependence']['3']),str(s['worst_loss_streak']),fmt(s['drawdown_native_usdt']),'extra10bp '+fmt(s['extra_cost_results']['10']),'PARTIAL / INSUFFICIENT'])+' |')
 for part,c in contracts.items():lines.append('| '+' | '.join(['No trade','Binance scenario',part,str(c['raw_candidates']),'0','0','0','0','0','0','N/A','N/A','N/A','N/A','0','0','0','NO_EXPOSURE_CONTROL'])+' |')
 (OUT/'comparison-table.md').write_text('\n'.join(lines)+'\n')
 print('portfolios',len(portfolios),'overlapping trade records',sum(s['fills'] for s in portfolios.values()),'reconciliation errors',sum(len(s['reconciliation_failures']) for s in portfolios.values()),flush=True)
 if any(s['reconciliation_failures'] for s in portfolios.values()):raise SystemExit(1)
if __name__=='__main__':run()
