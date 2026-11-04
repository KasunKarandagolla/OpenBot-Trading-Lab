"""Full-universe 5m opportunity diagnostics with no invented fills or cash PnL."""
from diagnosis_common import *
from diagnosis_audit import candles,clean
import pandas as pd

def run():
    results=[]
    for x in read(OUT/'five-funnel.json')['five-early']['qualified']:
        candidate=x['candidate'];g=candidate['variants']['five-early']['plan'];pair=candidate['pair'];at=pd.Timestamp(g['available_at']);end=pd.Timestamp(g['expires_at'])
        sign=1 if g['side']=='long' else -1;q=candles(pair,'5m');paths={}
        for minutes in (5,15,30,60,240):
            bars=q.loc[(q.date>=at)&(q.date<at+pd.Timedelta(minutes=minutes))]
            touches=bars.loc[bars.low.le(g['reference'])&bars.high.ge(g['reference'])]
            stop=bars.loc[bars.low.le(g['stop']) if sign==1 else bars.high.ge(g['stop'])]
            target=bars.loc[bars.high.ge(g['target']) if sign==1 else bars.low.le(g['target'])]
            paths[str(minutes)]=dict(bars=len(bars),reference_range_touch_bar=touches.date.iloc[0] if len(touches) else None,
                stop_range_touch_bar=stop.date.iloc[0] if len(stop) else None,target_range_touch_bar=target.date.iloc[0] if len(target) else None,
                signed_last_close_bp=sign*(bars.close.iloc[-1]/g['reference']-1)*10000 if len(bars) else None)
        legal=q.loc[(q.date>=at)&(q.date+pd.Timedelta(minutes=5)<=end)]
        results.append(dict(pair=pair,plan=g,original_shortlist=x['ranking'],diagnostic_universe='BYPASS_SHORTLIST_FOR_PATH_INSPECTION_ONLY',
            observed_legal_complete_bar_reference_touch=bool((legal.low.le(g['reference'])&legal.high.ge(g['reference'])).any()),
            post_trigger_paths=clean(paths),native_order_submitted=False,native_fill=False,cash_pnl=None,
            evidence_grade='INSUFFICIENT_EVIDENCE',interpretation='Two original qualified triggers only. Candle price paths are diagnostic hindsight; no assumption of entry, stop/TP ordering, legal fill, queue priority or deployable universe. Native portfolios retain original risk and shortlist controls.'))
    write(OUT/'five-diagnostic-paths.json',results)
    print('Full-universe qualified 5m diagnostic cases',len(results),'; no cash counterfactuals',flush=True)

if __name__=='__main__':run()
