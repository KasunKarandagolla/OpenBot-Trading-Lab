"""Isolated v3 identities: old registrations and strategy freezes stay intact."""
from foundation_common import ROOT, IMAGE, read, write, sha, now, public, frame
import re
import shutil
import os
import sys
sys.path.insert(0, str(ROOT/'research/policy'))
PROTOCOL = ROOT/'research/policy/protocol.json'


def paths(run_id):
    if not re.fullmatch(r'policy-[a-z0-9-]{3,32}', run_id):
        raise ValueError('use policy- followed by a bounded lowercase run ID')
    return ROOT/'evidence/additional-3'/run_id, ROOT/'user_data/data/policy'/run_id/'gate'


def sources():
    return sorted(set(list((ROOT/'research/policy').glob('*.*')) + list((ROOT/'scripts').glob('*.py')) + [p for p in (ROOT/'research').rglob('*.py')] + list((ROOT/'user_data/strategies').glob('*.py')) + list((ROOT/'configs').glob('*.json'))))


def register(run_id):
    from session3_common import frozen, sanitized_env
    frozen(); sanitized_env()
    out, _ = paths(run_id)
    if out.exists(): raise ValueError('preserve registered run; choose a new run ID')
    write(out/'registration.json', dict(schema_version=3, run_id=run_id, registered_at=now(), image=IMAGE,
        parent='913eec38213052f979e67fd532febac809cbcabd', protocol=read(PROTOCOL),
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources()}))


def verify(run_id):
    from session3_common import sanitized_env
    sanitized_env()
    out, data = paths(run_id); reg=read(out/'registration.json')
    hashes=dict(reg['source_hashes'])
    for p in sorted((out/'source-amendments').glob('*.json')):
        a=read(p)
        if a['registration_sha256']!=sha(out/'registration.json') or not a['reason']: raise ValueError('invalid amendment')
        for name,c in a['changes'].items():
            if hashes.get(name)!=c['old_sha256']: raise ValueError('broken amendment chain')
            hashes[name]=c['new_sha256']
    if any(sha(ROOT/p)!=h for p,h in hashes.items()): raise ValueError('registered v3 source changed; record explicit amendment')
    return out,data,reg['protocol']


def amend(run_id, reason):
    out,_=paths(run_id); reg=read(out/'registration.json'); old=dict(reg['source_hashes'])
    for p in sorted((out/'source-amendments').glob('*.json')):
        for n,c in read(p)['changes'].items(): old[n]=c['new_sha256']
    current={str(p.relative_to(ROOT)):sha(p) for p in sources()}
    changes={p:dict(old_sha256=old.get(p),new_sha256=h) for p,h in current.items() if old.get(p)!=h}
    if not changes: raise ValueError('no source change')
    write(out/'source-amendments'/f'{len(list((out/"source-amendments").glob("*.json")))+1:03}.json',
        dict(recorded_at=now(),registration_sha256=sha(out/'registration.json'),reason=reason,changes=changes,
             policy_thresholds_changed=False))


def config(run_id,name,period=None,leverage=1):
    out,data,spec=verify(run_id)
    if name not in spec['variants']: raise ValueError('unregistered variant')
    cfg=read(ROOT/'configs'/('research.json' if name=='TrendPullbackBaselineV1' else 'research-vwap.json'))
    stage=ROOT/'work/policy-strategies'/run_id/('revision-'+str(len(list((out/'source-amendments').glob('*.json')))))
    stage.mkdir(parents=True,exist_ok=True)
    modules=[]
    for directory in ['user_data/strategies','research/session3','research/bonus','research/master_audit','research/foundation','research/intelligence','research/policy']:
        modules+=list((ROOT/directory).glob('*.py'))
    for p in modules:
        if p.name=='__init__.py': continue
        target=stage/p.name
        if target.exists() and sha(target)!=sha(p): raise ValueError('staged source changed')
        if not target.exists(): shutil.copyfile(p,target)
    cfg.update(strategy=name,strategy_path=str(stage),dry_run=True,dry_run_wallet=1000,
        tradable_balance_ratio=1.,stake_amount='unlimited',max_open_trades=2,
        position_adjustment_enable=name=='PolicyManagedV3',fee=spec['fee_per_side'],
        db_url='sqlite://',lab_audit=False,bonus_schedule=str(out/'absolute-schedule.json'),
        intelligence_schedule=str(out/'signed-schedule.json'),policy_schedule=str(out/'policy-schedule.json'),
        policy_contracts=str(out/'contracts.json'),policy_marks=str(data/'futures'),
        policy_state=str(ROOT/'work/policy-state'/run_id/(name+'-'+(period or 'all')+'-'+str(leverage)+'.sqlite')),
        policy_events=str(out/'position-events'/(name+'-'+(period or 'all')+'-'+str(leverage)+'.jsonl')),
        policy_leverage=leverage,policy_notional_cap=25.,policy_mode='RESEARCH')
    if not name.startswith('Policy'): cfg.update(stake_amount=25)
    else: cfg['stoploss']=-.99  # native initial emergency geometry must not inherit a leveraged 3% ROI stop
    cfg['exchange']['pair_whitelist']=spec['pairs']
    for k in ['key','secret','password','uid']: cfg['exchange'].pop(k,None)
    cfg.pop('api_server',None)
    opts=dict(has={'fetchCurrencies':False},requests_trust_env=True,
        options={'defaultType':'swap','fetchMarkets':{'types':['swap']}})
    proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy: opts['httpsProxy']=proxy
    if os.environ.get('SSL_CERT_FILE'): opts['cafile']=os.environ['SSL_CERT_FILE']
    for k in ['ccxt_config','ccxt_sync_config','ccxt_async_config']: cfg['exchange'].setdefault(k,{}).update(opts)
    target=ROOT/'work/policy-configs'/run_id/(name+'-'+(period or 'all')+'-'+str(leverage)+'.json')
    write(target,cfg); return target
