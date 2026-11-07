"""Owner-run Binance USD-M Demo account read. All network operations are GET."""

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from http.client import HTTPSConnection, HTTPException
import json
import re
import time


HOST = 'demo-fapi.binance.com'
CLOCK = '/fapi/v1/time'
SIGNED = ('/fapi/v3/balance', '/fapi/v3/account', '/fapi/v3/positionRisk')
SCHEMA = 'openbot.binance.demo-readonly.v1'
KEY_NAMES = ('BINANCE_DEMO_API_KEY', 'BINANCE_DEMO_KEY', 'BINANCE_API_KEY', 'API_KEY')
SECRET_NAMES = ('BINANCE_DEMO_API_SECRET', 'BINANCE_DEMO_SECRET_KEY', 'BINANCE_DEMO_SECRET',
                'BINANCE_API_SECRET', 'BINANCE_SECRET_KEY', 'API_SECRET')


class ReadError(Exception):
    def __init__(self, reason, receipt=None):
        super().__init__(reason)
        self.receipt = receipt


def credentials():
    raise ReadError('EXECUTION_BLOCKED_CREDENTIAL_BOUNDARY')


def get(path, credentials=None, timestamp=None):
    if path == CLOCK and credentials is None and timestamp is None:
        query, headers = '', {}
    elif path in SIGNED and credentials is not None and type(timestamp) is int:
        raise ReadError('EXECUTION_BLOCKED_CREDENTIAL_BOUNDARY')
    else:
        raise ReadError('ENDPOINT_OR_SIGNING_MODE_REJECTED')
    link = HTTPSConnection(HOST, timeout=10)
    try:
        link.request('GET', path + query, headers={**headers, 'Cache-Control': 'no-store, no-cache'})
        response = link.getresponse()
        data = response.read(1024 * 1024 + 1)
        receipt = {'method': 'GET', 'endpoint': path, 'http_status': response.status,
                   'observed_at': datetime.now(timezone.utc).isoformat()}
    except (OSError, HTTPException):
        raise ReadError('TLS_OR_NETWORK_FAILURE', {'method': 'GET', 'endpoint': path}) from None
    finally:
        link.close()
    if len(data) > 1024 * 1024:
        raise ReadError('RESPONSE_SIZE_LIMIT', receipt)
    receipt['response_sha256'] = hashlib.sha256(data).hexdigest()
    try:
        payload = json.loads(data)
    except (ValueError, UnicodeError):
        raise ReadError('RESPONSE_NOT_JSON', receipt) from None
    if isinstance(payload, dict) and type(payload.get('code')) is int:
        receipt['binance_code'] = payload['code']
    if response.status != 200 or receipt.get('binance_code', 0) < 0:
        raise ReadError('BINANCE_READ_FAILED', receipt)
    return payload, receipt


def fields(row, names):
    result = {}
    for name in names:
        value = row.get(name)
        if isinstance(value, bool):
            result[name] = value
        elif isinstance(value, (str, int)) and re.fullmatch(r'-?\d{1,20}(?:\.\d{1,20})?', str(value)):
            result[name] = str(value)
        else:
            result[name] = 'UNKNOWN'
    return result


def summarize(balances, account, positions):
    if not isinstance(balances, list) or not isinstance(account, dict) or not isinstance(positions, list):
        raise ReadError('ACCOUNT_RESPONSE_SHAPE')
    assets = []
    for item in balances:
        symbol = item.get('asset')
        if not isinstance(symbol, str) or not re.fullmatch('[A-Z0-9]{2,16}', symbol):
            raise ReadError('ACCOUNT_ASSET_SHAPE')
        amounts = fields(item, ('balance', 'availableBalance', 'crossWalletBalance', 'marginAvailable'))
        if symbol in ('USDT', 'USDC') or amounts['balance'] not in ('UNKNOWN', False) and Decimal(amounts['balance']):
            assets.append({'asset': symbol, **amounts})
    active = []
    for item in positions:
        value = fields(item, ('positionAmt', 'notional', 'liquidationPrice', 'initialMargin', 'maintMargin'))
        if value['positionAmt'] == 'UNKNOWN':
            raise ReadError('ACCOUNT_POSITION_SHAPE')
        if Decimal(value['positionAmt']):
            symbol = item.get('symbol')
            side = item.get('positionSide')
            if not isinstance(symbol, str) or not re.fullmatch('[A-Z0-9_]{2,32}', symbol) or side not in ('BOTH', 'LONG', 'SHORT'):
                raise ReadError('ACCOUNT_POSITION_SHAPE')
            active.append({'symbol': symbol, 'side': side, **value})
    return {'assets': assets, 'positions': active, 'open_position_count': len(active),
            'account': fields(account, ('multiAssetsMargin', 'canTrade', 'availableBalance',
                                        'totalInitialMargin', 'totalOpenOrderInitialMargin', 'totalMaintMargin')),
            'fees': 'UNKNOWN', 'position_mode': 'UNKNOWN', 'symbol_leverage_brackets': 'UNKNOWN'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-run', action='store_true', required=True,
                        help='Run manually from a separate owner terminal, without the agent environment')
    parser.parse_args()
    # A separate terminal under the same user is not credential isolation.
    # Keep the inherited parser for compatibility, but do not load credentials
    # or issue signed reads from this agent-accessible principal.
    from trading_lab.execution import readiness
    print(json.dumps(readiness(), indent=2, sort_keys=True))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
