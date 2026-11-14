"""python -m researcher: explicit, read-only operator commands."""
import argparse
from pathlib import Path
from .contracts import ContractError, encode
from .discovery import scan_live, scan_now, smoke, scan_market_research
from .inventory import OwnerOfficialSnapshot
from .contracts import now_utc
from .settings import ROOT, load_config, provider_status, validate_config


def write_report(path, value):
    import os
    import tempfile
    path = Path(path).absolute()
    root = ROOT / "work"
    if (".." in path.parts or path.suffix != ".json" or not path.is_relative_to(root)
            or any(p.is_symlink() for p in [path, *path.parents])):
        raise ContractError("OUTPUT_MUST_BE_NEW_JSON_UNDER_WORK")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                prefix='.openbot-report-',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name);stream.write(encode(value)+'\n');stream.flush();os.fsync(stream.fileno())
        os.link(temporary,path)  # Atomic publication; existing user files win.
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    config = sub.add_parser("config"); config.add_argument("action", choices=["validate"])
    provider = sub.add_parser("provider"); provider.add_argument("action", choices=["status"])
    analytics=sub.add_parser('analytics')
    analytics.add_argument('action',choices=['contracts','local-oracle'])
    analytics.add_argument('--environment',choices=['CODEX_LOCAL'])
    analytics.add_argument('--symbol',default='BTCUSDT')
    analytics.add_argument('--timeframe',choices=['1h','15m'],default='1h')
    analytics.add_argument('--output',help='new JSON below work/; never overwrites')
    review = sub.add_parser('review')
    review.add_argument('action',choices=['replay-session3','probe-precursors'])
    review.add_argument('--output',help='new JSON file below work/; never overwrites')
    scan = sub.add_parser("scan"); scan.add_argument("action", choices=["smoke", "now", "live", "qualify"])
    scan.add_argument("--output", help="new JSON file below work/; never overwrites")
    scan.add_argument("--inventory", help="owner-supplied official exchangeInfo JSON")
    scan.add_argument("--inventory-provenance", help="required provenance manifest for --inventory")
    scan.add_argument('--db',help='research metadata SQLite below work/; default work/research-metadata.sqlite')
    scan.add_argument('--json',action='store_true',help='print full machine-readable report instead of the concise research summary')
    scan.add_argument('--replay',choices=['retained-session5','synthetic-6b'],
        help='offline sources through the ordinary scan now pipeline; zero provider network')
    scan.add_argument('--qualifications',help='operator-reviewed Local source manifest and hashed oracle proofs under work/')
    scan.add_argument('--native-review-dir',help='optional bounded request/reply exchange below work/; native OpenBot application invokes the existing agent')
    show=sub.add_parser('show');show.add_argument('action',choices=['results','watches','coverage'])
    show.add_argument('--db',default=str(ROOT/'work/research-metadata.sqlite'))
    args = parser.parse_args()
    try:
        config = load_config()
        if args.command == "config":
            report = validate_config(config)
        elif args.command == "provider":
            report = provider_status(config)
        elif args.command=='analytics':
            if args.action=='contracts':
                from .engine_capabilities import manifest
                report=manifest(config)
            else:
                from .analytical_probe import qualify_selected
                report=qualify_selected(environment=args.environment,native_symbol=args.symbol,timeframe=args.timeframe)
            if args.output:write_report(args.output,report)
        elif args.command=='show':
            from .persistence import read_latest_report
            saved=read_latest_report(args.db)
            report=saved if args.action=='results' else {args.action:saved.get(args.action if args.action=='watches' else 'research_coverage'),
                'mode':saved['mode'],'as_of_utc':saved['completed_at_utc'],'trade_authorization':False}
        elif args.command == 'review':
            from .session4 import replay_session3,probe_precursors
            report=replay_session3() if args.action=='replay-session3' else probe_precursors()
            if args.output:write_report(args.output,report)
        else:
            if args.native_review_dir and (args.action not in {'now','live'} or args.inventory):
                raise ContractError('NATIVE_REVIEW_REQUIRES_ORDINARY_SCAN')
            if bool(args.inventory) != bool(args.inventory_provenance) or (args.action != "now" and args.inventory):
                raise ContractError("INVENTORY_PROVENANCE_REQUIRED")
            inventory = (OwnerOfficialSnapshot(Path(args.inventory), Path(args.inventory_provenance)).load(now_utc())
                         if args.inventory else None)
            if args.replay:
                if args.action!='now' or inventory is not None or args.qualifications:raise ContractError('OFFLINE_REPLAY_SCOPE')
                from .replay import retained_session5,synthetic_6b
                api,client,sources,at,provenance=(retained_session5 if args.replay=='retained-session5' else synthetic_6b)()
                report=scan_market_research(config=config,api=api,client=client,sources=sources,clock=lambda:at,
                    mode=sources.mode,ledger_path=args.db,native_review_dir=args.native_review_dir)
                report['offline_source_provenance']=provenance
            elif args.action in {'now','live'} and inventory is None:
                from .query_planner import ResearchSources
                sources=ResearchSources.from_file(args.qualifications) if args.qualifications else None
                report=scan_market_research(config=config,ledger_path=args.db,sources=sources,
                    native_review_dir=args.native_review_dir)
            elif args.action == 'qualify':
                from .qualification5 import qualify_core
                report = qualify_core()
            else:
                report = scan_now(inventory=inventory, config=config) if args.action == "now" else smoke()
            if args.output:
                write_report(args.output, report)
        if args.command=='scan' and report.get('schema_version')=='openbot.market-research.v5' and not args.json:
            from .discovery import research_summary
            print(research_summary(report))
        else:print(encode(report))
        return 2 if report.get("operation_status") == "BLOCKED_OR_UNQUALIFIED" else 0
    except (ContractError, OSError) as error:
        from .screening import safe_error
        print(encode({"status": "REJECTED", "reason": safe_error(error) if isinstance(error, ContractError)
                      else "INPUT_OR_OUTPUT_FILE_UNAVAILABLE"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
