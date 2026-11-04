"""Native Freqtrade portfolios with nonmutating decision/order/capacity observers."""
import inspect
import os
import shutil
import zipfile
from diagnosis_common import *

IMAGE='freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7'

def stage():
    folders=['user_data/strategies','research/session3','research/bonus','research/master_audit','research/foundation','research/intelligence','research/policy','research/session4','research/recovery','research/setup','research/integrated','research/diagnosis']
    files=[p for d in folders for p in sorted((ROOT/d).glob('*.py')) if p.name!='__init__.py']
    identity=__import__('hashlib').sha256(''.join(sha(p) for p in files).encode()).hexdigest()[:16]
    target=WORK/'strategies'/identity;target.mkdir(parents=True,exist_ok=True)
    for p in files:
        dst=target/p.name
        if dst.exists() and sha(dst)!=sha(p):raise ValueError('staged collision')
        if not dst.exists():shutil.copyfile(p,dst)
    return target

def verify(cohort):
    verify_parent();seal=read(OUT/('plan-seal-'+cohort+'.json'))
    if sha(ROOT/'research/diagnosis/protocol.json')!=read(OUT/'preregistration.json')['sha256']:raise ValueError('protocol changed')
    for group in ('source_hashes','feature_hashes'):
        for p,h in seal[group].items():
            if sha(ROOT/p)!=h:raise ValueError('plan preparation source/input changed '+p)
    if cohort!='development':
        for row in read(OUT/'data-validation.json')[cohort]['files']:
            if sha(ROOT/row['path'])!=row['sha256']:raise ValueError('validation source changed')
    if (OUT/'execution-seal.json').exists():
        for p,h in read(OUT/'execution-seal.json')['source_hashes'].items():
            if sha(ROOT/p)!=h:raise ValueError('sealed execution source changed '+p)
    else:raise ValueError('seal native source before first result')
    return seal

def native(cohort,variant,fee=.00075,detail=False,short=False,through=False,replay_id=None):
    from freqtrade.commands import Arguments
    from freqtrade.commands.optimize_commands import setup_optimize_configuration
    from freqtrade.enums import RunMode
    from freqtrade.optimize.backtesting import Backtesting,DATE_IDX,LOW_IDX,HIGH_IDX
    from freqtrade.persistence import LocalTrade
    from recovery_funding import EventClockFunding,install as funding_install
    from session4_metadata import install
    from PaperPolicyV4 import PaperPolicyV4
    import pandas as pd
    seal=verify(cohort);entry=read(OUT/('plans-'+cohort+'.json'))[variant]
    planpath=WORK/cohort/'plans'/(variant+'.json')
    if sha(planpath)!=entry['sha256']:raise ValueError('native plan seal')
    if fee not in (.00075,.00175) or (detail and (not short or cohort!='development')):raise ValueError('unregistered experiment dimensions')
    label=f'{cohort}-{variant}'+('-oct5' if short else '')+('-detail5m' if detail else '')+('-through' if through else '-touch')+'-'+str(round(fee*1e6))+('-'+replay_id if replay_id else '')
    if replay_id and not __import__('re').fullmatch('[a-z0-9-]{3,30}',replay_id):raise ValueError('replay id')
    dest=OUT/'native'/label
    if (dest/'result.json').exists():raise ValueError('completed result preserved')
    attempt=WORK/'native'/label/('attempt-'+str(len(list((WORK/'native'/label).glob('attempt-*')))+1));attempt.mkdir(parents=True)
    features=PWORK/'features'/entry['features'] if cohort=='development' else WORK/cohort/'features'/entry['features']
    data=DATA/'gate' if cohort=='development' else ROOT/'user_data/data/diagnosis'/cohort/'gate'
    meta=DATA/'contract-source.json' if cohort=='development' else data.parent/'contract-source.json'
    name='RecoveryPolicyR1' if variant=='v4' else 'SetupPolicyV1' if variant=='pr12' else 'DiagnosisPolicyR1'
    cfg=read(ROOT/'configs/research-vwap.json')
    cfg.update(strategy=name,strategy_path=str(stage()),timeframe='15m',startup_candle_count=960,
        dry_run=True,dry_run_wallet=1000,stake_amount='unlimited',max_open_trades=2,tradable_balance_ratio=1.,stoploss=-.025,minimal_roi={'0':100.},
        fee=fee,db_url='sqlite://',policy_state=str(attempt/'account.sqlite'),policy_events=str(attempt/'events.jsonl'),policy_contracts=str(PARENT/'contracts.json'),
        policy_marks=str(data/'futures'),policy_notional_cap=25.,policy_leverage=1,session4_features=str(features),session4_plans=str(planpath),
        session4_constant_risk=False,recovery_risk=False,recovery_allocation_fraction=1.,position_adjustment_enable=False,setup_management=False,lab_audit=False,
        integrated_structural_exit=variant in ('structural','thesis-compatible'),diagnosis_thesis_guard=variant=='thesis-compatible')
    cfg['exchange']['pair_whitelist']=pairs()
    for k in ('key','secret','password','uid','apiKey'):cfg['exchange'].pop(k,None)
    cfg.pop('api_server',None);cfg['order_types']=dict(entry='limit',exit='limit',stoploss='market',stoploss_on_exchange=False)
    for k in ('ccxt_config','ccxt_sync_config','ccxt_async_config'):
        cfg['exchange'].setdefault(k,{}).update(dict(has={'fetchCurrencies':False},requests_trust_env=True,options={'defaultType':'swap','fetchMarkets':{'types':['swap']}}))
        if os.environ.get('HTTPS_PROXY'):cfg['exchange'][k]['httpsProxy']=os.environ['HTTPS_PROXY']
        if os.environ.get('SSL_CERT_FILE'):cfg['exchange'][k]['cafile']=os.environ['SSL_CERT_FILE']
    cp=attempt/'config.json';write(cp,cfg)
    window=read(ROOT/'research/diagnosis/protocol.json')['source_windows']['detail_cohort' if short else cohort]
    timerange=window[1].replace('-','')+'-'+window[2].replace('-','')
    args=['backtesting','--config',str(cp),'--datadir',str(data),'--timerange',timerange,'--cache','none','--enable-protections','--export','trades','--backtest-directory',str(attempt)]
    if detail:args+=['--timeframe-detail','5m']
    parsed=setup_optimize_configuration(Arguments(args).get_parsed_arg(),RunMode.BACKTEST)
    install(meta);funding_install()
    engine=type('DiagnosisNative',(EventClockFunding,Backtesting),{})(parsed)
    observations=[];trades={};orders={};risk_original=PaperPolicyV4.risk_size
    def risk_observer(self,pair,clock,side,rate,lev,min_stake=0):
        answer=risk_original(self,pair,clock,side,rate,lev,min_stake)
        observations.append(dict(event='NATIVE_RISK_SIZE',pair=pair,at=clock.isoformat(),side=side,rate=rate,verdict=answer))
        return answer
    PaperPolicyV4.risk_size=risk_observer
    original_enter=engine._enter_trade
    def entered(pair,row,direction,*a,**kw):
        before=len(observations);t=original_enter(pair,row,direction,*a,**kw)
        observations.append(dict(event='NATIVE_ENTER_ATTEMPT',pair=pair,at=row[DATE_IDX].isoformat(),side=direction,trade_id=t.id if t else None,
            observed_risk_events=observations[before:][-3:]))
        if t:
            trades[t.id]=t
            for o in t.orders:orders[(t.id,o.order_id)]=(t,o)
        return t
    engine._enter_trade=entered
    original_collate=engine._collate_rejected
    def capacity(pair,row):
        observations.append(dict(event='NATIVE_MAX_POSITION_REJECTION',pair=pair,at=row[DATE_IDX].isoformat(),positions=LocalTrade.bt_open_open_trade_count))
        return original_collate(pair,row)
    engine._collate_rejected=capacity
    original_loop=engine.backtest_loop
    def loop(row,pair,current_time,trade_dir,can_enter):
        is_signal=can_enter and trade_dir is not None
        before=len(observations)
        own_position=bool(LocalTrade.bt_trades_open_pp.get(pair))
        result=original_loop(row,pair,current_time,trade_dir,can_enter)
        if is_signal and not any(o['event'] in ('NATIVE_ENTER_ATTEMPT','NATIVE_MAX_POSITION_REJECTION') for o in observations[before:]):
            observations.append(dict(event='NATIVE_SIGNAL_NOT_ENTERED',pair=pair,at=current_time.isoformat(),side=trade_dir,
                existing_pair_position_at_loop_start=own_position,reason='EXISTING_PAIR_POSITION_OR_PAIR_LOCK;SEE_NATIVE_LOCKS_AND_POSITION_TIMES'))
        return result
    engine.backtest_loop=loop
    original_close=engine._try_close_open_order
    if through:
        contracts=read(PARENT/'contracts.json')
        def conservative(order,trade,current_date,row):
            if order and order.ft_order_side==trade.entry_side and order.order_type=='limit':
                tick=contracts[trade.pair]['price_precision']
                if (trade.is_short and row[HIGH_IDX]<order.ft_price+tick) or (not trade.is_short and row[LOW_IDX]>order.ft_price-tick):return False
            return original_close(order,trade,current_date,row)
        engine._try_close_open_order=conservative
    try:engine.start()
    finally:PaperPolicyV4.risk_size=risk_original
    archive=attempt/read(attempt/'.last_result.json')['latest_backtest']
    with zipfile.ZipFile(archive) as z:
        member=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
        result=__import__('json').loads(z.read(member))
    write(dest/'result.json',result)
    write(dest/'states.json',[dict(id=t.id,pair=t.pair,open_date=t.open_date_utc.isoformat(),plan=t.get_custom_data('policy_plan'),state=t.get_custom_data('policy_state'),funding=t.get_custom_data('v3_funding_events',[])) for t in LocalTrade.bt_trades])
    for t in trades.values():
        for o in t.orders:orders[(t.id,o.order_id)]=(t,o)
    plans=read(planpath);order_rows=[]
    for t,o in orders.values():
        g=t.get_custom_data('policy_plan') or plans.get(t.pair,{}).get(t.open_date_utc.isoformat())
        order_rows.append(dict(trade_id=t.id,pair=t.pair,side='short' if t.is_short else 'long',order_id=o.order_id,is_entry=o.ft_order_side==t.entry_side,
            order_type=o.order_type,status=o.status,created_at=o.order_date_utc.isoformat(),filled_at=o.order_filled_utc.isoformat() if o.filled and o.order_filled_utc else None,
            update_at=o.order_update_date.isoformat() if o.order_update_date else None,price=float(o.safe_price),amount=float(o.amount),filled=float(o.filled or 0),
            requested_reference=g['reference'] if g else None,decision_id=g['decision_id'] if g else None,opportunity_key=opportunity_key(t.pair,g) if g else None,
            plan_expires_at=g['expires_at'] if g else None))
    write(dest/'order-audit.json',dict(orders=order_rows,observations=observations))
    write(dest/'provenance.json',dict(at=now(),args=args,variant=variant,cohort=cohort,short_window=short,detail_5m=detail,fee_per_side=fee,trade_through=through,
        strategy=name,config_sha256=sha(cp),plans_sha256=sha(planpath),plan_seal_sha256=sha(OUT/('plan-seal-'+cohort+'.json')),
        execution_seal_sha256=sha(OUT/'execution-seal.json'),archive=str(archive.relative_to(ROOT)),archive_sha256=sha(archive),data_dir=str(data.relative_to(ROOT)),
        features_dir=str(features.relative_to(ROOT)),metadata_sha256=sha(meta),contracts_sha256=sha(PARENT/'contracts.json'),image=IMAGE,
        staged_hashes={p.name:sha(p) for p in Path(cfg['strategy_path']).glob('*.py')},python=__import__('sys').version,freqtrade=__import__('freqtrade').__version__,ccxt=__import__('ccxt').__version__,
        funding='REAL_SOURCE_EVENT_ONCE;ASOF_HOURLY_MARK_OPEN;NOT_EXACT_SETTLEMENT_MARK',queue='UNKNOWN_NATIVE_RANGE_TOUCH'))
    native_result=next(iter(result['strategy'].values()));print(label,len(native_result['trades']),sum(t['profit_abs'] for t in native_result['trades']),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('cohort',choices=['development','earlier','later']);p.add_argument('variant');p.add_argument('--fee',type=float,default=.00075)
    p.add_argument('--detail',action='store_true');p.add_argument('--short',action='store_true');p.add_argument('--through',action='store_true');p.add_argument('--replay-id')
    a=p.parse_args();native(a.cohort,a.variant,a.fee,a.detail,a.short,a.through,a.replay_id)
