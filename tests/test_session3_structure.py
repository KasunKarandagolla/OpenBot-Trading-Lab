"""Independent state-machine vectors and streaming/native-hour causality."""
from pathlib import Path
import sys,unittest
import numpy as np
import pandas as pd
sys.path[:0]=['/lab/scripts','/lab/research/session3','/lab/user_data/strategies']
from causal_structure import structure,closed_merge
from freqtrade.strategy import merge_informative_pair

def bars(highs,lows=None,closes=None):
 h=np.array(highs,dtype=float);l=np.array(lows if lows is not None else h-3,dtype=float);c=np.array(closes if closes is not None else (h+l)/2,dtype=float)
 return pd.DataFrame({'date':pd.date_range('2026-01-01',periods=len(h),freq='15min',tz='UTC'),'open':c,'high':h,'low':l,'close':c,'volume':10.})

class Structure(unittest.TestCase):
 def test_exact_right_confirmation_and_ties(self):
  d=bars([11,12,16,13,12,11,12]);r=structure(d)
  self.assertTrue(pd.isna(r.swing_high.iloc[3]));self.assertEqual(r.swing_high.iloc[4],16.)
  self.assertEqual(r.swing_high_pivot_at.iloc[4],d.date.iloc[2]);self.assertEqual(r.swing_high_known_at.iloc[4],d.date.iloc[4]+pd.Timedelta(minutes=15))
  self.assertEqual(r.struct_pivot_event.iloc[4]['first_eligible_decision_at'],r.swing_high_known_at.iloc[4])
  d=bars([11,12,16,16,12,11,12]);self.assertTrue(structure(d).swing_high.isna().all())
 def test_unknown_initial_bos_choch_wick_and_level_invalidation(self):
  d=bars([10,13,11,14,12,15,12,13,10,8], [7,9,8,10,8,11,7,9,6,4], [9,11,10,13.5,10,14.5,10,12,6.5,5])
  r=structure(d,left=1,right=1)
  self.assertEqual(r.struct_direction.iloc[2],'UNKNOWN')
  self.assertEqual(r.struct_event.iloc[3],'INITIAL_BREAK');self.assertEqual(r.struct_direction.iloc[3],'UP')
  self.assertEqual(r.struct_event.iloc[5],'BOS')
  self.assertTrue(r.struct_wick_low.iloc[6]);self.assertTrue(pd.isna(r.struct_event.iloc[6]))
  self.assertEqual(r.struct_event.iloc[8],'CHOCH');self.assertEqual(r.struct_direction.iloc[8],'DOWN')
  self.assertTrue(pd.isna(r.struct_event.iloc[9])) # consumed low is not repeatedly broken
  for _,row in r.loc[r.struct_event.isin(['BOS','CHOCH','INITIAL_BREAK'])].iterrows():self.assertLessEqual(row.struct_broken_level_known_at,row.date)
 def test_every_prefix_equals_batch_and_future_append(self):
  x=np.arange(110);d=bars(100+np.sin(x/3)*4+x*.01)
  batch=structure(d)
  for n in range(1,len(d)+1):
   prefix=structure(d.iloc[:n]);pd.testing.assert_frame_equal(prefix,batch.iloc[:n])
  pd.testing.assert_frame_equal(batch,structure(d))
 def test_gap_and_invalid_reset_unknown(self):
  d=bars([10,13,11,14,12,15,12,13,10,8]);d.loc[7:,'date']+=pd.Timedelta(minutes=15)
  r=structure(d);self.assertEqual(r.struct_direction.iloc[7],'UNKNOWN');self.assertTrue(pd.isna(r.swing_high.iloc[7]));self.assertFalse(r.struct_valid.iloc[7])
  d.loc[8,'close']=np.nan;r=structure(d);self.assertEqual(r.struct_direction.iloc[8],'UNKNOWN');self.assertFalse(r.struct_valid.iloc[8])
 def test_hour_merge_exact_native_availability(self):
  b=bars([10]*12);h=pd.DataFrame({'date':pd.date_range('2026-01-01',periods=3,freq='1h',tz='UTC'),'value':[10,20,30]})
  a=closed_merge(b,h);native=merge_informative_pair(b,h,'15m','1h',ffill=True)
  pd.testing.assert_series_equal(a.value_1h,native.value_1h)
  self.assertTrue(pd.isna(a.value_1h.iloc[2]));self.assertEqual(a.value_1h.iloc[3],10);self.assertEqual(a.value_1h.iloc[7],20)
  self.assertTrue(((a.date_1h+pd.Timedelta(hours=1))<=(a.date+pd.Timedelta(minutes=15))).loc[a.date_1h.notna()].all())
if __name__=='__main__':unittest.main()
