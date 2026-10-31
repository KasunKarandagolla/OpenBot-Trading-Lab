"""Accounting on native executions, never an alternative backtest/fill simulator."""
import json
from collections import Counter
import numpy as np
import pandas as pd
from bonus_common import *
from bonus_data import frame
sys.path[:0]=[str(ROOT/'user_data/strategies')]
from PlaybookRiskV1 import session_features


def fills(trade):
    entries=[o for o in trade['orders'] if o['ft_is_entry']]
    exits=[o for o in trade['orders'] if not o['ft_is_entry']]
    amount=sum(o['amount'] for o in entries)
    rate=sum(o['amount']*o['safe_price'] for o in entries)/amount
    sign=-1 if trade['is_short'] else 1
    gross=sum(sign*o['amount']*(o['safe_price']-rate) for o in exits)
    fees=sum(o['amount']*o['safe_price']*(trade['fee_open'] if o['ft_is_entry'] else trade['fee_close']) for o in trade['orders'])
    turnover=sum(o['amount']*o['safe_price'] for o in trade['orders'])
    return {'gross':gross,'fees':fees,'funding':trade.get('funding_fees',0) or 0,
            'turnover':turnover,'entry_amount':amount,'entry_rate':rate,
            'exit_amount':sum(o['amount'] for o in exits),'partial_exits':max(0,len(exits)-1)}


def summary(rows,native=None):
    if not rows:return {'trades':0,'net_usdt':0.,'verdict':'INSUFFICIENT OR UNAVAILABLE EVIDENCE'}
    net=sum(r['net_usdt'] for r in rows);wins=[r['net_usdt'] for r in rows if r['net_usdt']>0];loss=[r['net_usdt'] for r in rows if r['net_usdt']<0]
    risk=[r['net_R'] for r in rows if r['net_R'] is not None]
    order=sorted(rows,key=lambda r:(r['close_date'],r['pair']))
    curve=np.r_[0,np.cumsum([r['net_usdt'] for r in order])]
    dd=float((np.maximum.accumulate(curve)-curve).max())
    turnover=sum(r['turnover_usdt'] for r in rows)
    stats={'trades':len(rows),'net_usdt':net,'return_on_1000_equity_pct':net/10,
           'gross_price_pnl_usdt':sum(r['gross_price_pnl_usdt'] for r in rows),
           'fees_usdt':sum(r['fees_usdt'] for r in rows),'funding_signed_usdt':sum(r['funding_signed_usdt'] for r in rows),
           'turnover_usdt':turnover,'expectancy_usdt':net/len(rows),
           'mean_net_R':float(np.mean(risk)) if risk else None,'sum_net_R':sum(risk),
           'profit_factor':sum(wins)/-sum(loss) if loss else None,
           'mean_win_usdt':float(np.mean(wins)) if wins else None,'mean_loss_usdt':float(np.mean(loss)) if loss else None,
           'closed_trade_drawdown_usdt':dd,'hold_minutes_mean':float(np.mean([r['hold_minutes'] for r in rows])),
           'mean_directional_price_move_pct':float(np.mean([r['directional_exit_move_pct'] for r in rows])),
           'mean_MFE_pct_completed_intermediate_bars':float(np.mean([r['MFE_pct'] for r in rows])),
           'mean_MAE_pct_completed_intermediate_bars':float(np.mean([r['MAE_pct'] for r in rows])),
           'ambiguous_stop_target_candles':sum(r['unresolved_stop_target_candles'] for r in rows),
           'partial_exits':sum(r['partial_exits'] for r in rows),
           'friction':[{'extra_bps_per_side':bp,'net_usdt':net-turnover*bp/10000} for bp in [0,5,10,20]],
           'break_even_extra_bps_per_side':net/turnover*10000 if turnover else None,
           'per_pair':{p:sum(r['net_usdt'] for r in rows if r['pair']==p) for p in sorted({r['pair'] for r in rows})},
           'per_side':{p:sum(r['net_usdt'] for r in rows if r['side']==p) for p in ['long','short']},
           'per_regime':{p:{'trades':sum(r['regime']==p for r in rows),'net_usdt':sum(r['net_usdt'] for r in rows if r['regime']==p)} for p in sorted({r['regime'] for r in rows})},
           'net_without_best3_usdt':net-sum(sorted([r['net_usdt'] for r in rows],reverse=True)[:3]),
           'verdict':'REJECTED UNDER TESTED ASSUMPTIONS' if net<=0 else 'PROMISING BUT UNQUALIFIED'}
    if native:
        stats['native_rejected_signals']=native.get('rejected_signals')
        stats['native_timedout_entry_orders']=native.get('timedout_entry_orders')
        stats['native_canceled_entry_orders']=native.get('canceled_entry_orders')
    # Joint-market calendar-week resampling includes weeks with no trades.
    weeks=pd.date_range('2026-08-03','2026-10-26',freq='7D')
    values=[]
    for w in weeks:
        values.append(sum(r['net_usdt'] for r in rows if w<=pd.Timestamp(r['close_date']).tz_localize(None)<w+pd.Timedelta(days=7)))
    rng=np.random.default_rng(4104);values=np.asarray(values)
    totals=values[rng.integers(0,len(values),size=(2000,len(values)))].sum(axis=1)
    stats['development_week_block_interval_usdt']=[float(np.quantile(totals,.025)),float(np.quantile(totals,.975))]
    stats['uncertainty']='13 joint-market weekly development blocks, seed4104, 2000 draws; stationarity assumption, not independent qualification'
    return stats


def mtm_accounting(trades,frames):
    """Replay native fills into an equity ledger at completed candle marks.

    Funding aggregate recognized at final exit; not historical funding-event equity.
    No simulated entries, fills, exits, strategies or risk decisions are generated.
    """
    times=pd.date_range('2026-08-05','2026-10-30',freq='15min',tz='UTC',inclusive='left')
    prices={s:f.set_index(f.date+pd.Timedelta(minutes=15)).close.reindex(times) for s,f in frames.items()}
    events={}
    for i,t in enumerate(trades):
        for o in t['orders']:events.setdefault(o['order_filled_timestamp'],[]).append((i,t,o))
    sorted_events=sorted(events.items());cursor=0;realized=0.;positions={};curve=[]
    for at in times:
        ms=at.timestamp()*1000
        while cursor<len(sorted_events) and sorted_events[cursor][0]<=ms:
            for i,t,o in sorted_events[cursor][1]:
                sign=-1 if t['is_short'] else 1
                realized-=o['amount']*o['safe_price']*(t['fee_open'] if o['ft_is_entry'] else t['fee_close'])
                if o['ft_is_entry']:positions[i]=[t['pair'],sign,o['amount'],o['safe_price']]
                else:
                    if i not in positions:raise ValueError('accounting exit before entry')
                    pos=positions[i];realized+=sign*o['amount']*(o['safe_price']-pos[3]);pos[2]-=o['amount']
                    if pos[2]<1e-9:
                        positions.pop(i);realized+=t.get('funding_fees',0) or 0
            cursor+=1
        unrealized=sum(sign*qty*(prices[pair].loc[at]-entry) for pair,sign,qty,entry in positions.values())
        curve.append(1000+realized+unrealized)
    # End-exclusive final exits can be at the end marker; reconcile separately.
    values=np.asarray(curve);dd=float((np.maximum.accumulate(values)-values).max())
    return {'max_completed_mark_drawdown_usdt':dd,'min_completed_mark_equity':float(values.min()),
            'funding_timing':'aggregate at final exit; intermediate equity approximation',
            'mark_fidelity':'15m futures-close mark proxy; not actual exchange account equity',
            'no_fills_simulated':True}


def analyze():
    check()
    from bonus_funding_audit import audit
    funding_audit=audit()
    rawframes={s:frame(s) for s in spec()['pairs']}
    indicators={s:session_features(f).set_index('date') for s,f in rawframes.items()}
    from PlaybookRiskV1 import PlaybookRiskV1
    from freqtrade.enums import CandleType
    hours={s:PlaybookRiskV1({'candle_type_def':CandleType.FUTURES}).populate_indicators_1h(frame(s,'1h'),{}).set_index('date') for s in spec()['pairs']}
    candidates=pd.read_csv(OUT/'opportunity-ledger.csv')
    plans={}
    for _,r in candidates.loc[candidates.decision=='TRADE'].iterrows():
        plans[(r.variant,r.symbol,r.decision_at)]=json.loads(r.plan)
    variants={};all_ledgers={};native_trades={};destination=OUT/'trade-ledgers';destination.mkdir(exist_ok=True)
    for name in spec()['variants']:
        path=OUT/'native-results'/(name+'.json');provenance=read(OUT/'native-results'/(name+'-provenance.json'))
        if sha(path)!=provenance['result_sha256']:raise ValueError('result hash mismatch')
        result=read(path)['strategy'][name];trades=result['trades'];native_trades[name]=trades;rows=[]
        for t in trades:
            f=fills(t);at=pd.Timestamp(t['open_date']);end=pd.Timestamp(t['close_date'])
            signal=indicators[t['pair']].loc[indicators[t['pair']].index+pd.Timedelta(minutes=15)<=at].iloc[-1]
            context=hours[t['pair']].loc[hours[t['pair']].index+pd.Timedelta(hours=1)<=at].iloc[-1]
            regime=('TREND_UP' if context.ema20>context.ema50 else 'TREND_DOWN') if context.adx>=25 else 'BALANCE'
            sign=-1 if t['is_short'] else 1
            key=(name,t['pair'],at.isoformat());g=plans.get(key)
            buffer=.15 if name in ('LiquiditySweepReversalV1','StructureAwareSweepV1') else .2
            stop=g['stop'] if g else float(signal.high+buffer*signal.atr14 if t['is_short'] else signal.low-buffer*signal.atr14)
            price_risk=sign*(f['entry_rate']-stop)/f['entry_rate']
            if price_risk<=0:raise ValueError('invalid initial risk accounting')
            planned=f['entry_amount']*f['entry_rate']*(price_risk+.0035)
            # Exclude entry and exit candles; do not credit post-stop favorable wicks.
            b=rawframes[t['pair']];inside=b.loc[(b.date>at)&(b.date+pd.Timedelta(minutes=15)<=end)]
            best=max(0.,max((sign*(x-f['entry_rate'])/f['entry_rate'] for x in (inside.low if t['is_short'] else inside.high)),default=0))
            worst=min(0.,min((sign*(x-f['entry_rate'])/f['entry_rate'] for x in (inside.high if t['is_short'] else inside.low)),default=0))
            target=g['target'] if g else f['entry_rate']*(1+sign*2*price_risk)
            exitbars=b.loc[(b.date<=end)&(b.date+pd.Timedelta(minutes=15)>end)]
            ambiguous=sum(float(r.low)<=min(stop,target) and float(r.high)>=max(stop,target) for _,r in exitbars.iterrows())
            weighted_exit=sum(o['amount']*o['safe_price'] for o in t['orders'] if not o['ft_is_entry'])/f['exit_amount']
            residual=t['profit_abs']-(f['gross']-f['fees']+f['funding'])
            rows.append({'pair':t['pair'],'side':'short' if t['is_short'] else 'long','open_date':t['open_date'],
                         'close_date':t['close_date'],'entry_rate':f['entry_rate'],'weighted_exit_rate':weighted_exit,
                         'directional_exit_move_pct':sign*(weighted_exit/f['entry_rate']-1)*100,
                         'stop':stop,'initial_price_risk_pct':price_risk*100,'planned_risk_usdt':planned,
                         'net_usdt':t['profit_abs'],'net_R':t['profit_abs']/planned,
                         'gross_price_pnl_usdt':f['gross'],'fees_usdt':f['fees'],'funding_signed_usdt':f['funding'],
                         'reconciliation_residual_usdt':residual,'turnover_usdt':f['turnover'],
                         'MFE_pct':best*100,'MAE_pct':worst*100,'MFE_price_R':best/price_risk,'MAE_price_R':worst/price_risk,
                         'unresolved_stop_target_candles':ambiguous,'hold_minutes':t['trade_duration'],
                         'exit_reason':t['exit_reason'],'recipe':'sweep' if 'sweep' in str(t.get('enter_tag','')).lower() or 'Sweep' in name else 'vwap',
                         'regime':regime,
                         'partial_exits':f['partial_exits'],'entry_amount':f['entry_amount'],'exit_amount':f['exit_amount']})
        if rows:
            pd.DataFrame(rows).to_csv(destination/(name+'.csv'),index=False)
            if max(abs(r['reconciliation_residual_usdt']) for r in rows)>1e-5:raise ValueError('fill accounting does not reconcile')
        else:pd.DataFrame(columns=['pair','net_usdt']).to_csv(destination/(name+'.csv'),index=False)
        stats=summary(rows,result)
        audited=funding_audit['variants'][name]
        stats['source_funding_audit']={k:audited[k] for k in ('outside_bounds_trades','source_funding_net_min','source_funding_net_max')}
        stats['recipes']={recipe:summary([r for r in rows if r['recipe']==recipe]) for recipe in ('vwap','sweep')}
        stats['equity_accounting']=mtm_accounting(trades,rawframes)
        if name in set(candidates.variant):
            c=candidates.loc[candidates.variant==name]
            stats['decision_population']={'parent_candidates':len(c),'trade_plans':int((c.decision=='TRADE').sum()),
                                          'rejected':int((c.decision=='REJECT').sum()),'native_filled_trades':len(trades),
                                          'plan_fill_difference_interpretation':'capacity, ongoing position, callbacks, expiry and native fills; not all differences are unfilled orders'}
        variants[name]=stats;all_ledgers[name]=rows
    m0={(r['pair'],r['side'],r['open_date']):r for r in all_ledgers['RouterOnlyV1']}
    m1={(r['pair'],r['side'],r['open_date']):r for r in all_ledgers['RouterOnlyM1V1']}
    matched=[]
    for key in sorted(m0.keys()&m1.keys()):
        a=m0[key];b=m1[key];delta=b['net_usdt']-a['net_usdt']
        matched.append({'pair':key[0],'side':key[1],'open_date':key[2],'M0_net':a['net_usdt'],'M1_net':b['net_usdt'],
                        'delta':delta,'M1_partials':b['partial_exits'],'extra_fee':b['fees_usdt']-a['fees_usdt'],
                        'reduced_loss':a['net_usdt']<0 and delta>1e-8,'saved_profit':a['net_usdt']>0 and delta>1e-8,
                        'reduced_winner':a['net_usdt']>0 and delta< -1e-8,
                        'earlier_harmful_exit':b['hold_minutes']<a['hold_minutes'] and delta< -1e-8})
    management={'parent':'RouterOnlyV1','challenger':'RouterOnlyM1V1','reason':'Frozen integrated policy abstained; separately registered available-opportunity management experiment',
                'matched':len(matched),'M0_unmatched':len(m0.keys()-m1.keys()),'M1_unmatched':len(m1.keys()-m0.keys()),
                'matched_delta_usdt':sum(r['delta'] for r in matched),
                'reduced_losses':sum(r['reduced_loss'] for r in matched),'saved_profit':sum(r['saved_profit'] for r in matched),
                'reduced_winners':sum(r['reduced_winner'] for r in matched),'earlier_harmful_exits':sum(r['earlier_harmful_exit'] for r in matched),
                'extra_fees_usdt':sum(r['extra_fee'] for r in matched),'rows':matched,
                'fill_limit':'Native candle partial fills tested mechanically; no actual exchange queue or partial-fill history. Capacity can make later opportunities unmatched.'}
    write(OUT/'management-comparison.json',management)
    # Defined rejected populations, with *executed* frozen-parent controls.
    # Management differs from the router; these are diagnostic matches, not a
    # causal estimate of how rejected plans would trade under the new policy.
    controls={}
    for recipe,parent in [('vwap','VWAPTrendContinuationV1'),('sweep','LiquiditySweepReversalV1')]:
        for r in all_ledgers[parent]:controls[(r['pair'],pd.Timestamp(r['open_date']).isoformat(),recipe)]=r
    rejected=[]
    for _,r in candidates.loc[candidates.decision=='REJECT'].iterrows():
        control=controls.get((r.symbol,r.decision_at,r.recipe))
        rejected.append({'variant':r.variant,'symbol':r.symbol,'decision_at':r.decision_at,
                         'reason':r.reason,'recipe':r.recipe,'parent_native_match':control is not None,
                         'parent_net_usdt':control['net_usdt'] if control else None,
                         'parent_side':control['side'] if control else None})
    write(OUT/'rejected-control-evidence.json',{
        'population':'All rejected route-ready parent signals in the five-market sample; no selection by future return',
        'rows':rejected,'matched_native_controls':sum(r['parent_native_match'] for r in rejected),
        'limitation':'Exact entry-clock matches to native frozen parents, same fees/funding but different management/geometry. No identical-router-management counterfactual for every rejected or unselected market; no fictional PnL for unfilled plans.'})
    report={'protocol_sha256':sha(PROTOCOL),'classification':'INSPECTED_DEVELOPMENT_NOT_INDEPENDENT',
            'variants':variants,'management':{k:v for k,v in management.items() if k!='rows'},
            'orderflow_economics':'INSUFFICIENT OR UNAVAILABLE EVIDENCE; genuine future shadow only',
            'profitability_demonstrated':False,'limitations':[
                'Five surviving markets, no historic full-universe eligibility or quote spreads.',
                'OHLCV profile is approximate; no historical aggressor prints or news feed.',
                'Native requested-price fills; no queue model or observed partial execution.',
                'MFE/MAE only complete intermediate bars; entry/exit intrabar extrema intentionally excluded.',
                'Report adds native exported funding once. Independent source-event audit finds two M1 trades outside funding quantity bounds at exact-clock partial exits; native totals remain unchanged. M1 stays research-only.',
                'Mark-equity approximation recognizes aggregate funding at final exit, not at each actual event.',
                'No independent calendar holdout, new prospective cohort starts Nov9 after prior reserved cohort.',
                'Extra friction stresses native turnover without resimulating fills. No operational promotion.']}
    write(OUT/'economic-results.json',report)
    text='# Bonus economic results\n\nInspected development, 2026-08-05 to 2026-10-30 UTC exclusive. Five-market survivor sample; 1,000 USDT equity, <=25 notional, 1x, max two positions. Fee 0.06%/side plus actual signed funding.\n\n'
    text+='|Policy|Trades|Net USDT|PF|Mean net R|Fees|+10bp/side net|Verdict|\n|---|---:|---:|---:|---:|---:|---:|---|\n'
    for name,r in variants.items():
        text+=f"|{name}|{r['trades']}|{r['net_usdt']:.6f}|{r.get('profit_factor')}|{r.get('mean_net_R')}|{r.get('fees_usdt',0):.6f}|{r.get('friction',[{},{},{'net_usdt':0}])[2]['net_usdt']:.6f}|{r['verdict']}|\n"
    text+='\n'+ '\n'.join('- '+x for x in report['limitations'])+'\n\n**Profitability is not demonstrated.** Full recipe, risk, movement, concentration, drawdown and cost statistics: `economic-results.json`; native-fill accounting: `trade-ledgers/`; management: `management-comparison.json`; independent source-event funding bounds: `source-funding-audit.json`.\n'
    (OUT/'economic-report.md').write_text(text)
    print(text)
    return report
