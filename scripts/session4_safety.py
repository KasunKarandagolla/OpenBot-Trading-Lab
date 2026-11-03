"""Deliberate bounded-paper allowlist, separate from frozen research permissions."""
import hashlib
import json
import math
from pathlib import Path
import signal
import time

ROOT=Path('/lab') if Path('/lab/configs').exists() else Path(__file__).resolve().parents[1]
NET={'httpsProxy','httpProxy','cafile','requests_trust_env','aiohttp_trust_env'}


def verify_frozen():
    review=json.loads((ROOT/'research/session4/guard-review.json').read_text())
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if digest(ROOT/'scripts/guard.py')!=review['reviewed_guard_sha256'] or digest(ROOT/'scripts/session4_safety.py')!=review['reviewed_safety_sha256']:raise ValueError('unreviewed guard extension')
    if digest(ROOT/'scripts/session4_metadata.py')!=review['reviewed_metadata_sha256']:raise ValueError('unreviewed metadata recovery source')
    for session in ('session-1','session-2','session-3'):
        for line in (ROOT/'evidence'/session/'freeze.sha256').read_text().splitlines():
            expected,name=line.split(maxsplit=1)
            if name=='scripts/guard.py' and expected in review['original_guard_hashes']:continue
            if digest(ROOT/name)!=expected:raise ValueError('frozen strategy/config/protocol changed: '+name)


def normalized(cfg):
    cfg=json.loads(json.dumps(cfg));cfg.pop('session4_deadline',None)
    for key in ('ccxt_config','ccxt_sync_config','ccxt_async_config'):
        item=cfg.get('exchange',{}).get(key,{})
        for field in NET:item.pop(field,None)
    return cfg


def validate_paper(cfg,check_deadline=True):
    if cfg.get('strategy')!='PaperPolicyV4':raise ValueError('paper policy not allowlisted')
    mode=cfg.get('order_types',{}).get('entry')
    if mode not in ('limit','market'):raise ValueError('unreviewed paper order mode')
    template=json.loads((ROOT/'configs'/('paper-policy-'+mode+'.json')).read_text())
    if normalized(cfg)!=normalized(template):raise ValueError('unreviewed paper configuration change')
    if cfg.get('dry_run') is not True or cfg.get('margin_mode')!='isolated' or cfg.get('trading_mode')!='futures':raise ValueError('keyless isolated dry-run only')
    ex=cfg['exchange']
    if any(ex.get(k) for k in ('key','secret','password','uid','apiKey','privateKey','walletAddress','account_id')):raise ValueError('credentials forbidden')
    if cfg.get('policy_leverage')!=1:raise ValueError('paper release limited to 1x')
    if check_deadline and not 0<float(cfg.get('session4_deadline',0))-time.time()<=300:raise ValueError('bounded session4 deadline required (at most 300 seconds)')
    release=json.loads((ROOT/'research/session4/paper-release.json').read_text())
    directory=Path(cfg['strategy_path'])
    actual={p.name for p in directory.glob('*.py')}
    if actual!=set(release['modules']):raise ValueError('unreviewed strategy module set')
    if list(directory.glob('*.json')):raise ValueError('strategy parameter override forbidden')
    for name,digest in release['modules'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest:raise ValueError('reviewed paper source changed: '+name)
    return cfg


def launch(args,cfg,parsed,configs):
    validate_paper(cfg)
    mode=cfg['order_types']['entry']
    if args[0]!='trade' or list(map(str,configs))!=[str(ROOT/'work/session4'/('runtime-'+mode+'.json'))]:raise ValueError('only registered bounded native trade command permitted')
    for field in ('stake_amount','max_open_trades','dry_run_wallet','strategy_path','strategy','user_data_dir','db_url','pairs','pairs_file',
                  'strategy_list','freqaimodel','freqaimodel_path','timeframe','exchange','trading_mode','fee','recursive_strategy_search',
                  'position_stacking','enable_dynamic_pairlist'):
        value=parsed.get(field)
        if value is not None and value is not False:raise ValueError('CLI override forbidden: '+field)
    if str(parsed.get('datadir'))!='/lab/user_data/data/cache/session4/gate':raise ValueError('separate session4 paper cache required')
    verify_frozen()
    from session4_metadata import install
    install(cfg['session4_metadata_snapshot'],live=True)
    def deadline(signum,frame):raise KeyboardInterrupt('Session4 bounded paper deadline')
    signal.signal(signal.SIGALRM,deadline);signal.alarm(max(1,math.ceil(cfg['session4_deadline']-time.time())))
    from freqtrade.main import main
    try:return main(args)
    finally:signal.alarm(0)
