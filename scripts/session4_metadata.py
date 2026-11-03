"""Native metadata recovery from an actual captured CCXT Gate public snapshot.

Only contract definitions/tier metadata are cached. No ticker, mark, candle,
order, fill or account method is replaced. This cannot make stale prices fresh.
"""
from datetime import datetime,timezone
import json
from pathlib import Path


def install(snapshot,live=False):
    from freqtrade.exchange.exchange import Exchange
    from freqtrade.exchange.gate import Gate
    data=json.loads(Path(snapshot).read_text())
    for pair,row in data.items():
        market=row['market']
        if market['symbol']!=pair or not market['linear'] or not market['swap']:raise ValueError('invalid actual contract snapshot')
        if live and (datetime.now(timezone.utc)-datetime.fromisoformat(row['observed_at'])).total_seconds()>86400:raise ValueError('contract metadata cache expired')
    def load(self,reload=False):
        if self.name.lower()!='gate' or self._config.get('dry_run') is not True:raise ValueError('snapshot scope is Gate native dry-run only')
        self._api_async.set_markets([r['market'] for r in data.values()])
    def tiers(self):
        self._leverage_tiers={pair:[self.parse_leverage_tier(t) for t in row['tiers']] for pair,row in data.items() if row['tiers']}
    Exchange._load_async_markets=load
    Gate.fill_leverage_tiers=tiers
