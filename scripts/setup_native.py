"""Official Freqtrade portfolio replay, reusing parent risk, funding and contracts."""
import os
import shutil
import zipfile
from setup_common import *

def stage():
    from recovery_native import stage as parent_stage
    source=parent_stage()
    files=list(source.glob('*.py'))+list((ROOT/'research/setup').glob('*.py'))
    seal=__import__('hashlib').sha256(''.join(sha(p) for p in sorted(files)).encode()).hexdigest()[:16]
    target=WORK/'strategies'/seal
    target.mkdir(parents=True,exist_ok=True)
    for p in files:
        if not (target/p.name).exists():shutil.copyfile(p,target/p.name)
    return target

def native(variant,risk=False,fee=.00075,execution='touch',half=False,detail=False,replay_id=None):
    from freqtrade.commands import Arguments
    from freqtrade.commands.optimize_commands import setup_optimize_configuration
    from freqtrade.enums import RunMode
    from freqtrade.optimize.backtesting import Backtesting
    from freqtrade.persistence import LocalTrade
    from recovery_funding import EventClockFunding,install as funding_install
    from session4_metadata import install
    if not (OUT/'freeze.json').exists():raise ValueError('freeze required')
    from setup_verify import verify
    verify()
    for file,digest in read(OUT/'freeze.json')['decision_source_hashes'].items():
        if sha(ROOT/file)!=digest:raise ValueError('frozen decision source changed: '+file)
    label=variant+('-risk' if risk else '-fixed')+'-'+execution+'-'+str(round(fee*1e6))+('-half' if half else '')+('-1m' if detail else '')
    if replay_id:
        import re
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,30}',replay_id):raise ValueError('invalid replay id')
        label+='-replay-'+replay_id
    dest=OUT/'native'/label
    if (dest/'result.json').exists():raise ValueError('completed native result exists')
    attempt=WORK/'native'/label/('attempt-'+str(len(list((WORK/'native'/label).glob('attempt-*')))+1))
    attempt.mkdir(parents=True)
    name='RecoveryPolicyR1' if variant.startswith('v4-') else 'SetupPolicyV1'
    cfg=read(ROOT/'configs/research-vwap.json');data=DATA/'development/gate'
    cfg.update(strategy=name,strategy_path=str(stage()),dry_run=True,dry_run_wallet=1000,stake_amount='unlimited',max_open_trades=2,
        tradable_balance_ratio=1.,stoploss=-.025,minimal_roi={'0':100.},fee=fee,db_url='sqlite://',
        policy_state=str(attempt/'account.sqlite'),policy_events=str(attempt/'events.jsonl'),policy_contracts=str(OUT/'contracts.json'),
        policy_marks=str(data/'futures'),policy_notional_cap=25.,policy_leverage=1,
        session4_features=str(WORK/'features'/('v4' if variant.startswith('v4-') else 'new')),
        session4_plans=str(WORK/'plans'/(variant+'.json')),session4_constant_risk=False,recovery_risk=risk,
        recovery_allocation_fraction=.5 if half else 1.,setup_management=variant=='management',position_adjustment_enable=variant=='management',lab_audit=False)
    cfg['exchange']['pair_whitelist']=pairs()
    for k in ['key','secret','password','uid','apiKey']:cfg['exchange'].pop(k,None)
    cfg.pop('api_server',None)
    cfg['order_types']=dict(entry='limit',exit='limit',stoploss='market',stoploss_on_exchange=False)
    for k in ['ccxt_config','ccxt_sync_config','ccxt_async_config']:
        cfg['exchange'].setdefault(k,{}).update(dict(has={'fetchCurrencies':False},requests_trust_env=True,options={'defaultType':'swap','fetchMarkets':{'types':['swap']}}))
        if os.environ.get('HTTPS_PROXY'):cfg['exchange'][k]['httpsProxy']=os.environ['HTTPS_PROXY']
        if os.environ.get('SSL_CERT_FILE'):cfg['exchange'][k]['cafile']=os.environ['SSL_CERT_FILE']
    cp=attempt/'config.json';write(cp,cfg)
    args=['backtesting','--config',str(cp),'--datadir',str(data),'--timerange',('20261029-20261103' if detail else '20260901-20261103'),'--cache','none','--enable-protections','--export','trades','--backtest-directory',str(attempt)]
    if detail:args+=['--timeframe-detail','1m']
    parsed=setup_optimize_configuration(Arguments(args).get_parsed_arg(),RunMode.BACKTEST)
    install(DATA/'contract-source.json');funding_install()
    engine=type('SetupNative',(EventClockFunding,Backtesting),{})(parsed)
    if execution in ('through','drop25'):
        from freqtrade.optimize.backtesting import LOW_IDX,HIGH_IDX
        original=engine._try_close_open_order
        def conservative(order,trade,current_date,row):
            if order and order.ft_order_side==trade.entry_side and order.order_type=='limit':
                if execution=='through' and ((trade.is_short and row[HIGH_IDX]<order.ft_price*1.0001) or (not trade.is_short and row[LOW_IDX]>order.ft_price*.9999)):return False
                if execution=='drop25' and int(__import__('hashlib').sha256(f'{trade.pair}:{order.order_date_utc}'.encode()).hexdigest()[:8],16)%4==0:return False
            return original(order,trade,current_date,row)
        engine._try_close_open_order=conservative
    engine.start()
    archive=attempt/read(attempt/'.last_result.json')['latest_backtest']
    with zipfile.ZipFile(archive) as z:
        member=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
        result=__import__('json').loads(z.read(member))
    write(dest/'result.json',result)
    write(dest/'states.json',[dict(id=t.id,pair=t.pair,open_date=t.open_date_utc.isoformat(),plan=t.get_custom_data('policy_plan'),state=t.get_custom_data('policy_state'),funding=t.get_custom_data('v3_funding_events',[])) for t in LocalTrade.bt_trades])
    write(dest/'provenance.json',dict(at=now(),args=args,strategy=name,risk=risk,fee_per_side=fee,execution=execution,half=half,detail=detail,
        archive=str(archive.relative_to(ROOT)),archive_sha256=sha(archive),config_sha256=sha(cp),
        plans_sha256=sha(WORK/'plans'/(variant+'.json')),feature_sha256=sha(OUT/'features.json'),source_sha256=sha(OUT/'data-development.json'),
        freeze_sha256=sha(OUT/'freeze.json'),staged_source_hashes={p.name:sha(p) for p in Path(cfg['strategy_path']).glob('*.py')},
        source_funding='ACTUAL_EVENT_CLOCK_ASOF_HOURLY_MARK_OPEN_EVENT_ONCE',engine='Freqtrade2026.10_CCXT4.5.90'))
    trades=result['strategy'][name]['trades'];print(label,len(trades),sum(t['profit_abs'] for t in trades),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('variant');p.add_argument('--risk',action='store_true');p.add_argument('--fee',type=float,default=.00075)
    p.add_argument('--execution',choices=['touch','through','drop25'],default='touch');p.add_argument('--half',action='store_true');p.add_argument('--detail',action='store_true');p.add_argument('--replay-id')
    a=p.parse_args();native(a.variant,a.risk,a.fee,a.execution,a.half,a.detail,a.replay_id)
