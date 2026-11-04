"""Official pinned Freqtrade replay; no custom PnL or exchange simulation."""
import os
import shutil
import zipfile
from integrated_common import *

IMAGE='freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7'

def freeze_path():
    amended=OUT/'decision-freeze-v2.json'
    return amended if amended.exists() else OUT/'decision-freeze.json'

def verify():
    freeze=read(freeze_path())
    if sha(OUT/'data.json')!=freeze['source_sha256']: raise ValueError('input manifest changed')
    if sha(DATA/'contract-source.json')!=read(OUT/'data.json')['metadata_sha256']: raise ValueError('contract metadata changed')
    if freeze.get('contracts_sha256') and sha(OUT/'contracts.json')!=freeze['contracts_sha256']: raise ValueError('risk contract input changed')
    for name,digest in read(OUT/'starting-freeze.json')['preexisting_files'].items():
        if name.startswith(('research/','configs/','user_data/strategies/','scripts/')) and name.endswith(('.py','.json')) and sha(ROOT/name)!=digest:
            raise ValueError('frozen parent source changed '+name)
    for row in read(OUT/'data.json')['files']:
        if sha(ROOT/row['path'])!=row['sha256']: raise ValueError('market input changed')
    for group in ('decision_source_hashes','feature_hashes'):
        for name,digest in freeze[group].items():
            if sha(ROOT/name)!=digest: raise ValueError('frozen source changed '+name)
    return freeze

def stage():
    folders=['user_data/strategies','research/session3','research/bonus','research/master_audit','research/foundation','research/intelligence','research/policy','research/session4','research/recovery','research/setup','research/integrated']
    files=[p for folder in folders for p in sorted((ROOT/folder).glob('*.py')) if p.name!='__init__.py']
    identity=__import__('hashlib').sha256(''.join(sha(p) for p in files).encode()).hexdigest()[:16]
    target=WORK/'strategies'/identity;target.mkdir(parents=True,exist_ok=True)
    for p in files:
        dest=target/p.name
        if dest.exists() and sha(dest)!=sha(p): raise ValueError('duplicate or modified staged module '+p.name)
        if not dest.exists(): shutil.copyfile(p,dest)
    return target

def native(variant,fee=.00075,execution='touch',replay_id=None):
    from freqtrade.commands import Arguments
    from freqtrade.commands.optimize_commands import setup_optimize_configuration
    from freqtrade.enums import RunMode
    from freqtrade.optimize.backtesting import Backtesting
    from freqtrade.persistence import LocalTrade
    from recovery_funding import EventClockFunding,install as funding_install
    from session4_metadata import install
    freeze=verify();registration=read(OUT/'plans.json')[variant]
    plans=WORK/'plans'/(variant+'.json')
    if sha(plans)!=registration['sha256']: raise ValueError('plan source changed')
    if fee not in (.00075,.00175) or execution not in ('touch','through'): raise ValueError('unregistered friction experiment')
    label=f'{variant}-{execution}-{round(fee*1e6)}'+('-'+replay_id if replay_id else '')
    if replay_id and not __import__('re').fullmatch('[a-z0-9-]{3,30}',replay_id): raise ValueError('invalid replay id')
    dest=OUT/'native'/label
    if (dest/'result.json').exists(): raise ValueError('completed result is immutable')
    attempt=WORK/'native'/label/('attempt-'+str(len(list((WORK/'native'/label).glob('attempt-*')))+1))
    attempt.mkdir(parents=True)
    timeframe=registration['timeframe'];five=timeframe=='5m'
    name='RecoveryPolicyR1' if variant=='control-v4' else 'SetupPolicyV1' if variant=='control-pr12' else 'IntegratedFiveMinuteR1' if five else 'IntegratedPolicyR1'
    cfg=read(ROOT/'configs/research-vwap.json')
    cfg.update(strategy=name,strategy_path=str(stage()),timeframe=timeframe,startup_candle_count=1 if five else 960,
        dry_run=True,dry_run_wallet=1000,stake_amount='unlimited',max_open_trades=2,tradable_balance_ratio=1.,stoploss=-.025,
        minimal_roi={'0':100.},fee=fee,db_url='sqlite://',policy_state=str(attempt/'account.sqlite'),policy_events=str(attempt/'events.jsonl'),
        policy_contracts=str(OUT/'contracts.json'),policy_marks=str(DATA/'gate/futures'),policy_notional_cap=25.,policy_leverage=1,
        session4_features=str(WORK/'features'/registration['features']),session4_plans=str(plans),session4_constant_risk=False,
        recovery_risk=False,recovery_allocation_fraction=1.,position_adjustment_enable=False,setup_management=False,lab_audit=False,
        integrated_structural_exit=variant in ('thesis-exit','integrated') or five)
    cfg['exchange']['pair_whitelist']=pairs()
    for k in ('key','secret','password','uid','apiKey'): cfg['exchange'].pop(k,None)
    cfg.pop('api_server',None)
    cfg['order_types']=dict(entry='limit',exit='limit',stoploss='market',stoploss_on_exchange=False)
    for k in ('ccxt_config','ccxt_sync_config','ccxt_async_config'):
        cfg['exchange'].setdefault(k,{}).update(dict(has={'fetchCurrencies':False},requests_trust_env=True,options={'defaultType':'swap','fetchMarkets':{'types':['swap']}}))
        if os.environ.get('HTTPS_PROXY'): cfg['exchange'][k]['httpsProxy']=os.environ['HTTPS_PROXY']
        if os.environ.get('SSL_CERT_FILE'): cfg['exchange'][k]['cafile']=os.environ['SSL_CERT_FILE']
    cp=attempt/'config.json';write(cp,cfg)
    start=read(OUT/'data.json')['five_minute_start'].replace('-','') if five else '20260901'
    args=['backtesting','--config',str(cp),'--datadir',str(DATA/'gate'),'--timerange',start+'-20261103','--cache','none','--enable-protections','--export','trades','--backtest-directory',str(attempt)]
    parsed=setup_optimize_configuration(Arguments(args).get_parsed_arg(),RunMode.BACKTEST)
    install(DATA/'contract-source.json');funding_install()
    engine=type('IntegratedNative',(EventClockFunding,Backtesting),{})(parsed)
    if execution=='through':
        from freqtrade.optimize.backtesting import LOW_IDX,HIGH_IDX
        original=engine._try_close_open_order
        def through(order,trade,current_date,row):
            if order and order.ft_order_side==trade.entry_side and order.order_type=='limit':
                tick=read(OUT/'contracts.json')[trade.pair]['price_precision']
                if (trade.is_short and row[HIGH_IDX]<order.ft_price+tick) or (not trade.is_short and row[LOW_IDX]>order.ft_price-tick): return False
            return original(order,trade,current_date,row)
        engine._try_close_open_order=through
    engine.start()
    archive=attempt/read(attempt/'.last_result.json')['latest_backtest']
    with zipfile.ZipFile(archive) as z:
        member=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
        result=__import__('json').loads(z.read(member))
    write(dest/'result.json',result)
    write(dest/'states.json',[dict(id=t.id,pair=t.pair,open_date=t.open_date_utc.isoformat(),plan=t.get_custom_data('policy_plan'),state=t.get_custom_data('policy_state'),funding=t.get_custom_data('v3_funding_events',[])) for t in LocalTrade.bt_trades])
    write(dest/'provenance.json',dict(at=now(),args=args,strategy=name,variant=variant,timeframe=timeframe,fee_per_side=fee,execution=execution,
        archive=str(archive.relative_to(ROOT)),archive_sha256=sha(archive),config_sha256=sha(cp),plans_sha256=sha(plans),
        decision_freeze_sha256=sha(freeze_path()),metadata_sha256=sha(DATA/'contract-source.json'),source_sha256=sha(OUT/'data.json'),
        staged_source_hashes={p.name:sha(p) for p in Path(cfg['strategy_path']).glob('*.py')},image=IMAGE,
        python=__import__('sys').version,freqtrade=__import__('freqtrade').__version__,ccxt=__import__('ccxt').__version__,
        funding='ACTUAL_EVENT_ONCE_WITH_ASOF_HOURLY_MARK_OPEN;SETTLEMENT_MARK_APPROXIMATION',
        classification='NEW_NATIVE_REPLAY_ON_BYTE_EQUAL_15M_HOURLY_SOURCES;GENUINE_5M_SEPARATE_COHORT' if five else 'NEW_NATIVE_REPLAY_ON_BYTE_EQUAL_15M_HOURLY_SOURCES'))
    trades=result['strategy'][name]['trades']
    print(label,len(trades),sum(t['profit_abs'] for t in trades),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('variant');p.add_argument('--fee',type=float,default=.00075)
    p.add_argument('--execution',choices=['touch','through'],default='touch');p.add_argument('--replay-id')
    a=p.parse_args();native(a.variant,a.fee,a.execution,a.replay_id)
