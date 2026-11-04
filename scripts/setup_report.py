"""Independent order-level PnL/funding audit and opportunity first-passage diagnostics."""
from collections import Counter,defaultdict
from decimal import Decimal as D
import math
import numpy as np
import pandas as pd
from setup_common import *
from recovery_report import path_extremes
from recovery_diagnose import interval

SOURCES={}
def source(pair,kind):
    key=(pair,kind)
    if key not in SOURCES:SOURCES[key]=pd.read_feather(DATA/'development/gate/futures'/(slug(pair)+'-'+kind+'.feather'))
    return SOURCES[key]

def reconcile(directory):
    result=read(directory/'result.json');native=next(iter(result['strategy'].values()))
    states={(x['pair'],pd.Timestamp(x['open_date']).value):x for x in read(directory/'states.json')};rows=[]
    for t in native['trades']:
        st=states[(t['pair'],pd.Timestamp(t['open_date']).value)];g=st['plan'];s=D(-1 if t['is_short'] else 1)
        entries=[o for o in t['orders'] if o['ft_is_entry']];exits=[o for o in t['orders'] if not o['ft_is_entry']]
        qty=sum(D(str(o['amount'])) for o in entries);outqty=sum(D(str(o['amount'])) for o in exits)
        if qty!=outqty:raise ValueError('quantity conservation')
        a=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in entries)
        b=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in exits)
        gross=s*(b-a);fees=a*D(str(t['fee_open']))+b*D(str(t['fee_close']))
        fund=D(str(t.get('funding_fees') or 0));net=gross-fees+fund
        if abs(net-D(str(t['profit_abs'])))>D('.00000011'):raise ValueError('native net mismatch')
        first=pd.Timestamp(min(o['order_filled_timestamp'] for o in entries),unit='ms',tz='UTC');end=pd.Timestamp(t['close_date'])
        f=source(t['pair'],'1h-funding_rate');m=source(t['pair'],'1h-mark').set_index('date').open
        events=f.loc[(f.date>=first)&(f.date<=end)]
        observed={pd.Timestamp(x['at']):x for x in st['funding']}
        if set(events.date)!=set(observed):raise ValueError('source funding coverage mismatch')
        independent=D(0)
        for _,e in events.iterrows():
            ms=e.date.timestamp()*1000
            held=sum(D(str(o['amount'])) for o in entries if o['order_filled_timestamp']<=ms)-sum(D(str(o['amount'])) for o in exits if o['order_filled_timestamp']<ms)
            if abs(float(held)-observed[e.date]['quantity'])>1e-8:raise ValueError('funding held quantity differs')
            independent-=s*held*D(str(e.funding_rate))*D(str(m.loc[:e.date].iloc[-1]))
        if abs(independent-fund)>D('.00000011'):raise ValueError('funding sign/quantity/mark mismatch')
        stoprisk=qty*abs(D(str(t['open_rate']))-D(str(g['stop'])))
        if stoprisk<=0:raise ValueError('invalid initial risk')
        q=source(t['pair'],'15m-futures');q=q.loc[(q.date>=first)&(q.date<end)]
        mfe,mae=path_extremes(q,t['open_rate'],float(s)) if len(q) else (None,None)
        rows.append(dict(pair=t['pair'],side=g['side'],playbook=g['recipe'],decision_id=g['decision_id'],setup_id=g.get('setup_id'),
            entry=first.isoformat(),exit=end.isoformat(),entry_notional=float(a),quantity=float(qty),gross=float(gross),fees=float(fees),funding=float(fund),net=float(net),
            turnover=float(a+b),risk=float(stoprisk),net_R=float(net/stoprisk),modeled_risk=float(a)*g['modeled_loss_per_notional'],
            hold_minutes=(end-first).total_seconds()/60,exit_reason=t['exit_reason'],partial_exits=max(0,len(exits)-1),
            mfe_bp_bar_upper_bound=mfe,mae_bp_bar_lower_bound=mae,stress={str(k):float(net)-float(a+b)*k/1e4 for k in [5,10,20]},
            independent_quantity_fee_funding_net_verified=True))
    write(directory/'ledger.json',rows)
    pd.DataFrame(rows).to_csv(directory/'ledger.csv',index=False)
    return native,rows

def daily(rows):
    days=pd.date_range(protocol()['evaluation_start'],pd.Timestamp(protocol()['end_exclusive'])-pd.Timedelta(days=1),tz='UTC')
    d=pd.Series(0.,index=days)
    for r in rows:d.loc[pd.Timestamp(r['exit']).floor('D')]+=r['net']
    return d

def summary(native,rows):
    a=np.array([r['net'] for r in rows]);wins=a[a>0];loss=a[a<0];d=daily(rows);n=len(rows);days=len(d)
    groups={}
    for k in ['playbook','pair','exit_reason','side']:
        groups[k]={v:dict(n=sum(r[k]==v for r in rows),net=sum(r['net'] for r in rows if r[k]==v)) for v in sorted({r[k] for r in rows})}
    risk=[r['risk'] for r in rows]
    return dict(n=n,net=float(a.sum()),gross=sum(r['gross'] for r in rows),fees=sum(r['fees'] for r in rows),funding=sum(r['funding'] for r in rows),
        profit_factor=float(wins.sum()/-loss.sum()) if len(loss) else None,win_rate=len(wins)/n if n else None,expectancy=float(a.mean()) if n else None,
        net_R=sum(r['net_R'] for r in rows),risk_min_median_max=np.quantile(risk,[0,.5,1]).tolist() if risk else None,
        native_max_drawdown=native.get('max_drawdown_abs'),closed_day_drawdown=float((d.cumsum().cummax().clip(lower=0)-d.cumsum()).max()),
        turnover=sum(r['turnover'] for r in rows),average_hold_minutes=float(np.mean([r['hold_minutes'] for r in rows])) if n else None,
        wallet_time_exposure=sum(r['entry_notional']*r['hold_minutes'] for r in rows)/(1000*days*1440),
        additional_friction_net={str(k):sum(r['stress'][str(k)] for r in rows) for k in [5,10,20]},
        without_top3_winners=float(a.sum()-np.sort(wins)[-3:].sum()),top3_positive_share=float(np.sort(wins)[-3:].sum()/wins.sum()) if len(wins) else None,
        weekly_block95_total=interval(d),chronological_months={k:float(v.sum()) for k,v in d.groupby(d.index.strftime('%Y-%m'))},
        groups=groups,partial_exits=sum(r['partial_exits'] for r in rows),timedout_entry_orders=native.get('timedout_entry_orders'),
        rejected_native_signals=native.get('rejected_signals'),calendar_days=days)

def passage(pair,g,target=None):
    """Barrier diagnostic only. No simulated portfolio or hypothetical cash ledger."""
    at=pd.Timestamp(g['available_at']);end=at+pd.Timedelta(hours=g['max_hold_hours'])
    if end>pd.Timestamp(protocol()['end_exclusive'],tz='UTC'):return None
    q=source(pair,'15m-futures');q=q.loc[(q.date>=at)&(q.date<end)]
    if len(q)!=int(g['max_hold_hours']*4):return None
    s=1 if g['side']=='long' else -1;entry=g['reference'];target=g['target'] if target is None else target
    mfe,mae=path_extremes(q,entry,s);outcome='NEITHER';ambiguous=False;elapsed=None
    for i,(_,r) in enumerate(q.iterrows()):
        stop=(r.low<=g['stop'] if s==1 else r.high>=g['stop'])
        hit=(r.high>=target if s==1 else r.low<=target)
        if stop or hit:
            ambiguous=bool(stop and hit);outcome='STOP_FIRST' if stop else 'TARGET_FIRST';elapsed=i*15;break
    return dict(outcome=outcome,ambiguous_same_bar=ambiguous,first_passage_minutes=elapsed,mfe_bp=mfe,mae_bp=mae,
                endpoint_bp=s*(float(q.close.iloc[-1])/entry-1)*1e4)

def report():
    portfolios={};ledgers={}
    for p in sorted((OUT/'native').glob('*/result.json')):
        native,rows=reconcile(p.parent);ledgers[p.parent.name]=rows;portfolios[p.parent.name]=summary(native,rows)
    comparisons={};baseline='v4-reference-fixed-touch-750';primary='setup-fixed-touch-750'
    for a,b in [(primary,baseline),('old-ranking-fixed-touch-750',primary),('simple-trigger-fixed-touch-750',primary),('fixed-r-fixed-touch-750',primary),('management-fixed-touch-750',primary)]:
        if a in ledgers and b in ledgers:
            diff=daily(ledgers[a])-daily(ledgers[b]);comparisons[a+' minus '+b]=dict(net_difference=float(diff.sum()),weekly_block95=interval(diff),
                common_entries=len({(x['pair'],x['entry']) for x in ledgers[a]}&{(x['pair'],x['entry']) for x in ledgers[b]}),
                capacity_note='Complete separate portfolios;changed holding periods/selection affect later capacity. Returns are not additive.')
    decisions=read(OUT/'decisions.json');paths=[]
    admitted=read(WORK/'plans/setup.json');selected={g['setup_id'] for z in admitted.values() for g in z.values()}
    for x in decisions:
        if not x['plan']:continue
        g=x['plan'];a=passage(x['pair'],g)
        if a:
            s=1 if g['side']=='long' else -1;b=passage(x['pair'],g,g['reference']+s*3*abs(g['reference']-g['stop']))
            paths.append(dict(pair=x['pair'],setup_id=g['setup_id'],selected=g['setup_id'] in selected,playbook=g['recipe'],objective=a,fixed_r=b))
    write(OUT/'first-passage.json',paths)
    nullkeys=['null-ranking-'+str(i)+'-fixed-touch-750' for i in [1,2,3]];null={}
    if all(k in portfolios for k in nullkeys) and primary in portfolios:
        v=np.array([portfolios[k]['net'] for k in nullkeys]);ref=portfolios[primary]['net']
        null=dict(replicates=3,mean_net=float(v.mean()),conditional_empirical_upper_p=float((1+(v>=ref).sum())/4),resolution=.25,
                  note='Three seeded equal-slot nulls are a coarse diagnostic, not a well-powered significance test. Turnover and capacity differ.')
    casebook=[]
    # Freeze entry evidence first in each case; future passage is a separate field.
    for category,predicate in [('accepted',lambda x:x['plan'] and x['plan']['setup_id'] in selected),('target_obstacle',lambda x:'OBSTACLE' in x['reason']),('structural_failure',lambda x:x['state']=='INVALIDATED'),('expired',lambda x:x['state']=='EXPIRED')]:
        for book in ['continuation','reversal','breakout']:
            x=next((z for z in decisions if z['playbook']==book and predicate(z)),None)
            if x:casebook.append(dict(category=category,entry_time_evidence=x,future_outcome_separate=passage(x['pair'],x['plan']) if x['plan'] else {'status':'NO_ADMITTED_TRADE'}))
    write(OUT/'casebook.json',casebook)
    funnel=read(OUT/'funnel.json');raw=eligible=0
    for pair in pairs():
        f=pd.read_pickle(WORK/'features/new'/(slug(pair)+'.pkl'));at=f.date+pd.Timedelta(minutes=15)
        mask=(at>=pd.Timestamp(protocol()['evaluation_start'],tz='UTC'))&(at<pd.Timestamp(protocol()['end_exclusive'],tz='UTC'))
        raw+=int(mask.sum());eligible+=int((mask&f.eligible&f.setup_valid).sum())
    funnel.update(raw_market_checks=raw,eligible_market_checks=eligible,
        setup_count_note='Distinct IDs include setups carried into evaluation from warmup; ARM events count events occurring inside evaluation.')
    write(OUT/'funnel.json',funnel)
    write(OUT/'economic-report.json',dict(portfolios=portfolios,comparisons=comparisons,ranking_null=null,funnel=funnel,
        native_portfolios=len(portfolios),reconciled_trade_records=sum(map(len,ledgers.values())),
        path_diagnostics=dict(n=len(paths),objective=dict(Counter(x['objective']['outcome'] for x in paths)),fixed_r=dict(Counter(x['fixed_r']['outcome'] for x in paths)),
            missed_target_first=sum(not x['selected'] and x['objective']['outcome']=='TARGET_FIRST' for x in paths),avoided_stop_first=sum(not x['selected'] and x['objective']['outcome']=='STOP_FIRST' for x in paths)),
        caveats=['DEVELOPMENT_ONLY','CURRENT_SURVIVOR_UNIVERSE','CURRENT_CONTRACT_SPEC_NOT_HISTORICAL_MEMBERSHIP','QUEUE_AND_OBSERVED_PARTIAL_FILLS_UNKNOWN',
                 'SOURCE_FUNDING_CLOCK_WITH_PRECEDING_HOURLY_MARK_OPEN_NOT_EXACT_SETTLEMENT_MARK','ADMISSION_ALLOWANCE_NOT_DOUBLE_CHARGED',
                 'BAR_PATH_EXTREMES_ARE_BOUNDS_NOT_TICK_PATH','PROFILE_ECONOMICS_NOT_TESTED','NO_RESERVED_HOLDOUT_ACCESS']))
    lines=['| Native portfolio | Fills | Net USDT | +10bp/side | Net stop-R |','|---|---:|---:|---:|---:|']
    for k,v in portfolios.items():lines.append(f"| {k} | {v['n']} | {v['net']:+.6f} | {v['additional_friction_net']['10']:+.6f} | {v['net_R']:+.3f} |")
    (OUT/'portfolio-table.md').write_text('\n'.join(lines)+'\n')
    print('Reconciled',len(portfolios),'native portfolios',sum(map(len,ledgers.values())),'trade records',flush=True)
if __name__=='__main__':report()
