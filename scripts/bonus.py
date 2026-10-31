"""Fixed bonus research operations. No server, credentials, trade or paper actions."""
import argparse
import subprocess
import sys
from bonus_common import *


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['acquire','detail','schedule','run','economics','reconcile','scan',
                                        'capture','replay','test','lookahead'])
    parser.add_argument('--observation-id')
    a=parser.parse_args();check()
    if a.observation_id and a.action not in ('capture','replay'):
        raise ValueError('observation ID applies only to capture/replay')
    if a.action in ('acquire','detail'):
        from bonus_data import acquire,detail
        acquire() if a.action=='acquire' else detail()
    elif a.action=='capture':
        import asyncio
        from bonus_orderflow import capture
        asyncio.run(capture(observation_id=a.observation_id))
    elif a.action=='replay':
        from bonus_orderflow import replay
        print(replay(a.observation_id))
    elif a.action in ('schedule','scan','run','lookahead'):
        from bonus_pipeline import schedule,scan,run,lookahead
        {'schedule':schedule,'scan':scan,'run':run,'lookahead':lookahead}[a.action]()
    elif a.action in ('economics','reconcile'):
        if a.action=='economics':
            from bonus_economics import analyze
            analyze()
        else:
            from bonus_reconcile import reconcile
            reconcile()
    else:
        return subprocess.call([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],env=sanitized_env())
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,FileNotFoundError,KeyError) as exc:
        print('BONUS RESEARCH REFUSAL: '+str(exc),file=sys.stderr);raise SystemExit(2)
