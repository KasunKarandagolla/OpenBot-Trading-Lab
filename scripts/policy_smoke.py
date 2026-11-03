"""Bounded official native stopped-state startup; never an observed paper fill."""
import signal
import sqlite3
import subprocess
import sys
import time
from policy_common import ROOT,verify,read,write,config,sha


def smoke(run_id):
    from session3_common import sanitized_env
    sanitized_env();out,_,_=verify(run_id)
    parent=ROOT/'work/policy-smoke'/run_id
    attempt=len(list(parent.glob('attempt-*')))+1;temp=parent/f'attempt-{attempt:03}';temp.mkdir(parents=True)
    cfg=read(config(run_id,'PolicyFixedV3','smoke'+str(attempt)))
    cfg.update(dry_run=True,db_url='sqlite:///'+str(temp/'native.sqlite'),initial_state='stopped',policy_state=str(temp/'account.sqlite'),policy_events=str(temp/'events.jsonl'))
    if any(cfg['exchange'].get(k) for k in ['key','secret','password']):raise ValueError('credentials forbidden')
    path=temp/'config.json';write(path,cfg)
    log=out/f'native-dryrun-smoke-attempt-{attempt:03}.txt'
    with log.open('x') as file:
        p=subprocess.Popen(['freqtrade','trade','--config',str(path)],stdout=file,stderr=subprocess.STDOUT)
        start=time.monotonic();ready=False
        try:
            while time.monotonic()-start<90 and p.poll() is None:
                time.sleep(.5)
                if 'Changing state to: STOPPED' in log.read_text():ready=True;break
        finally:
            if p.poll() is None:p.send_signal(signal.SIGINT)
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait()
    trades=orders=None
    if (temp/'native.sqlite').exists():
        with sqlite3.connect(temp/'native.sqlite') as db:
            if db.execute("select count(*) from sqlite_master where name='trades'").fetchone()[0]:
                trades=db.execute('select count(*) from trades').fetchone()[0];orders=db.execute('select count(*) from orders').fetchone()[0]
    installed=False
    if (temp/'account.sqlite').exists():
        with sqlite3.connect(temp/'account.sqlite') as db:
            row=db.execute("select v from kv where k='native_funding_adapter_installed'").fetchone()
            installed=row is not None and row[0]=='true'
    result=dict(passed=ready and trades==0 and orders==0 and installed,native_funding_adapter_installed=installed,native_process_returncode=p.returncode,db_trades=trades,db_orders=orders,
        process_seconds=round(time.monotonic()-start,2),initial_state='STOPPED',persistent_started=False,exchange_orders=False,
        forward_paper_fill_observed=False,config_sha256=sha(path),native_strategy='PolicyFixedV3',
        scope='Official native keyless stopped-state startup with scoped dry-run funding adapter; native fixtures qualify partial/final/restart paths separately')
    target=out/'native-dryrun-smoke.json'
    if target.exists():target=out/f'native-dryrun-smoke-attempt-{attempt:03}.json'
    write(target,result);print(result,flush=True)
    if not result['passed']:raise ValueError('bounded startup did not qualify; inspect retained native log')

if __name__=='__main__':smoke(sys.argv[1])
