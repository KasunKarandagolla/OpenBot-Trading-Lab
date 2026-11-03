"""Independent Decimal economics, matched daily uncertainty and explicit data limits."""
from collections import Counter,defaultdict
from decimal import Decimal as D
import json
import math
import sys
import numpy as np
import pandas as pd
from session4_common import *
FEATURES={}
MARKS={}


def reconcile_sources():
    reports=[]
    for manifest in [ROOT/'evidence/additional-2/intelligence-003/data-manifest.json',ROOT/'evidence/additional-3/policy-session3-002/data-manifest.json']:
        for old in read(manifest)['files']:
            p=DATA/'futures'/__import__('pathlib').Path(old['path']).name
            row=dict(original_manifest=str(manifest.relative_to(ROOT)),original_file=old['path'],original_sha256=old['sha256'],
                original_available=(ROOT/old['path']).exists(),original_rows_reported=old.get('rows'),
                original_first=old.get('first'),original_last=old.get('last'))
            if not p.exists():row['reacquired_available']=False;reports.append(row);continue
            f=pd.read_feather(p);start=old.get('first') or ('2026-09-21T00:00:00+00:00' if 'additional-2' in str(manifest) else '2026-07-26T00:00:00+00:00')
            end=old.get('last')
            overlap=f.loc[f.date>=pd.Timestamp(start)]
            if end:overlap=overlap.loc[overlap.date<=pd.Timestamp(end)]
            else:overlap=overlap.loc[overlap.date<pd.Timestamp('2026-11-01',tz='UTC')]
            scratch=STATE/'reconciliation'/manifest.parent.name/p.name;scratch.parent.mkdir(parents=True,exist_ok=True);overlap.reset_index(drop=True).to_feather(scratch)
            same=sha(scratch)==old['sha256'];row.update(reacquired_available=True,reacquired_total_rows=len(f),overlap_rows=len(overlap),
                overlap_sha256=sha(scratch),byte_identical=same,new_duplicates=int(f.date.duplicated().sum()),
                partial_end_boundary='New acquisition ends Nov3 exclusive; parent ends earlier; overlap cropped separately',
                timestamp_set_differences='ZERO_BY_BYTE_IDENTITY' if same else 'UNCOMPUTABLE_ORIGINAL_ROWS_UNAVAILABLE',
                missing_duplicate_original_candles='UNCOMPUTABLE_ORIGINAL_ROWS_UNAVAILABLE',
                ohlc_differences='ZERO_BY_BYTE_IDENTITY' if same else 'UNCOMPUTABLE_ORIGINAL_ROWS_UNAVAILABLE',
                volume_differences='ZERO_BY_BYTE_IDENTITY' if same else 'UNCOMPUTABLE_ORIGINAL_ROWS_UNAVAILABLE',
                mark_price_differences='ZERO_BY_BYTE_IDENTITY' if same else 'UNCOMPUTABLE_ORIGINAL_ROWS_UNAVAILABLE',
                signal_trade_materiality='NO_SOURCE_DIFFERENCE_IF_BYTE_IDENTICAL' if same else 'UNCOMPUTABLE_WITHOUT_ORIGINAL_ROWS; independent research only')
            reports.append(row)
    write(OUT/'source-reconciliation.json',dict(originals_overwritten=False,original_source_files_available=0,files=reports,
        limitation='Manifest hashes/counts do not reconstruct missing OHLCV/mark rows; no fabricated row-level comparison. Both original manifests and new sources preserved.'))


def ledger(label):
    result=read(OUT/'native-results'/(label+'.json'))['strategy']['Session4Replay'];states=read(OUT/'native-states'/(label+'.json'))
    bykey={(s['pair'],pd.Timestamp(s['open_date']).value):s for s in states};rows=[]
    for t in result['trades']:
        state=bykey[(t['pair'],pd.Timestamp(t['open_date']).value)];g=state['plan']
        if not g:raise ValueError('native trade missing frozen plan')
        entries=[o for o in t['orders'] if o['ft_is_entry']];exits=[o for o in t['orders'] if not o['ft_is_entry']]
        qty=sum(D(str(o['amount'])) for o in entries);entry_value=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in entries)
        exit_value=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in exits);exit_qty=sum(D(str(o['amount'])) for o in exits)
        if qty!=exit_qty:raise ValueError('native final quantity mismatch')
        sign=D(-1 if t['is_short'] else 1);gross=sign*(exit_value-entry_value)
        fees=entry_value*D(str(t['fee_open']))+exit_value*D(str(t['fee_close']));fund=D(str(t.get('funding_fees') or 0))
        net=gross-fees+fund
        if abs(net-D(str(t['profit_abs'])))>D('0.0000001'):raise ValueError('independent native PnL reconciliation failed')
        # Revalue each actual funding event/quantity against source, independently.
        source_fund=pd.read_feather(DATA/'futures'/(t['pair'].replace('/','_').replace(':','_')+'-1h-funding_rate.feather')).set_index('date')
        source_mark=pd.read_feather(DATA/'futures'/(t['pair'].replace('/','_').replace(':','_')+'-1h-mark.feather')).set_index('date')
        funding_check=D(0)
        for event in state['funding']:
            at=pd.Timestamp(event['at'])
            if at<pd.Timestamp(t['open_date']) or at>pd.Timestamp(t['close_date']):raise ValueError('funding outside actual filled trade')
            rate=D(str(source_fund.loc[at,'funding_rate']));mark=D(str(source_mark.loc[at,'open']))
            funding_check+=-sign*D(str(event['quantity']))*rate*mark
        if abs(funding_check-fund)>D('.0000001'):raise ValueError('independent funding event reconciliation failed')
        risk=qty*abs(D(str(t['open_rate']))-D(str(g['stop'])))
        if risk<=0:raise ValueError('nonpositive stop risk')
        if t['pair'] not in FEATURES:
            FEATURES[t['pair']]=pd.read_pickle(STATE/'features'/(t['pair'].replace('/','_').replace(':','_')+'.pkl')).set_index('date')
        feature=FEATURES[t['pair']].loc[pd.Timestamp(g['available_at'])-pd.Timedelta(minutes=15)]
        rows.append(dict(pair=t['pair'],side='short' if t['is_short'] else 'long',recipe=g['recipe'],
            entry=t['open_date'],exit=t['close_date'],decision_id=g['decision_id'],entry_notional=float(entry_value),
            exit_notional=float(exit_value),gross_usdt=float(gross),fees_usdt=float(fees),funding_usdt=float(fund),net_usdt=float(net),
            quantity=float(qty),entry_rate=float(entry_value/qty),stop_risk_usdt=float(risk),pure_stop_R=float(gross/risk),net_stop_R=float(net/risk),
            regime='TREND_ADX25' if feature.adx_1h>=25 else 'RANGE_OR_WEAK_TREND',
            fvg_retest=bool(feature.fvg_retest_up if sign==1 else feature.fvg_retest_down),
            funding_events=[dict(at=e['at'],signed_fee=float(-sign*D(str(e['quantity']))*D(str(e['rate']))*D(str(e['mark'])))) for e in state['funding']],
            cost_inclusive_R=float(net/(risk+fees+max(D(0),-fund))),net_entry_bp=float(net/entry_value*10000),
            hold_minutes=t['trade_duration'],exit_reason=t['exit_reason'],native_initial_stop=t['initial_stop_loss_abs'],
            logical_stop=g['stop'],target=g['target'],hour_structure=g.get('hour_structure'),dealing_location=g.get('dealing_location'),
            native_reconciled=True,source_funding_reconciled=True,
            stresses={str(bp):float(net-(entry_value+exit_value)*D(str(bp))/D(10000)) for bp in (0,2,5,10,20)},
            maker_fee_scenario_usdt=float(gross-(entry_value+exit_value)*D('.0002')+fund),
            stop_gap_10bp_usdt=float(net-exit_value*D('.001')) if 'stop' in t['exit_reason'] or 'protective' in t['exit_reason'] else float(net)))
    write(OUT/'trade-ledgers'/(label+'.json'),rows)
    return result,rows


def daily(rows,field='net_usdt'):
    dates=pd.date_range('2026-08-05','2026-11-02',tz='UTC')
    values=pd.Series(0.,index=dates)
    for r in rows:values.loc[pd.Timestamp(r['exit']).floor('D')]+=r[field]
    return values


def block_interval(values,seed=20261103):
    x=np.asarray(values,dtype=float);rng=np.random.default_rng(seed);n=len(x)
    starts=rng.integers(0,n,size=(2000,math.ceil(n/7)))
    idx=(starts[:,:,None]+np.arange(7))%n
    totals=x[idx.reshape(2000,-1)[:,:n]].sum(axis=1)
    return [float(z) for z in np.quantile(totals,[.025,.975])]


def summarize(rows):
    net=np.array([r['net_usdt'] for r in rows]);w=net[net>0];l=net[net<0];d=daily(rows);curve=np.r_[0,np.cumsum(d)]
    top=sorted([r['net_usdt'] for r in rows if r['net_usdt']>0],reverse=True)
    grouped={}
    for key in ('recipe','side','hour_structure','regime','fvg_retest','exit_reason'):
        groups=defaultdict(list)
        for r in rows:groups[str(r.get(key))].append(r)
        grouped[key]={k:dict(trades=len(v),net_usdt=sum(x['net_usdt'] for x in v),stress10=sum(x['stresses']['10'] for x in v)) for k,v in groups.items()}
    months={}
    for month in ['2026-08','2026-09','2026-10','2026-11']:
        q=[r for r in rows if r['exit'].startswith(month)];months[month]=dict(trades=len(q),net_usdt=sum(r['net_usdt'] for r in q),stress10=sum(r['stresses']['10'] for r in q))
    return dict(trades=len(rows),wins=len(w),losses=len(l),net_usdt=float(net.sum()),gross_usdt=sum(r['gross_usdt'] for r in rows),
        fees_usdt=sum(r['fees_usdt'] for r in rows),funding_usdt=sum(r['funding_usdt'] for r in rows),
        expectancy_usdt=float(net.mean()) if len(net) else None,profit_factor=float(w.sum()/-l.sum()) if len(l) else None,
        win_rate=len(w)/len(net) if len(net) else None,mean_win=float(w.mean()) if len(w) else None,mean_loss=float(l.mean()) if len(l) else None,
        pure_stop_R=sum(r['pure_stop_R'] for r in rows),net_stop_R=sum(r['net_stop_R'] for r in rows),cost_inclusive_R=sum(r['cost_inclusive_R'] for r in rows),
        net_bp_weighted=float(net.sum())/sum(r['entry_notional'] for r in rows)*10000 if rows else None,
        turnover_usdt=sum(r['entry_notional']+r['exit_notional'] for r in rows),
        average_entry_notional_exposure_fraction=sum(r['entry_notional']*r['hold_minutes'] for r in rows)/(90*1440*1000),
        closed_daily_drawdown_usdt=float(max(np.maximum.accumulate(curve)-curve)),
        block95_net_usdt=block_interval(d),zero_realization_days=int(d.eq(0).sum()),
        top3_winners_fraction_of_positive=sum(top[:3])/sum(top) if top else None,
        excluding_top3_winners_usdt=float(net.sum()-sum(top[:3])),
        stress_usdt={str(bp):sum(r['stresses'][str(bp)] for r in rows) for bp in (0,2,5,10,20)},
        maker_fee_scenario_usdt=sum(r['maker_fee_scenario_usdt'] for r in rows),stop_gap10bp_usdt=sum(r['stop_gap_10bp_usdt'] for r in rows),
        months=months,breakdowns=grouped,
        win_loss_quantiles={str(q):float(np.quantile(net,q)) for q in (0,.1,.25,.5,.75,.9,1)} if len(net) else {},
        caveat='Closed-trade/daily equity drawdown understates intraday MTM. Native engine drawdown reported separately. Conditional current-survivor development, not independent holdout.')


def hourly_mtm(rows):
    grid=pd.date_range('2026-08-05','2026-11-03',freq='h',tz='UTC');equity=np.full(len(grid),1000.)
    for r in rows:
        start=pd.Timestamp(r['entry']);end=pd.Timestamp(r['exit'])
        equity[grid>=end]+=r['net_usdt']
        ix=(grid>=start)&(grid<end)
        if not ix.any():continue
        pair=r['pair']
        if pair not in MARKS:MARKS[pair]=pd.read_feather(DATA/'futures'/(pair.replace('/','_').replace(':','_')+'-1h-mark.feather')).set_index('date').open
        marks=MARKS[pair].reindex(grid[ix])
        if marks.isna().any():raise ValueError('missing held-position hourly mark')
        sign=1 if r['side']=='long' else -1
        accrued=np.zeros(ix.sum())
        for e in r['funding_events']:accrued[grid[ix]>=pd.Timestamp(e['at'])]+=e['signed_fee']
        equity[ix]+=sign*r['quantity']*(marks.to_numpy()-r['entry_rate'])-.00075*(r['entry_notional']+r['quantity']*marks.to_numpy())+accrued
    return dict(max_drawdown_usdt=float(max(np.maximum.accumulate(equity)-equity)),min_equity=float(min(equity)),
        final_equity=float(equity[-1]),resolution='Hourly source mark OPEN + actual native held quantity, realized net and event-bounded funding; estimated close fee. Intrahour excursions/gaps UNKNOWN.')


def report():
    reports={};ledgers={}
    for p in sorted((OUT/'native-results').glob('*.json')):
        native,rows=ledger(p.stem);ledgers[p.stem]=rows;reports[p.stem]=summarize(rows)
        reports[p.stem]['native_max_drawdown_usdt']=native.get('max_drawdown_abs')
        reports[p.stem]['native_rejected_signals']=native.get('rejected_signals')
        reports[p.stem]['native_timedout_entry_orders']=native.get('timedout_entry_orders')
        reports[p.stem]['hourly_mark_mtm']=hourly_mtm(rows)
    reference=daily(ledgers['reference']);nulls=[daily(ledgers[v]) for v in ledgers if v.startswith('random-')]
    nullmean=pd.concat(nulls,axis=1).mean(axis=1)
    paired=reference-nullmean
    benchmarks=dict(reference_minus_mean_null_total=float(paired.sum()),block95_paired_usdt=block_interval(paired),
        null_replicates=len(nulls),null_total_net=[float(x.sum()) for x in nulls],reference_net=float(reference.sum()),
        reference_rank_among_null=len([x for x in nulls if x.sum()<=reference.sum()])+1,
        conditional_empirical_upper_tail_p=(1+sum(x.sum()>=reference.sum() for x in nulls))/(1+len(nulls)),
        uncertainty='Eight fixed-seed conditional ranking nulls; 7day circular moving-block bootstrap on paired daily net,2000 draws. Descriptive development uncertainty, no omnibus alpha claim.')
    comparisons={}
    for name in ('structure','hour','systematic'):
        diff=daily(ledgers[name])-reference
        comparisons[name]=dict(paired_net_difference=float(diff.sum()),block95_paired_usdt=block_interval(diff),
            basis='Same chronological eligible source universe, costs, capacity, native risk/exit engine; complete alternative portfolios')
    write(OUT/'economic-report.json',dict(at=now(),portfolios=reports,benchmark=benchmarks,comparisons=comparisons,
        definitions=dict(pure_stop_R='gross price PnL / initial logical stop price risk',net_stop_R='net after actual fees/funding / initial logical stop price risk',
                         cost_inclusive_R='net / (initial logical stop risk + actual entry/exit fees + adverse actual funding)',
                         bp='net / entry notional * 10000',fixed_notional='native lot-rounded <=25 USDT per entry',constant_risk='0.25 USDT modeled stop+38bp cost risk, ceiling50 USDT, native lot rounding'),
        economic_status='UNQUALIFIED',untouched_holdout_used=False))
    reconcile_sources()
    print({v:(x['trades'],x['net_usdt'],x['stress_usdt']['10']) for v,x in reports.items()},flush=True)
    print(benchmarks,flush=True)


if __name__=='__main__':
    import math
    globals()[sys.argv[1]]()
