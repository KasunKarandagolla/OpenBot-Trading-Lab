"""One bounded public real-trade sample. Partial tape cannot qualify historical profile."""
from setup_common import *
from recovery_data import client
from setup_profile import verified_profile
from intelligence_profile import volume_profile_v2
import time
def probe():
    ex=client();meta=read(DATA/'contract-source.json');pair=pairs()[0]
    ex.set_markets([r['market'] for r in meta.values()]);received=time.time()*1000
    raw=ex.fetch_trades(pair,limit=1000);received=time.time()*1000
    rows=[dict(id=str(r['id']),event_ms=r['timestamp'],received_ms=received,price=float(r['price']),amount=float(r['amount'])*float(meta[pair]['market']['contractSize'])) for r in raw]
    write(DATA/'partial-public-trades.json',rows)
    profile=volume_profile_v2([r['price'] for r in rows],[r['amount'] for r in rows],'OBSERVED_TRADES')
    write(OUT/'profile-probe.json',dict(source='GATE_PUBLIC_FUTURES_TRADES_CCXT',pair=pair,rows=len(rows),sha256=sha(DATA/'partial-public-trades.json'),
        fidelity='ACTUAL_EXECUTED_TRADE_SAMPLE',volume_unit='BASE_ASSET_FROM_CONTRACTS',sample_profile=profile,
        contract_result=verified_profile(rows,dict(fidelity='EXECUTED_TRADES',coverage='PARTIAL'),now()),
        historical_comparison='NOT_TESTED',reason='Latest1000 prints do not establish a complete prior-session profile or September/October tape coverage',
        implementation='Reused intelligence_profile.volume_profile_v2 contiguous bins; existing Freqtrade trade-to-volume-profile support already present; no new profile engine/dependency'))
if __name__=='__main__':probe()
