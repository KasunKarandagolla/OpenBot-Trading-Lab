"""Fail closed before the official CLI; never accepts credentials or live mode."""
import json
import os
from pathlib import Path
import sys

ROOT = Path('/lab') if Path('/lab/configs').exists() else Path(__file__).resolve().parents[1]


def merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            merge(a[k], v)
        else:
            a[k] = v
    return a


def validate(config):
    if config.get('strategy') == 'PaperPolicyV4':
        from session4_safety import validate_paper
        return validate_paper(config)
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    require(config.get('dry_run') is True, 'dry_run must be true')
    require(config.get('trading_mode') == 'futures', 'futures only')
    require(config.get('margin_mode') == 'isolated', 'isolated only')
    ex = config.get('exchange', {})
    require(ex.get('name') == 'gate', 'only reviewed Gate source allowed')
    require(all(not ex.get(k) for k in ('key', 'secret', 'password', 'uid', 'account_id', 'privateKey', 'walletAddress')), 'exchange credentials forbidden')
    require(not config.get('add_config_files'), 'nested configuration includes forbidden')
    require(not config.get('force_entry_enable'), 'forced entry forbidden')
    require(config.get('stake_currency') == 'USDT', 'USDT only')
    require(type(config.get('max_open_trades')) is int and 0 < config['max_open_trades'] <= 2, 'at most two positions')
    require(isinstance(config.get('stake_amount'), (int, float)) and 0 < config['stake_amount'] <= 25, 'fixed stake must be <=25 USDT')
    require(config.get('dry_run_wallet') == 1000, 'example wallet must be 1000 USDT')
    require(config.get('timeframe') == '15m', '15m only')
    require(not config.get('position_adjustment_enable'), 'DCA forbidden')
    name = config.get('strategy')
    require(name in {'TrendPullbackBaselineV1','VWAPTrendContinuationV1','LiquiditySweepReversalV1'}, 'unknown strategy')
    challenger = name != 'TrendPullbackBaselineV1'
    require(config.get('stoploss', -.03 if challenger else -.02) == (-.03 if challenger else -.02), 'frozen stoploss required')
    require(config.get('minimal_roi', {'0':100.} if challenger else {'0':.03}) == ({'0':100.} if challenger else {'0':.03}), 'frozen ROI required')
    require(config.get('strategy_path', '/lab/user_data/strategies') == '/lab/user_data/strategies', 'fixed strategy directory required')
    for key in ('leverage','trailing_stop','custom_price_max_distance_ratio','use_custom_stoploss','use_custom_roi',
                'ignore_roi_if_entry_signal','exit_profit_only','ignore_buying_expired_candle_after','disable_dataframe_checks','freqai'):
        require(key not in config, 'unauthorized strategy override: '+key)
    require(not config.get('recursive_strategy_search'), 'recursive strategies forbidden')
    require(config.get('order_types', {}).get('stoploss_on_exchange') is False, 'exchange stops disabled')
    for opts in ('ccxt_config', 'ccxt_sync_config', 'ccxt_async_config'):
        cfg = ex.get(opts, {})
        require(set(cfg) <= {'enableRateLimit', 'timeout', 'httpsProxy', 'httpProxy', 'cafile', 'requests_trust_env', 'aiohttp_trust_env'}, 'unreviewed CCXT overrides forbidden')
    api = config.get('api_server', {})
    if api.get('enabled'):
        require(api.get('listen_ip_address') in ('127.0.0.1', '0.0.0.0'), 'invalid API bind')
        require(api.get('listen_port') == 8080, 'API port must be 8080')
        require(api.get('username') and len(api.get('password', '')) >= 24, 'generate local API authentication first')
        require(len(api.get('jwt_secret_key', '')) >= 32 and len(api.get('ws_token', '')) >= 32, 'strong local API tokens required')
    return config


def main():
    args = sys.argv[1:]
    if any(k.startswith('FREQTRADE__') for k in os.environ):
        raise ValueError('FREQTRADE__ environment overrides forbidden')
    allowed = {'--version', 'show-config', 'test-pairlist', 'download-data', 'backtesting', 'lookahead-analysis', 'list-data', 'list-strategies', 'webserver', 'trade'}
    if not args or args[0] not in allowed:
        raise ValueError('unsupported operator command')
    if args[0] != '--version':
        # Use the installed parser so aliases (-cPATH/-s) and abbreviations cannot
        # introduce an unvalidated later config or exposure override.
        from freqtrade.commands import Arguments
        parsed = Arguments(args).get_parsed_arg()
        configs = parsed.get('config') or []
        if not configs:
            raise ValueError('explicit config required')
        effective = {}
        for filename in configs:
            merge(effective, json.loads(Path(filename).read_text()))
        if effective.get('strategy') == 'PaperPolicyV4':
            from session4_safety import launch
            return launch(args,effective,parsed,configs)
        validate(effective)
        public_configs = {'research.json','scanner.json','paper.json','ui.json','research-vwap.json','research-sweep.json'}
        for filename in configs:
            path = Path(filename)
            if path.parent == ROOT/'configs' and path.name in public_configs:
                continue
            overlay = json.loads(path.read_text())
            if path == ROOT/'user_data/runtime/cloud.json':
                if set(overlay) != {'exchange'} or not set(overlay['exchange']) <= {'ccxt_config','ccxt_sync_config','ccxt_async_config'}:
                    raise ValueError('unsafe network overlay')
            elif path == ROOT/'user_data/runtime/api.json':
                if set(overlay) != {'api_server'}:
                    raise ValueError('unsafe API overlay')
            else:
                raise ValueError('unregistered configuration path')
        name = effective['strategy']
        if args[0] == 'trade' and name != 'TrendPullbackBaselineV1':
            raise ValueError('challengers are research-only; no owner paper selection authorized')
        # Challengers only accept the exact registered public config plus reviewed network overlay.
        if name != 'TrendPullbackBaselineV1':
            registry = json.loads((ROOT/'research/strategy-registry.json').read_text())
            registered = json.loads((ROOT/registry['strategies'][name]['config']).read_text())
            expected = json.loads(json.dumps(effective))
            for key in ('ccxt_config','ccxt_sync_config','ccxt_async_config'):
                expected.get('exchange',{}).pop(key,None)
                registered.get('exchange',{}).pop(key,None)
            if expected != registered:
                raise ValueError('unregistered strategy/config combination')
        for field in ('stake_amount', 'max_open_trades', 'dry_run_wallet', 'strategy_path', 'user_data_dir', 'db_url', 'pairs', 'pairs_file',
                      'strategy_list', 'freqaimodel', 'freqaimodel_path'):
            if parsed.get(field) is not None:
                raise ValueError('unsafe CLI override: '+field)
        for field in ('recursive_strategy_search', 'position_stacking', 'enable_dynamic_pairlist'):
            if parsed.get(field): raise ValueError('unsafe CLI override: '+field)
        for field, expected in [('strategy',name), ('timeframe','15m'),
                                ('trading_mode','futures'), ('exchange','gate')]:
            if parsed.get(field) is not None and parsed[field] != expected:
                raise ValueError('unsafe CLI override: '+field)
        if parsed.get('fee') is not None and parsed['fee'] != .0006:
            raise ValueError('unregistered fee')
        modules = {'TrendPullbackBaselineV1.py','VWAPTrendContinuationV1.py','LiquiditySweepReversalV1.py','PlaybookRiskV1.py'}
        if any(p.name not in modules for p in (ROOT/'user_data/strategies').glob('*.py')):
            raise ValueError('unregistered strategy module; duplicate-name bypass forbidden')
        if (ROOT/'user_data/strategies'/ (name+'.json')).exists():
            raise ValueError('unregistered strategy parameter file')
        if args[0] == 'trade' and str(ROOT/'configs/paper.json') not in configs:
            raise ValueError('paper command requires approved paper configuration')
        import hashlib
        freeze = (ROOT/'evidence/session-1/freeze.sha256').read_text().splitlines()
        if (ROOT/'evidence/session-2/freeze.sha256').exists():
            freeze += (ROOT/'evidence/session-2/freeze.sha256').read_text().splitlines()
        for line in freeze:
            sha, filename = line.split(maxsplit=1)
            if hashlib.sha256((ROOT/filename).read_bytes()).hexdigest() != sha:
                if filename == 'scripts/guard.py':
                    from session4_safety import verify_frozen
                    verify_frozen()
                else:
                    raise ValueError('frozen strategy/protocol changed')
        if args[0] == 'trade' and str(parsed.get('datadir')) != '/lab/user_data/data/cache/gate':
            raise ValueError('paper must use separate cache data path')
        if args[0] in {'backtesting','lookahead-analysis','download-data'}:
            if str(parsed.get('datadir')) not in {'/lab/user_data/data/research/gate','/lab/user_data/data/session-2/gate'}:
                raise ValueError('unregistered research data path')
            expected_range = '20260726-20261030' if args[0] == 'download-data' else '20260730-20261030'
            if parsed.get('timerange') != expected_range:
                raise ValueError('unregistered research calendar window')
    from freqtrade.main import main as freqtrade_main
    return freqtrade_main(args)

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, IndexError) as exc:
        print('SAFETY REFUSAL: '+str(exc), file=sys.stderr)
        sys.exit(2)
