"""PR11 correction: shortlist before deep work; sealed, offline research only."""
from collections import Counter
import gzip
import json
import time
import pandas as pd
from setup_common import *
from setup_features import features
from setup_profile import load_profiles
from setup_screen import DeepProvider,Workflow,shortlist

def execute(frames,profiles=(),mode='new',start=None,end=None,checkpoint_loader=None):
    """Shared by real preparation and the normal-runner synthetic fixtures."""
    start=pd.Timestamp(start or protocol()['evaluation_start'],tz='UTC') if not isinstance(start,pd.Timestamp) else start
    end=pd.Timestamp(end or protocol()['end_exclusive'],tz='UTC') if not isinstance(end,pd.Timestamp) else end
    provider=DeepProvider(frames,protocol()['deep_warmup_bars'],checkpoint_loader);workflow=Workflow(provider,profiles,mode)
    indexed={p:f.set_index('date',drop=False) for p,f in frames.items()}
    dates=sorted({at for f in frames.values() for at in f.date if start<=at+pd.Timedelta(minutes=15)<end})
    old_selections={};begin=time.perf_counter()
    for date in dates:
        rows={p:f.loc[date] for p,f in indexed.items() if date in f.index}
        workflow.tick(rows)
        if mode=='new':
            old,_,_=shortlist(rows,profiles,old=True)
            old_selections[(date+pd.Timedelta(minutes=15)).isoformat()]={p:[b+':'+s for b,s in lanes] for p,lanes in old.items()}
    return workflow,provider,dict(elapsed_seconds=time.perf_counter()-begin,old_selections=old_selections)

def prepare(audit=False):
    if RUN_ID!='run-003':raise ValueError('candidate requires isolated run-003')
    if (OUT/'plans.json').exists():raise ValueError('completed candidate registration is immutable')
    source=ROOT/'evidence/setup/run-002/data-development.json';manifest=read(source)
    for item in manifest['files']:
        if sha(ROOT/item['path'])!=item['sha256']:raise ValueError('sealed market source differs')
    meta=read(DATA/'contract-source.json')
    for pair in pairs():
        m=meta[pair]['market']
        if m['symbol']!=pair or not m['linear'] or not m['swap'] or m['quote']!='USDT':raise ValueError('Gate instrument identity')
    OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    registration=dict(at=now(),protocol=protocol(),protocol_sha256=sha(protocol_path()),starting_commit='f0ef4453144869ca013ad156fdd46c81b767af2c',
        source_archive_sha256=protocol()['source_archive_sha256'],source_manifest_sha256=sha(source),evaluation='INSPECTED_DEVELOPMENT',audit_requested=audit)
    if (OUT/'registration.json').exists():
        old=read(OUT/'registration.json')
        if any(old[k]!=registration[k] for k in ['protocol_sha256','source_manifest_sha256','audit_requested']):raise ValueError('partial registration differs')
    else:write(OUT/'registration.json',registration)
    import shutil
    shutil.copyfile(source,OUT/'data-development.json')
    write(OUT/'contracts.json',read(ROOT/'evidence/setup/run-002/contracts.json'))
    root=DATA/'development/gate/futures';frames={};source_rows=source_bytes=0;begin=time.perf_counter()
    for pair in pairs():
        bp=root/(slug(pair)+'-15m-futures.feather');hp=root/(slug(pair)+'-1h-futures.feather')
        b=pd.read_feather(bp);h=pd.read_feather(hp)
        frames[pair]=features(b,h,deep=False)
        source_rows+=len(b)+len(h);source_bytes+=bp.stat().st_size+hp.stat().st_size
    cheap_elapsed=time.perf_counter()-begin
    index=DATA/'profile-index.json'
    profiles,profile_status=load_profiles(index,DATA,now())
    # Existing authentic sample is a later assembly. Supply it through the
    # normal path so availability checks, rather than missing wiring, exclude it.
    if not index.exists() and (DATA/'verified-profile-sample-receipt.json').exists():
        from setup_profile import verified_profile
        profiles=[verified_profile(read(DATA/'verified-profile-sample-trades.json'),read(DATA/'verified-profile-sample-receipt.json'),now())]
        profile_status=dict(status='VERIFIED_LATER_ASSEMBLY',references=1,historical_coverage='NOT_TESTED',receipt_not_backdated=True)
    profile_files=[]
    if index.exists():
        profile_files.append(index)
        for item in read(index).get('references',[]):
            for key in ('trades','receipt'):
                if key not in item:continue
                p=(DATA/item[key]).resolve()
                if p.is_relative_to(DATA.resolve()) and p.exists():profile_files.append(p)
    else:profile_files=[p for p in [DATA/'verified-profile-sample-trades.json',DATA/'verified-profile-sample-receipt.json'] if p.exists()]
    profile_status['input_hashes']={str(p.relative_to(ROOT)):sha(p) for p in profile_files}
    from setup_checkpoint import ArchiveCheckpoints
    checkpoints=ArchiveCheckpoints(ROOT/'work/setup/run-002/features/new',read(ROOT/'evidence/setup/run-002/features.json')['new'])
    workflow,provider,timing=execute(frames,profiles,checkpoint_loader=checkpoints)
    source_refs={p:[x for x in manifest['files'] if slug(p)+'-' in Path(x['path']).name] for p in pairs()}
    for pair,z in workflow.plans.items():
        for g in z.values():g['source_data_refs']=[{'path':x['path'],'sha256':x['sha256']} for x in source_refs[pair]]
    for pair,f in provider.native_frames().items():
        path=WORK/'features/new'/(slug(pair)+'.pkl');path.parent.mkdir(parents=True,exist_ok=True);f.to_pickle(path)
    path=WORK/'plans/setup.json';write(path,workflow.plans)
    write(OUT/'plans.json',{'setup':dict(plans=sum(map(len,workflow.plans.values())),sha256=sha(path),conflicts=sum(e['reason']=='CONFLICTING_COMPLETE_PLANS' for e in workflow.events))})
    write(OUT/'features.json',{'new':{p:sha(WORK/'features/new'/(slug(p)+'.pkl')) for p in pairs()}})
    write(OUT/'decisions.json',workflow.events)
    trace=WORK/'compute-trace.jsonl.gz'
    with gzip.open(trace,'wt') as f:
        for row in workflow.trace:f.write(json.dumps(row,sort_keys=True,default=str)+'\n')
    funnel=dict(workflow.counts,states=dict(Counter(e['state'] for e in workflow.events)),reasons=dict(Counter(e['reason'] for e in workflow.events)),
        distinct_setups=len({e['setup_id'] for e in workflow.events}),distinct_market_observations=len({(e['pair'],e['at']) for e in workflow.events}))
    write(OUT/'funnel.json',funnel)
    write(OUT/'profile-inputs.json',dict(**profile_status,economic_status='NOT_TESTED_UNLESS_TIMESTAMP_VALID_HISTORICAL_REFERENCES_EXIST'))
    stats=dict(classification='MEASURED_OFFLINE_ARCHIVE_COMPUTE;NOT_NETWORK_LATENCY_OR_API_COST',provider_requests=0,new_market_downloads=0,
        cached_source_files=2*len(pairs()),cached_source_rows=source_rows,cached_source_bytes=source_bytes,cheap_elapsed_seconds=cheap_elapsed,
        primary=dict(workflow.counts,**provider.counts,deep_elapsed_seconds=provider.elapsed,total_elapsed_seconds=timing['elapsed_seconds']),
        trace_sha256=sha(trace),trace_path=str(trace.relative_to(ROOT)),trace_sample=workflow.trace[:30],gate_samples=workflow.gate_samples,
        management_reservation='Conservative max-hold data reservation for every ready plan; actual fills are only known during later native replay')
    if audit:
        reference,audit_provider,audit_timing=execute(frames,profiles,'audit',checkpoint_loader=checkpoints)
        qualified=[e for e in reference.events if e.get('plan') and e['reason'] in ('TRADE','CONFLICTING_COMPLETE_PLANS')]
        def key(e):return (e['pair'],e['playbook'],e['side'],e['at'])
        ready={key(e) for e in workflow.events if e['state']=='READY'}
        coverage=[]
        for e in qualified:
            lane=e['playbook']+':'+e['side']
            old=e['pair'] in timing['old_selections'].get(e['at'],{}) and lane in timing['old_selections'][e['at']][e['pair']]
            coverage.append(dict(pair=e['pair'],playbook=e['playbook'],side=e['side'],at=e['at'],setup_id=e['setup_id'],plan=e['plan'],
                new_pipeline_ready=key(e) in ready,old_PR11_filter_at_confirmation=old,
                classification='CORRECTED_RULES_FULL_UNIVERSE_OFFLINE_REFERENCE;NOT_HYPOTHETICAL_NATIVE_FILL'))
        write(OUT/'audit-opportunities.json',coverage)
        # Compare each frozen PR11 candidate using only corrected evidence
        # available by its original decision time, including earlier invalidation.
        frozen=read(ROOT/'work/setup/run-002/plans/setup.json');paired=[]
        for pair,z in frozen.items():
            frame=frames[pair].set_index('date',drop=False)
            for at,g in z.items():
                cutoff=pd.Timestamp(at);date=cutoff-pd.Timedelta(minutes=15)
                evidence=[e for e in reference.events if e['pair']==pair and e['playbook']==g['recipe'] and e['side']==g['side'] and cutoff-pd.Timedelta(hours=2)<=pd.Timestamp(e['at'])<=cutoff]
                same=[e for e in evidence if e['at']==at]
                paired.append(dict(pair=pair,at=at,frozen_plan=g,corrected_events_at_cutoff=same,
                    corrected_previous_events=evidence[-4:],corrected_pipeline_ready=at in workflow.plans.get(pair,{}),
                    map4h=dict(ready=bool(frame.loc[date,'map4h_ready']),known_at=str(frame.loc[date,'known4h']),
                        opposing_swing=frame.loc[date,'swing_high_4h' if g['side']=='long' else 'swing_low_4h'] if pd.notna(frame.loc[date,'swing_high_4h' if g['side']=='long' else 'swing_low_4h']) else None)))
        write(OUT/'paired-frozen-opportunities.json',paired)
        stats['full_universe_audit']=dict(reference.counts,**audit_provider.counts,deep_elapsed_seconds=audit_provider.elapsed,total_elapsed_seconds=audit_timing['elapsed_seconds'])
        stats['coverage']=dict(full_universe_qualified=len(coverage),new_ready_matched=sum(x['new_pipeline_ready'] for x in coverage),
            missed_by_new=sum(not x['new_pipeline_ready'] for x in coverage),old_filter_selected=sum(x['old_PR11_filter_at_confirmation'] for x in coverage),
            missed_by_old_filter=sum(not x['old_PR11_filter_at_confirmation'] for x in coverage),
            new_ready_outside_reference_lifecycle=len(ready-{key(e) for e in qualified}),
            caveat='Same cutoffs and3-per-lane budget; full-universe audit recognizes all setups before old confirmation-time filtering. Candidate lifecycles begin only on eligible shortlist observation and survive later shortlist drops.')
    stats['sealed_checkpoint_transport']=dict(checkpoints.counts)
    write(OUT/'checkpoint-inputs.json',{str(Path(p).relative_to(ROOT)):h for p,h in checkpoints.inputs.items()})
    write(OUT/'compute-work.json',stats)
    print('Candidate plans',sum(map(len,workflow.plans.values())),'deep calls',provider.counts['deep_calls'],flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--audit',action='store_true');prepare(p.parse_args().audit)
