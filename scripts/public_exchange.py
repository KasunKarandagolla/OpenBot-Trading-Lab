"""CCXT public-only instance; Cloud proxy settings are local, optional and not credentials."""
import json
from pathlib import Path
import ccxt

def public_exchange():
    options={'enableRateLimit':True,'timeout':30000,
             'options':{'defaultType':'swap','fetchMarkets':{'types':['swap']}}}
    path=Path('/lab/user_data/runtime/cloud.json')
    if path.exists(): options.update(json.loads(path.read_text())['exchange']['ccxt_config'])
    return ccxt.gate(options)
