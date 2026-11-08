"""Owner-invoked multi-market historical research through the existing watchlist.

Current public discovery reuses public.capture; freshness/network failure stays BLOCKED.
This command never starts a resident service, account route or paper trader.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import pandas as pd
from trading_lab.panel import ArchivePanel, ROOT, digest
from trading_lab.playbooks import prepare, discover, research_symbol, ms, VERSION
from trading_lab.watchlist import connect, encode
from trading_lab.panel_monitor import add, tick
from local_recovery_data import write_json


def prepared(panel, symbol):
    key=('features',symbol)
    if key not in panel.cache:
        # Feature math and archive ingestion are separate caches. Reuse across every scan/tick.
        five=panel.frame(symbol,'5m');hours_base=panel.frame(symbol,'1h')
        begin,end=getattr(panel,'feature_window',(None,None))
        if begin is not None:
            five=five.loc[(five.date>=begin)&(five.date<end)]
            hours_base=hours_base.loc[(hours_base.date>=begin)&(hours_base.date<end)]
        d,h=prepare(five,hours_base)
        # Adopt the existing historical Binance scanner's suitability calculation:
        # 14-day published quote activity, causal 4H readiness and 15m context.
        from local_recovery_scan import cheap_frame
        hours=panel.frame(symbol,'1h',sidecar=True).rename(columns={'base_volume':'volume'})
        quarters=panel.frame(symbol,'15m')
        if begin is not None:
            hours=hours.loc[(hours.date>=begin)&(hours.date<end)]
            quarters=quarters.loc[(quarters.date>=begin)&(quarters.date<end)]
        cheap=cheap_frame(hours,quarters)
        parent=cheap[['at','activity','map4h_ready','atr_hour_frac']].rename(columns={'at':'screen_known_at','activity':'activity14d'})
        h=pd.merge_asof(h,parent,left_on='at',right_on='screen_known_at',direction='backward')
        side=panel.frame(symbol,'5m',sidecar=True)
        quote=pd.DataFrame({'at':side.date+pd.Timedelta(minutes=5),
                            'quote24':side.quote_volume.rolling(288,min_periods=288).sum()})
        panel.cache[key]=(d,h,quote)
        panel.cache[('monitor-features',symbol)]=d
    else:panel.metrics['feature_cache_hits']+=1
    return panel.cache[key]


def scan(panel,at):
    """Extend the existing cheap-to-expensive scanner to the pinned archive source.

    Production eligibility/spread is public.capture/openbot_current_market.screen.
    Archive research has a distinct, explicit eligibility grade, never fabricated books.
    """
    at=pd.Timestamp(at)
    if at.tzinfo is None:raise ValueError('UTC_CUTOFF_REQUIRED')
    if not hasattr(panel,'feature_window'):panel.feature_window=(at.floor('D')-pd.Timedelta(days=40),at+pd.Timedelta(minutes=5))
    btc=prepared(panel,'BTCUSDT')[1]
    bc=btc.loc[btc['at']<=at].iloc[-1]
    rows=[]
    for symbol in panel.symbols:
        d,h,quote=prepared(panel,symbol)
        q=quote.loc[quote['at'].eq(at),'quote24']
        rows.append(discover(symbol,d,h,at,panel.identity,quote_volume_24h=None if q.empty else float(q.iloc[-1]),
                            btc={'trend1h':bc.trend1h,'structure1h':bc.struct_direction,'known_at':bc['at'].isoformat()}))
    # Ranking allocates attention only; all population rows and family hypotheses survive.
    interesting=[r for r in rows if r['status']=='DEVELOPING_WATCH']
    ranked=sorted(interesting,key=lambda r:(r['distance_to_boundary_atr'],-r['quote_volume_24h'],r['symbol']))[:4]
    return dict(as_of=at.isoformat(),mode='HISTORICAL',source_id=panel.identity,
                universe=len(rows),ledger=rows,shortlist=[r['symbol'] for r in ranked],
                watch=[s for r in ranked for s in r['setups']],
                risk_qualification='AGENT_NOT_VERIFIED / NO ACTION',feature_version=VERSION)


def experiments(panel,start,end,out,variant='retest'):
    out=Path(out)
    if out.exists():raise ValueError('PRESERVE_SCAN_OUTPUT_USE_NEW_DIRECTORY')
    out.mkdir(parents=True)
    begin=time.perf_counter();scans=[];events=[];plans=[]
    if not hasattr(panel,'feature_window'):
        left,right=pd.Timestamp(start),pd.Timestamp(end)
        if left.tzinfo is None:left=left.tz_localize('UTC')
        if right.tzinfo is None:right=right.tz_localize('UTC')
        panel.feature_window=(left-pd.Timedelta(days=40),right)
    btc=prepared(panel,'BTCUSDT')[1]
    for symbol in panel.symbols:
        d,h,quote=prepared(panel,symbol)
        s,e,p=research_symbol(symbol,d,h,quote,start,end,panel.identity,variant,btc)
        scans.extend(s);events.extend(e);plans.extend(p)
    # Same cheap stage computes all 24; retain at most four deep markets at a decision clock.
    byclock={}
    for row in scans:
        if row['status']=='DEVELOPING_WATCH':byclock.setdefault(row['as_of'],[]).append(row)
    keep=set()
    for rows in byclock.values():
        rows.sort(key=lambda r:(r['distance_to_boundary_atr'],-r['quote_volume_24h'],r['symbol']))
        for row in rows[:4]:
            keep.update(s['setup_key'] for s in row['setups'])
    selected=[p for p in plans if p['setup_key'] in keep]
    # Retain the shortlisted hypotheses in the existing source-bound SQLite store,
    # then obtain native plans by chronologically advancing that persisted history.
    runtime=Path('/tmp')/('openbot-v3-replay-'+hashlib.sha256(str(out.resolve()).encode()).hexdigest()[:16])
    if runtime.exists():raise ValueError('EXPERIMENT_RUNTIME_ALREADY_EXISTS')
    db=connect(runtime)
    try:
        for row in scans:
            for setup in row['setups']:
                if setup['setup_key'] in keep:
                    add(db,panel,dict(setup,entry_variant=variant))
        monitored=tick(db,panel,ms(pd.Timestamp(end).tz_localize('UTC') if pd.Timestamp(end).tzinfo is None else pd.Timestamp(end)))
        counts=dict(db.execute('SELECT state,COUNT(*) FROM events GROUP BY state').fetchall())
        # Different wrapper paths must agree exactly before native economics are run.
        byid={p['decision_id']:p for p in selected}
        assert {p['decision_id']:p for p in monitored['plans']}==byid,'SCANNER_MONITOR_PLAN_DIVERGENCE'
        selected=monitored['plans']
        snapshot=sqlite3.connect(runtime/'backup.sqlite3');db.backup(snapshot);snapshot.close()
    finally:db.close()
    # Reopen persisted history and inspect backup integrity; runtime DB remains private.
    db=connect(runtime)
    try:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        restart_count=db.execute('SELECT COUNT(*) FROM source_bindings').fetchone()[0]
    finally:db.close()
    write_json(out/'monitor-receipt.json',dict(states=counts,source_bound_setups=restart_count,
               restart='PASS',backup_sha256=digest(runtime/'backup.sqlite3'),runtime=str(runtime),
               scanner_monitor_plan_equality='PASS',execution_authority='NONE'))
    # Independent long/short hypotheses can trigger on one timestamp. Native requires one
    # direction/pair/candle: retain both records and explicitly suppress conflicts.
    groups={}
    for proposal in selected:
        if proposal['diagnostics']=='GEOMETRY_PASS_RESEARCH_ONLY':
            groups.setdefault((proposal['symbol'],proposal['decision_at'],proposal['family']),[]).append(proposal)
    for group in groups.values():
        opposing=len({p['side'] for p in group})>1
        group.sort(key=lambda p:(p['armed_at'],p['decision_id']))
        for number,proposal in enumerate(group):
            if opposing or number>0:
                proposal['diagnostics']='REJECT'
                proposal['reasons'].append('COLLIDING_NATIVE_PAIR_TIME_SIGNAL' if opposing else 'OVERLAPPING_SETUP_SUPPRESSED_OLDEST_FIRST')
    code_hashes={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'scripts/trading_lab/playbooks.py',ROOT/'scripts/trading_lab/panel_monitor.py',ROOT/'scripts/trading_lab/rehearsal.py']}
    doc=dict(feature_window=[x.isoformat() for x in panel.feature_window],code_sha256=code_hashes,feature_version=VERSION,source_id=panel.identity,start=start,end=end,variant=variant,plans=selected,
             scope='PREVIOUSLY_STUDIED_PRESELECTED_PANEL_NOT_HOLDOUT',execution_authority='NONE')
    write_json(out/'plans.json',doc)
    # Deterministic gzip payloads are compact reproducible population evidence.
    for name,value in [('scans',scans),('transitions',events),('unselected-plans',[p for p in plans if p['setup_key'] not in keep])]:
        (out/(name+'.json.gz')).write_bytes(gzip.compress(encode(value).encode(),mtime=0))
    summary=dict(start=start,end=end,variant=variant,markets=len(panel.symbols),market_scans=len(scans),
                 status_counts=dict(Counter(r['status'] for r in scans)),selected_setups=len(keep),
                 meaningful_transitions=dict(Counter(e['reason'] for e in events)),
                 selected_trigger_plans=len(selected),qualified_geometry=dict(Counter(p['family'] for p in selected if p['diagnostics']=='GEOMETRY_PASS_RESEARCH_ONLY')),
                 rejected_geometry=dict(Counter(reason for p in selected for reason in p['reasons'])),
                 wall_seconds=time.perf_counter()-begin,source_id=panel.identity,metrics=panel.metrics,
                 plan_sha256=digest(out/'plans.json'),verdict='UNQUALIFIED',execution_authority='NONE')
    write_json(out/'summary.json',summary);return summary


def watch(panel,root,at):
    result=scan(panel,at);db=connect(root)
    try:
        ids=[add(db,panel,s) for s in result['watch']]
    finally:db.close()
    return dict(**result,setup_ids=ids)


def status(db):
    rows=db.execute('SELECT s.id,s.definition,e.state,e.at_ms FROM setups s JOIN events e ON e.seq=(SELECT MAX(seq) FROM events WHERE setup_id=s.id) ORDER BY s.id').fetchall()
    return [dict(setup_id=i,definition=json.loads(d),state=s,at_ms=t) for i,d,s,t in rows]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',default='/tmp/openbot-v3-owner-research',help='Dedicated Linux SQLite runtime, not persistent OpenBot profiles')
    sub=p.add_subparsers(dest='action',required=True)
    for name in ['scan','watch']:
        a=sub.add_parser(name);a.add_argument('--at',required=True);a.add_argument('--out',type=Path)
    a=sub.add_parser('replay');a.add_argument('--start',required=True);a.add_argument('--end',required=True);a.add_argument('--out',required=True,type=Path);a.add_argument('--variant',choices=['retest','immediate','early'],default='retest')
    a=sub.add_parser('tick');a.add_argument('--at',required=True)
    for name in ['list','status']:sub.add_parser(name)
    a=sub.add_parser('history');a.add_argument('setup_id')
    a=sub.add_parser('backup');a.add_argument('destination',type=Path)
    a=sub.add_parser('refresh');a.add_argument('destination',type=Path)
    a=p.parse_args()
    if a.action=='refresh':
        from trading_lab.public import capture
        result=capture(a.destination)  # actual existing Binance scanner and clock checks, no cached-live shortcut
        result['watchlist_admission']='LIVE_ADAPTER_NOT_ACCEPTED_WITHOUT_SOURCE_RECEIPT_AND_INCREMENTAL_VALIDATION'
    elif a.action in ['scan','watch','replay','tick']:
        panel=ArchivePanel()
        if a.action=='scan':result=scan(panel,a.at)
        elif a.action=='watch':result=watch(panel,a.root,a.at)
        elif a.action=='replay':result=experiments(panel,a.start,a.end,a.out,a.variant)
        else:
            db=connect(a.root)
            try:result=tick(db,panel,ms(a.at))
            finally:db.close()
    else:
        db=connect(a.root)
        try:
            if a.action in ['list','status']:result=status(db)
            elif a.action=='history':result=[dict(at_ms=t,state=s,body=json.loads(b)) for t,s,b in db.execute('SELECT at_ms,state,body FROM events WHERE setup_id=? ORDER BY seq',(a.setup_id,))]
            else:
                if a.destination.exists() or a.destination.is_symlink():raise ValueError('BACKUP_DESTINATION_EXISTS_OR_SYMLINK')
                dest=sqlite3.connect(a.destination)
                try:db.backup(dest)
                finally:dest.close()
                result={'backup_sha256':digest(a.destination),'status':'BACKED_UP'}
        finally:db.close()
    if getattr(a,'out',None) and a.action in ['scan','watch']:
        if a.out.exists():raise ValueError('PRESERVE_PRIOR_OUTPUT')
        write_json(a.out,result)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
