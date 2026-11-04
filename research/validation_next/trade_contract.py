"""Immutable pre-entry geometry and one preregistered target hypothesis."""
import copy,math
import pandas as pd
COST=.0038

def economics(g):
 s=1 if g['side']=='long' else -1;e=float(g['reference'])
 risk=s*(e-g['stop'])/e;reward=s*(g['target']-e)/e
 return dict(risk_fraction=risk,reward_fraction=reward,modeled_loss_per_notional=risk+COST,after_cost_rr=(reward-COST)/(risk+COST))

def parent_target(g,row,tick):
 out=copy.deepcopy(g);s=1 if g['side']=='long' else -1;e=g['reference'];risk=s*(e-g['stop']);c=[]
 for period in ['day','session']:
  key='prior_'+period+('_high' if s==1 else '_low');p=row.get(key)
  if p is None or not math.isfinite(float(p)):continue
  known=pd.Timestamp(row.date).floor('D' if period=='day' else '8h')
  reward=s*(float(p)-e)
  if known>pd.Timestamp(g['available_at']) or not 2*risk<=reward<=3*risk or reward>6*g['atr_at_signal']:continue
  candidate=copy.deepcopy(g);candidate['target']=float(p);q=economics(candidate)
  if q['after_cost_rr']<1.25:continue
  if any(abs(float(p)-x['price'])<tick/2 for x in c):continue
  c.append(dict(price=float(p),source=key,known_at=known.isoformat(),timeframe='1d' if period=='day' else '8h',age_seconds=(pd.Timestamp(g['available_at'])-known).total_seconds()))
 if c:
  objective=min(c,key=lambda x:s*(x['price']-e));out.update(target=objective['price'],target_origin=objective['source'],objective_evidence=objective)
 out.update(economics(out));return out

def audit(g,tick,row=None,management='v4-fast'):
 s=1 if g['side']=='long' else -1;q=economics(g);errors=[]
 if q['risk_fraction']<.003-1e-12 or q['risk_fraction']>.025+1e-12:errors.append('STOP_RISK_BOUNDS')
 if q['reward_fraction']<=0:errors.append('TARGET_WRONG_SIDE')
 if q['after_cost_rr']<1.25-1e-12:errors.append('NET_RR')
 if s*(g['reference']-g['stop'])<=0:errors.append('STOP_WRONG_SIDE')
 if pd.Timestamp(g['expires_at'])<=pd.Timestamp(g['available_at']):errors.append('EXPIRY')
 if s*(g['target']-g['reference'])>6*g['atr_at_signal']+tick:errors.append('TARGET_HORIZON')
 if row is not None:
  if pd.Timestamp(row.date)+pd.Timedelta(minutes=15)>pd.Timestamp(g['available_at']):errors.append('UNCOMPLETED_SIGNAL')
  if pd.Timestamp(row.date_1h)+pd.Timedelta(hours=1)>pd.Timestamp(g['available_at']):errors.append('UNCOMPLETED_HOUR')
 ob=g.get('objective_evidence')
 if ob and pd.Timestamp(ob['known_at'])>pd.Timestamp(g['available_at']):errors.append('FUTURE_OBJECTIVE')
 # Repriced inherited plans can carry stale after_cost_rr. Recompute; never debit allowance twice.
 stored=g.get('after_cost_rr');stale=stored is not None and abs(stored-q['after_cost_rr'])>1e-9
 levels=[]
 for x in g.get('obstacles',[]):
  same=next((z for z in levels if abs(z['price']-x['price'])<tick/2),None)
  if same:same['sources'].append(x['source'])
  else:levels.append(dict(price=x['price'],sources=[x['source']],fidelity=x['fidelity']))
 first=min([x for x in levels if s*(x['price']-g['reference'])>0],key=lambda x:s*(x['price']-g['reference']),default=None)
 boundary=g.get('boundary');failure=None
 if g['recipe']=='continuation' and boundary is not None and math.isfinite(float(boundary)):failure=float(boundary)-s*.15*g['atr_at_signal']
 before_stop=failure is not None and s*(failure-g['stop'])>tick
 fast=management=='v4-fast' or (management=='compatible' and not g.get('diagnosis_structural_compatible',False))
 return dict(errors=errors,economics=q,stored_economics_stale=stale,first_barrier=first,distinct_levels=levels,barrier_authority='CAUTION_ONLY;NOT_TARGET_OR_AUTOMATIC_VETO',hard_stop_independent=True,fast_exit_retained=fast,management_authority=management,structural_failure_line=failure,structural_invalidation_before_stop=before_stop,warning='STRUCTURAL_FAILURE_BEYOND_PROTECTIVE_STOP' if management=='structural' and not before_stop and g['recipe']=='continuation' else None)
