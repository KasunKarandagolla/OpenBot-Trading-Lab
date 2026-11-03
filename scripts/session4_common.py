"""Session 4 additive paths and native, public-only configuration."""
from foundation_common import ROOT, IMAGE, read, write, sha, now, public
import os
import shutil
import sys
import re

sys.path.insert(0, str(ROOT/'research/policy'))
sys.path.insert(0, str(ROOT/'research/session4'))
RUN=os.environ.get('SESSION4_RUN_ID','run-001')
if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,32}',RUN):raise ValueError('invalid session4 run ID')
OUT = ROOT/'evidence/session4'/RUN
DATA = ROOT/'user_data/data/session4'/RUN/'gate'
STATE = ROOT/'work/session4' if RUN=='run-001' else ROOT/'work/session4'/RUN
STAGE = STATE/'strategies'


def stage():
    STAGE.mkdir(parents=True, exist_ok=True)
    seen = set()
    for directory in ['user_data/strategies','research/session3','research/bonus','research/master_audit',
                      'research/foundation','research/intelligence','research/policy','research/session4']:
        for source in (ROOT/directory).glob('*.py'):
            if source.name=='__init__.py':continue
            if source.name in seen: raise ValueError('duplicate strategy module')
            seen.add(source.name)
            shutil.copyfile(source, STAGE/source.name)
    return STAGE


def config(name='PaperPolicyV4', label='runtime', mode='limit'):
    cfg = read(ROOT/'configs/research-vwap.json')
    pairs = read(OUT/'cohort.json')['pairs']
    cfg.update(strategy=name, strategy_path=str(STAGE), dry_run=True, dry_run_wallet=1000,
               stake_amount='unlimited', max_open_trades=2, tradable_balance_ratio=1.,
               stoploss=-.025, minimal_roi={'0':100.}, position_adjustment_enable=False,
               fee=.00075, initial_state='running', db_url='sqlite:///'+str(STATE/(label+'-trades.sqlite')),
               policy_state=str(STATE/(label+'-account.sqlite')), policy_events=str(OUT/'events'/(label+'.jsonl')),
               policy_contracts=str(OUT/'contracts.json'), policy_marks=str(DATA/'futures'),
               policy_notional_cap=25., policy_leverage=1, session4_mode='structure',
               session4_features=str(STATE/'features'), session4_plans=str(STATE/'plans'/ (label+'.json')),
               session4_selection=str(OUT/'cohort.json'), lab_audit=False, cancel_open_orders_on_exit=True)
    cfg['exchange']['pair_whitelist']=pairs
    for k in ['key','secret','password','uid','apiKey']: cfg['exchange'].pop(k,None)
    cfg.pop('api_server',None)
    cfg['order_types'] = dict(entry=mode, exit=mode, stoploss='market', stoploss_on_exchange=False)
    cfg['entry_pricing']['price_side']='other'; cfg['exit_pricing']['price_side']='other'
    opts=dict(has={'fetchCurrencies':False}, requests_trust_env=True,
              options={'defaultType':'swap','fetchMarkets':{'types':['swap']}})
    proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy: opts['httpsProxy']=proxy
    if os.environ.get('SSL_CERT_FILE'):opts['cafile']=os.environ['SSL_CERT_FILE']
    for key in ['ccxt_config','ccxt_sync_config','ccxt_async_config']:
        cfg['exchange'].setdefault(key,{}).update(opts)
    return cfg


def register():
    from session3_common import sanitized_env
    from session4_safety import verify_frozen
    verify_frozen(); sanitized_env()
    if (OUT/'registration.json').exists(): raise ValueError('registration already exists')
    files=sorted(list((ROOT/'research/session4').glob('*.*'))+[p for p in (ROOT/'scripts').glob('session4*.py')])
    write(OUT/'registration.json',dict(at=now(),protocol=read(ROOT/'research/session4/protocol.json'),
         image=IMAGE,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in files}))


def amendment(reason):
    """Engineering changes remain explicit; never rewrite registration."""
    files=sorted(list((ROOT/'research/session4').glob('*.*'))+list((ROOT/'scripts').glob('session4*.py')))
    directory=OUT/'amendments'
    write(directory/f'{len(list(directory.glob("*.json")))+1:03}.json',dict(at=now(),reason=reason,
        registration_sha256=sha(OUT/'registration.json'),hashes={str(p.relative_to(ROOT)):sha(p) for p in files}))
