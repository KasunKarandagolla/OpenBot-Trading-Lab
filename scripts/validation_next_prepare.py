"""Generate frozen V4 logic on new Binance sources; never use Gate dollar results."""
import io,zipfile,copy
import numpy as np
import pandas as pd
from validation_next_common import *
from binance_research_data import convert_funding_frame,convert_kline_frame
from trade_contract import parent_target,audit,economics
from session4_features import hourly,indicators,candidates
from freqtrade.strategy import merge_informative_pair
from diagnosis_prepare import rank,canonical
from policy_features import execution_plan
from targeted_rules import compatible_thesis
VARIANTS=['v4-transfer','passive-transfer','structural-transfer','thesis-compatible-transfer','continuation-only-diagnostic','parent-target']

def convert():
 verify_sources();manifest=read(OUT/'data-manifest.json')
 for pair in pairs():
  rows=[x for x in manifest['source_files'] if x['pair']==pair]
  for kind,tf,ftkind in [('klines','15m','futures'),('klines','1h','futures'),('klines','5m','futures'),('markPriceKlines','1h','mark'),('fundingRate',None,'funding_rate')]:
   frames=[]
   for r in rows:
    if (r['kind'],r['timeframe'])!=(kind,tf):continue
    with zipfile.ZipFile(ROOT/r['path']) as z:source_frame=pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
    standard,research=(convert_funding_frame(source_frame,r) if kind=='fundingRate'
      else convert_kline_frame(source_frame,r,kind=kind,timeframe=tf))
    sidecar=DATA/'binance/research'/(slug(pair)+'-'+(tf or '1h')+'-'+ftkind+'-research.feather')
    sidecar.parent.mkdir(parents=True,exist_ok=True)
    frames.append((standard,research,sidecar))
   target=DATA/'binance/futures'/(slug(pair)+'-'+(tf or '1h')+'-'+ftkind+'.feather')
   target.parent.mkdir(parents=True,exist_ok=True)
   standard=pd.concat([x[0] for x in frames]).sort_values('date').reset_index(drop=True)
   sidecar_rows=pd.concat([x[1] for x in frames]).sort_values('date').reset_index(drop=True)
   standard.to_feather(target)
   sidecar_rows.to_feather(frames[0][2])
 markets=read(ROOT/'research/validation_next/binance-fixture-markets.json');contracts={}
 for pair,m in markets.items():
  contracts[pair]=dict(verified=True,verification_scope='FIXTURE_SCHEMA_ONLY;NOT_HISTORICAL_VENUE',economic_qualified=False,contract_size=m['contractSize'],step_contracts=m['precision']['amount'],min_contracts=m['limits']['amount']['min'],max_contracts=m['limits']['amount']['max'],min_notional=m['limits']['cost']['min'],price_precision=m['precision']['price'],tiers=[],taker=m['taker'],observed_at=now())
 write(OUT/'scenario-contracts.json',contracts)
 write(OUT/'converted-inputs.json',{str(p.relative_to(ROOT)):sha(p) for p in (DATA/'binance').rglob('*.feather')})

def generate(partition):
 verify_old();verify_sources()
 if partition=='holdout' and not (OUT/'holdout-opened.json').exists():raise ValueError('sealed holdout not opened')
 begin,end=spec()['partitions'][partition];a=pd.Timestamp(begin,tz='UTC');b=pd.Timestamp(end,tz='UTC')
 feature_dir=WORK/partition/'features';plans={v:{} for v in VARIANTS};frames={};contracts=read(OUT/'scenario-contracts.json');raw=[]
 for pair in pairs():
  root=DATA/'binance/futures';base=pd.read_feather(root/(slug(pair)+'-15m-futures.feather'));hour=pd.read_feather(root/(slug(pair)+'-1h-futures.feather'))
  # No evaluation features are calculated beyond the authorized block.
  base=base.loc[(base.date>=a-pd.Timedelta(days=11))&(base.date<b)].reset_index(drop=True)
  hour=hour.loc[(hour.date>=a-pd.Timedelta(days=11))&(hour.date<b)].reset_index(drop=True)
  f=indicators(merge_informative_pair(base,hourly(hour),'15m','1h',ffill=True));feature_dir.mkdir(parents=True,exist_ok=True);f.to_pickle(feature_dir/(slug(pair)+'.pkl'))
  frames[pair]=f.set_index('date',drop=False)
  for x in candidates(f,'structure'):
   if a<=pd.Timestamp(x['at'])<b:
    g=x.get('plan');horizon_ok=g is not None and pd.Timestamp(g['expires_at'])+pd.Timedelta(hours=g['max_hold_hours'])<=b
    raw.append(dict(pair=pair,**x,horizon_ok=horizon_ok))
 registry=[]
 def put(v,p,g):plans[v].setdefault(p,{})[g['available_at']]=g
 for x in raw:
  p=x['pair'];g=x.get('plan');item=dict(id='|'.join([p,x['at'],x['recipe'],x['side']]),pair=p,at=x['at'],recipe=x['recipe'],side=x['side'],raw_reason=x['reason'],horizon_ok=x['horizon_ok'],selected=False)
  if g:
   row=frames[p].loc[pd.Timestamp(x['at'])-pd.Timedelta(minutes=15)];rows={k:f.loc[row.date] for k,f in frames.items()};shortlist=rank(rows,x['recipe'],x['side'])
   g=canonical(p,x);item.update(plan=g,liquidity_eligible=bool(row.eligible),shortlist=shortlist,state='TREND' if row.adx_1h>=25 else 'RANGE_OR_TRANSITION',contract=audit(g,contracts[p]['price_precision'],row),features={k:float(row[k]) for k in ['rvol','adx_1h','atr_ratio','return4h','activity'] if np.isfinite(row[k])})
   selected=x['reason']=='TRADE' and x['horizon_ok'] and p in shortlist
   item['selected']=selected
   if selected:
    put('v4-transfer',p,copy.deepcopy(g));put('parent-target',p,parent_target(g,row,contracts[p]['price_precision']))
    if g['recipe']=='continuation':put('continuation-only-diagnostic',p,copy.deepcopy(g))
    passive=copy.deepcopy(g);s=1 if g['side']=='long' else -1;passive['reference']-=s*.15*g['atr_at_signal']
    passive=execution_plan(passive,passive['reference'],pd.Timestamp(g['available_at']))
    if passive:put('passive-transfer',p,passive)
    structural=copy.deepcopy(g)
    # PR13 structural boundary is the previous completed15m session VWAP.
    prior=frames[p].loc[frames[p].index<row.date].iloc[-1]
    if g['recipe']=='continuation':structural['boundary']=float(prior.vwap)
    structural['reference_known_at']=row.date.isoformat();put('structural-transfer',p,copy.deepcopy(structural))
    structural['diagnosis_structural_compatible']=compatible_thesis(structural,contracts[p]['price_precision']);put('thesis-compatible-transfer',p,structural)
  registry.append(item)
 for v,ps in plans.items():write(WORK/partition/'plans'/(v+'.json'),ps)
 write(OUT/('opportunities-'+partition+'.json'),registry)
 seal=dict(at_utc=now(),partition=partition,window=[begin,end],features={str(p.relative_to(ROOT)):sha(p) for p in feature_dir.glob('*.pkl')},plans={v:dict(count=sum(map(len,ps.values())),sha256=sha(WORK/partition/'plans'/(v+'.json'))) for v,ps in plans.items()},registry_sha256=sha(OUT/('opportunities-'+partition+'.json')))
 write(OUT/('plans-'+partition+'.json'),seal);print(partition,len(registry),{v:r['count'] for v,r in seal['plans'].items()},flush=True)
if __name__=='__main__':
 import sys
 if sys.argv[1]=='convert':convert()
 else:generate(sys.argv[1])
