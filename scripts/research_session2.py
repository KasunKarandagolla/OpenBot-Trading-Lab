"""Thin frozen batch around official Freqtrade; comparison reads recorded results only."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import pandas as pd
from data_session2 import verify
from report import summarize
ROOT=Path('/lab')
OUT=ROOT/'evidence/session-2'


def read(path):
    return json.loads(path.read_text())


def write(path, obj):
    path.write_text(json.dumps(obj,indent=2,allow_nan=False,sort_keys=True)+'\n')


def frozen():
    for folder in ['session-1','session-2']:
        for line in (ROOT/f'evidence/{folder}/freeze.sha256').read_text().splitlines():
            sha,path=line.split(maxsplit=1)
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:
                raise ValueError('freeze mismatch: '+path)
    return read(ROOT/'research/session-2-protocol.json')


def run():
    p=frozen(); verify()
    registry=read(ROOT/'research/strategy-registry.json')['strategies']
    for name in p['strategies']:
        run_dir=ROOT/'user_data/backtest_results/session-2'/name
        run_dir.mkdir(parents=True,exist_ok=True)
        dest=OUT/'runs'/name
        dest.mkdir(parents=True,exist_ok=True)
        audit=ROOT/'user_data/logs/s2-events.jsonl'
        audit.unlink(missing_ok=True)
        args=[sys.executable,'/lab/scripts/guard.py','backtesting','--config','/lab/'+registry[name]['config'],
              '--datadir','/lab/user_data/data/session-2/gate','--timerange',p['evaluation_timerange'],
              '--fee',str(p['fee_per_side']),'--enable-protections','--cache','none','--export','trades',
              '--backtest-directory',str(run_dir)]
        if (ROOT/'user_data/runtime/cloud.json').exists():
            args+=['--config','/lab/user_data/runtime/cloud.json']
        started=datetime.now(timezone.utc).isoformat()
        with (dest/'engine-output.txt').open('w') as log:
            completed=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
        with (OUT/'commands-and-results.txt').open('a') as log:
            log.write(started+' '+ ' '.join(args)+'\nexit='+str(completed.returncode)+'\n')
        if completed.returncode:
            raise RuntimeError('native backtest failed: '+name+'; see '+str(dest/'engine-output.txt'))
        pointer=read(run_dir/'.last_result.json')
        archive=run_dir/pointer['latest_backtest']
        with zipfile.ZipFile(archive) as z:
            filename=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
            raw=z.read(filename)
        (dest/'native-result.json').write_bytes(raw)
        native=json.loads(raw); trades=native['strategy'][name]['trades']
        fields=['pair','is_short','open_date','close_date','open_rate','close_rate','amount','stake_amount','leverage',
                'fee_open','fee_close','funding_fees','trade_duration','exit_reason','profit_ratio','profit_abs','is_open','initial_stop_loss_abs','stop_loss_abs']
        with (dest/'trade-ledger.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(trades)
        if audit.exists():
            (dest/'callback-events.jsonl').write_bytes(audit.read_bytes())
        write(dest/'execution-diagnostics.json', overlaps(trades, audit))
        write(dest/'provenance.json',{'started_utc':started,'completed_utc':datetime.now(timezone.utc).isoformat(),
          'public_config':registry[name]['config'],'local_network_overlay_used':(ROOT/'user_data/runtime/cloud.json').exists(),'exit_code':completed.returncode,'engine':'2026.10',
          'native_result_sha256':hashlib.sha256(raw).hexdigest(),'native_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
          'native_zip_local_only':True,'source_data_manifest_sha256':hashlib.sha256((OUT/'source-data-manifest.json').read_bytes()).hexdigest(),
          'strategy_hashes':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in registry[name]['sources']}})
        print(name+': '+str(len(trades))+' native trades',flush=True)
    subprocess.run([sys.executable,'/lab/scripts/signal_counts.py'],check=True)
    compare()


def overlaps(trades, audit):
    events=[json.loads(x) for x in audit.read_text().splitlines()] if audit.exists() else []
    count=0; matched=0; frames={}
    for t in trades:
        accepted=[e for e in events if e['reason']=='ACCEPTED' and e['pair']==t['pair'] and e['decision_utc']==pd.Timestamp(t['open_date']).isoformat()]
        if not accepted:
            continue
        matched+=1;g=accepted[0]['geometry']
        if t['pair'] not in frames:
            stem=t['pair'].replace('/','_').replace(':','_')+'-15m-futures.feather'
            frames[t['pair']]=pd.read_feather(ROOT/'user_data/data/session-2/gate/futures'/stem)
        data=frames[t['pair']]
        window=data.loc[(data.date>=pd.Timestamp(t['open_date']))&(data.date<=pd.Timestamp(t['close_date']))]
        target=t['open_rate']*(1-g['target_roi'] if t['is_short'] else 1+g['target_roi'])
        both=((window.high>=g['stop'])&(window.low<=target)) if t['is_short'] else ((window.low<=g['stop'])&(window.high>=target))
        count+=int(both.any())
    return {'matched_trades':matched,'stop_target_overlap_trades':count if matched else None,
            'ordering':'native stop first; overlap diagnostic uses approximate price target, not exact fee-adjusted ROI rate'}


def metrics(name):
    folder=OUT/'runs'/name
    result=read(folder/'native-result.json')['strategy'][name]; trades=result['trades']
    m=summarize(trades)
    m.update(net_usdt=sum(t['profit_abs'] for t in trades),
      max_drawdown_usdt=result.get('max_drawdown_abs'),max_drawdown_account=result.get('max_drawdown_account'),
      fees_usdt=sum(t['amount']*(t['open_rate']*t['fee_open']+t['close_rate']*t['fee_close']) for t in trades),
      funding_usdt=sum(t.get('funding_fees',0) or 0 for t in trades),
      gross_price_pnl_usdt=sum(t['amount']*(t['close_rate']-t['open_rate'])*(-1 if t['is_short'] else 1) for t in trades),
      turnover_usdt=sum(t['amount']*(t['open_rate']+t['close_rate']) for t in trades),
      exposure_notional_hours=sum(t['stake_amount']*t['trade_duration']/60 for t in trades),
      native_rejected_signals=result.get('rejected_signals'),native_canceled_entry_orders=result.get('canceled_entry_orders'),
      native_timedout_entry_orders=result.get('timedout_entry_orders'))
    m['average_gross_price_pnl_usdt']=m['gross_price_pnl_usdt']/len(trades) if trades else None
    m['reconciliation_residual_usdt']=m['net_usdt']-(m['gross_price_pnl_usdt']-m['fees_usdt']+m['funding_usdt'])
    m['directions']={side:{'trades':len([t for t in trades if t['is_short']==short]),
        'net_usdt':sum(t['profit_abs'] for t in trades if t['is_short']==short)} for side,short in [('long',False),('short',True)]}
    m['friction']=[{'extra_bps_per_side':bps,'net_usdt':m['net_usdt']-m['turnover_usdt']*bps/10000} for bps in [0,5,10,20]]
    ordered=sorted([t['profit_abs'] for t in trades],reverse=True)
    m['top3_trade_pnl_usdt']=sum(ordered[:3]);m['net_without_top3_usdt']=m['net_usdt']-sum(ordered[:3])
    m['payoff']={'average_win_usdt':sum(x for x in ordered if x>0)/max(1,sum(x>0 for x in ordered)),
                 'average_loss_usdt':sum(x for x in ordered if x<0)/max(1,sum(x<0 for x in ordered))}
    events=[]
    if (folder/'callback-events.jsonl').exists():
        events=[json.loads(s) for s in (folder/'callback-events.jsonl').read_text().splitlines()]
    m['callback_counts']=pd.Series([e['reason'] for e in events],dtype='str').value_counts().to_dict()
    # Custom data is not exported in the native result JSON by this engine. Match accepted entry geometry.
    risk=[]; risk_rows=[]; ambiguous=0; regimes={}
    for t in trades:
        accepted=[e for e in events if e['reason']=='ACCEPTED' and e['pair']==t['pair'] and e['decision_utc']==pd.Timestamp(t['open_date']).isoformat()]
        if accepted:
            g=accepted[0]['geometry']
            # No trailing/adjustment: native final absolute stop is the unchanged initial applied stop.
            actual_stop=t['stop_loss_abs']
            adverse=abs(t['open_rate']-actual_stop)/t['open_rate']
            initial=t['stake_amount']*(adverse+.0035)
            risk.append(t['profit_abs']/initial)
            risk_rows.append({'pair':t['pair'],'open_date':t['open_date'],'initial_intended_risk_usdt':initial,
                              'stop_reference':g['stop'],'native_applied_stop':actual_stop,'net_R':t['profit_abs']/initial})
    m['initial_intended_risk_matched_trades']=len(risk)
    m['net_R_quantiles']={str(q):float(pd.Series(risk).quantile(q)) for q in [0,.25,.5,.75,1]} if risk else None
    m['coarse_bar_stop_target_overlap_trades']=read(folder/'execution-diagnostics.json')['stop_target_overlap_trades']
    write(folder/'initial-risk-ledger.json',risk_rows)
    m['regime_breakdown']='UNAVAILABLE: no separate ex-ante calendar regime classification; strategy hourly filters only'
    m['status']='INSUFFICIENT EVIDENCE' if len(trades)<30 else ('REJECTED under evaluated assumptions' if m['net_usdt']<=0 else 'UNQUALIFIED DEVELOPMENT RESULT')
    m['provenance']=read(folder/'provenance.json')
    return m


def compare():
    p=frozen()
    # Comparison uses only recorded native outputs; no data download/backtest invoked.
    strategies={name:metrics(name) for name in p['strategies']}
    obj={'schema_version':1,'mode':'SIMULATED HISTORICAL FUTURES','sample_class':'INSPECTED DEVELOPMENT DATA',
         'source':'recorded native Freqtrade 2026.10 trade results','window':p['evaluation_timerange'],
         'pairs':p['pairs'],
         'run_completed_utc':{n:m['provenance']['completed_utc'] for n,m in strategies.items()},
         'strategy_hashes':{n:m['provenance']['strategy_hashes'] for n,m in strategies.items()},
         'signal_counts':read(OUT/'signal-counts.json')['strategies'],
         'protocol_sha256':hashlib.sha256((ROOT/'research/session-2-protocol.json').read_bytes()).hexdigest(),
         'assumptions':p,'strategies':strategies,
         'limitations':['No independent holdout, no economic qualification or automatic promotion.',
           '15m limit fills are within-candle simulations; five-minute expiry cannot establish historical queue fills.',
           'Friction stresses deduct additional turnover costs without resimulating fills or drawdown.',
           'Risk controls rely on assumed stop/friction/funding allowances; gaps/outages can exceed them.',
           'UTC realized-loss halt excludes unrealized account losses; full daily-loss ceiling NOT ENFORCED.',
           'Current surviving BTC/ETH/SOL only; correlated days are not independent samples.']}
    write(OUT/'strategy-comparison.json',obj)
    write(OUT/'research-summary.json',{k:v for k,v in obj.items() if k!='strategies'}|{'strategies':{n:{k:m[k] for k in ['status','trades','net_usdt','expectancy_usdt','profit_factor','max_drawdown_usdt','fees_usdt','funding_usdt','friction']} for n,m in strategies.items()}})
    write(OUT/'strategy-risks.json',{'schema_version':1,'mode':'RESEARCH ONLY','window':p['evaluation_timerange'],'source':'frozen code and recorded native outputs','strategy_hashes':obj['strategy_hashes'],'run_completed_utc':obj['run_completed_utc'],'active_paper_strategy':'TrendPullbackBaselineV1',
      'challengers_paper_approved':False,'enforced':['dry_run','1x frozen code','25 USDT maximum','max2 native positions','no DCA',
        'signal geometry and entry deviation rejection','five-minute native paper order timeout','fixed initial custom stop and 2R ROI request','holding-time exit request','cooldown'],
      'limited':['intended monetary-risk ceilings within bounded cost assumptions','UTC realized closed-trade loss halt only','restart pending-order path not exercised on owner host'],
      'not_enforced':['exact 1% mark-to-market daily account halt','fills/stop protection during process outage','guaranteed five-minute historical fills','OpenBot host isolation']})
    report='# Session 2 real-market comparison — DEVELOPMENT ONLY\n\n'
    report+='Gate BTC/ETH/SOL linear USDT perpetuals, 2026-07-30 through 2026-10-30 UTC end exclusive; wallet1000, stake<=25, max2, 1x. Native fee0.06% each side, actual funding. No threshold tuning.\n\n'
    report+='| Strategy | Trades (L/S) | Net USDT | Expectancy | PF | Max DD USDT | Fees | Signed funding | +5bp | +10bp | +20bp | Status |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|\n'
    for n,m in strategies.items():
        f=m['friction']; pf='undefined' if m['profit_factor'] is None else f"{m['profit_factor']:.4f}"
        exp='undefined' if m['expectancy_usdt'] is None else f"{m['expectancy_usdt']:.6f}"
        report+=f"| {n} | {m['trades']} ({m['directions']['long']['trades']}/{m['directions']['short']['trades']}) | {m['net_usdt']:.6f} | {exp} | {pf} | {m['max_drawdown_usdt']:.6f} | {m['fees_usdt']:.6f} | {m['funding_usdt']:.6f} | {f[1]['net_usdt']:.6f} | {f[2]['net_usdt']:.6f} | {f[3]['net_usdt']:.6f} | {m['status']} |\n"
    for n,m in strategies.items():
        report+=f"\n## {n}\n\nDistinct entry days: {m['trading_days']}; per pair: {m.get('per_pair_usdt',{})}; direction net: {m['directions']}. Gross price P&L {m['gross_price_pnl_usdt']:.6f}; net minus gross-fees+funding residual {m['reconciliation_residual_usdt']:.10f}. Mean gross {m['average_gross_price_pnl_usdt']}; win/loss payoff {m['payoff']}. Holding-minute quantiles {m['hold_minutes']}; exits {m.get('exit_reasons',{})}. Turnover {m['turnover_usdt']:.4f} USDT, notional-hours {m['exposure_notional_hours']:.4f}. Net without best three trades {m['net_without_top3_usdt']:.6f}. R matched trades {m['initial_intended_risk_matched_trades']}; R quantiles {m['net_R_quantiles']}. Callback decisions {m['callback_counts']}. Native rejected/timeout/cancel counts {m['native_rejected_signals']}/{m['native_timedout_entry_orders']}/{m['native_canceled_entry_orders']}. Coarse stop/target overlap {m['coarse_bar_stop_target_overlap_trades']} (diagnostic reference-price target, not exact net-ROI execution price).\n"
    report+='\n## Economic interpretation\n\nThe challengers trade far less often; this alone is not improvement. Both have positive native conditional expectancy on this inspected cohort, but almost all net advantage disappears with an extra10bp/side and both lose at20bp/side. VWAP has17 trades over13 entry days, negative short-side P&L and negative net without its best3 trades. Sweep has39 trades over29 entry days, with most gains from short trades and SOL. The baseline rerun matches the original386-trade loss. These are small correlated development samples with no independent qualification.\n'
    report+='\n'+ '\n'.join('- '+s for s in obj['limitations'])+'\n\nFewer trades alone are not success. Status thresholds are descriptive: fewer than30 trades means insufficient evidence; nonpositive larger samples rejected for this cohort; positive samples remain unqualified development. No significance/power claim is made. See signal-counts.json for feature-level opportunities and strategy-risks.json for enforced versus limited controls.\n'
    (OUT/'comparison-report.md').write_text(report)
    print(report.split('\n## ')[0],flush=True)


def info(name):
    registry=read(ROOT/'research/strategy-registry.json')['strategies']
    if name not in registry:
        raise ValueError('unknown strategy')
    print((ROOT/registry[name]['card']).read_text())
    print(json.dumps({f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in registry[name]['sources']},indent=2))

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='run':run()
    elif mode=='compare':compare()
    elif mode=='info':info(sys.argv[2])
    else:raise ValueError('unsupported research action')
