"""Disposable real dry_run=true worker, bounded by parent timeout AND native alarm."""
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from session4_common import *


def templates():
    stage()
    runtime=ROOT/'user_data/runtime/session4';runtime.mkdir(parents=True,exist_ok=True)
    for source,target in [(OUT/'contracts.json',runtime/'contracts.json'),(DATA.parent/'contract-source.json',runtime/'contract-source.json')]:
        if not target.exists():__import__('shutil').copyfile(source,target)
    for mode in ('limit','market'):
        cfg=config('PaperPolicyV4','runtime-'+mode,mode)
        cfg['policy_contracts']=str(runtime/'contracts.json')
        cfg['session4_metadata_snapshot']=str(runtime/'contract-source.json')
        cfg.pop('session4_features',None);cfg.pop('session4_plans',None)
        # Public defaults contain no session-specific proxy or CA path.
        for key in ('ccxt_config','ccxt_sync_config','ccxt_async_config'):
            for field in ('httpsProxy','httpProxy','cafile','requests_trust_env','aiohttp_trust_env'):cfg['exchange'][key].pop(field,None)
        write(ROOT/'configs'/('paper-policy-'+mode+'.json'),cfg)
    seal()


def refresh():
    """Refresh mutable runtime metadata; immutable historical sources stay intact."""
    ex=public();markets=ex.load_markets();raw={};contracts={}
    for pair in read(ROOT/'configs/paper-policy-limit.json')['exchange']['pair_whitelist']:
        m=markets[pair];info=m['info']
        if not (m.get('active') and m.get('linear') and m.get('swap') and info.get('contract_type')=='' and info.get('in_delisting') is False and info.get('is_pre_market') is False):raise ValueError('runtime contract no longer eligible '+pair)
        if m.get('taker') is None or m['taker']>.00075:raise ValueError('runtime cost exceeds reviewed fee')
        tiers=ex.fetch_market_leverage_tiers(pair)
        raw[pair]=dict(market=m,tiers=tiers,observed_at=now())
        contracts[pair]=dict(verified=True,id=m['id'],contract_size=m['contractSize'],step_contracts=m['precision']['amount'],
            min_contracts=m['limits']['amount']['min'],max_contracts=m['limits']['amount'].get('max'),min_notional=m['limits']['cost'].get('min') or 0,
            taker=m['taker'],maker=m['maker'],price_precision=m['precision']['price'],funding_interval_seconds=int(info['funding_interval']),observed_at=now(),
            tiers=[dict(min_notional=t['minNotional'],max_notional=t['maxNotional'],maintenance_rate=t['maintenanceMarginRate'],max_leverage=t['maxLeverage'],maintenance_deduction=0) for t in tiers])
    runtime=ROOT/'user_data/runtime/session4';runtime.mkdir(parents=True,exist_ok=True)
    write(runtime/'contracts.json',contracts);write(runtime/'contract-source.json',raw)
    print('Refreshed reviewed runtime contract metadata; historical sources unchanged',flush=True)


def seal():
    stage()
    write(ROOT/'research/session4/paper-release.json',dict(strategy='PaperPolicyV4',version='structure-execution-v4.0.0',
        parent_reference='PolicyFixedV3 v3.0.0 unchanged',economic_status='UNQUALIFIED',persistent_paper_allowed=False,
        modules={p.name:sha(p) for p in sorted(STAGE.glob('*.py'))},initial_protection='2.5% price-distance bound, ROI stop ratio -0.025*leverage; reviewed paper configuration 1x only'))
    old={}
    for session in ('session-1','session-2','session-3'):
        for line in (ROOT/'evidence'/session/'freeze.sha256').read_text().splitlines():
            digest,name=line.split(maxsplit=1)
            if name=='scripts/guard.py':old[digest]=name
    write(ROOT/'research/session4/guard-review.json',dict(reason='Owner explicitly requested deliberate paper-policy allowlist update; original freezes remain intact.',
        original_guard_hashes=list(old),reviewed_guard_sha256=sha(ROOT/'scripts/guard.py'),
        reviewed_safety_sha256=sha(ROOT/'scripts/session4_safety.py'),reviewed_metadata_sha256=sha(ROOT/'scripts/session4_metadata.py')))


def snapshot(db):
    if not db.exists():return dict(trades=None,orders=None)
    with sqlite3.connect(db) as con:
        exists=con.execute("select count(*) from sqlite_master where name='trades'").fetchone()[0]
        if not exists:return dict(trades=None,orders=None)
        trades=con.execute('select id,pair,is_open,is_short,open_rate,close_rate,stop_loss,amount,stake_amount from trades').fetchall()
        orders=con.execute('select order_id,ft_order_side,order_type,status,amount,filled,remaining from orders').fetchall()
    return dict(trades=trades,orders=orders)


def run(mode,seconds=150,restart=False):
    from session3_common import sanitized_env
    sanitized_env()
    if mode not in ('limit','market') or not 45<=seconds<=240:raise ValueError('bounded reviewed mode required')
    # Do not overwrite an existing observed run; restart intentionally reuses its databases.
    label=mode+('-restart' if restart else '')
    target=OUT/'runtime'/(label+'.json')
    if target.exists():raise ValueError('preserve observed runtime evidence')
    cfg=read(ROOT/'configs'/('paper-policy-'+mode+'.json'))
    net=config(mode=mode)['exchange']
    for key in ('ccxt_config','ccxt_sync_config','ccxt_async_config'):cfg['exchange'][key]=net[key]
    cfg['session4_deadline']=time.time()+seconds
    path=STATE/('runtime-'+mode+'.json');write(path,cfg)
    db=STATE/('runtime-'+mode+'-trades.sqlite')
    if db.exists() and not restart:raise ValueError('existing native DB; use explicit restart')
    before=snapshot(db);start=time.monotonic();datetime_start=now();log=OUT/'runtime'/(label+'.txt');log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('x') as file:
        p=subprocess.Popen(['timeout','--signal=INT','--kill-after=20s',str(seconds+2)+'s',sys.executable,str(ROOT/'scripts/guard.py'),
                            'trade','--config',str(path),'--datadir','/lab/user_data/data/cache/session4/gate'],stdout=file,stderr=subprocess.STDOUT)
        p.wait(timeout=seconds+30)
    after=snapshot(db);text=log.read_text();events=Path(cfg['policy_events'])
    monitors=[]
    if events.exists():
        for line in events.read_text().splitlines():
            item=__import__('json').loads(line)
            if item['event']=='PAPER_MONITOR' and item['at']>=datetime_start:monitors.append(item)
    result=dict(mode=mode,at=now(),seconds=round(time.monotonic()-start,2),returncode=p.returncode,
        running_observed='Changing state to: RUNNING' in text,native_heartbeat='Bot heartbeat' in text,
        public_data_observed=any(m['source_health'].startswith('PUBLIC_RECEIPT_CLOCK_CHECKED') for m in monitors),
        public_source_outage_observed='503 Service Unavailable' in text,
        before=before,after=after,monitor_events=monitors,
        observed_order_count=len(after['orders']) if after['orders'] is not None else None,
        forward_fill_observed=bool(after['orders'] and any(float(o[5] or 0)>0 for o in after['orders'])),
        force_entry_used=False,external_exchange_orders=False,persistent_activation=False,
        db_sha256=sha(db) if db.exists() else None,config_sha256=sha(path),restart=restart,
        qualification='Native live public-data bounded dry_run; absent order paths are separately isolated native tests.')
    write(target,result);print(result,flush=True)
    if not result['running_observed']:raise ValueError('real dry-run did not reach RUNNING; retained log')


if __name__=='__main__':
    if sys.argv[1]=='templates':templates()
    elif sys.argv[1]=='seal':seal()
    elif sys.argv[1]=='refresh':refresh()
    else:run(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 150,'--restart' in sys.argv)
