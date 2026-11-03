"""Causal selection inputs and full portfolios evaluated by official native Freqtrade."""
from collections import Counter
import json
import sys
import zipfile
import numpy as np
import pandas as pd
from session4_common import *


def prepare():
    from freqtrade.strategy import merge_informative_pair
    from session4_features import indicators,hourly,candidates
    if (OUT/'selection-summary.json').exists():raise ValueError('preserve completed experiment inputs')
    stage();frames={};pieces=[];all_candidates={};checks=[]
    contracts=read(OUT/'contracts.json');listing=[]
    for pair in read(OUT/'cohort.json')['pairs']:
        slug=pair.replace('/','_').replace(':','_')
        missing=[suffix for suffix in ('15m-futures','1h-futures','1h-mark','1h-funding_rate') if not (DATA/'futures'/(slug+'-'+suffix+'.feather')).exists()]
        if missing:
            listing.append(dict(symbol=pair,eligible_bars=0,missing=missing,reason='SOURCE_OUTAGE_INCOMPLETE_INPUT_NO_RETURNS_INSPECTED'))
            continue
        b=pd.read_feather(DATA/'futures'/(slug+'-15m-futures.feather'))
        h=pd.read_feather(DATA/'futures'/(slug+'-1h-futures.feather'))
        target=STATE/'features'/(slug+'.pkl')
        d=pd.read_pickle(target) if target.exists() else indicators(merge_informative_pair(b,hourly(h),'15m','1h',ffill=True))
        d['symbol']=pair
        d['eligible'] &= d.date>=h.date.iloc[0]+pd.Timedelta(hours=240)
        target.parent.mkdir(parents=True,exist_ok=True);d.to_pickle(target)
        frames[pair]=d
        pieces.append(d[['date','eligible','prior_day_quote','prior7_quote','return4h','activity','ema20_1h','ema50_1h','atr14','close','prior_low','prior_high']].assign(symbol=pair))
        all_candidates[pair]={mode:candidates(d,mode) for mode in ('reference','structure','hour')}
        listing.append(dict(symbol=pair,create_time_public_current_contract=contracts[pair].get('listing_time_source'),
            first_returned_candle=b.date.iloc[0].isoformat(),last=b.date.iloc[-1].isoformat(),
            first_eligible_at=(d.loc[d.eligible,'date'].iloc[0]+pd.Timedelta(minutes=15)).isoformat() if d.eligible.any() else None,
            eligible_bars=int(d.eligible.sum()),coverage_rows=len(b),coverage_gaps=int(b.date.diff().iloc[1:].ne(pd.Timedelta(minutes=15)).sum()),
            historical_membership='OBSERVED_RETURNED_CANDLES_ONLY; delisted omissions unresolved'))
        print('Prepared',pair,{m:dict(Counter(x['reason'] for x in items)) for m,items in all_candidates[pair].items()},flush=True)
        # Prefix equality on feature values that enter decisions (future suffix must not change past).
        cut=min(1200,len(b)-1)
        small=indicators(merge_informative_pair(b.iloc[:cut].copy(),hourly(h.loc[h.date<b.date.iloc[cut]].copy()),'15m','1h',ffill=True))
        keys=['vwap','atr14','prior_day_high','prior_session_low','swing_high','swing_low','struct_direction','fvg_retest_up','recent_shift_long','prior7_quote']
        same=True
        for key in keys:
            a=small[key].reset_index(drop=True);z=d.iloc[:cut][key].reset_index(drop=True)
            same &= bool(((a==z)|(a.isna()&z.isna())).all())
        checks.append(dict(pair=pair,cut=cut,prefix_equal=same,columns=keys))
    if not all(c['prefix_equal'] for c in checks):
        write(OUT/'causality.json',checks);raise ValueError('prefix causality failed')
    write(OUT/'causality.json',checks);write(OUT/'listing-coverage.json',listing)
    wide=pd.concat(pieces,ignore_index=True);btc=frames['BTC/USDT:USDT'].set_index('date').return4h
    wide['relative']=wide.return4h-wide.date.map(btc)
    wide.loc[wide.symbol.eq('BTC/USDT:USDT'),'relative']=wide.return4h
    specs=read(ROOT/'research/session4/protocol.json');variants=specs['variants'];slots={v:{} for v in variants}
    rngs={v:np.random.default_rng(int(v.split('-')[1])) for v in variants if v.startswith('random-')}
    eligibility=[]
    for date,g in wide.groupby('date',sort=True):
        at=(date+pd.Timedelta(minutes=15)).isoformat();g=g.loc[g.eligible & np.isfinite(g.relative)&np.isfinite(g.activity)].copy()
        if not len(g):continue
        eligibility.append(dict(at=at,eligible=len(g),symbols=sorted(g.symbol.tolist())))
        for recipe in ('continuation','reversal'):
            for side,sign in [('long',1),('short',-1)]:
                q=g.loc[sign*(g.ema20_1h-g.ema50_1h)>0].copy() if recipe=='continuation' else g.copy()
                if q.empty:continue
                q['score']=sign*q.relative+.01*q.activity.clip(upper=3) if recipe=='continuation' else sign*(q.close-(q.prior_low if sign==1 else q.prior_high))/q.atr14
                ranked=q.sort_values(['score','symbol'],ascending=[False,True]).symbol.head(3).tolist();lane=recipe+':'+side
                for v in ('reference','structure','hour'):slots[v].setdefault(at,{})[lane]=ranked
                slots['systematic'].setdefault(at,{})[lane]=q.sort_values(['prior_day_quote','symbol'],ascending=[False,True]).symbol.head(3).tolist()
                for v,rng in rngs.items():
                    choices=sorted(q.symbol.tolist());slots[v].setdefault(at,{})[lane]=rng.choice(choices,size=min(3,len(choices)),replace=False).tolist()
    counts={};full_ledger=[]
    for v in variants:
        plans={};reasons=Counter();mode=v if v in ('structure','hour') else 'reference'
        for pair,by_mode in all_candidates.items():
            for item in by_mode[mode]:
                reason=item['reason'];g=item['plan'];at=item['at'];lane=item['recipe']+':'+item['side']
                if not '2026-08-05'<=at<'2026-11-03':continue
                if reason=='TRADE' and pair not in slots[v].get(at,{}).get(lane,[]):reason='REJECT_RANK_OR_LIQUIDITY'
                reasons[reason]+=1
                if reason=='TRADE':
                    old=plans.setdefault(pair,{}).get(at)
                    if old and old['side']!=g['side']:
                        plans[pair].pop(at);reasons['CONFLICTING_SIDES']+=1
                    elif old is None:plans[pair][at]=dict(g,decision_id=pair+':'+g['decision_id'])
                if v in ('reference','structure','hour'):
                    r=frames[pair].iloc[item['index']]
                    full_ledger.append(dict(variant=v,symbol=pair,at=at,recipe=item['recipe'],side=item['side'],reason=reason,plan=g,
                        hour_structure=str(r.get('struct_direction_1h')),regime='TREND' if r.adx_1h>=25 else 'RANGE_WEAK_TREND',
                        equal_high=bool(r.equal_high),equal_low=bool(r.equal_low),fvg_retest=bool(r.fvg_retest_up or r.fvg_retest_down),
                        profile='OHLCV_PROXY',flow='UNKNOWN',dealing_location=float(r.dealing_location) if pd.notna(r.dealing_location) else None))
        write(STATE/'plans'/(v+'.json'),plans)
        counts[v]=dict(plans=sum(len(v) for v in plans.values()),reasons=dict(reasons),plan_sha256=sha(STATE/'plans'/(v+'.json')))
    write(OUT/'eligibility.json',eligibility)
    write(OUT/'opportunities.json',full_ledger)
    write(OUT/'selection-summary.json',counts)
    write(OUT/'feature-manifest.json',dict(files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted((STATE/'features').glob('*.pkl'))],
        known_fidelity='CAUSAL_CLOSED_CANDLES; receipt clocks historically UNKNOWN; profiles OHLCV_PROXY; orderflow UNKNOWN'))


def native(label,base=None,detail=False,through=False,constant_risk=False,open_only=False,market=False):
    import re
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,40}',label):raise ValueError('invalid native result label')
    from freqtrade.commands import Arguments
    from freqtrade.commands.optimize_commands import setup_optimize_configuration
    from freqtrade.enums import RunMode
    from freqtrade.optimize.backtesting import Backtesting
    from freqtrade.persistence import LocalTrade
    from policy_native import PersistentFunding
    stage();base=base or label
    if base not in read(ROOT/'research/session4/protocol.json')['variants']:raise ValueError('unregistered input variant')
    cfg=config('Session4Replay',label,'market' if market else 'limit');cfg['session4_plans']=str(STATE/'plans'/(base+'.json'))
    cfg['session4_constant_risk']=constant_risk
    if constant_risk:cfg['policy_notional_cap']=50.
    cfg['db_url']='sqlite://'
    if (OUT/'native-results'/(label+'.json')).exists():raise ValueError('preserve completed native portfolio')
    parent=ROOT/'user_data/backtest_results/session4'/label
    directory=parent/f'attempt-{len(list(parent.glob("attempt-*")))+1:03}'
    directory.mkdir(parents=True)
    # A research replay always starts a new account. Only real paper restarts reuse state.
    cfg['policy_state']=str(STATE/'research-state'/label/(directory.name+'.sqlite'))
    cfg['policy_events']=str(OUT/'events'/(label+'-'+directory.name+'.jsonl'))
    path=STATE/'configs'/(label+'-'+directory.name+'.json');write(path,cfg)
    args=['backtesting','--config',str(path),'--datadir',str(DATA),'--timerange','20261029-20261103' if detail else '20260805-20261103',
          '--cache','none','--enable-protections','--export','trades','--backtest-directory',str(directory)]
    if detail:
        if not read(OUT/'detail-manifest.json')['complete']:raise ValueError('detail data incomplete')
        args+=['--timeframe-detail','1m']
    # Execution sensitivity is installed below against the pinned method, never a new engine.
    engine_cls=type('Session4Native',(PersistentFunding,Backtesting),{})
    cfg=setup_optimize_configuration(Arguments(args).get_parsed_arg(),RunMode.BACKTEST)
    cfg['exchange']['pair_whitelist']=[pair for pair in cfg['exchange']['pair_whitelist'] if (STATE/'features'/(pair.replace('/','_').replace(':','_')+'.pkl')).exists() and all((DATA/'futures'/(pair.replace('/','_').replace(':','_')+'-'+suffix+'.feather')).exists() for suffix in ('15m-futures','1h-futures','1h-mark','1h-funding_rate'))]
    from session4_metadata import install
    install(DATA.parent/'contract-source.json')
    engine=engine_cls(cfg)
    captured=read(DATA.parent/'contract-source.json');restored=[]
    for pair in cfg['exchange']['pair_whitelist']:
        if pair not in engine.exchange._leverage_tiers and captured[pair]['tiers']:
            original=captured[pair]['market'];m=engine.exchange.markets[pair]
            if m['id']!=original['id'] or m['contractSize']!=original['contractSize']:raise ValueError('contract identity changed')
            engine.exchange._leverage_tiers[pair]=[engine.exchange.parse_leverage_tier(t) for t in captured[pair]['tiers']];restored.append(pair)
    if through or open_only:
        from freqtrade.optimize.backtesting import LOW_IDX,HIGH_IDX,OPEN_IDX
        original=engine._try_close_open_order
        def trade_through(order,trade,current_date,row):
            if order and order.ft_order_side==trade.entry_side and order.order_type=='limit':
                if open_only:
                    if current_date>order.order_date_utc:return False
                    if not trade.is_short and row[OPEN_IDX]>order.ft_price:return False
                    if trade.is_short and row[OPEN_IDX]<order.ft_price:return False
                # One bp THROUGH the limit in its fill direction; exits unchanged.
                bound=row[HIGH_IDX] if trade.is_short else row[LOW_IDX]
                if through and trade.is_short and bound<order.ft_price*1.0001:return False
                if through and not trade.is_short and bound>order.ft_price*.9999:return False
            return original(order,trade,current_date,row)
        engine._try_close_open_order=trade_through
    engine.start()
    archive=directory/read(directory/'.last_result.json')['latest_backtest']
    with zipfile.ZipFile(archive) as z:
        member=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
        result=json.loads(z.read(member))
    trades=result['strategy']['Session4Replay']['trades']
    write(OUT/'native-results'/(label+'.json'),result)
    states=[dict(id=t.id,pair=t.pair,open_date=t.open_date_utc.isoformat(),plan=t.get_custom_data('policy_plan'),
        state=t.get_custom_data('policy_state'),funding=t.get_custom_data('v3_funding_events',[])) for t in LocalTrade.bt_trades]
    write(OUT/'native-states'/(label+'.json'),states)
    write(OUT/'native-provenance'/(label+'.json'),dict(image=IMAGE,args=args,config_sha256=sha(path),
        archive_sha256=sha(archive),archive_path=str(archive.relative_to(ROOT)),plan_sha256=sha(STATE/'plans'/(base+'.json')),
        feature_manifest_sha256=sha(OUT/'feature-manifest.json'),restored_actual_current_tiers=restored,detail=detail,
        execution='NATIVE_IMMEDIATE_OPEN_ONLY_LIMIT_SENSITIVITY' if open_only else 'NATIVE_WITH_ENTRY_1BP_TRADE_THROUGH_SENSITIVITY' if through else 'NATIVE_MARKET_CANDLE_SCENARIO' if market else 'NATIVE_CANDLE_TOUCH',constant_risk=constant_risk))
    print(label,len(trades),sum(t['profit_abs'] for t in trades),flush=True)


def portfolios():
    for label in read(ROOT/'research/session4/protocol.json')['variants']:
        if (OUT/'native-results'/(label+'.json')).exists():continue
        log=OUT/(label+'-native.txt')
        if log.exists():log=OUT/(label+f'-native-attempt-{len(list(OUT.glob(label+"-native*.txt")))+1:03}.txt')
        import subprocess
        with log.open('x') as file:
            r=subprocess.run([sys.executable,__file__,'native',label],stdout=file,stderr=subprocess.STDOUT)
        if r.returncode:raise ValueError('native failure '+label+'; retained log')
        summary=read(OUT/'native-results'/(label+'.json'))['strategy']['Session4Replay']
        print(label,summary['total_trades'],summary['profit_total_abs'],flush=True)


if __name__=='__main__':
    action=sys.argv[1]
    if action=='native':native(sys.argv[2],base=sys.argv[3] if len(sys.argv)>3 and not sys.argv[3].startswith('--') else None,detail='--detail' in sys.argv,through='--through' in sys.argv,constant_risk='--risk' in sys.argv,open_only='--open-only' in sys.argv,market='--market' in sys.argv)
    else:globals()[action]()
