"""Final source preservation, real-input clock checks and amendment equivalence."""
from collections import Counter
import pandas as pd
from integrated_common import *
from integrated_native import verify
from market_reader import interpret

def run():
    verify()
    starting=read(OUT/'starting-freeze.json')['preexisting_files']
    changed=[name for name,digest in starting.items() if sha(ROOT/name)!=digest]
    if changed: raise ValueError('parent files modified '+str(changed))
    frames={p:pd.read_pickle(WORK/'features/new'/(slug(p)+'.pkl')).set_index('date',drop=False) for p in pairs()}
    decisions=read(OUT/'selection-audit.json');equal=0
    for x in decisions:
        g=x['plan'];r=frames[x['pair']].loc[pd.Timestamp(x['at'])-pd.Timedelta(minutes=15)]
        relative=r.return4h-(0 if x['pair']=='BTC/USDT:USDT' else frames['BTC/USDT:USDT'].loc[r.date,'return4h'])
        current=interpret(r,g['side'],g['recipe'],g['reference'],g['stop'],relative)
        if current!=x['context']: raise ValueError('amendment changed historical market decision')
        equal+=1
    five_rows=0
    for pair in pairs():
        f=pd.read_pickle(WORK/'features/five'/(slug(pair)+'.pkl'))
        valid=f.source15_closed_at.notna()
        if not (f.loc[valid,'source15_closed_at']<=f.loc[valid,'date']).all(): raise ValueError('unfinished 15m context in 5m')
        if not (f.loc[valid,'date_1h']+pd.Timedelta(hours=1)<=f.loc[valid,'date']).all(): raise ValueError('unfinished 1h context in 5m')
        if not (f.loc[valid,'known4h']<=f.loc[valid,'date']).all(): raise ValueError('unfinished 4h context in 5m')
        five_rows+=len(f)
    five=read(OUT/'five-opportunities.json')
    by_variant={}
    for variant in ('five-15m-response','five-early','five-passive'):
        observations=[(x,x.get('variants',{}).get(variant)) for x in five]
        qualified=[(x,y) for x,y in observations if y and y.get('plan')]
        for x,y in qualified:
            g=y['plan']
            if not pd.Timestamp(g['available_at'])>pd.Timestamp(x['armed_at']): raise ValueError('backdated trigger')
            if pd.Timestamp(g['first_objective']['known_at'])>pd.Timestamp(x['armed_at']): raise ValueError('future objective')
        by_variant[variant]=dict(trigger_reasons=dict(Counter(y['reason'] for x,y in observations if y)),
            qualified_before_shortlist=len(qualified),qualified_after_shortlist=sum(x['shortlisted'] for x,y in qualified))
    report=dict(preserved_parent_files=len(starting),preserved_parent_evidence_files=sum(x.startswith('evidence/') for x in starting),changed_parent_files=changed,
        amended_market_reads_exactly_equal=equal,five_minute_rows_with_causal_context_checked=five_rows,
        five_minute=by_variant,reserved_holdout_accessed=False,
        paper_or_live_activation=False,external_exchange_orders=False,partial_management_enabled=False,
        checks='All source, feature and plan seals pass; native source fee/funding and legal lot/tick checks are in economic-report.json')
    write(OUT/'final-verification.json',report)
    print(report,flush=True)

if __name__=='__main__':run()
