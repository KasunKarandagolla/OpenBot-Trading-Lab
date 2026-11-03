"""Complete registered portfolios in the official pinned Freqtrade engine."""
import shutil
import sys
import zipfile
from recovery_common import *

def stage():
    names=['user_data/strategies','research/session3','research/bonus','research/master_audit','research/foundation','research/intelligence','research/policy','research/session4','research/recovery']
    import hashlib
    seal=hashlib.sha256(''.join(sha(p) for name in names for p in sorted((ROOT/name).glob('*.py'))).encode()).hexdigest()[:16]
    target=WORK/'strategies'/seal;target.mkdir(parents=True,exist_ok=True);seen=set()
    for name in names:
        for p in (ROOT/name).glob('*.py'):
            if p.name=='__init__.py':continue
            if p.name in seen:raise ValueError('duplicate strategy module')
            seen.add(p.name)
            dest=target/p.name
            if not dest.exists():shutil.copyfile(p,dest)
            elif sha(dest)!=sha(p):raise ValueError('sealed staged module changed '+p.name)
    return target

def native(window,variant,risk=False,execution='touch',fee=.00075,detail=False,half=False,management='native',replay_id=None):
    from freqtrade.commands import Arguments
    from freqtrade.commands.optimize_commands import setup_optimize_configuration
    from freqtrade.enums import RunMode
    from freqtrade.optimize.backtesting import Backtesting
    from freqtrade.persistence import LocalTrade
    from recovery_funding import EventClockFunding
    from session4_metadata import install
    import os
    import pandas as pd
    registered=read(OUT/('plans-'+window+'.json'))
    if variant not in registered:
        parent=read(OUT/'parent-plan-restoration.json') if (OUT/'parent-plan-restoration.json').exists() else {}
        if window!='development' or variant not in parent.get('plans',{}):raise ValueError('unregistered plans')
        if sha(WORK/window/'plans'/(variant+'.json'))!=parent['plans'][variant]['sha256']:raise ValueError('parent plan seal differs')
    if not (OUT/'freeze.json').exists():raise ValueError('protocol not frozen')
    label=f'{variant}-'+('risk' if risk else 'fixed')+'-'+execution+'-fee'+str(round(fee*1e6))+('-1m' if detail else '')+('-half' if half else '')+('-barriers' if management=='barriers-only' else '')
    if replay_id:
        import re
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,30}',replay_id):raise ValueError('invalid replay id')
        label+='-replay-'+replay_id
    dest=OUT/'native'/window/label
    if (dest/'result.json').exists():raise ValueError('preserve completed portfolio '+label)
    attempt=WORK/window/'native'/label/('attempt-'+str(len(list((WORK/window/'native'/label).glob('attempt-*')))+1).zfill(3))
    attempt.mkdir(parents=True)
    hourly=window.startswith('hourly-');name='RecoveryMomentumHourlyR1' if hourly else 'RecoveryPolicyR1'
    cfg=read(ROOT/'configs/research-vwap.json');data=DATA/window/'gate'
    cfg.update(strategy=name,strategy_path=str(stage()),dry_run=True,dry_run_wallet=1000,
        stake_amount='unlimited',max_open_trades=2,tradable_balance_ratio=1.,stoploss=-.025,minimal_roi={'0':100.},
        position_adjustment_enable=False,fee=fee,db_url='sqlite://',policy_state=str(attempt/'account.sqlite'),
        policy_events=str(attempt/'events.jsonl'),policy_contracts=str(OUT/'contracts.json'),policy_marks=str(data/'futures'),
        policy_notional_cap=25.,policy_leverage=1,session4_features=str(WORK/window/'features'),
        session4_plans=str(WORK/window/'plans'/(variant+'.json')),session4_constant_risk=False,
        recovery_risk=risk,recovery_allocation_fraction=.5 if half else 1.,recovery_management=management,lab_audit=False)
    cfg['exchange']['pair_whitelist']=pairs()
    for k in ['key','secret','password','uid','apiKey']:cfg['exchange'].pop(k,None)
    cfg.pop('api_server',None)
    mode='market' if execution=='market' or variant in ('momentum','liquid-momentum') else 'limit'
    cfg['order_types']=dict(entry=mode,exit=mode,stoploss='market',stoploss_on_exchange=False)
    for k in ['ccxt_config','ccxt_sync_config','ccxt_async_config']:
        cfg['exchange'].setdefault(k,{}).update(dict(has={'fetchCurrencies':False},requests_trust_env=True,options={'defaultType':'swap','fetchMarkets':{'types':['swap']}}))
        if os.environ.get('HTTPS_PROXY'):cfg['exchange'][k]['httpsProxy']=os.environ['HTTPS_PROXY']
        if os.environ.get('SSL_CERT_FILE'):cfg['exchange'][k]['cafile']=os.environ['SSL_CERT_FILE']
    cp=attempt/'config.json';write(cp,cfg)
    if hourly:cfg['timeframe']='1h';cfg['startup_candle_count']=240;write(cp,cfg)
    timerange=('20261029-20261103' if 'development' in window else '20260721-20260726') if detail else ('20260805-20261103' if 'development' in window else '20260520-20260726' if hourly else '20260101-20260726')
    args=['backtesting','--config',str(cp),'--datadir',str(data),'--timerange',timerange,'--cache','none','--enable-protections','--export','trades','--backtest-directory',str(attempt)]
    if detail:args+=['--timeframe-detail','1m']
    parsed=setup_optimize_configuration(Arguments(args).get_parsed_arg(),RunMode.BACKTEST)
    install(DATA/'contract-source.json')
    from recovery_funding import install as funding_alignment
    funding_alignment()
    engine=type('RecoveryNative',(EventClockFunding,Backtesting),{})(parsed)
    if execution in ['through','open','drop25']:
        from freqtrade.optimize.backtesting import LOW_IDX,HIGH_IDX,OPEN_IDX
        original=engine._try_close_open_order
        def conservative(order,trade,current_date,row):
            if order and order.ft_order_side==trade.entry_side and order.order_type=='limit':
                if execution=='open':
                    if current_date>order.order_date_utc:return False
                    if not trade.is_short and row[OPEN_IDX]>order.ft_price:return False
                    if trade.is_short and row[OPEN_IDX]<order.ft_price:return False
                if execution=='through':
                    if trade.is_short and row[HIGH_IDX]<order.ft_price*1.0001:return False
                    if not trade.is_short and row[LOW_IDX]>order.ft_price*.9999:return False
                if execution=='drop25':
                    import hashlib
                    key=f'{trade.pair}:{order.order_date_utc.isoformat()}'
                    if int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%4==0:return False
            return original(order,trade,current_date,row)
        engine._try_close_open_order=conservative
    engine.start()
    archive=attempt/read(attempt/'.last_result.json')['latest_backtest']
    with zipfile.ZipFile(archive) as z:
        member=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
        result=__import__('json').loads(z.read(member))
    write(dest/'result.json',result)
    states=[dict(id=t.id,pair=t.pair,open_date=t.open_date_utc.isoformat(),plan=t.get_custom_data('policy_plan'),
                 state=t.get_custom_data('policy_state'),funding=t.get_custom_data('v3_funding_events',[])) for t in LocalTrade.bt_trades]
    write(dest/'states.json',states)
    write(dest/'provenance.json',dict(at=now(),args=args,label=label,window=window,variant=variant,risk=risk,execution=execution,
        fee_per_side=fee,detail=detail,half=half,management=management,config_sha256=sha(cp),archive_sha256=sha(archive),
        archive=str(archive.relative_to(ROOT)),plans_sha256=sha(WORK/window/'plans'/(variant+'.json')),
        feature_manifest_sha256=sha(OUT/('features-'+window+'.json')),source_manifest_sha256=sha(OUT/('data-'+window+'.json')),
        metadata_sha256=sha(DATA/'contract-source.json'),freeze_sha256=sha(OUT/'freeze.json'),
        strategy_source_hashes={x.name:sha(x) for x in Path(cfg['strategy_path']).glob('*.py')},
        engine_source_hashes={x:sha(ROOT/'scripts'/x) for x in ['recovery_native.py','recovery_common.py']},
        detail_source_manifest_sha256=sha(OUT/'detail-manifest.json') if detail else None,
        engine='FREQTRADE_2026.10_CCXT_4.5.90',image='freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7',
        constraints='1000USDT;1x;2positions;25USDT ceiling;0.25 modeled-risk target in risk mode; same native lot/risk/cooldown and source funding',
        funding_alignment='ACTUAL_EVENT_TIMESTAMPS;ASOF_LAST_SOURCE_HOURLY_MARK_OPEN<=1H;NO_EVENT_CLOCK_ROUNDING;NATIVE_SIGNED_FEES;EVENT_ONCE_CURSOR',
        partial_note='Half desired allocation scenario, NOT observed partial-order queue simulation' if half else None))
    trades=result['strategy'][name]['trades']
    print(window,label,len(trades),sum(t['profit_abs'] for t in trades),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('window',choices=['development','independent','hourly-development','hourly-independent']);p.add_argument('variant')
    p.add_argument('--risk',action='store_true');p.add_argument('--execution',default='touch',choices=['touch','through','open','market','drop25'])
    p.add_argument('--fee',type=float,default=.00075);p.add_argument('--detail',action='store_true');p.add_argument('--half',action='store_true');p.add_argument('--barriers',action='store_true')
    p.add_argument('--replay-id')
    a=p.parse_args();native(a.window,a.variant,a.risk,a.execution,a.fee,a.detail,a.half,'barriers-only' if a.barriers else 'native',a.replay_id)
