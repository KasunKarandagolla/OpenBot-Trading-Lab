"""Bounded live public observations, separate from historical replay and signing."""
from http.client import HTTPSConnection, HTTPException
from pathlib import Path
from urllib.parse import urlencode
from decimal import Decimal
import hashlib
import json
import math
import time

from binance_research_data import DataError, KLINE_COLUMNS, INTERVAL_MS
import openbot_current_market as previous

RESEARCH_HOST = 'fapi.binance.com'
DEMO_HOST = 'demo-fapi.binance.com'
PUBLIC = {'time', 'exchangeInfo', 'ticker/24hr', 'ticker/bookTicker', 'premiumIndex', 'klines'}
MAX_BYTES = 4 * 1024 * 1024


def milliseconds():
    return time.time_ns() // 1_000_000


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


class PublicFeed:
    """No credentials, URL input, proxy support, redirects, or mutating methods."""
    def __init__(self, directory, *, demo=False):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.host = DEMO_HOST if demo else RESEARCH_HOST
        self.receipts = {}
        self.deadline_ms = milliseconds() + 180_000

    def get(self, label, endpoint, **params):
        if milliseconds() >= self.deadline_ms:
            raise DataError('PUBLIC_CAPTURE_TIME_BUDGET')
        if endpoint not in PUBLIC or not label.replace('-', '').isalnum():
            raise DataError('PUBLIC_ENDPOINT_OR_LABEL_REJECTED')
        if endpoint == 'klines':
            if (set(params) != {'symbol', 'interval', 'limit', 'endTime'}
                    or not previous.re.fullmatch('[A-Z0-9_]{2,32}', params['symbol'])
                    or params['interval'] not in INTERVAL_MS
                    or type(params['limit']) is not int or not 1 <= params['limit'] <= 1000
                    or type(params['endTime']) is not int or params['endTime'] > milliseconds()):
                raise DataError('KLINE_REQUEST_REJECTED')
        elif params:
            raise DataError('UNSUPPORTED_PUBLIC_PARAMETERS')
        path = '/fapi/v1/' + endpoint
        query = '?' + urlencode(params) if params else ''
        target = self.directory / (label + '.json')
        if target.exists():
            raise DataError('IMMUTABLE_SOURCE_ALREADY_EXISTS')
        started = milliseconds()
        for attempt in range(3):
            link = HTTPSConnection(self.host, timeout=12)
            try:
                link.request('GET', path + query, headers={'Cache-Control': 'no-store, no-cache'})
                response = link.getresponse()
                body = response.read(MAX_BYTES + 1)
                status = response.status
            except (OSError, HTTPException):
                if attempt == 2:
                    raise DataError('PUBLIC_TLS_OR_NETWORK_FAILURE') from None
                time.sleep(.25 * 2 ** attempt)
                continue
            finally:
                link.close()
            # A ban/rate limit/redirect never starts an adaptive request storm.
            if status != 200 or len(body) > MAX_BYTES:
                write_new(self.directory / (label + '-failure.json'), {
                    'host': self.host, 'path': path, 'status': status,
                    'body_sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)})
                raise DataError('PUBLIC_HTTP_OR_SIZE_FAILURE:' + str(status))
            payload = json.loads(body)
            if isinstance(payload, dict) and payload.get('code', 0) < 0:
                raise DataError('PUBLIC_EXCHANGE_ERROR')
            target.write_bytes(body)
            observed = milliseconds()
            self.receipts[label] = {
                'url': 'https://' + self.host + path + query, 'source_hostname': self.host,
                'status': status, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                'retrieved_at_utc': previous.iso(observed), 'observed_at_ms': observed,
                'available_at_ms': observed, 'request_started_ms': started,
                'venue': 'binance', 'market_type': previous.MARKET,
                'price_environment': 'DEMO_PUBLIC' if self.host == DEMO_HOST else 'PRODUCTION_PUBLIC_RESEARCH',
            }
            return payload
        raise DataError('PUBLIC_READ_RETRY_EXHAUSTED')


def validate_bars(rows, timeframe, cutoff, minimum):
    width = INTERVAL_MS[timeframe]
    if not isinstance(rows, list) or not rows:
        raise DataError('EMPTY_KLINES')
    closed = []
    for row in rows:
        if (not isinstance(row, list) or len(row) != len(KLINE_COLUMNS)
                or type(row[0]) is not int or type(row[6]) is not int
                or row[0] % width or row[6] != row[0] + width - 1):
            raise DataError('KLINE_CLOCK_OR_SHAPE')
        values = [Decimal(str(row[n])) for n in (1, 2, 3, 4, 5, 7, 9, 10)]
        if (not all(x.is_finite() for x in values) or min(values[:4]) <= 0
                or min(values[4:]) < 0 or values[1] < max(values[0], values[2], values[3])
                or values[2] > min(values[0], values[1], values[3])
                or values[6] > values[4] or values[7] > values[5]):
            raise DataError('KLINE_OHLCV_INCONSISTENT')
        if row[6] + 1 <= cutoff:
            closed.append(row)
    if (len(closed) < minimum or closed[-1][6] + 1 != cutoff // width * width
            or any(b[0] - a[0] != width for a, b in zip(closed, closed[1:]))):
        raise DataError('INSUFFICIENT_STALE_OR_GAPPED_BARS')
    return closed


def quality(row, bars, funding, cutoff):
    """Transparent research priority, not a profitability or entry decision."""
    close = float(bars[-1][4])
    high = max(float(b[2]) for b in bars[-25:-1])
    low = min(float(b[3]) for b in bars[-25:-1])
    location = (close - low) / max(high - low, close * .00001)
    trend = (close / float(bars[-7][4]) - 1)
    volumes = [float(b[7]) for b in bars[-25:-1]]
    rvol = float(bars[-1][7]) / max(sum(volumes) / len(volumes), 1)
    rate = abs(float(funding['lastFundingRate']))
    funding_in = int(funding['nextFundingTime']) - cutoff
    if not 0 < funding_in <= 24 * 3600_000 or int(funding.get('time', 0)) > cutoff:
        raise DataError('FUNDING_TIME_UNQUALIFIED')
    # Edge proximity, trend, participation, liquidity, spread and funding are distinct inputs.
    structural = max(0, 1 - min(abs(location), abs(1 - location)) * 2)
    score = (min(8, math.log10(float(row['quote_volume_24h']))) * 2
             - float(row['spread_bps']) + structural * 4 + min(abs(trend) * 100, 3)
             + min(rvol, 2) - rate * 10_000 * (2 if funding_in < 3600_000 else 1))
    return {'priority_score': round(score, 6), 'range_24h_high': high, 'range_24h_low': low,
            'range_location': location, 'return_6h': trend, 'quote_rvol_1h_prior24': rvol,
            'next_funding_ms': int(funding['nextFundingTime']), 'funding_rate': funding['lastFundingRate'],
            'entry_status': 'REVIEW_REQUIRED', 'expected_reward_risk': 'REQUIRES_STRUCTURAL_PROPOSAL',
            'flow': 'KLINE_PARTICIPATION_PROXY_ONLY', 'news_macro': 'NOT_FETCHED'}


def capture(directory, *, universe=24, shortlist=4):
    if not 24 <= universe <= 40 or not 3 <= shortlist <= 6:
        raise DataError('SCAN_BUDGET_REJECTED')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    feed = PublicFeed(directory)
    clock = feed.get('clockstart', 'time')['serverTime']
    if abs(milliseconds() - clock) > 5000:
        raise DataError('EXCHANGE_CLOCK_DRIFT')
    exchange = feed.get('exchange', 'exchangeInfo')
    tickers = feed.get('tickers', 'ticker/24hr')
    books = feed.get('books', 'ticker/bookTicker')
    funding = {r['symbol']: r for r in feed.get('funding', 'premiumIndex')}
    cutoff = feed.get('time', 'time')['serverTime']
    if abs(milliseconds() - cutoff) > 5000:
        raise DataError('EXCHANGE_CLOCK_DRIFT')
    names = [s['symbol'] for s in exchange['symbols']]
    instruments={s['symbol']:s for s in exchange['symbols']}
    ledger = previous.screen(names, exchange, tickers, books, cutoff)
    for row in ledger:
        row.update(market_type=previous.MARKET, source_hostname=RESEARCH_HOST,
                   quote_currency=instruments[row['symbol']].get('quoteAsset'),
                   instrument=instruments[row['symbol']].get('contractType'),
                   futures_status=instruments[row['symbol']].get('status'),
                   as_of_ms=cutoff, observed_at_ms=feed.receipts['books']['observed_at_ms'])
        if row.get('quote_time_ms', 0) > cutoff or row.get('quote_volume_time_ms', 0) > cutoff:
            row['status'] = 'REJECT_FUTURE_QUOTE'
    broad = sorted((r for r in ledger if r['status'] == 'ELIGIBLE'),
                   key=lambda r: -Decimal(r['quote_volume_24h']))[:universe]
    assessed = []
    for row in broad:
        name = row['symbol']
        try:
            data = feed.get(name + '-cheap', 'klines', symbol=name, interval='1h', limit=73, endTime=cutoff-1)
            bars = validate_bars(data, '1h', cutoff, 72)
            row.update(quality(row, bars, funding[name], cutoff))
            row.update(last_closed_bar_available_ms=bars[-1][6]+1,
                       data_age_ms=cutoff-(bars[-1][6]+1))
            assessed.append(row)
        except (DataError, KeyError, ValueError, ArithmeticError) as error:
            row.update(status='REJECT_CONTEXT', reason=str(error))
    ranked = sorted(assessed, key=lambda r: (-r['priority_score'], r['symbol']))[:shortlist]
    for row in ranked:
        for tf, count in previous.LIMITS.items():
            data = feed.get(row['symbol']+'-'+tf, 'klines', symbol=row['symbol'], interval=tf,
                            limit=count, endTime=cutoff-1)
            validate_bars(data, tf, cutoff, count-1)
    if milliseconds() - cutoff > previous.PACKET_FRESH_MS:
        raise DataError('SCAN_FRESHNESS_BUDGET_EXCEEDED')
    bundle = {'schema': previous.SCHEMA, 'market_type': previous.MARKET,
              'as_of_ms': cutoff, 'as_of': previous.iso(cutoff), 'observed_at': previous.iso(milliseconds()),
              'sources': feed.receipts, 'ranked': [r['symbol'] for r in ranked], 'ledger': ledger,
              'runtime': 'openbot.live.public.v2', 'broad_context_count': len(broad),
              'exchange_symbol_count': len(ledger), 'historical_strategy': 'FROZEN_LOCAL_RECOVERY_V1',
              'alternatives': 'AGENTS_MAY_PROPOSE_EVIDENCE_BACKED_ALTERNATIVES',
              'status': 'REVIEW_REQUIRED' if ranked else 'NO_OPPORTUNITY'}
    write_new(directory/'capture.json', bundle)
    return {'as_of': bundle['as_of'], 'broad_context_count': len(broad),
            'exchange_symbol_count': len(ledger), 'shortlist': bundle['ranked'],
            'public_requests': len(feed.receipts), 'status': bundle['status']}
