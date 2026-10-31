"""Offline, causal feature opportunity census; never substitutes for native simulated fills."""
import csv
import json
from pathlib import Path
import sys
import pandas as pd
from freqtrade.enums import CandleType
from freqtrade.strategy import merge_informative_pair
sys.path.insert(0,'/lab/user_data/strategies')
from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
from TrendPullbackBaselineV1 import TrendPullbackBaselineV1
ROOT=Path('/lab')


def main():
    p=json.loads((ROOT/'research/session-2-protocol.json').read_text());output={}
    start=pd.to_datetime('20260730',format='%Y%m%d',utc=True);end=pd.to_datetime('20261030',format='%Y%m%d',utc=True)
    for cls in [TrendPullbackBaselineV1,VWAPTrendContinuationV1,LiquiditySweepReversalV1]:
        frames=[];counts={}
        for pair in p['pairs']:
            stem=pair.replace('/','_').replace(':','_');folder=ROOT/'user_data/data/session-2/gate/futures'
            s=cls({'candle_type_def':CandleType.FUTURES})
            d=pd.read_feather(folder/(stem+'-15m-futures.feather'))
            if cls!=TrendPullbackBaselineV1:
                h=s.populate_indicators_1h(pd.read_feather(folder/(stem+'-1h-futures.feather')),{'pair':pair})
                d=merge_informative_pair(d,h,'15m','1h',ffill=True)
            d=s.populate_entry_trend(s.populate_indicators(d,{'pair':pair}),{'pair':pair})
            # Native startup consumes240/200 bars before evaluate; source has384bar buffer, sufficient.
            d=d.loc[(d.date>=start)&(d.date<end)]
            count={'evaluated_bars':len(d),'qualified_long_signals':int(d.enter_long.sum()),'qualified_short_signals':int(d.enter_short.sum()),
              'pre_geometry_candidates':int(d[['candidate_long','candidate_short']].sum().sum()) if 'candidate_long' in d else int(d[['enter_long','enter_short']].sum().sum()),
              'reason_counts':d.reason.value_counts().to_dict() if 'reason' in d else None}
            counts[pair]=count
            f=d.loc[(d.enter_long==1)|(d.enter_short==1)].copy();f['pair']=pair
            f['decision_available_utc']=f.date+pd.Timedelta(minutes=15)
            cols=['pair','date','decision_available_utc','close','enter_long','enter_short','atr14']
            cols += [c for c in ['vwap','rvol','prior_low','prior_high','adx_1h'] if c in f]
            frames.append(f[cols])
        output[cls.__name__]=counts
        dest=ROOT/'evidence/session-2/runs'/cls.__name__;dest.mkdir(parents=True,exist_ok=True)
        pd.concat(frames).to_csv(dest/'signal-candidates.csv',index=False)
    (ROOT/'evidence/session-2/signal-counts.json').write_text(json.dumps({'schema_version':1,'source':'offline features on validated actual candles',
      'semantics':'Qualified feature signals are opportunities, not callback admissions or fills; native capacity/cooldown/expiry may reduce counts.',
      'strategies':output},indent=2)+'\n')
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()
