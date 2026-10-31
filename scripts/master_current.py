"""Bounded current Gate deep check using existing validated strategy components."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import ccxt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from bonus_orderflow import observed_setup


def main():
    out=ROOT/'evidence/master-audit/current-001.json'
    if out.exists():raise ValueError('preserve current observation')
    source=json.loads((ROOT/'evidence/master-audit/source-001/coverage.json').read_text())
    options=dict(enableRateLimit=True,timeout=15000,has={'fetchCurrencies':False},
                 options={'defaultType':'swap','fetchMarkets':{'types':['swap']}},
                 requests_trust_env=True)
    proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy:options['httpsProxy']=proxy
    exchange=ccxt.gate(options)
    exchange.load_markets()
    rows=[]
    for contract in source['gate_scan']['shortlisted'][:5]:
        symbol=next(m['symbol'] for m in exchange.markets.values() if m['id']==contract and m.get('linear') and m.get('swap'))
        asof=time.time()*1000
        try:
            # UNKNOWN explicitly denotes no trade-flow acquisition. It does not
            # mean a measured zero delta/trade count, and cannot confirm entries.
            row=observed_setup(exchange,contract,dict(asof_ms=asof,coverage_status='UNKNOWN'),symbol)
            row.update(execution_decision='NO_TRADE',execution_reason='NO_SIMULTANEOUS_VALIDATED_QUOTE_AND_ACCOUNT_RISK',
                       screen_source='source-001 broad observed shortlist; not a historical universe',orders_created=False)
        except Exception as error:
            row=dict(symbol=symbol,execution_decision='NO_TRADE',error=type(error).__name__+':'+str(error),orders_created=False)
        rows.append(row)
    out.write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
