"""Posthoc feasibility counts, NOT a portfolio or exchange execution engine."""
from collections import Counter
import pandas as pd
from session4_common import *


def diagnose():
    results={}
    for variant in ('reference','structure','hour'):
        plans=read(STATE/'plans'/(variant+'.json'));rows=[];counts=Counter()
        for pair,items in plans.items():
            slug=pair.replace('/','_').replace(':','_')
            coarse=pd.read_feather(DATA/'futures'/(slug+'-15m-futures.feather'))
            minute=DATA/'futures'/(slug+'-1m-futures.feather')
            detail=pd.read_feather(minute) if minute.exists() else None
            for at,g in items.items():
                start=pd.Timestamp(at);end=pd.Timestamp(g['expires_at']);sign=1 if g['side']=='long' else -1
                q=coarse.loc[(coarse.date>=start)&(coarse.date<start+pd.Timedelta(hours=g['max_hold_hours']))]
                first=q.iloc[0] if len(q) else None
                touch=bool(first is not None and first.low<=g['reference']<=first.high)
                through=bool(touch and (first.low<=g['reference']*.9999 if sign==1 else first.high>=g['reference']*1.0001))
                marketable_open=bool(first is not None and sign*(float(first.open)-g['reference'])<=0)
                ambiguity=bool(first is not None and first.low<=g['stop']<=first.high and first.low<=g['target']<=first.high)
                if detail is not None:
                    one=detail.loc[(detail.date>=start)&(detail.date<end)]
                    complete=len(one)==5 and one.date.diff().iloc[1:].eq(pd.Timedelta(minutes=1)).all()
                    timed_touch=bool(complete and ((one.low<=g['reference'])&(one.high>=g['reference'])).any())
                else:complete=False;timed_touch=None
                target_later=bool(len(q) and (q.high.max()>=g['target'] if sign==1 else q.low.min()<=g['target']))
                rows.append(dict(pair=pair,at=at,coarse_touch=touch,coarse_1bp_through=through,marketable_at_next_open=marketable_open,
                    expiry_resolution='COMPLETE_1M' if complete else 'UNKNOWN_15M_CANDLE_CANNOT_ESTABLISH_5MIN_FILL',
                    within_expiry_touch=timed_touch if complete else None,same_candle_stop_target_ambiguous=ambiguity,
                    target_reached_within_plan_hold=target_later,unfilled_candidate_target_later=bool(timed_touch is False and target_later) if complete else None,
                    queue_priority='UNKNOWN',historical_spread='UNKNOWN',profitability='NOT_COMPUTED_DIAGNOSTIC_ONLY'))
                counts.update(dict(coarse_touch=int(touch),coarse_through=int(through),marketable_open=int(marketable_open),ambiguous_stop_target=int(ambiguity),complete_1m_expiry=int(complete),target_later=int(target_later)))
        results[variant]=dict(opportunities=len(rows),counts=dict(counts),rows=rows)
    write(OUT/'execution-diagnostics.json',dict(variants=results,portfolio_comparison='Use complete native reference/structure/hour and through/open-only alternatives, not a PnL sum over filled-trade subsets.',
        cost_evidence='Public current maker/taker and funding interval in contracts.json; historical account-specific rebates, spreads and tier changes UNKNOWN.',
        fill_limitations='Candle touch/trade-through cannot establish queue priority. Without complete minute input no 5min historical fill claim is possible. Live native timeout is loop-driven. Native same-candle sequencing remains a model assumption.',
        market_stress='2/5/10/20bp additional friction per entry+exit; stop-only10bp gap scenario in economic report; native market candle portfolio separately labeled.'))


if __name__=='__main__':diagnose()
