"""After-cost native development comparison, accounting and source-event bounds."""
import json
from pathlib import Path
from master_review import independent_accounting,economics,funding_bounds,save,OUT


def main():
    directory=OUT/'native-results'
    rows=[];byname={}
    for path in sorted(directory.glob('*.json')):
        if path.name=='summary.json':continue
        result=json.loads(path.read_text())['strategy'][path.stem]
        trades=result['trades'];byname[path.stem]=trades
        bounds=funding_bounds(trades)
        rows.append(dict(strategy=path.stem,**economics(trades),
            internal_accounting=independent_accounting(trades),
            source_funding_outside_bounds=sum(x['outside'] for x in bounds),
            source_funding=bounds,
            native_closed_equity_drawdown_usdt=result['max_drawdown_abs'],
            native_closed_equity_drawdown_fraction=result['max_drawdown_account'],
            average_initial_notional=result['avg_stake_amount'],
            time_weighted_initial_notional=sum(t['stake_amount']*t['trade_duration'] for t in trades)/(86*1440),
            capital_limit='<=25 USDT initial notional/position, 1x, <=2 positions; no leveraged fill claim',
            drawdown_limit='Native closed-trade equity drawdown, not a full intraday account MTM audit',
            economic_qualification='BLOCKED_NO_INDEPENDENT_HOLDOUT'))
    key=lambda t:(t['pair'],t['open_timestamp'],t['is_short'])
    base={key(t):t for t in byname['RouterOnlyV1']}
    new={key(t):t for t in byname['AuditStructuralCloseM0V1']}
    assert base.keys()==new.keys()
    matched=[dict(pair=k[0],open_timestamp=k[1],short=k[2],old_net=base[k]['profit_abs'],new_net=new[k]['profit_abs'],
                  delta=new[k]['profit_abs']-base[k]['profit_abs'],old_exit=base[k]['exit_reason'],new_exit=new[k]['exit_reason']) for k in base]
    save(OUT/'comparisons.json',dict(classification='INSPECTED_DEVELOPMENT',policies=rows,
        matched_exit_comparison=matched,exit_delta=sum(x['delta'] for x in matched),
        generalization='UNPROVEN; policies are related tests on already inspected source history',
        holdout='2026-11-17/2026-12-01 reserved, not observed; no automatic collection',
        no_combined_portfolio_pnl=True))
    print(len(rows),'native policies;',sum(x['trades'] for x in rows),'trade records reconciled')


if __name__=='__main__':main()
