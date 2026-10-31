import json
from pathlib import Path
import ccxt
root=Path('/lab')
from public_exchange import public_exchange
e=public_exchange()
markets=e.load_markets()
pairs=json.loads((root/'research/protocol.json').read_text())['pairs']
selected={}
for pair in pairs:
 m=markets[pair]
 assert m['active'] and m['swap'] and m['linear'] and m['settle']=='USDT' and m['quote']=='USDT'
 selected[pair]={k:m.get(k) for k in ['id','symbol','type','spot','swap','future','linear','inverse','settle','quote','active','contractSize','expiry']}
 selected[pair]['funding_interval_seconds']=m['info'].get('funding_interval')
 selected[pair]['contract_type']=m['info'].get('contract_type')
 selected[pair]['in_delisting']=m['info'].get('in_delisting')
 selected[pair]['launch_time']=m['info'].get('launch_time')
(root/'user_data/runtime/contracts.json').write_text(json.dumps(selected,indent=2)+'\n')
print('Public contract identity verified for '+', '.join(selected))
