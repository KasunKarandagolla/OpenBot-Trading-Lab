"""Independent source-event/quantity audit; never change a native execution result."""
from bonus_common import *
from bonus_data import frame
import pandas as pd


def event_bounds(trade,events):
    """Exact-clock fills have unknown venue funding priority: bound both orders."""
    low=high=0.;rows=[];sign=1 if trade['is_short'] else -1
    for event in events:
        at=event['timestamp_ms']
        if not trade['open_timestamp']<=at<=trade['close_timestamp']:continue
        before=sum(o['amount']*(1 if o['ft_is_entry'] else -1) for o in trade['orders'] if o['order_filled_timestamp']<at)
        entries=sum(o['amount'] for o in trade['orders'] if o['ft_is_entry'] and o['order_filled_timestamp']==at)
        exits=sum(o['amount'] for o in trade['orders'] if not o['ft_is_entry'] and o['order_filled_timestamp']==at)
        after=before+entries-exits
        quantities=[max(0.,before),max(0.,after),max(0.,before+entries),max(0.,before-exits)]
        perbase=sign*event['rate']*event['mark_open']
        lo=min(quantities)*perbase;hi=max(quantities)*perbase
        lo,hi=min(lo,hi),max(lo,hi);low+=lo;high+=hi
        rows.append(event|{'quantity_before':before,'quantity_after':after,
                          'funding_min':lo,'funding_max':hi,'clock_priority_ambiguous':bool(entries or exits)})
    return low,high,rows


def audit():
    check();events={}
    for symbol in spec()['pairs']:
        funding=frame(symbol,'1h','funding_rate');marks=frame(symbol,'1h','mark').set_index('date')
        events[symbol]=[{'timestamp_ms':r.date.timestamp()*1000,'rate':float(r.funding_rate),
                         'mark_open':float(marks.loc[r.date,'open'])} for _,r in funding.iterrows()]
    variants={}
    for name in spec()['variants']:
        trades=read(OUT/'native-results'/(name+'.json'))['strategy'][name]['trades'];rows=[]
        for t in trades:
            lo,hi,observations=event_bounds(t,events[t['pair']]);native=t.get('funding_fees',0) or 0
            residual=max(lo-native,native-hi,0.)
            rows.append({'pair':t['pair'],'open_date':t['open_date'],'native_funding':native,
                         'source_quantity_funding_min':lo,'source_quantity_funding_max':hi,
                         'outside_bounds_usdt':residual,'native_net':t['profit_abs'],
                         'source_funding_net_min':t['profit_abs']-native+lo,
                         'source_funding_net_max':t['profit_abs']-native+hi,'events':observations})
        variants[name]={'trades':len(rows),'outside_bounds_trades':sum(r['outside_bounds_usdt']>1e-8 for r in rows),
                        'native_net':sum(r['native_net'] for r in rows),
                        'source_funding_net_min':sum(r['source_funding_net_min'] for r in rows),
                        'source_funding_net_max':sum(r['source_funding_net_max'] for r in rows),'rows':rows}
    obj={'method':'Independently multiply recorded funding rates * native-source mark open * quantity held from native fills. Exact-clock funding/fill priority bounded both ways.',
         'variants':variants,'native_results_modified':False,
         'finding':'Pinned native partial-exit funding at exact funding boundary can exceed source-event quantity bounds. Keep M1 research-only; no persistent paper qualification.',
         'limitations':['Mark open is the pinned native funding price proxy, not an exchange account statement.',
                        'Funding-vs-fill priority at the same exported timestamp is unobserved; report bounds, not a manufactured precise correction.']}
    write(OUT/'source-funding-audit.json',obj)
    print(json.dumps({n:{k:v for k,v in r.items() if k!='rows'} for n,r in variants.items()},indent=2))
    return obj


if __name__=='__main__':audit()
