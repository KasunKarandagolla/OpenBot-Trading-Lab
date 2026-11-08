"""Run the existing historical deterministic gate on source-bound v3 plans."""
import argparse
from collections import Counter
import json
from pathlib import Path
import pandas as pd
from trading_lab.panel import ArchivePanel
from trading_lab.risk import historical_geometry


def qualify(doc,panel):
    if doc['source_id']!=panel.identity:raise ValueError('PLAN_SOURCE_IDENTITY')
    frames={};results=[]
    for plan in doc['plans']:
        symbol=plan['symbol'];at=pd.Timestamp(plan['decision_at'])
        if symbol not in frames:frames[symbol]=panel.frame(symbol,'5m')
        frame=frames[symbol]
        closed=frame.loc[frame.date+pd.Timedelta(minutes=5)<=at].tail(3)
        evidence=dict(cutoff_ms=int(at.value//1_000_000),symbol=symbol,source_sha256=panel.identity,
                      archive_sha256_verified=True,completed_5m_bars=[dict(open_ms=int(r.date.value//1_000_000),
                      available_ms=int((r.date+pd.Timedelta(minutes=5)).value//1_000_000),close=float(r.close)) for r in closed.itertuples()])
        gate=historical_geometry(plan,evidence)
        results.append(dict(decision_id=plan['decision_id'],planner_diagnostics=plan['diagnostics'],
                            historical_gate=gate,modeled_notional=25,modeled_leverage=1,
                            modeled_initial_cash_risk=25*(plan['risk_fraction']+plan['admission_cost_allowance']),
                            risk_limits='New planner enforces .0025-.025 structural risk and net RR>=1.25; <=25 notional, two native slots. This is not account/native Risk qualification.',
                            native_risk='AGENT_NOT_VERIFIED',stage='RISK_QUALIFICATION',
                            combined_diagnostic='PASS_RESEARCH_ONLY' if plan['diagnostics']=='GEOMETRY_PASS_RESEARCH_ONLY' and gate['geometry_status']=='PASS' else 'REJECT',final='NO_ACTION',execution_authority='NONE'))
    return dict(source_id=panel.identity,results=results,geometry_counts=dict(Counter(r['historical_gate']['geometry_status'] for r in results)),
                native_risk='AGENT_NOT_VERIFIED',risk_qualification='NO_ACTION',execution_authority='NONE')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plans',nargs='+',type=Path);a=p.parse_args();panel=ArchivePanel()
    for path in a.plans:
        value=qualify(json.loads(path.read_text()),panel)
        out=path.parent/'risk-diagnostics.json'
        if out.exists():raise ValueError('PRESERVE_DIAGNOSTICS')
        out.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
        print(path.parent.name,value['geometry_counts'],flush=True)
