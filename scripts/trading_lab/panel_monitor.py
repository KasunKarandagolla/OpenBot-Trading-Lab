"""Bind the existing immutable SQLite history to verified archive adapters."""
import hashlib
import json
import pandas as pd
from trading_lab.watchlist import create, encode
from trading_lab.playbooks import VERSION, ms, stamp, prepare, advance, initial_state, plan_for
from trading_lab.case_monitor import expire

TERMINAL={'EXPIRED','INVALIDATED','RESEARCH_PROPOSAL','REJECT_GEOMETRY'}


def add(db, panel, setup):
    if (panel.mode!='HISTORICAL' or setup['source_id']!=panel.identity or setup['symbol'] not in panel.symbols
            or setup['feature_version']!=VERSION or pd.Timestamp(setup['boundary_known_at'])>pd.Timestamp(setup['armed_at'])):
        raise ValueError('PANEL_IDENTITY_OR_LOOKAHEAD')
    at=ms(setup['armed_at'])
    # The adapter validates completed data, not a caller's hash or symbol claim.
    panel.completed(setup['symbol'],'5m',at)
    sign=1 if setup['side']=='long' else -1
    value=dict(symbol=setup['symbol'],venue=panel.venue,direction=setup['side'].upper(),family=setup['family'],
               source_cutoff_ms=at,source_sha256=panel.identity,level=setup['boundary'],
               invalidation=setup['boundary']-sign*1.5*setup['atr1h'],expires_ms=ms(setup['expires_at']),
               hypothesis=setup['hypothesis'],opposition=setup['opposition'],confirmation=setup['confirmation'],feature_version=VERSION)
    return create(db,value,_panel_binding=(panel.version,panel.identity,encode(setup)))


def tick(db, panel, as_of_ms):
    if type(as_of_ms) is not int or as_of_ms%300000:
        raise ValueError('INVALID_COMPLETED_CUTOFF')
    records=db.execute('SELECT setup_id,source_version,source_id,setup FROM source_bindings ORDER BY setup_id').fetchall()
    prepared={};counts={};plans=[]
    for sid,version,identity,body in records:
        if version!=panel.version or identity!=panel.identity:raise ValueError('SOURCE_VERSION_MISMATCH')
        setup=json.loads(body)
        if setup['feature_version']!=VERSION:raise ValueError('FEATURE_VERSION_MISMATCH_REPLAY_OLD_CODE_OR_NEW_SETUP')
        last=db.execute('SELECT at_ms,state,body FROM events WHERE setup_id=? ORDER BY seq DESC LIMIT 1',(sid,)).fetchone()
        if as_of_ms<last[0]:raise ValueError('TIME_MOVED_BACKWARDS')
        if last[1] in TERMINAL:continue
        # Expiry needs no new source bar, including after archive end.
        cutoff=min(as_of_ms,ms(setup['expires_at'])-300000)
        symbol=setup['symbol']
        cachekey=('monitor-features',symbol)
        if cachekey not in panel.cache or panel.cache[cachekey]['at'].max()<pd.Timestamp(cutoff,unit='ms',tz='UTC'):
            # Archive integrity is established before math. Features are causal;
            # prefix-equivalence tests verify that future values cannot alter them.
            panel.cache[cachekey]=prepare(panel.frame(symbol,'5m'),panel.frame(symbol,'1h'))[0]
        data=panel.cache[cachekey]
        data=data.loc[(data['at']>pd.Timestamp(setup['armed_at'])) & (data['at']<=pd.Timestamp(cutoff,unit='ms',tz='UTC'))]
        if data.empty or ms(data['at'].iloc[-1])!=cutoff:
            raise ValueError('STALE_OR_GAPPED_MONITOR_SOURCE')
        old=json.loads(last[2]);state=old.get('kernel_state',initial_state())
        # Reconcile observed history before processing; pinned raw archives separately protect corrections.
        history=db.execute('SELECT at_ms,body FROM events WHERE setup_id=? AND event_key LIKE ? ORDER BY seq',(sid,'panel-bar:%')).fetchall()
        index={ms(row['at']):row for row in data.to_dict('records')}
        for at,oldbody in history:
            row=index.get(at);audit=json.loads(oldbody)
            if row is None or bar_hash(row)!=audit['bar_sha256']:
                raise ValueError('CORRECTED_COMPLETED_BAR_REQUIRES_NEW_SOURCE_VERSION')
        subsequent=data.loc[(data['at']>pd.Timestamp(last[0],unit='ms',tz='UTC')) & (data['at']<=pd.Timestamp(cutoff,unit='ms',tz='UTC'))]
        db.execute('BEGIN IMMEDIATE')
        try:
            # A concurrent writer may already have advanced this setup.
            latest=db.execute('SELECT at_ms,state FROM events WHERE setup_id=? ORDER BY seq DESC LIMIT 1',(sid,)).fetchone()
            if latest!=(last[0],last[1]):
                db.execute('ROLLBACK');continue
            for row in subsequent.to_dict('records'):
                if ms(row['at'])!=last[0]+300000:raise ValueError('GAPPED_SETUP_HISTORY')
                state,event=advance(setup,state,row,variant=setup.get('entry_variant','retest'))
                detail=dict(reason=event['reason'],kernel_state=state,bar_sha256=bar_hash(row),
                            source_id=identity,source_version=version,available_at=stamp(row['at']),
                            captured_receipt_scope='Historical archive, not a live capture',execution_authority='NONE')
                eventstate=event['state']
                if eventstate=='TRIGGER_CANDIDATE':
                    db.execute('INSERT INTO events(setup_id,event_key,at_ms,state,body) VALUES(?,?,?,?,?)',
                               (sid,'trigger:'+str(ms(row['at'])),ms(row['at']),'TRIGGER_CANDIDATE',encode(detail)))
                    proposal=plan_for(setup,state,row,setup.get('entry_variant','retest'))
                    plans.append(proposal);detail['plan']=proposal
                    eventstate='RESEARCH_PROPOSAL' if proposal['diagnostics']=='GEOMETRY_PASS_RESEARCH_ONLY' else 'REJECT_GEOMETRY'
                db.execute('INSERT INTO events(setup_id,event_key,at_ms,state,body) VALUES(?,?,?,?,?)',
                           (sid,'panel-bar:'+str(ms(row['at'])),ms(row['at']),eventstate,encode(detail)))
                counts[eventstate]=counts.get(eventstate,0)+1
                last=(ms(row['at']),eventstate)
                if eventstate in TERMINAL:break
            db.execute('COMMIT')
        except BaseException:
            if db.in_transaction:db.execute('ROLLBACK')
            raise
        if as_of_ms>=ms(setup['expires_at']) and last[1] not in TERMINAL:
            expire(db,sid,as_of_ms)
            counts['EXPIRED']=counts.get('EXPIRED',0)+1
    return dict(states=counts,plans=plans,mode='HISTORICAL',risk_qualification='AGENT_NOT_VERIFIED / NO ACTION')


def bar_hash(row):
    return hashlib.sha256(encode([ms(row['date']),*[float(row[c]) for c in ['open','high','low','close','volume']]]).encode()).hexdigest()
