"""One bounded scanner-to-native-policy-to-OpenBot command. No persistent service."""
import sys
from policy_common import *

def main():
    action,run_id,*args=sys.argv[1:]
    if action=='register':register(run_id);print('Registered',run_id,flush=True);return
    if action=='amend':amend(run_id,' '.join(args));return
    verify(run_id)
    if action in ('native','lookahead-analysis','recursive-analysis'):
        from policy_native import native
        return native(run_id,args[0],args[1] if len(args)>1 else 'all',int(args[2]) if len(args)>2 else 1, None if action=='native' else action)
    if action in ('acquire','detail','scan','sources'):
        from policy_market import acquire,detail,scan,compare_sources
        return dict(acquire=acquire,detail=detail,scan=scan,sources=compare_sources)[action](run_id)
    if action in ('schedule','assess'):
        from policy_opportunities import schedule,assess
        return dict(schedule=schedule,assess=assess)[action](run_id)
    if action=='flow':
        import asyncio
        from foundation_intelligence_flow import capture
        return asyncio.run(capture(run_id,context=verify))
    if action=='events':
        from foundation_events import collect
        return collect(run_id,context=verify)
    if action in ('report','export','scenarios'):
        from policy_report import report,export,scenarios
        return dict(report=report,export=export,scenarios=scenarios)[action](run_id)
    raise ValueError('unsupported bounded action')

if __name__=='__main__':main()
