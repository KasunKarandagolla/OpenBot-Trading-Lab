"""Additive native research CLI. No trade/server/private API command exists.

Uses frozen bonus configs and strategies plus a public-futures metadata scope.
The scope avoids an unrelated Gate spot-currencies endpoint; it never supplies
invented market metadata. Raw data and old evidence are never overwritten.
"""
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from bonus_common import check, config, stage, spec
from session3_common import sanitized_env


def native_config(name):
    cfg=config('RouterOnlyV1' if name.startswith('Audit') else name)
    cfg['strategy']=name
    cfg['strategy_path']=str(ROOT/'work/master-strategies')
    cfg['position_adjustment_enable']=False
    schedule=json.loads((ROOT/'evidence/bonus/schedule.json').read_text())
    for row in schedule['decisions'].values():
        row['selected']=spec()['pairs']
    all_schedule=ROOT/'work/master-all-schedule.json'
    all_schedule.parent.mkdir(parents=True,exist_ok=True)
    all_schedule.write_text(json.dumps(schedule)+'\n')
    cfg['master_all_schedule']=str(all_schedule)
    if name=='AuditRegimeOnlyM0V1':
        cfg['bonus_schedule']=str(all_schedule)
    cfg['exchange'].setdefault('ccxt_config',{}).update({
        'has':{'fetchCurrencies':False},
        'options':{'defaultType':'swap','fetchMarkets':{'types':['swap']}}})
    # Containers receive the runtime's reachable proxy address. The host's
    # optional overlay can contain an outer-only hostname; use inherited routing.
    proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy:
        cfg['exchange']['ccxt_config']['httpsProxy']=proxy
    # All Freqtrade sync/async instances use the same native CCXT public scope.
    for key in ('ccxt_async_config','ccxt_sync_config'):
        cfg['exchange'].setdefault(key,{}).update(cfg['exchange']['ccxt_config'])
    for key in ('key','secret','password','uid'):
        cfg['exchange'].pop(key,None)
    assert cfg['dry_run'] is True and cfg['trading_mode']=='futures'
    return cfg


def main():
    import shutil
    action=sys.argv[1]
    if action not in ('acquire','backtest'):
        raise ValueError('research acquire/backtest only')
    name=sys.argv[2] if len(sys.argv)>2 else 'RouterOnlyV1'
    registered=['VWAPTrendContinuationV1','LiquiditySweepReversalV1','RouterOnlyV1',
                'AuditStructuralCloseM0V1','AuditNearestObjectiveM0V1',
                'AuditRankingVWAPV1','AuditRankingSweepV1','AuditRegimeOnlyM0V1',
                'AuditRegimeVWAPV1','AuditRegimeSweepV1']
    if name not in registered:
        raise ValueError('unregistered strategy or disabled M1')
    check()
    original=stage()
    target=ROOT/'work/master-strategies'
    target.mkdir(parents=True,exist_ok=True)
    for file in original.glob('*.py'):
        shutil.copyfile(file,target/file.name)
    variants=ROOT/'research/master_audit/AuditVariantsV1.py'
    if variants.exists():
        shutil.copyfile(variants,target/variants.name)
    cfg=native_config(name)
    path=ROOT/'work/master-configs'/(name+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(cfg,indent=2)+'\n')
    data=ROOT/'user_data/data/bonus/gate'
    if action=='acquire':
        if any(data.rglob('*.feather')):
            raise ValueError('refuse overwrite; use isolated checkout to reacquire')
        args=['download-data','--config',str(path),'--datadir',str(data),
              '--trading-mode','futures','--timeframes','15m','1h',
              '--timerange',spec()['download_timerange']]
    else:
        # Hash identity against the original manifest is required before replay.
        import hashlib
        manifest=json.loads((ROOT/'evidence/bonus/source-manifest.json').read_text())
        for row in manifest['files']:
            if hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()!=row['sha256']:
                raise ValueError('raw source differs from original; do not claim exact replay')
        destination=ROOT/'work/master-backtests'/name
        destination.mkdir(parents=True)
        args=['backtesting','--config',str(path),'--datadir',str(data),
              '--timerange',spec()['timerange'],'--fee','0.0006','--enable-protections',
              '--cache','none','--export','trades','--backtest-directory',str(destination)]
    env=sanitized_env()
    os.environ.clear();os.environ.update(env)
    from freqtrade.main import main as freqtrade_main
    return freqtrade_main(args)


if __name__=='__main__':
    raise SystemExit(main())
