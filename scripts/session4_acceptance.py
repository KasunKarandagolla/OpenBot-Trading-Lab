"""Artifact acceptance with explicit blocked live-source qualifications."""
import subprocess
from session4_common import *


def check():
    from session4_safety import verify_frozen
    verify_frozen()
    preserved=[];reviewed_changes=[]
    records=subprocess.check_output(['git','ls-tree','-r','c0ec703a3ae7e94ab704d7d833c1e3f51733c3ce'],cwd=ROOT,text=True)
    for record in records.splitlines():
        meta,name=record.split('\t',1);oid=meta.split()[2]
        actual=subprocess.check_output(['git','hash-object',name],cwd=ROOT,text=True).strip()
        if actual!=oid:
            if name not in ('.gitattributes','README.md','scripts/guard.py','scripts/session3_common.py'):raise ValueError('unexpected parent mutation '+name)
            reviewed_changes.append(name)
        else:preserved.append(name)
    manifest=read(OUT/'data-manifest.json')
    for row in manifest['files']:
        if sha(ROOT/row['path'])!=row['sha256']:raise ValueError('source identity changed')
        if row['last'] and row['last']>='2026-11-17':raise ValueError('reserved holdout acquired')
    features=read(OUT/'feature-manifest.json')
    for row in features['files']:
        if sha(ROOT/row['path'])!=row['sha256']:raise ValueError('causal feature cache changed')
    if not all(row['prefix_equal'] for row in read(OUT/'causality.json')):raise ValueError('causal prefix check failed')
    original=read(OUT/'native-results/reference.json')['strategy']['Session4Replay']['trades']
    replay=read(OUT/'native-results/reference-reproduce.json')['strategy']['Session4Replay']['trades']
    if original!=replay:raise ValueError('reference economic reproduction differs')
    economics=read(OUT/'economic-report.json')
    for label in economics['portfolios']:
        rows=read(OUT/'trade-ledgers'/(label+'.json'))
        if not all(r['native_reconciled'] and r['source_funding_reconciled'] for r in rows):raise ValueError('unreconciled native ledger')
        native=read(OUT/'native-results'/(label+'.json'))['strategy']['Session4Replay']['trades']
        if not all(t['initial_stop_loss_ratio']==-.025 for t in native):raise ValueError('unsafe research initial stop')
    runtime={label:read(OUT/'runtime'/(label+'.json')) for label in ('limit','market','limit-restart')}
    if not all(r['running_observed'] and r['observed_order_count']==0 for r in runtime.values()):raise ValueError('runtime observation differs')
    if runtime['limit-restart']['public_data_observed']:raise ValueError('outage run claimed fresh public data')
    write(OUT/'acceptance.json',dict(parent='c0ec703a3ae7e94ab704d7d833c1e3f51733c3ce',unchanged_parent_files=len(preserved),
        unchanged_parent_evidence_files=sum(n.startswith('evidence/') for n in preserved),reviewed_parent_changes=reviewed_changes,
        actual_native_portfolio_records=len(economics['portfolios']),reconciled_trade_records=sum(p['trades'] for p in economics['portfolios'].values()),
        reference_exact_trade_reproduction=True,causal_markets=len(read(OUT/'causality.json')),source_files=len(manifest['files']),
        credentials_used=False,external_orders=False,persistent_activated=False,
        functional_qualification='Bounded native RUNNING/source-outage/restart and isolated native dry-order paths verified',
        live_fresh_source_order_vertical_slice='BLOCKED_PUBLIC_GATE_503; zero forward orders/fills observed',
        genuine_prospective_flow='UNKNOWN_PUBLIC_GATE_503',minute_execution='UNAVAILABLE_NO_5MIN_HISTORICAL_FILL_CLAIM',
        historical_universe='CONDITIONAL_CURRENT_SURVIVORS; delisted membership unresolved',economic_status='UNQUALIFIED',
        tests=dict(current_paper=13,flow_profile=20,confirmed_structure=5,frozen_parent_mechanics=32,
                   current_old_exact_registration='1 expected source-seal refusal retained; remaining31 mechanics pass')))
    print('Acceptance recorded; fresh-source/order and economic qualifications remain blocked',flush=True)


if __name__=='__main__':check()
