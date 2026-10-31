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
    require(config.get('timeframe') == '15m', '15m baseline only')
    require(not config.get('position_adjustment_enable'), 'DCA forbidden')
    require(config.get('stoploss', -0.02) == -0.02, 'frozen stoploss required')
    require(config.get('minimal_roi', {'0':0.03}) == {'0':0.03}, 'frozen ROI required')
    require(config.get('strategy') == 'TrendPullbackBaselineV1', 'frozen baseline only')
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
        validate(effective)
        for field in ('stake_amount', 'max_open_trades', 'dry_run_wallet', 'strategy_path',
                      'strategy_list', 'freqaimodel', 'freqaimodel_path'):
            if parsed.get(field) is not None:
                raise ValueError('unsafe CLI override: '+field)
        for field in ('recursive_strategy_search', 'position_stacking', 'enable_dynamic_pairlist'):
            if parsed.get(field): raise ValueError('unsafe CLI override: '+field)
        for field, expected in [('strategy','TrendPullbackBaselineV1'), ('timeframe','15m'),
                                ('trading_mode','futures'), ('exchange','gate')]:
            if parsed.get(field) is not None and parsed[field] != expected:
                raise ValueError('unsafe CLI override: '+field)
        import hashlib
        for line in (ROOT/'evidence/session-1/freeze.sha256').read_text().splitlines():
            sha, filename = line.split(maxsplit=1)
            if hashlib.sha256((ROOT/filename).read_bytes()).hexdigest() != sha:
                raise ValueError('frozen strategy/protocol changed')
    from freqtrade.main import main as freqtrade_main
    return freqtrade_main(args)

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, IndexError) as exc:
        print('SAFETY REFUSAL: '+str(exc), file=sys.stderr)
        sys.exit(2)
