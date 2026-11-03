"""The official pinned Freqtrade engine with persistent event-once research funding."""
import json
import zipfile
import pandas as pd
from policy_common import *

class PersistentFunding:
    def _run_funding_fees(self,trade,current_time,force=False):
        from freqtrade.enums import TradingMode
        if self.trading_mode!=TradingMode.FUTURES or not(force or current_time.timestamp()%self.funding_fee_timeframe_secs==0):return
        f=self.futures_data[trade.pair]
        if not f.date.is_monotonic_increasing or f.date.duplicated().any():raise ValueError('unordered funding source')
        cursor=trade.get_custom_data('v3_funding_cursor')
        entry_clocks=[o.order_filled_utc for o in trade.orders if o.ft_order_side==trade.entry_side and o.filled and o.order_filled_utc]
        if not entry_clocks:return
        first_fill=min(entry_clocks)
        eligible=f.loc[(f.date>=pd.Timestamp(first_fill))&(f.date<=pd.Timestamp(current_time))]
        if cursor is not None:eligible=eligible.loc[eligible.date>pd.Timestamp(cursor)]
        fee=0.
        if len(eligible):
            fee=self.exchange.calculate_funding_fees(eligible,amount=trade.amount,is_short=trade.is_short,open_date=first_fill,close_date=current_time)
            trade.set_custom_data('v3_funding_cursor',eligible.date.iloc[-1].isoformat())
            ledger=trade.get_custom_data('v3_funding_events',[])
            for _,r in eligible.iterrows():
                ledger.append(dict(at=r.date.isoformat(),quantity=float(trade.amount),rate=float(r.open_fund),mark=float(r.open_mark)))
            trade.set_custom_data('v3_funding_events',ledger)
        trade.set_funding_fees(float(trade.funding_fee_running or 0)+fee)


def native(run_id,name,period='all',lev=1,diagnostic=None):
    from freqtrade.commands import Arguments
    from freqtrade.commands.optimize_commands import setup_optimize_configuration
    from freqtrade.enums import RunMode
    from freqtrade.optimize.backtesting import Backtesting
    out,data,spec=verify(run_id);cfg_path=config(run_id,name,diagnostic or period,lev)
    timerange=spec['evaluation_timerange'] if period=='all' else {'october':'20261001-20261101','detail':'20261028-20261102','newday':'20261101-20261102'}[period]
    base=ROOT/'user_data/backtest_results/policy'/run_id/name/period/('lev'+str(lev))
    directory=base/('attempt-'+str(len(list(base.glob('attempt-*')))+1).zfill(3))
    args=['backtesting','--config',str(cfg_path),'--datadir',str(data),'--timerange',timerange,'--fee',str(spec['fee_per_side']),
        '--cache','none','--enable-protections','--export','trades','--backtest-directory',str(directory)]
    if period in ('detail','newday'):
        if not read(out/'detail-manifest.json')['all_valid']:raise ValueError('detail source incomplete')
        args+=['--timeframe-detail','1m']
    if diagnostic:
        from freqtrade.main import main
        args=[diagnostic,'--config',str(cfg_path),'--datadir',str(data),'--timerange',timerange]
        if diagnostic=='lookahead-analysis':args+=['--minimum-trade-amount','5','--targeted-trade-amount','8','--allow-limit-orders','--lookahead-analysis-exportfilename',str(out/'diagnostics'/(name+'-lookahead.csv'))]
        else:args+=['--startup-candle','240','480','960']
        return main(args)
    if directory.exists():raise ValueError('preserve native attempt directory')
    directory.mkdir(parents=True)
    parsed=Arguments(args).get_parsed_arg();cfg=setup_optimize_configuration(parsed,RunMode.BACKTEST)
    class NativeBacktesting(PersistentFunding,Backtesting):pass
    engine=NativeBacktesting(cfg)
    # Gate can return a partial all-market tier response. Use only the actual
    # per-market snapshot captured before outcomes, never invented tiers.
    tier_source=data.parent/'contract-source.json'
    captured=read(tier_source);tier_fallback=[]
    for symbol in spec['pairs']:
        original=captured[symbol];market=engine.exchange.markets[symbol]
        if market['id']!=original['market']['id'] or market['contractSize']!=original['market']['contractSize']:
            raise ValueError('contract identity changed; snapshot fallback unsupported')
        if symbol not in engine.exchange._leverage_tiers:
            if not original['tiers']:raise ValueError('no native or captured leverage tiers; unsupported '+symbol)
            engine.exchange._leverage_tiers[symbol]=[engine.exchange.parse_leverage_tier(t) for t in original['tiers']]
            tier_fallback.append(symbol)
    engine.start()
    archive=directory/read(directory/'.last_result.json')['latest_backtest']
    with zipfile.ZipFile(archive) as z:
        member=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
        result=json.loads(z.read(member))
    label=name+'-'+period+'-'+str(lev)
    write(out/'native-results'/(label+'.json'),result)
    write(out/'native-provenance'/(label+'.json'),dict(engine='freqtrade 2026.10',image=IMAGE,
        args=args,config_sha256=sha(cfg_path),archive_sha256=sha(archive),archive_local_path=str(archive.relative_to(ROOT)),
        data_manifest_sha256=sha(out/'data-manifest.json'),captured_tier_source_sha256=sha(tier_source),native_missing_tiers_restored_from_actual_snapshot=tier_fallback,native_trades=result['strategy'][name]['total_trades'],
        funding='NATIVE_CALCULATE_FUNDING_FEES_WITH_PERSISTED_EVENT_CURSOR; event before same-clock exit; venue priority UNKNOWN'))
    # Preserve native custom state (not exported by the standard result ZIP).
    from freqtrade.persistence import LocalTrade
    states=[]
    for t in LocalTrade.bt_trades:
        states.append(dict(id=t.id,pair=t.pair,open_date=t.open_date_utc.isoformat(),
            plan=t.get_custom_data('policy_plan'),state=t.get_custom_data('policy_state'),funding_events=t.get_custom_data('v3_funding_events',[])))
    write(out/'trade-states'/(label+'.json'),states)
    print(label,result['strategy'][name]['total_trades'],result['strategy'][name]['profit_total_abs'],flush=True)
