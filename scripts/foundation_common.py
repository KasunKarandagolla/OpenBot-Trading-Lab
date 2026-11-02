"""Bounded research identities; separate source, evidence and export trees."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'research'),
               str(ROOT/'research/bonus'), str(ROOT/'research/session3'),
               str(ROOT/'research/master_audit'), str(ROOT/'user_data/strategies')]
PROTOCOL = ROOT/'research/foundation/protocol.json'
IMAGE = 'freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7'


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic single-file publication; no NaN, no partially written reader file.
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)+'\n')
    temp.replace(path)


def paths(run_id):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,40}', run_id):
        raise ValueError('use a bounded lowercase run ID')
    out = ROOT/'evidence/additional-1'/run_id
    data = ROOT/'user_data/data/foundation'/run_id/'gate'
    return out, data


def public(venue='gate'):
    import ccxt
    if venue not in ('gate', 'binance'):
        raise ValueError('unsupported source')
    opts = dict(enableRateLimit=True, timeout=15000,
                options={'defaultType': 'swap', 'fetchMarkets': {'types': ['swap']}},
                has={'fetchCurrencies': False}, requests_trust_env=True)
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy:
        opts['httpsProxy'] = proxy
    return (ccxt.gate if venue == 'gate' else ccxt.binanceusdm)(opts)


def source_files():
    return sorted(list((ROOT/'research/foundation').glob('*.py')) +
                  list((ROOT/'research/foundation').glob('*.json')) +
                  list((ROOT/'scripts').glob('foundation*.py')))


def register(run_id):
    from session3_common import frozen, sanitized_env
    frozen(); sanitized_env()
    out, _ = paths(run_id)
    if out.exists():
        raise ValueError('preserve existing run; use individual actions or a new ID')
    obj = dict(schema_version=1, run_id=run_id, registered_at=now(), image=IMAGE,
               protocol=read(PROTOCOL), source_hashes={str(p.relative_to(ROOT)): sha(p) for p in source_files()})
    write(out/'registration.json', obj)
    return obj


def verify(run_id):
    from session3_common import frozen, sanitized_env
    frozen(); sanitized_env()
    out, data = paths(run_id)
    reg = read(out/'registration.json')
    for name, digest in reg['source_hashes'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('registered source changed: '+name)
    return out, data, reg['protocol']


def frame(data, symbol, tf='15m', kind='futures'):
    import pandas as pd
    name = symbol.replace('/', '_').replace(':', '_')+'-'+tf+'-'+kind+'.feather'
    return pd.read_feather(data/'futures'/name)


def config(run_id, name):
    from session3_common import sanitized_env
    sanitized_env()
    out, data, spec = verify(run_id)
    if name not in spec['strategies']:
        raise ValueError('unknown strategy')
    stage = ROOT/'work/foundation-strategies'/run_id
    stage.mkdir(parents=True, exist_ok=True)
    sources = (list((ROOT/'user_data/strategies').glob('*.py')) +
               list((ROOT/'research/session3').glob('*.py')) +
               list((ROOT/'research/bonus').glob('*.py')) +
               [ROOT/'research/master_audit/AuditVariantsV1.py', ROOT/'research/foundation/FoundationRouterV1.py'])
    expected = {p.name: p for p in sources}
    if len(expected) != len(sources):
        raise ValueError('duplicate strategy module')
    if any(p.suffix in ('.py', '.json') and p.name not in expected for p in stage.iterdir()):
        raise ValueError('unexpected staged executable')
    for filename, source in expected.items():
        target = stage/filename
        if target.exists() and sha(target) != sha(source):
            raise ValueError('staged strategy changed')
        if not target.exists():
            shutil.copyfile(source, target)
    base = 'research.json' if name == 'TrendPullbackBaselineV1' else 'research-vwap.json'
    cfg = read(ROOT/'configs'/base)
    cfg.update(strategy=name, strategy_path=str(stage), lab_audit=False,
               fee=spec['fee_per_side'], position_adjustment_enable=name == 'FoundationRouterM1V1',
               bonus_schedule=str(out/'schedule.json'))
    cfg['exchange']['pair_whitelist'] = spec['pairs']
    for key in ('key', 'secret', 'password', 'uid'):
        cfg['exchange'].pop(key, None)
    opts = dict(has={'fetchCurrencies': False},
                options={'defaultType': 'swap', 'fetchMarkets': {'types': ['swap']}})
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy:
        opts['httpsProxy'] = proxy
    for key in ('ccxt_config', 'ccxt_sync_config', 'ccxt_async_config'):
        cfg['exchange'].setdefault(key, {}).update(opts)
    cfg['db_url'] = 'sqlite://'
    cfg.pop('api_server', None)
    assert cfg['dry_run'] is True and cfg['trading_mode'] == 'futures'
    target = ROOT/'work/foundation-configs'/run_id/(name+'.json')
    write(target, cfg)
    return target
