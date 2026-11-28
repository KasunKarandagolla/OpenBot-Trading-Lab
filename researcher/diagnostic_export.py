"""Allowlisted sanitized research diagnostics. No native databases or traces."""
import json
import os
from pathlib import Path
import re
import uuid
import zipfile
from .contracts import ContractError, digest, encode
from .native_identity import local_path,under_work
from .settings import ROOT

PRIVATE_KEYS=frozenset({'openbot_db','provider_db','provider_databases','agent_workspace','native_python','headers','request_headers',
    'authorization','cookie','cookies','password','secret','api_key','access_token','refresh_token','account_id','creator_account_id','creator_user_id',
    'session_id','external_session_id','thread_id','turn_id','resume_cursor','raw_reasoning','encrypted_content'})


def sanitize(value):
    if isinstance(value,dict):
        return {k:sanitize(v) for k,v in value.items() if k.casefold() not in PRIVATE_KEYS}
    if isinstance(value,(list,tuple)):return [sanitize(v) for v in value]
    if isinstance(value,str):
        # These artifacts contain research evidence, never machine-local paths.
        value=re.sub(r'(?i)(?:[a-z]:[\\/]|/mnt/[a-z]/|/home/|/Users/)[^\s"<>]+','<PRIVATE_PATH>',value)
        value=re.sub(r'(?i)(bearer\s+)[^\s]+',r'\1<REDACTED>',value)
        return value
    return value


def _publish(path,raw):
    if '..' in path.parts or any(p.is_symlink() for p in (path,*path.parents)):
        raise ContractError('DIAGNOSTIC_OUTPUT_BOUNDARY')
    if path.exists():
        if path.read_bytes()!=raw:raise ContractError('DIAGNOSTIC_EXPORT_COLLISION')
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name('.'+path.name+'-'+uuid.uuid4().hex)
    try:
        with temp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.link(temp,path)
    finally:temp.unlink(missing_ok=True)


def export_job(folder,report,config):
    folder=under_work(folder)
    state=json.loads((folder/'state.json').read_text(encoding='utf-8'))
    brief={'job_id':state['job_id'],'commit':state['commit'],'mode':report.get('mode'),
        'start_proof':state.get('start_proof'),'native_status':report.get('consultant',{}).get('status'),
        'acceptance':'PARTIAL; RESULT_DELIVERY_REQUIRES_NATIVE_APP_PROOF',
        'source_limits':'Specialist feeds, M14/M15 definitions, quota/cadence, execution costs and prospective performance remain unqualified.',
        'trade_authorization':False}
    # A fixed file list is the boundary. No glob of a workspace/work/DB folder.
    values={'manifest.json':brief,'report.json':report,
        'environment.json':{'commit':state['commit'],'host_os':os.name,'python':__import__('sys').version.split()[0],
            'scanner_command':'scan_market_research through the owner-authorized OpenBot runner',
            'orchestration_command':'python3 -m researcher.openbot_runner start --request-id <request-id>',
            'blueprint_sha256':digest((ROOT/'docs/implementation/OpenBot_Final_External_First_Market_Discovery_Blueprint.md').read_bytes()),
            'plan_sha256':digest((ROOT/'docs/implementation/OpenBot_Cloud_First_GitHub_Synced_Implementation_Plan.md').read_bytes()),
            'skill_sha256':digest((ROOT/'.agents/skills/market-research-review/SKILL.md').read_bytes())},
        'native.json':{'review':report.get('consultant'), 'decision_delta':report.get('native_control_comparison'),
            'ai_research':report.get('ai_research')},
        'coverage.json':{k:report.get(k) for k in ('inventory','coverage','research_coverage','route_coverage','packs','causal_packs',
            'nominee_dispositions','not_reviewed_budget','source_faults','costs','measurement_coverage')},
        'candidates.json':{k:report.get(k) for k in ('conditional_research_candidates','shortlist','active_coin_watchlist',
            'watch_counts','candidate_consideration','conditional_research_export','handoff_export','targeted_samples')}}
    entries={name:(encode(sanitize(value))+'\n').encode() for name,value in values.items()}
    entries['SHA256SUMS.json']=(encode({k:digest(v) for k,v in entries.items()})+'\n').encode()
    if sum(map(len,entries.values()))>100*1024*1024:raise ContractError('DIAGNOSTIC_EXPORT_SIZE')
    import io
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in entries.items():archive.writestr(name,raw)
    raw=buf.getvalue();verify_zip(raw)
    name=state['job_id']+'.zip';private=folder/name;_publish(private,raw)
    workspace=local_path(config['agent_workspace']);target=workspace/'market-research-results'/name
    _publish(target,raw)
    return {'name':name,'sha256':digest(raw),'bytes':len(raw),
        'attachment_path':str(target),'verification':'ZIP_ENTRIES_AND_SHA256_LIST_VERIFIED',
        'private_native_data_included':False}


def verify_zip(raw):
    import io
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        if len(set(names))!=len(names) or any('/' in n or '\\' in n or n.startswith('.') for n in names):
            raise ContractError('DIAGNOSTIC_ARCHIVE_INVALID')
        if z.testzip() is not None:raise ContractError('DIAGNOSTIC_ARCHIVE_INVALID')
        hashes=json.loads(z.read('SHA256SUMS.json'))
        if set(hashes)!=set(names)-{'SHA256SUMS.json'}:raise ContractError('DIAGNOSTIC_ARCHIVE_INVALID')
        if any(digest(z.read(n))!=v for n,v in hashes.items()):raise ContractError('DIAGNOSTIC_ARCHIVE_INVALID')
    return True
