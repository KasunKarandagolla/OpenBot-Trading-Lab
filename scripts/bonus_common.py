"""Additive bonus research identity, immutable outputs and fixed native arguments."""
import json
import shutil
import sys
from pathlib import Path
from session3_common import ROOT, sha, read, write, frozen, sanitized_env

OUT = ROOT / 'evidence/bonus'
DATA = ROOT / 'user_data/data/bonus/gate'
STAGE = ROOT / 'work/bonus-strategies'
PROTOCOL = ROOT / 'research/bonus/protocol.json'


def spec():
    obj=read(PROTOCOL)
    supplement=ROOT/'research/bonus/management-supplement.json'
    if supplement.exists():obj['variants']+=read(supplement)['additional_variants']
    return obj


def source_paths():
    return (list((ROOT/'research/bonus').glob('*.py')) + list((ROOT/'research/bonus').glob('*.json'))
            + list((ROOT/'scripts').glob('bonus*.py')))


def check():
    sanitized_env()
    frozen()
    entries=(OUT/'freeze.sha256').read_text().splitlines()
    registered={line.split(maxsplit=1)[1] for line in entries}
    if registered!={str(p.relative_to(ROOT)) for p in source_paths()}:
        raise ValueError('bonus source registration mismatch')
    for line in entries:
        h, name = line.split(maxsplit=1)
        if sha(ROOT/name) != h:
            raise ValueError('bonus source freeze changed: '+name)


def stage():
    check()
    paths = list((ROOT/'user_data/strategies').glob('*.py'))
    paths += list((ROOT/'research/session3').glob('*.py'))
    paths += list((ROOT/'research/bonus').glob('*.py'))
    STAGE.mkdir(parents=True, exist_ok=True)
    # Clear native-generated executable caches outside the source-hash registry.
    cache=STAGE/'__pycache__'
    if cache.exists():shutil.rmtree(cache)
    expected = {p.name: p for p in paths}
    if len(expected) != len(paths):
        raise ValueError('duplicate strategy module')
    if any(p.name not in expected for p in STAGE.iterdir()):
        raise ValueError('unregistered staging file')
    for name, p in expected.items():
        target = STAGE/name
        if target.exists() and sha(target) != sha(p):
            raise ValueError('staging tampered')
        if not target.exists():
            shutil.copyfile(p, target)
    return STAGE


def config(name):
    if name not in spec()['variants']:
        raise ValueError('unknown bonus variant')
    from session3_common import config as prior_config
    cfg = prior_config('s3-development-v1', 'VWAPTrendContinuationV1')
    cfg.update(strategy=name, strategy_path=str(STAGE), lab_audit=False)
    cfg['exchange']['pair_whitelist'] = spec()['pairs']
    cfg['position_adjustment_enable'] = name in ('IntegratedM1V1','RouterOnlyM1V1')
    cfg['bonus_schedule'] = str(OUT/'schedule.json')
    cfg['bonus_protocol'] = str(PROTOCOL)
    return cfg


def native_args(action, name):
    check(); stage()
    cfg = ROOT/'work/bonus-configs'/(name+'.json')
    write(cfg, config(name))
    args = [action, '--config', str(cfg), '--datadir', str(DATA)]
    if action == 'download-data':
        if any(DATA.rglob('*.feather')):
            raise ValueError('preserve existing raw data')
        return args+['--trading-mode','futures','--timeframes','15m','1h',
                     '--timerange',spec()['download_timerange']]
    if action not in ('backtesting','lookahead-analysis'):
        raise ValueError('research actions only')
    from bonus_data import verify
    verify()
    args += ['--timerange',spec()['timerange'],'--fee','0.0006']
    if action == 'backtesting':
        dest = ROOT/'user_data/backtest_results/bonus'/name
        dest.mkdir(parents=True,exist_ok=True)
        return args+['--enable-protections','--cache','none','--export','trades',
                     '--backtest-directory',str(dest)]
    return args+['--minimum-trade-amount','1','--targeted-trade-amount','20',
                 '--lookahead-analysis-exportfilename',str(OUT/(name+'-lookahead.csv'))]


if __name__ == '__main__':
    import os
    action, name = sys.argv[1:]
    args = native_args(action, name)
    env = sanitized_env(); os.environ.clear(); os.environ.update(env)
    from freqtrade.main import main
    raise SystemExit(main(args))
