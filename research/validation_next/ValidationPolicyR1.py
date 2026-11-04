"""Native historical scenario only. Never an activation-qualified Binance policy."""
from DiagnosisPolicyR1 import DiagnosisPolicyR1

class ValidationPolicyR1(DiagnosisPolicyR1):
 def version(self):return 'fresh-market-validation-r1.0.0-unqualified-fixture'
 def bot_start(self,**kwargs):
  if self.config.get('validation_fixture_scenario') is not True:raise ValueError('unqualified fixture scenario must be explicit')
  if self.config.get('exchange',{}).get('name')!='binance':raise ValueError('Binance-only scenario')
  if float(self.config.get('policy_leverage',0))!=1:raise ValueError('1x only')
  super().bot_start(**kwargs)
 def populate_indicators(self,d,metadata):
  from pathlib import Path
  import pandas as pd
  pair=metadata['pair'];f=pd.read_pickle(Path(self.config['session4_features'])/(pair.replace('/','_').replace(':','_')+'.pkl'))
  # Native loader may retain the end-exclusive boundary row for validation.
  # Preserve its actual OHLCV; unavailable cached features remain NaN, with no plan.
  raw=['date','open','high','low','close','volume']
  return d[raw].merge(f.drop(columns=[k for k in raw if k!='date']),on='date',how='left',validate='one_to_one').set_axis(d.index)
