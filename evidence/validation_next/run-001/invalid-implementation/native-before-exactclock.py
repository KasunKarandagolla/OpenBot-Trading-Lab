"""Freqtrade native, offline Binance fixture scenario; no orders or API calls."""
import shutil,zipfile,inspect
from validation_next_common import *
IMAGE='freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7'

def stage():
 from diagnosis_native import stage as oldstage
 target=WORK/'strategies';target.mkdir(exist_ok=True)
 for p in oldstage().glob('*.py'):shutil.copyfile(p,target/p.name)
 for p in (ROOT/'research/validation_next').glob('*.py'):shutil.copyfile(p,target/p.name)
 return target

def install_metadata():
 from freqtrade.exchange.exchange import Exchange
 markets=read(ROOT/'research/validation_next/binance-fixture-markets.json')
 def load(self,reload=False):
  if self.name.lower()!='binance' or not self._config.get('validation_fixture_scenario') or not self._config.get('dry_run'):raise ValueError('fixture scope')
  self._api_async.set_markets(list(markets.values()))
 Exchange._load_async_markets=load

def run(partition,variant,detail=False,through=False,fee=.0005):
 import pandas as pd
 from freqtrade.commands import Arguments
 from freqtrade.commands.optimize_commands import setup_optimize_configuration
 from freqtrade.enums import RunMode
 from freqtrade.optimize.backtesting import Backtesting,DATE_IDX,LOW_IDX,HIGH_IDX
 from freqtrade.persistence import LocalTrade
 from recovery_funding import EventClockFunding,install as funding_install
 from PaperPolicyV4 import PaperPolicyV4
 if fee not in (.0005,.0015):raise ValueError('unregistered fee')
 verify_old();verify_sources();seal=read(OUT/('plans-'+partition+'.json'))
 if partition=='holdout':
  frozen=read(OUT/'evaluation-freeze.json')
  for p,h in frozen['code_hashes'].items():
   if sha(ROOT/p)!=h:raise ValueError('evaluation code changed '+p)
 for p,h in seal['features'].items():
  if sha(ROOT/p)!=h:raise ValueError('feature hash')
 path=WORK/partition/'plans'/(variant+'.json')
 if sha(path)!=seal['plans'][variant]['sha256']:raise ValueError('plan hash')
 label=partition+'-'+variant+('-detail5m' if detail else '-15m')+('-through' if through else '-touch')+'-fee'+str(round(fee*1e6))
 dest=OUT/'native'/label
 if (dest/'result.json').exists():raise ValueError('completed native result preserved')
 attempt=WORK/'native'/label/('attempt-'+str(len(list((WORK/'native'/label).glob('attempt-*')))+1));attempt.mkdir(parents=True)
 cfg=read(ROOT/'configs/research-vwap.json');cfg.update(strategy='ValidationPolicyR1',strategy_path=str(stage()),user_data_dir=str(ROOT/'user_data'),timeframe='15m',startup_candle_count=960,dry_run=True,dry_run_wallet=1000,stake_amount='unlimited',max_open_trades=2,tradable_balance_ratio=1.,stoploss=-.025,minimal_roi={'0':100.},fee=fee,db_url='sqlite://',policy_state=str(attempt/'account.sqlite'),policy_events=str(attempt/'events.jsonl'),policy_contracts=str(OUT/'scenario-contracts.json'),policy_marks=str(DATA/'binance/futures'),policy_notional_cap=25.,policy_leverage=1,session4_features=str(WORK/partition/'features'),session4_plans=str(path),session4_constant_risk=False,recovery_risk=False,recovery_allocation_fraction=1.,position_adjustment_enable=False,setup_management=False,lab_audit=False,integrated_structural_exit=variant in ('structural-transfer','thesis-compatible-transfer'),diagnosis_thesis_guard=variant=='thesis-compatible-transfer',validation_fixture_scenario=True)
 cfg['exchange'].update(name='binance',pair_whitelist=pairs(),pair_blacklist=[])
 for k in ('key','secret','password','uid','apiKey'):cfg['exchange'].pop(k,None)
 cfg.pop('api_server',None);cfg['unfilledtimeout'].update(entry=5,exit=5,unit='minutes')
 for k in ('ccxt_config','ccxt_sync_config','ccxt_async_config'):cfg['exchange'][k]=dict(enableRateLimit=True,has={'fetchCurrencies':False},options={'defaultType':'swap','fetchMarkets':{'types':['linear']}})
 cp=attempt/'config.json';write(cp,cfg);begin,end=spec()['partitions'][partition]
 args=['backtesting','--config',str(cp),'--datadir',str(DATA/'binance'),'--timerange',begin.replace('-','')+'-'+end.replace('-',''),'--cache','none','--enable-protections','--export','trades','--backtest-directory',str(attempt)]
 if detail:args+=['--timeframe-detail','5m']
 parsed=setup_optimize_configuration(Arguments(args).get_parsed_arg(),RunMode.BACKTEST)
 install_metadata();funding_install();engine=type('ValidationNative',(EventClockFunding,Backtesting),{})(parsed)
 observations=[];orders={};trades={};terminals=[]
 original_enter=engine._enter_trade
 def enter(pair,row,direction,*a,**kw):
  t=original_enter(pair,row,direction,*a,**kw);observations.append(dict(event='ENTER_ATTEMPT',pair=pair,at=row[DATE_IDX].isoformat(),side=direction,trade_id=t.id if t else None))
  if t:
   trades[t.id]=t
   for o in t.orders:orders[(t.id,o.order_id)]=(t,o)
  return t
 engine._enter_trade=enter
 original_capacity=engine._collate_rejected
 def capacity(pair,row):
  observations.append(dict(event='CAPACITY_REJECT',pair=pair,at=row[DATE_IDX].isoformat()));return original_capacity(pair,row)
 engine._collate_rejected=capacity
 original_risk=PaperPolicyV4.risk_size
 def risk(self,pair,clock,side,rate,lev,min_stake=0):
  r=original_risk(self,pair,clock,side,rate,lev,min_stake);observations.append(dict(event='RISK',pair=pair,at=clock.isoformat(),side=side,rate=rate,verdict=r));return r
 PaperPolicyV4.risk_size=risk
 original_manage=engine.manage_open_orders
 def manage(trade,clock,row):
  pending=[o for o in trade.orders if o.ft_order_side==trade.entry_side and not o.filled];answer=original_manage(trade,clock,row)
  if answer:
   for o in pending:terminals.append(dict(pair=trade.pair,trade_id=trade.id,order_id=o.order_id,created_at=o.order_date_utc.isoformat(),terminal_at=clock.isoformat(),age_minutes=(clock-o.order_date_utc).total_seconds()/60,plan_expires_at=(trade.get_custom_data('policy_plan') or {}).get('expires_at'),native_timeout=cfg['unfilledtimeout']['entry'],status='REMOVED_UNFILLED_ENTRY'))
  return answer
 engine.manage_open_orders=manage
 if through:
  original_fill=engine._try_close_open_order;contracts=read(OUT/'scenario-contracts.json')
  def fill(o,t,clock,row):
   if o and o.ft_order_side==t.entry_side and o.order_type=='limit':
    tick=contracts[t.pair]['price_precision']
    if (t.is_short and row[HIGH_IDX]<o.ft_price+tick) or (not t.is_short and row[LOW_IDX]>o.ft_price-tick):return False
   return original_fill(o,t,clock,row)
  engine._try_close_open_order=fill
 try:engine.start()
 finally:PaperPolicyV4.risk_size=original_risk
 archive=attempt/read(attempt/'.last_result.json')['latest_backtest']
 with zipfile.ZipFile(archive) as z:
  n=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n);result=__import__('json').loads(z.read(n))
 write(dest/'result.json',result)
 states=[]
 for t in LocalTrade.bt_trades:states.append(dict(id=t.id,pair=t.pair,open_date=t.open_date_utc.isoformat(),plan=t.get_custom_data('policy_plan'),state=t.get_custom_data('policy_state'),funding=t.get_custom_data('v3_funding_events',[])))
 write(dest/'states.json',states)
 for t in trades.values():
  for o in t.orders:orders[(t.id,o.order_id)]=(t,o)
 order_rows=[]
 for t,o in orders.values():
  g=t.get_custom_data('policy_plan') or read(path).get(t.pair,{}).get(t.open_date_utc.isoformat())
  order_rows.append(dict(trade_id=t.id,pair=t.pair,side='short' if t.is_short else 'long',order_id=o.order_id,is_entry=o.ft_order_side==t.entry_side,order_type=o.order_type,status=o.status,created_at=o.order_date_utc.isoformat(),filled_at=o.order_filled_utc.isoformat() if o.filled and o.order_filled_utc else None,price=float(o.safe_price),amount=float(o.amount),filled=float(o.filled or 0),decision_id=g['decision_id'] if g else None,plan_expires_at=g['expires_at'] if g else None))
 write(dest/'order-audit.json',dict(orders=order_rows,observations=observations,terminal_events=terminals))
 write(dest/'provenance.json',dict(at=now(),args=args,partition=partition,variant=variant,detail_5m=detail,trade_through=through,fee_per_side=fee,config_sha256=sha(cp),plans_sha256=sha(path),archive=str(archive.relative_to(ROOT)),archive_sha256=sha(archive),image=IMAGE,freqtrade=__import__('freqtrade').__version__,ccxt=__import__('ccxt').__version__,engine_source_sha256=sha(inspect.getfile(Backtesting)),scenario_contracts_sha256=sha(OUT/'scenario-contracts.json'),metadata='PUBLIC_CCXT_FIXTURE;NOT_HISTORICAL_EXCHANGEINFO',funding='ACTUAL_EVENT_ONCE;PRECEDING_1H_MARK_OPEN;EXACT_SETTLEMENT_MARK_UNKNOWN',economic_status='PARTIAL_COST_MODEL / INSUFFICIENT_ECONOMIC_VALIDATION'))
 trades_out=next(iter(result['strategy'].values()))['trades'];print(label,len(trades_out),sum(x['profit_abs'] for x in trades_out),flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('partition',choices=['development','validation','holdout']);p.add_argument('variant');p.add_argument('--detail',action='store_true');p.add_argument('--through',action='store_true');p.add_argument('--fee',type=float,default=.0005);a=p.parse_args();run(a.partition,a.variant,a.detail,a.through,a.fee)
