"""Compact canonical opportunity and rejection views, including nonfills."""
import gzip
import json
from collections import Counter
from diagnosis_common import *
from diagnosis_audit import state_at,rank_at,clean

def run():
    forensic=read(OUT/'trade-forensics.json');bykey={}
    for row in forensic:bykey.setdefault(row['key'],{})[row['source_strategy']]=row
    raw=read(OUT/'opportunities-development.json');unique={}
    for row in raw:
        x=unique.setdefault(row['key'],dict(pair=row['pair'],plan=row['plan'],raw_pools=[]))
        x['raw_pools'].append(row['pool'])
    funnel={r['key']:r for r in read(OUT/'native/development-v4-touch-750/execution-funnel.json')}
    obstacle={r['key']:r for r in read(OUT/'obstacle-relevance.json')}
    context={r['key']:r for r in read(OUT/'entry-context.json') if r['strategy']=='v4'}
    rows=[]
    for key,x in sorted(unique.items()):
        pair=x['pair'];g=x['plan'];records=bykey.get(key,{})
        v4=records.get('v4');execution=funnel.get(key);barrier=obstacle.get(key)
        categories=[]
        if execution and not execution['order_filled']:
            categories.append(dict(category='MISSED_FILL_OR_ADVERSE_SELECTION' if execution['order_submitted'] else 'SHORTLIST_OR_CAPACITY',grade='OBSERVED_MECHANISM',evidence=execution['execution_status']))
        if v4 and 'passive' not in records and execution and execution['order_filled']:
            categories.append(dict(category='MISSED_FILL_OR_ADVERSE_SELECTION',grade='CAUSAL_MATCHED_DIFFERENCE',evidence='V4 filled; unchanged original passive entry did not fill. Native portfolio and missed-fill view retain clocks.'))
        if not categories:categories=[dict(category='UNDETERMINED',grade='INSUFFICIENT_EVIDENCE',evidence='Outcome and overlapping feature distributions do not identify a unique loss cause.')]
        rows.append(dict(key=key,decision_id=g['decision_id'],source_strategy='V4_STRICT_AND_CONTROLLED_EMA_RELAXED_RAW_UNION',raw_pools=sorted(x['raw_pools']),
            pair=pair,side=g['side'],playbook=g['recipe'],decision_timestamp=g['available_at'],market_state_at_decision=state_at(pair,g),
            original_plan=g,original_v4_selected=execution is not None,original_v4_execution=execution,
            shortlist_decision=rank_at(pair,g),nearest_known_obstacle=barrier,entry_touch_context=context.get(key),
            portfolio_outcomes={name:dict(ledger=value['ledger'],path=value['path'],thesis_failure_observation=value['thesis_observations']) for name,value in records.items()},
            failure_mechanisms=categories,unresolved_questions=['No unique causal loss label from outcome alone','Historical spread and queue unknown','Authentic flow/profile economics not tested'],
            feature_authority_note='As-of enrichment is descriptive unless the field is present in original_plan. Future paths are segregated in portfolio_outcomes and never determine admission.'))
    write(OUT/'opportunity-forensics.json',clean(rows))
    original=json.loads(gzip.open(PARENT/'forensics-rejected.json.gz','rt').read())
    with gzip.open(OUT/'pr12-rejected-asof.jsonl.gz','wt',encoding='utf-8') as output:
        for row in original:
            g=dict(available_at=row['at'],side=row['side'])
            state=state_at(row['pair'],g)
            value=dict(original_event=row,asof_context=state,order_submitted=False,order_filled=False,
                failure_mechanisms=[dict(category='SHORTLIST_OR_CAPACITY' if 'SHORTLIST' in row['reason'] else 'UNDETERMINED',grade='OBSERVED_MECHANISM',evidence=row['reason'])],
                interpretation='Original rejected decision event, not an independent opportunity or synthetic losing trade; repeated setup events remain linked by setup_id.')
            output.write(json.dumps(clean(value),allow_nan=False,separators=(',',':'))+'\n')
    write(OUT/'views-index.json',dict(raw_union_opportunities=len(rows),strict_raw=sum('strict' in x['raw_pools'] for x in rows),
        pr12_rejected_events=len(original),pr12_unique_rejected_setups=len({r['setup_id'] for r in original}),
        pr12_rejection_reasons=dict(Counter(r['reason'] for r in original)),
        views={'original_opportunities':'opportunity-forensics.json','filled_winner_loser_paths':'trade-forensics.json','passive_matched':'passive-matched.json',
        'passive_missed':'passive-missed.json','six_structural_changes':'structural-changes.json','ema_new_displaced':'ema-membership.json',
        'first_objective_rejections':'obstacle-relevance.json','five_full_funnel':'five-funnel.json','validation':'economic-report.json',
        'pr12_rejections':'pr12-rejected-asof.jsonl.gz'},
        note='Every original rejected PR12 event is preserved and enriched. Counts are events, not independent trades. Canonical raw-union IDs remain stable across correction variants.'))
    print('Canonical opportunities',len(rows),'; original PR12 rejected events',len(original),flush=True)

if __name__=='__main__':run()
