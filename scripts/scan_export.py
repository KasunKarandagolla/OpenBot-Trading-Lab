"""Small public ticker export supplementing native test-pairlist, no order methods."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import ccxt

ROOT = Path('/lab')

def number(x):
    try:
        n = float(x)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def shortlist(markets, tickers, rules, now_ms, native_candidates=None):
    rows, rejects = [], []
    eligible = 0
    for symbol, market in sorted(markets.items()):
        if not (market.get('active') is True and market.get('swap') is True
                and market.get('linear') is True and market.get('settle') == 'USDT'
                and market.get('quote') == 'USDT' and symbol.endswith('/USDT:USDT')):
            continue
        info=market.get('info',{})
        if info.get('contract_type') != '' or info.get('in_delisting') is not False or info.get('is_pre_market') is not False:
            continue
        launch=number(info.get('launch_time'))
        if launch is None or now_ms-launch*1000 < rules.get('min_age_days',30)*86400000:
            continue
        eligible += 1
        if native_candidates is not None and symbol not in native_candidates: continue
        t = tickers.get(symbol, {})
        vol, bid, ask = (number(t.get(k)) for k in ('quoteVolume', 'bid', 'ask'))
        ts = number(t.get('timestamp'))
        spread = 1-bid/ask if bid and ask and 0 < bid <= ask else None
        reasons = []
        if vol is None or vol <= 0: reasons.append('VOLUME_UNKNOWN')
        elif vol < rules['min_quote_volume']: reasons.append('LOW_VOLUME')
        if spread is None: reasons.append('SPREAD_UNKNOWN')
        elif spread > rules['max_spread_ratio']: reasons.append('WIDE_SPREAD')
        # Timestamp unknown is disclosed; local receipt does not establish venue freshness.
        if ts is not None and (now_ms-ts > rules['max_ticker_age_seconds']*1000 or ts > now_ms+5000):
            reasons.append('STALE_OR_FUTURE_TICKER')
        row = {'symbol':symbol,'quote_volume_24h_usdt':vol,'bid':bid,'ask':ask,
               'spread_ratio':spread,'spread_status':'UNKNOWN' if spread is None else 'OBSERVED',
               'venue_timestamp_ms':ts,'freshness_status':'UNKNOWN' if ts is None else 'CHECKED',
               'reasons':reasons}
        (rejects if reasons else rows).append(row)
    rows.sort(key=lambda r: (-r['quote_volume_24h_usdt'], r['symbol']))
    for rank, row in enumerate(rows[:rules['limit']], 1): row['rank'] = rank
    return eligible, rows[:rules['limit']], rejects, max(0,len(rows)-rules['limit'])


def main():
    p=ROOT/'configs/scan-rules.json'; rules=json.loads(p.read_text())
    from public_exchange import public_exchange
    exchange=public_exchange()
    markets=exchange.load_markets()
    tickers=exchange.fetch_tickers(params={'type':'swap','settle':'usdt'})
    now=datetime.now(timezone.utc)
    native_log=(ROOT/'user_data/logs/scan-native.log').read_text()
    candidates=None
    for line in native_log.splitlines():
        if line.startswith('['):
            try:
                parsed=json.loads(line)
                if isinstance(parsed,list) and all(isinstance(x,str) for x in parsed): candidates=set(parsed)
            except json.JSONDecodeError: pass
    if candidates is None: raise ValueError('native pairlist output missing; run lab.sh scan')
    eligible, rows, rejected, capped=shortlist(markets,tickers,rules,now.timestamp()*1000,candidates)
    manifest={'schema':'scan-v1','environment':'PUBLIC_MARKET_SNAPSHOT','exchange':'gate',
      'market_type':'linear USDT perpetual','as_of_utc':now.isoformat(),
      'source':'CCXT gate public instruments + futures/usdt/tickers; native VolumePairList + SpreadFilter tested separately',
      'native_candidate_count':len(candidates),'eligible_universe_count':eligible,'shortlisted':rows,'rejected':rejected,
      'valid_but_below_top_cap':capped,'rules':rules,'configuration_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
      'orders_created':False,'trading_engine_started':False,
      'limitations':['Current membership only; never used as historical dynamic eligibility.','Unknown venue timestamp means freshness UNKNOWN; receipt timestamp is local.','30-day age and delisting/premarket flags use current public metadata; no historical calendar reconstruction or volatility scan.']}
    out=ROOT/'evidence/session-1/scan-snapshot.json';out.write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Public scan: {eligible} eligible contracts, {len(rows)} shortlisted; no trading engine started.')
    print(', '.join(r['symbol'] for r in rows))

if __name__=='__main__': main()
