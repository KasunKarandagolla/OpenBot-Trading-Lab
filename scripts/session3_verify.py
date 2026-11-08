"""Recompute native economics and verify frozen research boundaries, without exchange access."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
import pandas as pd


def audit(run):
    run=Path(run);summary=json.loads((run/'summary.json').read_text());ledger=json.loads((run/'ledger.json').read_text())
    plans={p['decision_id']:p for p in json.loads((run/'selected-plans.json').read_text())} if (run/'selected-plans.json').exists() else {}
    errors=[];checks=Counter();net=0.;fees=0.;funding=0.;sources={}
    for t in ledger:
        sign=-1 if t['is_short'] else 1
        fee=t['amount']*(t['open_rate']*t['fee_open']+t['close_rate']*t['fee_close'])
        expected=sign*t['amount']*(t['close_rate']-t['open_rate'])-fee+t.get('funding_fees',0.)
        if abs(expected-t['profit_abs'])>2e-7:errors.append('NATIVE_PNL_MISMATCH:'+str(t['enter_tag']))
        if t['amount']*t['open_rate']>25+1e-7 or t['leverage']!=1:errors.append('RISK_EXPOSURE')
        if t['trade_duration']>900:errors.append('HOLD_OVER_15H')
        # Independent source funding recomputation, distinct from the native P&L identity.
        from local_recovery_convert import load
        symbol=t['pair'].split('/')[0]+'USDT'
        if symbol not in sources:
            sources[symbol]=(load(symbol,None,'fundingRate',sidecar=True),load(symbol,'1h','markPriceKlines').set_index('date')['open'])
        rates,marks=sources[symbol]
        first=min(o['order_filled_timestamp'] for o in t['orders'] if o['ft_is_entry'])
        begin=pd.Timestamp(first,unit='ms',tz='UTC');end=pd.Timestamp(t['close_timestamp'],unit='ms',tz='UTC')
        events=rates.loc[(rates.date>begin)&(rates.date<=end)]
        expected_funding=0.
        for event in events.itertuples():
            hour=pd.Timestamp(event.date).floor('h')
            if hour not in marks.index:errors.append('SOURCE_FUNDING_MARK_MISSING');continue
            expected_funding+=(-sign)*t['amount']*float(marks.loc[hour])*float(event.funding_rate)
        if abs(expected_funding-t.get('funding_fees',0.))>2e-7:errors.append('SOURCE_FUNDING_ALLOCATION_MISMATCH')
        checks['source_funding_events']+=len(events)
        checks['native_trades']+=1
        p=plans.get(t['enter_tag'])
        if p:
            filled=min(o['order_filled_timestamp'] for o in t['orders'] if o['ft_is_entry'])
            at=pd.Timestamp(p['decision_at']).value//1_000_000
            expiry=pd.Timestamp(p['expires_at']).value//1_000_000
            if not at<=filled<expiry:errors.append('FILL_CLOCK_OR_EXPIRY')
            if pd.Timestamp(p['armed_at'])>=pd.Timestamp(p['decision_at']):errors.append('SAME_BAR_SETUP_TRIGGER')
            if pd.Timestamp(p['objective']['known_at'])>pd.Timestamp(p['armed_at']):errors.append('FUTURE_OBJECTIVE')
            if t['trade_duration']>p['max_hold_minutes']+5:errors.append('PLAYBOOK_HOLD_OVER_CAP')
            if not .0025<=sign*(t['open_rate']-p['stop'])/t['open_rate']<=.025+1e-10:errors.append('STRUCTURAL_STOP_GEOMETRY')
            if abs(t['open_rate']/p['entry']-1)>.0015+1e-10:errors.append('CHASE_OR_PRICE_REWRITE')
            checks['source_bound_plan_trades']+=1
        net+=t['profit_abs'];fees+=fee;funding+=t.get('funding_fees',0.)
    if abs(net-summary['native_net_usdt'])>1e-7:errors.append('SUMMARY_LEDGER_MISMATCH')
    archive=run/summary['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=summary['archive_sha256']:errors.append('NATIVE_ARCHIVE_DRIFT')
    result=dict(status='PASS' if not errors else 'FAIL',checks=dict(checks),errors=errors,net_usdt=net,
                fees_usdt=fees,funding_net_usdt=funding,exit_reasons=dict(Counter(t['exit_reason'] for t in ledger)),
                source_qualification=summary['source_scope'],queue_spread_impact='UNKNOWN',execution_authority='NONE')
    (run/'independent-arithmetic-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    if errors:raise ValueError(result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);a=p.parse_args()
    print(json.dumps({str(r):audit(r) for r in a.runs},indent=2))
