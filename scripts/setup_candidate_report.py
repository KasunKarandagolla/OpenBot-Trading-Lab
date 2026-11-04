"""One new native replay and two sealed archived controls, with causal traces."""
from collections import Counter
import shutil
import pandas as pd
from setup_common import *
from setup_report import reconcile,summary

def archived_control(variant):
    directory=ROOT/'evidence/setup/run-002/native'/(variant+'-fixed-touch-750')
    p=read(directory/'provenance.json');cfg=read(ROOT/Path(p['archive']).parent/'config.json')
    if p['source_sha256']!=sha(OUT/'data-development.json'):raise ValueError('control source cohort differs')
    for key,value in [('dry_run_wallet',1000),('max_open_trades',2),('policy_notional_cap',25),('policy_leverage',1),('fee',.00075)]:
        if cfg[key]!=value:raise ValueError('control setting differs '+key)
    if cfg['exchange']['name']!='gate' or cfg['exchange']['pair_whitelist']!=pairs():raise ValueError('control venue/universe differs')
    if sha(ROOT/p['archive'])!=p['archive_sha256']:raise ValueError('archived native ZIP differs')
    if sha(Path(cfg['session4_plans']))!=p['plans_sha256']:raise ValueError('archived control plans differ')
    for name,h in p['staged_source_hashes'].items():
        if sha(Path(cfg['strategy_path'])/name)!=h:raise ValueError('archived strategy source differs '+name)
    temporary=WORK/'control-ledger-audit'/variant
    for name in ['result.json','states.json','provenance.json']:write(temporary/name,read(directory/name))
    native,rows=reconcile(temporary)
    return summary(native,rows),dict(classification='ARCHIVED_NATIVE_RESULT;LEDGER_INDEPENDENTLY_RECOMPUTED;NOT_A_FRESH_REPLAY',
        provenance_sha256=sha(directory/'provenance.json'),archive_sha256=p['archive_sha256'],native_record=str(directory.relative_to(ROOT)),plans=read(ROOT/'evidence/setup/run-002/plans.json')[variant]['plans'])

def report():
    if RUN_ID!='run-003':raise ValueError('candidate report requires run-003')
    directory=OUT/'native/setup-fixed-touch-750'
    native,rows=reconcile(directory);candidate=summary(native,rows)
    controls={};control_provenance={}
    for key,variant in [('Frozen V4 structure','v4-structure'),('Frozen PR11 setup-v1.1','setup')]:
        controls[key],control_provenance[key]=archived_control(variant)
    controls['Corrected setup-v1.2']=candidate
    decisions=read(OUT/'decisions.json');plans=read(WORK/'plans/setup.json');work=read(OUT/'compute-work.json')
    provenance=read(directory/'provenance.json');attempt=ROOT/Path(provenance['archive']).parent
    events_path=attempt/'events.jsonl'
    events=[__import__('json').loads(x) for x in events_path.read_text().splitlines()] if events_path.exists() else []
    admissions={e['decision_id']:e for e in events if e.get('event')=='ADMITTED'}
    filled={r['decision_id']:r for r in rows}
    execution=[];holding_violations=[];management_missing=[]
    import gzip
    trace=[]
    with gzip.open(WORK/'compute-trace.jsonl.gz','rt') as f:trace=[__import__('json').loads(line) for line in f]
    trace_lookup={(x['pair'],x['at']):x for x in trace}
    for pair,z in plans.items():
        for at,g in z.items():
            status='EXITED' if g['decision_id'] in filled else 'UNFILLED' if g['decision_id'] in admissions else 'NOT_NATIVE_ADMITTED'
            execution.append(dict(pair=pair,at=at,decision_id=g['decision_id'],setup_id=g['setup_id'],state=status,
                admission=admissions.get(g['decision_id']),result=filled.get(g['decision_id']),
                unobserved_veto_reason=None if status!='NOT_NATIVE_ADMITTED' else 'Individual native risk/cooldown/capacity/minimum veto not instrumented'))
    for r in rows:
        if r['hold_minutes']>900:holding_violations.append(r['decision_id'])
        for at in pd.date_range(pd.Timestamp(r['entry']).ceil('15min'),pd.Timestamp(r['exit']).floor('15min'),freq='15min'):
            if (r['pair'],at.isoformat()) not in trace_lookup:management_missing.append(dict(pair=r['pair'],at=at.isoformat(),decision_id=r['decision_id']))
    if holding_violations or management_missing:raise ValueError('hold or management coverage violation')
    write(directory/'execution-funnel.json',execution)
    continuation=[e for e in decisions if e['playbook']=='continuation']
    continuation_counts=dict(armed=sum(e['state']=='ARMED' for e in continuation),
        completed_confirmations=sum(bool(e.get('plan') or e.get('candidate_geometry')) for e in continuation),
        rejected_geometry=sum(bool(e.get('candidate_geometry')) for e in continuation),
        shortlisted_pair_times=sum('continuation:long' in x['new_lanes'] or 'continuation:short' in x['new_lanes'] for x in trace),
        ready=sum(e['state']=='READY' for e in continuation),native_admitted=sum(e['plan']['recipe']=='continuation' for e in admissions.values()),
        filled=sum(r['playbook']=='continuation' for r in rows),
        old_ema_would_veto_armed=sum(e['state']=='ARMED' and e['old_ema_would_veto'] for e in continuation),
        old_ema_would_veto_ready=sum(e['state']=='READY' and e['old_ema_would_veto'] for e in continuation))
    chosen=next((e for e in execution),None)
    case=None
    if chosen:
        g=plans[chosen['pair']][chosen['at']]
        armed=next((e for e in decisions if e['setup_id']==g['setup_id'] and e['state']=='ARMED'),None)
        case=dict(selection_rule='FIRST_CHRONOLOGICAL_READY_PLAN;NOT_CHOSEN_BY_RETURN',
            eligibility_and_shortlist=trace_lookup.get((chosen['pair'],g['setup_armed_at'])),registered_setup=armed,
            confirmed_plan=g,native_risk_and_result=chosen)
    paired=read(OUT/'paired-frozen-opportunities.json') if (OUT/'paired-frozen-opportunities.json').exists() else []
    rejected=next((x for x in paired if not x['corrected_pipeline_ready']),None)
    write(OUT/'traced-opportunities.json',dict(opportunity=case,rejected_frozen_opportunity=rejected))
    report=dict(portfolios=controls,control_provenance=control_provenance,new_native_portfolios=1,control_native_replays=0,
        candidate_classification='ONE_NEW_MATCHED_NATIVE_LIMIT_TOUCH_SIMULATION;INSPECTED_DEVELOPMENT_BUNDLED_FIXES',
        funnel=read(OUT/'funnel.json'),continuation=continuation_counts,screening_work=work,
        candidate_plan_execution=dict(Counter(x['state'] for x in execution)),
        management_coverage=dict(checked_trade_records=len(rows),missing_updates=management_missing,hold_violations=holding_violations),
        profile=read(OUT/'profile-inputs.json'),additional10bp_per_side_ledger_sensitivity=candidate['additional_friction_net']['10'],
        attribution='Bundled changes only. No individual fix receives causal PnL attribution.',
        verdict='MECHANICAL_FIXES_VERIFIED;NO_PROMOTION_FROM_ONE_INSPECTED_DEVELOPMENT_RUN',reserved_holdout_inspected=False)
    write(OUT/'comparison.json',report)
    lines=['| Same archived Gate cohort | Evidence | Plans | Fills | Gross price PnL | Fees | Funding | Net USDT | +10bp/side ledger |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,x in controls.items():
        count=control_provenance[name]['plans'] if name in control_provenance else sum(map(len,plans.values()))
        evidence='archived native; ledger re-audited' if name in control_provenance else 'new native replay'
        lines.append(f"| {name} | {evidence} | {count} | {x['n']} | {x['gross']:+.6f} | {x['fees']:.6f} | {x['funding']:+.6f} | {x['net']:+.6f} | {x['additional_friction_net']['10']:+.6f} |")
    (OUT/'comparison.md').write_text('\n'.join(lines)+'\n')
    print('One candidate replay reconciled:',candidate['n'],'fills;',candidate['net'],'net; two archived control ledgers re-audited',flush=True)

if __name__=='__main__':report()
