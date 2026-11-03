"""Independent trade/funding reconciliation, uncertainty, exposure and qualification."""
from collections import defaultdict
from decimal import Decimal as D
import math
import numpy as np
import pandas as pd
from recovery_common import *
from recovery_diagnose import interval

SOURCE={}
def path_extremes(q,entry,sign):
    high=sign*(q.high/entry-1);low=sign*(q.low/entry-1)
    return float(max(high.max(),low.max())*1e4),float(min(high.min(),low.min())*1e4)

def source(window,pair,kind):
    key=(window,pair,kind)
    if key not in SOURCE:SOURCE[key]=pd.read_feather(DATA/window/'gate/futures'/(slug(pair)+'-'+kind+'.feather'))
    return SOURCE[key]

def calendar(window,detail=False):
    a,b=('2026-08-05','2026-11-03') if 'development' in window else ('2026-05-20','2026-07-26')
    if detail:a='2026-10-29' if 'development' in window else '2026-07-21'
    return pd.date_range(a,pd.Timestamp(b)-pd.Timedelta(days=1),tz='UTC')

def daily(rows,window,detail=False,stress=0):
    d=pd.Series(0.,index=calendar(window,detail))
    for r in rows:
        at=pd.Timestamp(r['exit']).floor('D')
        if at not in d.index:raise ValueError('trade outside evaluation')
        d.loc[at]+=r['net_usdt']-r['turnover_usdt']*stress/1e4
    return d

def reconcile(directory):
    p=read(directory/'provenance.json');result=read(directory/'result.json');s=next(iter(result['strategy'].values()))
    states=read(directory/'states.json');lookup={(z['pair'],pd.Timestamp(z['open_date']).value):z for z in states};rows=[]
    for t in s['trades']:
        st=lookup[(t['pair'],pd.Timestamp(t['open_date']).value)];g=st['plan'];sign=D(-1 if t['is_short'] else 1)
        entries=[o for o in t['orders'] if o['ft_is_entry']];exits=[o for o in t['orders'] if not o['ft_is_entry']]
        qty=sum(D(str(o['amount'])) for o in entries);qtyout=sum(D(str(o['amount'])) for o in exits)
        a=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in entries)
        b=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in exits)
        if qty!=qtyout:raise ValueError('quantity conservation')
        fee=a*D(str(t['fee_open']))+b*D(str(t['fee_close']));gross=sign*(b-a);fund=D(str(t.get('funding_fees') or 0))
        net=gross-fee+fund
        if abs(net-D(str(t['profit_abs'])))>D('.00000011'):raise ValueError('native PnL reconciliation '+str(directory))
        first=pd.Timestamp(min(o['order_filled_timestamp'] for o in entries),unit='ms',tz='UTC');end=pd.Timestamp(t['close_date'])
        f=source(p['window'],t['pair'],'1h-funding_rate');m=source(p['window'],t['pair'],'1h-mark').set_index('date').open
        expected=f.loc[(f.date>=first)&(f.date<=end)]
        observed={pd.Timestamp(e['at']) for e in st['funding']}
        if set(expected.date)!=observed:raise ValueError('missing/extra actual source funding event '+str(directory)+' '+t['pair'])
        independent_funding=D(0)
        for _,e in expected.iterrows():
            mark=m.loc[:e.date].iloc[-1]
            independent_funding-=sign*qty*D(str(e.funding_rate))*D(str(mark))
        if abs(fund-independent_funding)>D('.00000011'):raise ValueError('signed source funding differs')
        stoprisk=qty*abs(D(str(t['open_rate']))-D(str(g['stop'])))
        if stoprisk<=0:raise ValueError('invalid logical risk')
        risk=float(stoprisk);turnover=float(a+b)
        row=dict(pair=t['pair'],side='short' if t['is_short'] else 'long',recipe=g['recipe'],entry=str(first),exit=t['close_date'],
            decision_id=g['decision_id'],entry_notional=float(a),exit_notional=float(b),quantity=float(qty),entry_rate=t['open_rate'],exit_rate=t['close_rate'],
            logical_stop=g['stop'],target=g['target'],risk_fraction=float(stoprisk/a),modeled_loss_per_notional=g['modeled_loss_per_notional'],
            gross_usdt=float(gross),fees_usdt=float(fee),funding_usdt=float(fund),net_usdt=float(net),turnover_usdt=turnover,
            net_bp=float(net/a*10000),stop_risk_usdt=risk,pure_stop_R=float(gross/stoprisk),net_stop_R=float(net/stoprisk),
            cost_inclusive_R=float(net/(stoprisk+fee+max(D(0),-fund))),hold_minutes=(end-first).total_seconds()/60,
            exit_reason=t['exit_reason'],source_funding_events=[dict(at=str(e.date),rate=float(e.funding_rate)) for _,e in expected.iterrows()],
            independent_funding_verified=True,independent_quantity_fee_net_verified=True,
            stress={str(k):float(net)-turnover*k/1e4 for k in [0,2,5,10,20]},hour_structure=g.get('hour_structure'),
            source_flow='UNKNOWN',profile='OHLCV_PROXY')
        spreads={x['pair']:x['spread_bp'] for x in read(OUT/'current-spreads.json')}
        venue_fee=.0005+.0002+spreads[t['pair']]/2/1e4
        row['venue_cost_scenario_net']=float(gross)-turnover*venue_fee+float(fund)
        row['venue_cost_per_side_bp']=venue_fee*1e4
        # Source path while held. Full entry/exit candle intrabar ordering unknown.
        kind='1h-futures' if p['window'].startswith('hourly-') else '15m-futures'
        candles=source(p['window'],t['pair'],kind)
        q=candles.loc[(candles.date>=first)&(candles.date<end)]
        if len(q):
            mfe,mae=path_extremes(q,t['open_rate'],float(sign))
            row['held_path_bar_mfe_bp_upper_bound']=mfe
            row['held_path_bar_mae_bp_lower_bound']=mae
            row['held_path_resolution']=kind
        rows.append(row)
    write(directory/'ledger.json',rows)
    return p,s,rows

def summarize(p,native,rows):
    x=np.array([r['net_usdt'] for r in rows]);n=len(x);wins=x[x>0];loss=x[x<0]
    d=daily(rows,p['window'],p['detail']);days=len(d);total=float(x.sum());entry=sum(r['entry_notional'] for r in rows)
    turnover=sum(r['turnover_usdt'] for r in rows);curve=np.r_[0,d.cumsum().to_numpy()]
    weeks=np.array([d.iloc[i:i+7].sum() for i in range(0,days,7)])
    sd=float(weeks.std(ddof=1)) if len(weeks)>1 else None
    mde=(2.8*sd/math.sqrt(len(weeks))) if sd is not None else None
    groups={}
    for key in ['recipe','side','exit_reason','pair','hour_structure']:
        sets=defaultdict(list)
        for r in rows:sets[str(r.get(key))].append(r)
        groups[key]={k:dict(n=len(q),net=sum(r['net_usdt'] for r in q),stress10=sum(r['stress']['10'] for r in q),mean_bp=float(np.mean([r['net_bp'] for r in q]))) for k,q in sets.items()}
    month={}
    for label,q in d.groupby(d.index.strftime('%Y-%m')):month[label]=float(q.sum())
    # Hourly mark MTM, actual native held quantity and source funding clocks.
    grid=pd.date_range(d.index[0],d.index[-1]+pd.Timedelta(days=1),freq='h');equity=np.full(len(grid),1000.)
    for r in rows:
        a=pd.Timestamp(r['entry']);b=pd.Timestamp(r['exit']);equity[grid>=b]+=r['net_usdt'];held=(grid>=a)&(grid<b)
        if not held.any():continue
        mark=source(p['window'],r['pair'],'1h-mark').set_index('date').open.reindex(grid[held])
        if mark.isna().any():raise ValueError('held mark missing')
        sgn=1 if r['side']=='long' else -1;fund=np.zeros(held.sum())
        f=source(p['window'],r['pair'],'1h-funding_rate').set_index('date').funding_rate
        for e in r['source_funding_events']:
            at=pd.Timestamp(e['at']);mp=source(p['window'],r['pair'],'1h-mark').set_index('date').open.loc[:at].iloc[-1]
            fund[grid[held]>=at]+=-sgn*r['quantity']*e['rate']*mp
        equity[held]+=sgn*r['quantity']*(mark.to_numpy()-r['entry_rate'])-p['fee_per_side']*(r['entry_notional']+r['quantity']*mark.to_numpy())+fund
    return dict(n=n,net_usdt=total,gross_usdt=sum(r['gross_usdt'] for r in rows),fees_usdt=sum(r['fees_usdt'] for r in rows),
        funding_usdt=sum(r['funding_usdt'] for r in rows),turnover_usdt=turnover,entry_notional=entry,
        mean_net_usdt=total/n if n else None,weighted_net_bp=total/entry*1e4 if entry else None,
        mean_trade_bp=float(np.mean([r['net_bp'] for r in rows])) if n else None,
        win_rate=len(wins)/n if n else None,average_win=float(wins.mean()) if len(wins) else None,
        average_loss=float(loss.mean()) if len(loss) else None,profit_factor=float(wins.sum()/-loss.sum()) if len(loss) else None,
        stop_R=sum(r['net_stop_R'] for r in rows),cost_inclusive_R=sum(r['cost_inclusive_R'] for r in rows),
        top3_positive_share=float(np.sort(wins)[-3:].sum()/wins.sum()) if len(wins) else None,
        excluding_top3_usdt=float(total-np.sort(wins)[-3:].sum()),
        mean_hold_minutes=float(np.mean([r['hold_minutes'] for r in rows])) if n else None,
        exposure_wallet_fraction=sum(r['entry_notional']*r['hold_minutes'] for r in rows)/(days*1440*1000),
        modeled_risk_deployed=sum(r['entry_notional']*r['modeled_loss_per_notional'] for r in rows),
        mean_stop_risk_usdt=float(np.mean([r['stop_risk_usdt'] for r in rows])) if n else None,
        additional_friction_stress_usdt={str(k):sum(r['stress'][str(k)] for r in rows) for k in [0,2,5,10,20]},
        current_quote_anchored_venue_scenario_net=sum(r['venue_cost_scenario_net'] for r in rows),
        venue_scenario_note='5bp public current taker + observed current half-spread + hypothetical2bp slippage per side;not measured historical execution costs. Complete native market portfolio uses worst observed half-spread across cohort.',
        extra_break_even_bp_per_side=total/turnover*1e4 if turnover else None,
        block95_total_usdt=interval(d),block95_total_stress10_usdt=interval(daily(rows,p['window'],p['detail'],10)),
        source_hourly_mark_drawdown_usdt=float(np.max(np.maximum.accumulate(equity)-equity)),
        closed_day_drawdown_usdt=float(np.max(np.maximum.accumulate(curve)-curve)),native_drawdown_usdt=native.get('max_drawdown_abs'),
        zero_realization_days=int(d.eq(0).sum()),calendar_days=days,monthly_net_usdt=month,groups=groups,
        top_positive_week_share=float(weeks.max()/weeks[weeks>0].sum()) if (weeks>0).any() else None,
        top3_positive_days_share=float(d[d>0].nlargest(3).sum()/d[d>0].sum()) if (d>0).any() else None,
        rejected_signals=native.get('rejected_signals'),timedout_entry_orders=native.get('timedout_entry_orders'),
        fill_count_note='Plans minus fills includes capacity,risk,cooldown,lot and nonfill exclusions;not a pure fill probability.',
        effect_detection=dict(weekly_blocks=len(weeks),weekly_sd_usdt=sd,detectable_weekly_mean_usdt_80pct_power_5pct_two_sided=mde,
            detectable_total_usdt=mde*len(weeks) if mde is not None else None,
            detectable_mean_trade_bp=mde*len(weeks)/entry*1e4 if mde is not None and entry else None,
            assumption='Normal approximation using observed nonoverlapping weekly dispersion;few blocks and nonstationarity limit power planning.'))

def report():
    reports={};ledgers={};prov={}
    for path in sorted((OUT/'native').glob('*/*/result.json')):
        directory=path.parent;p,native,rows=reconcile(directory);key=p['window']+'/'+p['label']
        reports[key]=summarize(p,native,rows);ledgers[key]=rows;prov[key]=p
    comparisons={}
    pairs_to_compare=[]
    for v in ['structure','context','context-smc','momentum','liquid-momentum']:
        pairs_to_compare.append(('development/'+v+'-fixed-touch-fee750','development/reference-fixed-touch-fee750'))
    for w in ['development','hourly-development','hourly-independent']:
        for sizing in ['fixed','risk']:
            for fee in ['750','1750']:pairs_to_compare.append((w+'/momentum-'+sizing+'-touch-fee'+fee,w+'/liquid-momentum-'+sizing+'-touch-fee'+fee))
    pairs_to_compare+=[('development/context-smc-fixed-touch-fee750','development/context-fixed-touch-fee750'),
        ('development/reference-fixed-touch-fee750-barriers','development/reference-fixed-touch-fee750')]
    for a,b in pairs_to_compare:
        if a not in ledgers or b not in ledgers:continue
        p=prov[a];diff=daily(ledgers[a],p['window'])-daily(ledgers[b],p['window'])
        comparisons[a+' minus '+b]=dict(net_difference=float(diff.sum()),block95=interval(diff),
            exposure_ratio=reports[a]['exposure_wallet_fraction']/reports[b]['exposure_wallet_fraction'] if reports[b]['exposure_wallet_fraction'] else None,
            caveat='Complete alternatives;different eligible opportunity counts and exposures disclosed;returns not additive.')
    nullkeys=[k for k in reports if k.startswith('development/rank-') and k.endswith('fixed-touch-fee750')]
    null={}
    if nullkeys:
        ref='development/reference-fixed-touch-fee750';s=np.array([reports[k]['net_usdt'] for k in nullkeys]);rd=daily(ledgers[ref],'development')
        nd=np.mean([daily(ledgers[k],'development').to_numpy() for k in nullkeys],axis=0)
        null=dict(replicates=len(s),conditional_empirical_upper_p=float((1+(s>=reports[ref]['net_usdt']).sum())/(len(s)+1)),
            p_resolution=1/(len(s)+1),native_null_net_mean=float(s.mean()),native_null_net_p5_p95=np.quantile(s,[.05,.95]).tolist(),
            mean_null_fills=float(np.mean([reports[k]['n'] for k in nullkeys])),reference_fills=reports[ref]['n'],
            mean_null_turnover=float(np.mean([reports[k]['turnover_usdt'] for k in nullkeys])),reference_turnover=reports[ref]['turnover_usdt'],
            mean_null_entry_weighted_bp=float(np.mean([reports[k]['weighted_net_bp'] for k in nullkeys])),
            reference_minus_mean_null=float(reports[ref]['net_usdt']-s.mean()),paired_block95=interval(rd.to_numpy()-nd),
            limitation='Conditional rank randomization only;changes setup incidence and capacity;not an omnibus test of timing,direction,or all research multiplicity.')
    write(OUT/'economic-report.json',dict(at=now(),portfolios=reports,comparisons=comparisons,ranking_null=null,
        native_portfolios=len(reports),reconciled_trades=sum(len(x) for x in ledgers.values()),
        native_alternatives=sum('-replay-' not in k for k in reports),native_reproduction_records=sum('-replay-' in k for k in reports),
        qualification='NO_AUTOMATIC_PROMOTION;see owner report and decision.json',
        definitions=dict(native='Actual pinned Freqtrade full portfolios',extra_friction='Posthoc turnover stress plus separate complete native fee1750 portfolios',
            funding='All source-reported funding event clocks/rates independently reconciled,each once,with preceding hourly source mark OPEN. Exact second-level settlement mark and venue entry/exit priority UNKNOWN.',risk='Same25USDT ceiling in fixed and0.25 modeledrisk portfolios;modeled allowance never charged twice',
            mtm='Hourly source mark OPEN plus realized net,estimated close fee and source-event funding;intrahour drawdown unknown'),
        future_holdout_used=False,private_parent_archive_available=False))
    lines=['| Portfolio | Fills | Native net | +10bp/side beyond displayed fee | Stop-R |','|---|---:|---:|---:|---:|']
    for key,r in reports.items():
        if 'rank-' in key:continue
        lines.append(f"| {key} | {r['n']} | {r['net_usdt']:+.6f} | {r['additional_friction_stress_usdt']['10']:+.6f} | {r['stop_R']:+.3f} |")
    (OUT/'portfolio-table.md').write_text('\n'.join(lines)+'\n')
    print('Reconciled',len(reports),'native portfolios',sum(len(x) for x in ledgers.values()),'trades',flush=True)

if __name__=='__main__':report()
