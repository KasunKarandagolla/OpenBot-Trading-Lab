"""Export native trades and cost sensitivities; never simulates orders."""
import csv
import hashlib
import json
from pathlib import Path
import zipfile
import pandas as pd
ROOT=Path('/lab')


def summarize(trades):
    if not trades:
        return {'trades':0,'wins':0,'losses':0,'draws':0,'win_rate':None,'profit_factor':None,'expectancy_usdt':None,'trading_days':0,'hold_minutes':{}}
    df=pd.DataFrame(trades)
    pnl=df.profit_abs
    gain=float(pnl[pnl>0].sum()); loss=-float(pnl[pnl<0].sum())
    return {'trades':len(df),'wins':int((pnl>0).sum()),'losses':int((pnl<0).sum()),'draws':int((pnl==0).sum()),
      'win_rate':float((pnl>0).mean()),'profit_factor':gain/loss if loss>0 else None,
      'expectancy_usdt':float(pnl.mean()),'average_trade_ratio':float(df.profit_ratio.mean()),
      'trading_days':int(pd.to_datetime(df.open_date,utc=True).dt.date.nunique()),
      'hold_minutes':{str(q):float(df.trade_duration.quantile(q)) for q in [0,.25,.5,.75,.95,1]},
      'exit_reasons':df.exit_reason.value_counts().to_dict(),
      'per_pair_usdt':df.groupby('pair').profit_abs.sum().to_dict()}


def main():
    folder=ROOT/'user_data/backtest_results'
    pointer=json.loads((folder/'.last_result.json').read_text())
    path=folder/pointer['latest_backtest']
    with zipfile.ZipFile(path) as z:
        name=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
        raw=z.read(name); native=json.loads(raw)
    result=native['strategy']['TrendPullbackBaselineV1']; trades=result['trades']
    out=ROOT/'evidence/session-1'
    # Native result retains complete trade data, not reconstructed performance.
    (out/'native-backtest-result.json').write_bytes(raw)
    # Native config contains no UI credentials (backtest uses research.json).
    fields=['pair','is_short','open_date','close_date','open_rate','close_rate','amount','stake_amount','leverage','fee_open','fee_close','funding_fees','trade_duration','exit_reason','profit_ratio','profit_abs','is_open']
    with (out/'trade-ledger.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(trades)
    stats=summarize(trades)
    fees=sum(t['amount']*(t['open_rate']*t['fee_open']+t['close_rate']*t['fee_close']) for t in trades)
    funding=sum(t.get('funding_fees',0) or 0 for t in trades)
    geometric=sum(t['amount']*(t['close_rate']-t['open_rate'])*(-1 if t.get('is_short') else 1) for t in trades)
    net=sum(t['profit_abs'] for t in trades)
    sensitivity=[]
    for bps in [0,5,10,20]:
        friction=sum(t['amount']*(t['open_rate']+t['close_rate'])*bps/10000 for t in trades)
        sensitivity.append({'extra_bps_per_side':bps,'extra_cost_usdt':friction,'net_usdt_after_extra_cost':net-friction,'return_on_initial_1000_pct':(net-friction)/10})
    report={'status':'EXPLORATORY / UNQUALIFIED','native_file':path.name,'native_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
      'summary':stats,'net_profit_usdt':net,'native_profit_total_ratio':result.get('profit_total'),
      'native_max_drawdown_account':result.get('max_drawdown_account'),
      'native_max_drawdown_usdt':result.get('max_drawdown_abs'),
      'geometric_price_pnl_before_fees_and_funding_usdt':geometric,'reconstructed_fees_usdt':fees,
      'native_funding_sum_usdt':funding,'reconciliation_residual_usdt':net-(geometric-fees+funding),
      'sensitivity':sensitivity,'fees':'0.0006 per side, applied entry and exit; conservative assumption, not verified account tier',
      'funding':'Native funding_fees from actual downloaded events; inspect dataset manifest for completeness; no zero-funding fallback configured.',
      'limitations':['Candle backtest assumes requested-price fills; no measured historical spread/slippage, order-book depth, latency or outage model.',
        'Extra friction is a postprocessing sensitivity only; it does not change fills, sequencing or drawdown.',
        'Current surviving static BTC/ETH/SOL contracts; historical universe membership not reconstructed.',
        '1x leverage fixed; liquidation accuracy not validated. No independent holdout or economic qualification.',
        'No exact 0.25%/0.50% monetary-risk or 1% daily-loss halt guarantee. Paper stops require running process.']}
    (out/'backtest-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    text=f'''# Baseline real-market backtest — EXPLORATORY / UNQUALIFIED

Native Freqtrade 2026.10, Gate USDT perpetuals BTC/ETH/SOL. Evaluation 2026-07-30 00:00 UTC to 2026-10-30 00:00 UTC (end exclusive). Data starts July 26 for 200-bar warm-up. Static current surviving universe; no historical dynamic VolumePairList. Strategy frozen before outcome inspection; no tuning.

- Trades: {stats['trades']}; wins {stats['wins']}, losses {stats['losses']}, draws {stats['draws']}; win rate {stats['win_rate']}.
- Net modeled profit: {net:.8f} USDT ({net/10:.6f}% of initial 1,000 wallet).
- Native max drawdown: {result.get('max_drawdown_account')} of account; {result.get('max_drawdown_abs')} USDT.
- Average/expectancy: {stats['expectancy_usdt']} USDT/trade; profit factor {stats['profit_factor']} (null if undefined).
- Distinct entry UTC days: {stats['trading_days']} (correlated crypto trades are not independent samples).
- Geometric price P&L before fees/funding: {geometric:.8f} USDT; reconstructed entry+exit fees: {fees:.8f}; native signed funding: {funding:.8f}.
- Reconciliation residual: {net-(geometric-fees+funding):.10f} USDT.
- Fees: 0.0006 per side, conservative research assumption, not verified exchange account rate.
- Wallet 1,000 USDT; fixed 25 USDT stake; 1x; max 2 positions; protections enabled.

## Additional spread/slippage sensitivity

| Extra basis points per side | Additional cost USDT | Net profit USDT |
|---|---:|---:|
'''
    for s in sensitivity: text+=f"| {s['extra_bps_per_side']} | {s['extra_cost_usdt']:.6f} | {s['net_usdt_after_extra_cost']:.6f} |\n"
    text+='\nThese are extra costs beyond native fees/funding, not measured historical spreads or a new fill simulation. Holding quantiles, exit counts and per-pair contributions are in [backtest-summary.json](backtest-summary.json). Full native trade/result JSON and CSV are retained. Research files/checksums, gaps and funding/mark coverage are in [market-data-manifest.json](market-data-manifest.json).\n\n'
    text+='\n'.join('- '+x for x in report['limitations'])+'\n'
    (out/'backtest-report.md').write_text(text)
    print(json.dumps({k:report[k] for k in ['status','summary','net_profit_usdt','native_max_drawdown_account','native_max_drawdown_usdt','reconciliation_residual_usdt']},indent=2))

if __name__=='__main__':main()
