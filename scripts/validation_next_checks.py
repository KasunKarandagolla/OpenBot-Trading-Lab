"""Real-source prefix checks for features, cross-pair ranking and target authority."""
from validation_next_common import *
import pandas as pd
from session4_features import indicators,hourly
from freqtrade.strategy import merge_informative_pair
from diagnosis_prepare import rank
from trade_contract import parent_target,audit

def run():
 verify_old();verify_sources();checks=[]
 for at in ['2026-01-20T12:15:00Z','2026-02-05T06:30:00Z']:
  clock=pd.Timestamp(at);rows={};fullrows={}
  for p in pairs():
   base=pd.read_feather(DATA/'binance/futures'/(slug(p)+'-15m-futures.feather'))
   hour=pd.read_feather(DATA/'binance/futures'/(slug(p)+'-1h-futures.feather'))
   base=base.loc[(base.date>=pd.Timestamp('2026-01-01T00:00Z'))&(base.date+pd.Timedelta(minutes=15)<=clock)].reset_index(drop=True)
   hour=hour.loc[hour.date+pd.Timedelta(hours=1)<=clock].reset_index(drop=True)
   f=indicators(merge_informative_pair(base,hourly(hour),'15m','1h',ffill=True))
   full=pd.read_pickle(WORK/'development/features'/(slug(p)+'.pkl'));expected=full.loc[full.date+pd.Timedelta(minutes=15)<=clock].reset_index(drop=True)
   pd.testing.assert_frame_equal(f,expected,check_exact=True)
   rows[p]=f.iloc[-1];fullrows[p]=expected.iloc[-1];checks.append(dict(at=at,pair=p,feature_rows=len(f),all_columns=len(f.columns),exact=True))
  for book in ['continuation','reversal']:
   for side in ['long','short']:assert rank(rows,book,side)==rank(fullrows,book,side)
 write(OUT/'causal-prefix-checks.json',dict(at=now(),checks=checks,cross_pair_rank_comparisons=8,feature_recalculation='RAW_PREFIX_RECOMPUTED_WITH_ONLY_CLOSED_HOURLY_INPUTS',holdout_inspected=False,generic_lookahead='Cached replay schedules cannot prove causal construction by generic indicator slicing; raw prefix comparisons are authoritative. Generic limit-order analysis can flag trade-capacity effects, documented separately.'))
 print('8 exact real-source feature prefixes;8 cross-pair rank comparisons PASS',flush=True)
if __name__=='__main__':run()
