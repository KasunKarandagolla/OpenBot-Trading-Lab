"""Network-disabled native Freqtrade comparison, reusing the existing archive engine."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import pandas as pd
from freqtrade.commands import Arguments
from freqtrade.commands.optimize_commands import setup_optimize_configuration
from freqtrade.enums import RunMode
from freqtrade.persistence import LocalTrade
from local_recovery_backtest import RecoveryBacktest, install_snapshot, IMAGE
from local_recovery_data import ROOT, WORK, write_json


def run(strategy, start, end, destination, plans_file=None, mode='through', fee=.0005):
    from trading_lab.panel import ArchivePanel
    panel=ArchivePanel()
    native_pins=json.loads((ROOT/'research/session3_v3/native-data-pins.json').read_text())
    for name,expected in native_pins.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('NATIVE_SOURCE_CONVERSION_DRIFT:'+name)
    dest=Path(destination)
    if dest.exists():raise ValueError('PRESERVE_COMPLETED_OR_INTERRUPTED_RUN_USE_NEW_DIRECTORY')
    dest.mkdir(parents=True)
    symbols=json.loads((ROOT/'research/session3_v3/panel-pins.json').read_text())['symbols']
    metadata=json.loads((ROOT/'research/session3_v3/native-metadata-pin.json').read_text())
    if hashlib.sha256((ROOT/metadata['snapshot']).read_bytes()).hexdigest()!=metadata['sha256']:raise ValueError('METADATA_SNAPSHOT_DRIFT')
    markets=install_snapshot(symbols)
    plans={}
    if plans_file:
        doc=json.loads(Path(plans_file).read_text())
        if doc['source_id']!=panel.identity:raise ValueError('PLAN_SOURCE_IDENTITY')
        if doc['feature_version']!='multi-playbook-v3.0.2':raise ValueError('PLAN_SOURCE_VERSION')
        for name,expected in doc['code_sha256'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('PLAN_KERNEL_DRIFT')
        book='BREAKOUT_RETEST' if strategy.startswith('Breakout') else 'SWEEP_RECLAIM'
        plans={p['decision_id']:p for p in doc['plans'] if p['family']==book and p['diagnostics']=='GEOMETRY_PASS_RESEARCH_ONLY'}
    config_name={'TrendPullbackBaselineV1':'research.json','LiquiditySweepReversalV1':'research-sweep.json'}.get(strategy,'research-vwap.json')
    cfg=json.loads((ROOT/'configs'/config_name).read_text())
    challenger=bool(plans_file)
    strategy_path=ROOT/('research/session3_v3' if challenger else 'user_data/strategies')
    cfg.update(strategy=strategy,strategy_path=str(strategy_path),user_data_dir=str(ROOT/'user_data'),
               timeframe='5m' if challenger else '15m',fee=fee,dry_run=True,dry_run_wallet=1000,
               max_open_trades=2,stake_amount=25,db_url='sqlite://',lab_audit=False,
               pairlists=[{'method':'StaticPairList'}],custom_price_max_distance_ratio=1.,
               position_adjustment_enable=False,initial_state='stopped')
    cfg['exchange']=dict(name='binance',key='',secret='',pair_whitelist=list(markets),pair_blacklist=[],
                         ccxt_config={'has':{'fetchCurrencies':False}},ccxt_async_config={'has':{'fetchCurrencies':False}})
    cfg['order_types'].update(entry='market' if mode=='market' else 'limit')
    if challenger:cfg['order_types']['exit']='market'
    if challenger:
        pfile=dest/'selected-plans.json';write_json(pfile,list(plans.values()))
        cfg.update(recovery_plans=str(pfile),plan_sha256=hashlib.sha256(pfile.read_bytes()).hexdigest(),
                   stoploss=-.025,minimal_roi={'0':100.})
    path=dest/'config.json';write_json(path,cfg)
    args=['backtesting','--config',str(path),'--datadir',str(WORK/'binance'),
          '--timerange',start.replace('-','')+'-'+end.replace('-',''),'--cache','none',
          '--export','trades','--backtest-directory',str(dest)]
    if not challenger:
        args += ['--timeframe-detail','5m']
    parsed=setup_optimize_configuration(Arguments(args).get_parsed_arg(),RunMode.BACKTEST)
    dates=[pd.Timestamp(x,tz='UTC') for x in (start,end)]
    engine=RecoveryBacktest(parsed,plans,dates,markets,mode)
    engine.start()
    archive=dest/json.loads((dest/'.last_result.json').read_text())['latest_backtest']
    with zipfile.ZipFile(archive) as z:
        name=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json'))
        native=json.loads(z.read(name))
    result=native['strategy'][strategy]
    ledger=result['trades']
    for trade in ledger:
        plan=plans.get(trade['enter_tag'])
        if plan:
            pure_stop_cash=trade['amount']*abs(trade['open_rate']-plan['stop'])
            trade.update(plan_id=plan['decision_id'],source_id=plan['source_id'],frozen_stop=plan['stop'],
                         frozen_target=plan['target'],after_cost_plan_rr=plan['net_rr'],
                         price_R=trade['profit_abs']/pure_stop_cash,
                         cost_inclusive_R=trade['profit_abs']/(pure_stop_cash+trade['amount']*trade['open_rate']*plan['admission_cost_allowance']))
        trade['fees_usdt']=trade['amount']*(trade['open_rate']*trade['fee_open']+trade['close_rate']*trade['fee_close'])
        trade['stress_net_usdt']={str(bp):trade['profit_abs']-bp/10000*trade['amount']*(trade['open_rate']+trade['close_rate']) for bp in [5,10,20]}
    ledger.sort(key=lambda t:(t['open_timestamp'],t['pair'],t['is_short']))
    terminal={}
    filled={t['enter_tag'] for t in ledger}
    for key,p in plans.items():
        terminal[key]='FILLED' if key in filled else ('EXPIRED_UNFILLED' if key in engine.expired else 'CAPACITY_REJECT' if key in engine.capacity else 'NATIVE_ENTRY_REJECT' if key in engine.entries else 'PAIR_OCCUPIED_OR_COLLIDING_SIGNAL_OR_NATIVE_SUPPRESSED')
    write_json(dest/'ledger.json',ledger)
    orders={key:[dict(price=o.safe_price,amount=o.amount,status=o.status,side=o.ft_order_side,
                     submitted_at=o.order_date_utc.isoformat(),filled_at=o.order_filled_utc.isoformat() if o.order_filled_utc else None)
                 for o in item['trade'].orders] for key,item in engine.entries.items() if item['trade'] is not None}
    write_json(dest/'orders.json',orders);write_json(dest/'terminal.json',terminal)
    summary=dict(strategy=strategy,start=start,end=end,entry_mode=mode,fee_per_side=fee,
                 trades=len(ledger),longs=sum(not t['is_short'] for t in ledger),shorts=sum(t['is_short'] for t in ledger),
                 native_net_usdt=sum(t['profit_abs'] for t in ledger),
                 funding_net_usdt=sum(t.get('funding_fees',0) for t in ledger),
                 max_drawdown_abs=result.get('max_drawdown_abs'),max_drawdown_account=result.get('max_drawdown_account'),
                 stress_net_usdt={str(bp):sum(t['stress_net_usdt'][str(bp)] for t in ledger) for bp in [5,10,20]},
                 native_metrics={k:result[k] for k in ['rejected_signals','timedout_entry_orders','canceled_trade_entries','max_open_trades'] if k in result},
                 archive=archive.name,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                 args=args,image=IMAGE,plan_count=len(plans),terminal_counts={s:list(terminal.values()).count(s) for s in sorted(set(terminal.values()))},
                 source_scope='CHECKSUM_REVERIFIED_BINANCE_ARCHIVES_PREVIOUSLY_STUDIED_PANEL',
                 historical_filters='2026-11-05 public snapshot; historical execution metadata UNQUALIFIED',
                 funding='Sourced event milliseconds, same-hour mark open; strict (entry,exit] event assignment. Marks are an hourly approximation.',
                 fill='Native next-candle execution; touch/one-tick-through candle model. Queue, real spread/impact and partial fills unknown.',
                 verdict='UNQUALIFIED' if ledger else 'INSUFFICIENT',execution_authority='NONE')
    write_json(dest/'summary.json',summary);print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('strategy');p.add_argument('--start',required=True);p.add_argument('--end',required=True)
    p.add_argument('--out',required=True);p.add_argument('--plans');p.add_argument('--mode',choices=['through','touch','market'],default='through')
    p.add_argument('--fee',type=float,default=.0005)
    a=p.parse_args();run(a.strategy,a.start,a.end,a.out,a.plans,a.mode,a.fee)
