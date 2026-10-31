"""Independent recorded-evidence arithmetic plus source-candle reconstruction.

Requires pinned native image and exact reacquired sources. Does not rewrite any
old evidence, place orders, tune parameters or label development as holdout.
"""
import collections
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'research/bonus'),str(ROOT/'research/session3'),str(ROOT/'user_data/strategies')]
from bonus_pipeline import analyzed
from bonus_common import config,spec
from bonus_data import frame
from OpportunityRouterV1 import RouterOnlyV1
from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
from freqtrade.enums import CandleType

OLD=ROOT/'evidence/bonus'
OUT=ROOT/'evidence/master-audit'


def read(path):
    return json.loads(path.read_text())


def clean(value):
    if isinstance(value,dict):
        return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [clean(v) for v in value]
    if isinstance(value,(pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value,np.generic):
        return clean(value.item())
    if isinstance(value,float) and not np.isfinite(value):
        return None
    return value


def save(path,obj):
    if path.exists():
        raise ValueError('preserve existing result: '+str(path))
    path.write_text(json.dumps(clean(obj),indent=2,allow_nan=False)+'\n')


def native(name):
    return read(OLD/'native-results'/(name+'.json'))['strategy'][name]['trades']


def clock(value):
    return pd.Timestamp(value)


def independent_accounting(trades):
    total=D(0);max_residual=D(0);fees=D(0);funding=D(0);gross=D(0)
    for trade in trades:
        entries=[x for x in trade['orders'] if x['ft_is_entry']]
        exits=[x for x in trade['orders'] if not x['ft_is_entry']]
        quantity=sum(D(str(x['amount'])) for x in entries)
        assert abs(quantity-sum(D(str(x['amount'])) for x in exits))<D('1e-8')
        average=sum(D(str(x['amount']))*D(str(x['safe_price'])) for x in entries)/quantity
        sign=D(-1 if trade['is_short'] else 1)
        g=sum(sign*D(str(x['amount']))*(D(str(x['safe_price']))-average) for x in exits)
        f=sum(D(str(x['amount']))*D(str(x['safe_price']))*D(str(trade['fee_open'] if x['ft_is_entry'] else trade['fee_close'])) for x in trade['orders'])
        u=D(str(trade.get('funding_fees') or 0));net=D(str(trade['profit_abs']))
        residual=abs(g-f+u-net)
        assert residual<D('0.00001')
        gross+=g;fees+=f;funding+=u;total+=net;max_residual=max(max_residual,residual)
    return dict(count=len(trades),gross=str(gross),fees=str(fees),native_funding=str(funding),
                native_net=str(total),max_residual=str(max_residual),internal_accounting='PASS')


def funding_bounds(trades):
    rows=[]
    for trade in trades:
        symbol=trade['pair']
        rates=frame(symbol,'1h','funding_rate');marks=frame(symbol,'1h','mark').set_index('date')
        low=high=D(0);events=[]
        for _,event in rates.iterrows():
            stamp=int(event.date.timestamp()*1000)
            if not trade['open_timestamp']<=stamp<=trade['close_timestamp']:
                continue
            before=sum(D(str(o['amount']))*(1 if o['ft_is_entry'] else -1)
                       for o in trade['orders'] if o['order_filled_timestamp']<stamp)
            incoming=sum(D(str(o['amount'])) for o in trade['orders'] if o['ft_is_entry'] and o['order_filled_timestamp']==stamp)
            outgoing=sum(D(str(o['amount'])) for o in trade['orders'] if not o['ft_is_entry'] and o['order_filled_timestamp']==stamp)
            quantities=[max(D(0),x) for x in (before,before+incoming,before-outgoing,before+incoming-outgoing)]
            unit=D(str(float(event.funding_rate)))*D(str(float(marks.loc[event.date,'open'])))*(-1 if not trade['is_short'] else 1)
            values=[q*unit for q in quantities];low+=min(values);high+=max(values)
            events.append(dict(at=event.date.isoformat(),minimum=str(min(values)),maximum=str(max(values)),ambiguous=bool(incoming or outgoing)))
        funding=D(str(trade.get('funding_fees') or 0))
        rows.append(dict(pair=symbol,open_date=trade['open_date'],native=str(funding),minimum=str(low),maximum=str(high),
                         outside=max(D(0),low-funding,funding-high)>D('1e-8'),events=events))
    return rows


def economics(trades):
    pnl=np.array([x['profit_abs'] for x in trades])
    turnover=sum(float(o['amount'])*float(o['safe_price']) for t in trades for o in t['orders'])
    rng=np.random.default_rng(4101)
    sums=rng.choice(pnl,size=(10000,len(pnl)),replace=True).sum(axis=1) if len(pnl) else np.array([0.])
    byside={side:dict(trades=sum(t['is_short']==(side=='short') for t in trades),
                     net=sum(t['profit_abs'] for t in trades if t['is_short']==(side=='short'))) for side in ('long','short')}
    return dict(trades=len(trades),net=float(pnl.sum()),side=byside,
                extra_bps_per_side={str(b):float(pnl.sum()-turnover*b/10000) for b in (0,1.5,5,10,20)},
                net_without_top3=float(np.sort(pnl)[:-3].sum()) if len(pnl)>=3 else None,
                descriptive_iid_bootstrap_net_95=np.quantile(sums,[.025,.975]).tolist(),
                bootstrap_warning='Descriptive IID trade resampling ignores serial/cross-market dependence and selection; not a qualification test',
                friction_warning='Turnover overlay keeps modeled fills; 1.5bp/side is current public taker fee sensitivity, not historical fee verification')


def candles_for_chart(frame,start,end,step):
    d=frame.loc[(frame.date>=start)&(frame.date+pd.Timedelta(minutes=step)<=end)]
    fields=[k for k in ('date','open','high','low','close','volume','vwap','ema20','ema50') if k in d]
    return clean(d[fields].to_dict('records'))


def main():
    assert read(OUT/'source-identity.json')['exact_original_bytes']
    ledger=pd.read_csv(OLD/'opportunity-ledger.csv')
    ledger=ledger.loc[ledger.variant.eq('RouterOnlyV1')].copy()
    assert len(ledger)==92
    old_counts=ledger.reason.value_counts().to_dict()
    assert old_counts==dict(CHEAP_SCREEN_OR_RANK=50,TARGET_ROOM_OR_COST=32,TRADE=10)
    router=native('RouterOnlyV1');managed=native('RouterOnlyM1V1')
    parents={'vwap':native('VWAPTrendContinuationV1'),'sweep':native('LiquiditySweepReversalV1')}
    plans=[p for p in read(OLD/'trade-plans.json') if p['variant']=='RouterOnlyV1']
    assert len(plans)==10 and len(router)==9
    feature_frames={s:analyzed(s) for s in ledger.symbol.unique()}
    reconstructed=[]; parent_signals={};reconstruction_mismatches=[]
    for symbol,d in feature_frames.items():
        metadata={'pair':symbol};cfg=config('RouterOnlyV1')|{'candle_type_def':CandleType.FUTURES}
        routed=RouterOnlyV1(cfg).populate_entry_trend(d.copy(),metadata)
        choices={recipe:klass(cfg).populate_entry_trend(d.copy(),metadata) for recipe,klass in
                 [('vwap',VWAPTrendContinuationV1),('sweep',LiquiditySweepReversalV1)]}
        for _,old in ledger.loc[ledger.symbol.eq(symbol)].iterrows():
            at=clock(old.decision_at);idx=d.index[d.date+pd.Timedelta(minutes=15)==at][0]
            row=routed.loc[idx];parent=choices[old.recipe].loc[idx]
            side='long' if parent.enter_long==1 else 'short' if parent.enter_short==1 else None
            parent_signals[(symbol,at.isoformat())]=side
            if old.reason!=row.bonus_reason:
                reconstruction_mismatches.append(dict(symbol=symbol,at=at.isoformat(),old=old.reason,new=row.bonus_reason))
            reconstructed.append(dict(symbol=symbol,at=at.isoformat(),recipe=old.recipe,side=side,
                                      reason=row.bonus_reason,closed_15m_at=at.isoformat(),
                                      adx_1h=float(row.adx_1h),struct_direction_1h=row.struct_direction_1h,
                                      structure_known_at=str(row.get('struct_known_at_1h')),
                                      rvol=float(row.rvol),vwap=float(row.vwap),reference=float(row.close)))
    assert not reconstruction_mismatches
    # Independently ingest the entire ranking CSV and check every recorded selection.
    ranking=pd.read_csv(OLD/'market-ranking.csv')
    ranking['decision_at']=pd.to_datetime(ranking.decision_at,utc=True)
    schedule=read(OLD/'schedule.json')['decisions']
    rank_mismatches=[]
    for at,group in ranking.groupby('decision_at'):
        selected=group.loc[group.cheap_pass].sort_values(['score','symbol'],ascending=[False,True]).symbol.iloc[:3].tolist()
        if schedule[at.isoformat()]['selected']!=selected:
            rank_mismatches.append(at.isoformat())
    assert not rank_mismatches
    max_score_error=0.;max_volume_error=0.
    btc=frame('BTC/USDT:USDT').set_index('date').close.pct_change(16)
    for symbol in ledger.symbol.unique():
        base=frame(symbol).set_index('date');ret=base.close.pct_change(16)
        relative=ret if symbol=='BTC/USDT:USDT' else ret-btc
        quote=base.volume*(base.high+base.low+base.close)/3
        activity=quote.rolling(16,min_periods=16).sum()/quote.shift(16).rolling(16,min_periods=16).sum()
        expected=(relative.abs()+.01*activity.clip(0,3)).to_numpy()
        recorded=ranking.loc[ranking.symbol.eq(symbol)].sort_values('decision_at')
        max_score_error=max(max_score_error,float(np.nanmax(abs(expected-recorded.score.to_numpy()))))
        max_volume_error=max(max_volume_error,float(np.nanmax(abs(quote.rolling(96,min_periods=96).sum().to_numpy()-recorded.quote_volume24h_proxy.to_numpy()))))
    assert max_score_error<1e-12
    cases=[];plot_data=[]
    for number,plan in enumerate(sorted(plans,key=lambda p:p['decision_at']),1):
        symbol=plan['symbol'];at=clock(plan['decision_at']);g=plan['plan'];sign=-1 if g['side']=='short' else 1
        trade=next((t for t in router if t['pair']==symbol and clock(t['open_date'])==at),None)
        parent=next((t for t in parents[g['recipe']] if t['pair']==symbol and clock(t['open_date'])==at and t['is_short']==(sign==-1)),None)
        partial=next((t for t in managed if t['pair']==symbol and clock(t['open_date'])==at),None)
        assert parent is not None or trade is None
        feature=feature_frames[symbol];row=feature.loc[feature.date+pd.Timedelta(minutes=15)==at].iloc[0]
        known_stop=g['stop'];obstacles=[]
        for key in ('prior_day_high','prior_day_low','prior_swing_high','prior_swing_low','vp_val','vp_vah','vp_poc'):
            value=row.get(key)
            if pd.notna(value) and 0<sign*(value-g['reference'])<sign*(g['target']-g['reference']):
                obstacles.append(dict(source=key,value=float(value),net_rr=(sign*(value-g['reference'])/g['reference']-.0035)/(g['risk_fraction']+.0035)))
        stop_time=clock(trade['close_date']) if trade else at+pd.Timedelta(hours=g['max_hold_hours'])
        fullbars=feature.loc[(feature.date>=at)&(feature.date+pd.Timedelta(minutes=15)<stop_time)]
        entry=trade['open_rate'] if trade else g['reference']
        mfe=mae=None
        if len(fullbars):
            mfe=(fullbars.high.max()/entry-1) if sign==1 else (1-fullbars.low.min()/entry)
            mae=(fullbars.low.min()/entry-1) if sign==1 else (1-fullbars.high.max()/entry)
        item=dict(case_id=f'trade-{number:02d}',symbol=symbol,at=at.isoformat(),side=g['side'],recipe=g['recipe'],
                  status='NATIVE_FILLED' if trade else 'PLAN_UNFILLED_NO_PNL',plan=g,
                  information_at_entry=next(r for r in reconstructed if r['symbol']==symbol and r['at']==at.isoformat()),
                  obstacles=obstacles,router_net=trade['profit_abs'] if trade else None,
                  parent_net=parent['profit_abs'] if parent and trade else None,
                  router_exit=trade['exit_reason'] if trade else None,
                  exit_clock=trade['close_date'] if trade else None,
                  parent_exit=parent['exit_reason'] if parent else None,
                  M1_net=partial['profit_abs'] if partial else None,
                  complete_bar_mfe=mfe,complete_bar_mae=mae,
                  excursion_limit='Excludes exit bar; no executable price or intrabar ordering claim')
        cases.append(item)
        path_end=max(stop_time,clock(parent['close_date']) if parent else stop_time)+pd.Timedelta(hours=2)
        hourly=frame(symbol,'1h')
        plot_data.append(dict(case_id=item['case_id'],symbol=symbol,at=at.isoformat(),side=g['side'],recipe=g['recipe'],
                             plan=g,obstacles=obstacles,entry_15m=candles_for_chart(feature,at-pd.Timedelta(hours=12),at,15),
                             entry_1h=candles_for_chart(hourly,at-pd.Timedelta(hours=48),at,60),
                             path=candles_for_chart(feature,at-pd.Timedelta(hours=2),path_end,15),
                             trade=trade,parent=parent,information_at_entry=item['information_at_entry']))
    rejected=[]
    for old in reconstructed:
        if old['reason']=='TRADE':continue
        at=clock(old['at']);match=next((t for t in parents[old['recipe']] if t['pair']==old['symbol'] and clock(t['open_date'])==at and t['is_short']==(old['side']=='short')),None)
        rejected.append(old|dict(parent_matched=match is not None,parent_net=match['profit_abs'] if match else None))
    # First chronologically in each rejection-reason x parent-outcome category.
    examples=[]
    for reason in ('CHEAP_SCREEN_OR_RANK','TARGET_ROOM_OR_COST'):
        for positive in (False,True):
            pool=sorted([r for r in rejected if r['reason']==reason and r['parent_matched'] and (r['parent_net']>0)==positive],key=lambda r:r['at'])
            if not pool:continue
            chosen=pool[0];identifier=f'rejected-{len(examples)+1:02d}';examples.append(chosen|dict(case_id=identifier))
            at=clock(chosen['at']);d=feature_frames[chosen['symbol']]
            parent=next(t for t in parents[chosen['recipe']] if t['pair']==chosen['symbol'] and clock(t['open_date'])==at and t['is_short']==(chosen['side']=='short'))
            plot_data.append(dict(case_id=identifier,symbol=chosen['symbol'],at=at.isoformat(),side=chosen['side'],recipe=chosen['recipe'],
                plan=None,obstacles=[],entry_15m=candles_for_chart(d,at-pd.Timedelta(hours=12),at,15),
                entry_1h=candles_for_chart(frame(chosen['symbol'],'1h'),at-pd.Timedelta(hours=48),at,60),
                path=candles_for_chart(d,at-pd.Timedelta(hours=2),clock(parent['close_date'])+pd.Timedelta(hours=2),15),
                trade=None,parent=parent,information_at_entry=chosen))
    matched=[x for x in cases if x['status']=='NATIVE_FILLED']
    thesis=[x for x in matched if x['router_exit']=='closed_hour_thesis_invalidated']
    m1delta=[m['profit_abs']-r['profit_abs'] for r in router for m in managed if m['pair']==r['pair'] and m['open_date']==r['open_date']]
    aggregates={reason:dict(total=sum(r['reason']==reason for r in rejected),matched=sum(r['reason']==reason and r['parent_matched'] for r in rejected),
        parent_net=sum(r['parent_net'] for r in rejected if r['reason']==reason and r['parent_matched'])) for reason in ('CHEAP_SCREEN_OR_RANK','TARGET_ROOM_OR_COST')}
    hashes=[]
    for line in (OLD/'artifact-hashes.sha256').read_text().splitlines():
        digest,name=line.split(maxsplit=1)
        hashes.append(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest)
    assert all(hashes)
    preservation=read(OUT/'preservation-source.json')
    tracked=preservation['files']
    changed=preservation['changed']
    assert not changed
    report=dict(source_reconstruction=dict(candidate_count=len(reconstructed),counts=old_counts,mismatches=reconstruction_mismatches),
        ranking=dict(rows=len(ranking),decision_times=len(schedule),selection_mismatches=rank_mismatches,
                     max_score_error=max_score_error,max_quote_volume_absolute_error=max_volume_error,
                     claim='All recorded five-market rows ingested; selection/formula reproduced, full-exchange selection not established'),
        matched_exits=dict(trades=len(matched),parent_net=sum(x['parent_net'] for x in matched),router_net=sum(x['router_net'] for x in matched),
            router_minus_parent=sum(x['router_net']-x['parent_net'] for x in matched),
            thesis_exits=len(thesis),thesis_exit_delta=sum(x['router_net']-x['parent_net'] for x in thesis),
            warning='Same entry clocks; original parent portfolio management differs. Nine inspected trades are not a holdout'),
        M1=dict(advantage=sum(m1delta),advantage_without_best=max([0.])+sum(m1delta)-max(m1delta),enabled=False),
        rejected_summary=aggregates,all_rejected=rejected,casebook=cases,rejected_examples=examples,
        funding=dict(M0=funding_bounds(router),M1=funding_bounds(managed)),
        native_accounting={name:independent_accounting(native(name)) for name in read(OLD/'economic-results.json').get('variants',{})} if isinstance(read(OLD/'economic-results.json').get('variants'),dict) else {},
        economics={name:economics(native(name)) for name in ('VWAPTrendContinuationV1','LiquiditySweepReversalV1','RouterOnlyV1','RouterOnlyM1V1')},
        preservation=dict(original_files=len(tracked),changed=changed,old_artifact_hashes=len(hashes),all_hashes_match=all(hashes)))
    # Always independently reconcile every original native policy, including zero-trade ones.
    report['native_accounting']={name:independent_accounting(native(name)) for name in spec()['variants']}
    save(OUT/'independent-review.json',report)
    chart_path=ROOT/'work/master-chart-data.json'
    chart_path.write_text(json.dumps(clean(plot_data),allow_nan=False)+'\n')
    print(json.dumps(clean({k:report[k] for k in ('source_reconstruction','ranking','matched_exits','M1','rejected_summary','preservation')}),indent=2))


if __name__=='__main__':
    main()
