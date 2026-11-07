"""Exercise persistent lifecycle/recovery using ONLY an offline simulated venue."""
import argparse
import json
from pathlib import Path
from trading_lab.execution import OfflineManager, OfflineVenue


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('new_directory',type=Path)
    args=parser.parse_args();args.new_directory.mkdir(parents=True,exist_ok=False)
    venue=OfflineVenue();venue.timeout_entry=True;venue.timeout_close=True
    path=args.new_directory/'offline-journal.db'
    manager=OfflineManager(path,venue)
    plan={'decision':'LIMIT','symbol':'SYNTHETICUSDT','side':'LONG','entry':'100',
          'quantity':'0.2','stop':'99','tp1':'103','expires_at_ms':60000,'hold_seconds':3600,
          'engine_mode':'OFFLINE_SIMULATION','margin_type':'ISOLATED','position_side':'BOTH',
          'preapproved_emergency_flatten':True}
    job=manager.propose(plan,{'status':'PASS'},1000)
    manager.approve_offline(job,1100);manager.step(job,1200)
    manager.db.close();manager=OfflineManager(path,venue);manager.step(job,1300)
    venue.fill(job,'.05');manager.step(job,1400)
    venue.fill(job,'.2',terminal=True);manager.step(job,1500)
    venue.protections.clear();manager.step(job,1600)
    manager.db.close();manager=OfflineManager(path,venue);manager.step(job,1700)
    timeline=[dict(zip(['sequence','job','state','at','reason'],row)) for row in manager.db.execute('select * from events order by sequence')]
    report={'mode':'OFFLINE_SIMULATION','risk_input':'SYNTHETIC_UNIT_INPUT_NOT_REAL_GATE_ACCEPTANCE',
            'actual_exchange_requests':0,'actual_orders':0,'simulated_entry_calls':venue.entry_calls,
            'final_simulated_position':str(venue.position),'final_state':timeline[-1]['state'],
            'timeline':timeline}
    manager.db.close();(args.new_directory/'replay.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
