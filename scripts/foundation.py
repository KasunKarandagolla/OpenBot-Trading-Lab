"""Session 1 coherent native research CLI. No arbitrary engine/admin command."""
import sys
from foundation_common import register, verify


def main():
    action, run_id, *extra = sys.argv[1:]
    if action == 'register':
        if extra: raise ValueError('unexpected arguments')
        register(run_id); print('Registered', run_id); return 0
    verify(run_id)
    if action in ('native', 'native-lookahead'):
        from foundation_native import native
        if len(extra) != 1: raise ValueError('one registered strategy required')
        return native(run_id, extra[0], action == 'native-lookahead')
    if extra: raise ValueError('unexpected arguments')
    from foundation_market import preflight, scan, acquire, validate, assess
    from foundation_native import schedule, backtest, lookahead
    from foundation_report import report, export
    from foundation_events import collect
    from foundation_checks import doctor, ui_smoke, dryrun_smoke
    actions = dict(preflight=preflight, scan=scan, acquire=acquire, validate=validate,
        assess=assess, schedule=schedule, backtest=backtest, report=report, export=export,
        events=collect, doctor=doctor, lookahead=lookahead, **{'ui-smoke': ui_smoke, 'dryrun-smoke': dryrun_smoke})
    if action not in actions: raise ValueError('unsupported research action')
    actions[action](run_id)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
