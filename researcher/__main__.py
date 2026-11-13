"""python -m researcher: explicit, read-only operator commands."""
import argparse
from pathlib import Path
from .contracts import ContractError, encode
from .discovery import scan_live, scan_now, smoke
from .inventory import OwnerOfficialSnapshot
from .contracts import now_utc
from .settings import ROOT, load_config, provider_status, validate_config


def write_report(path, value):
    path = Path(path).absolute()
    root = ROOT / "work"
    if (".." in path.parts or path.suffix != ".json" or not path.is_relative_to(root)
            or any(p.is_symlink() for p in [path, *path.parents])):
        raise ContractError("OUTPUT_MUST_BE_NEW_JSON_UNDER_WORK")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encode(value) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    config = sub.add_parser("config"); config.add_argument("action", choices=["validate"])
    provider = sub.add_parser("provider"); provider.add_argument("action", choices=["status"])
    scan = sub.add_parser("scan"); scan.add_argument("action", choices=["smoke", "now", "live", "qualify"])
    scan.add_argument("--output", help="new JSON file below work/; never overwrites")
    scan.add_argument("--inventory", help="owner-supplied official exchangeInfo JSON")
    scan.add_argument("--inventory-provenance", help="required provenance manifest for --inventory")
    args = parser.parse_args()
    try:
        config = load_config()
        if args.command == "config":
            report = validate_config(config)
        elif args.command == "provider":
            report = provider_status(config)
        else:
            if bool(args.inventory) != bool(args.inventory_provenance) or (args.action != "now" and args.inventory):
                raise ContractError("INVENTORY_PROVENANCE_REQUIRED")
            inventory = (OwnerOfficialSnapshot(Path(args.inventory), Path(args.inventory_provenance)).load(now_utc())
                         if args.inventory else None)
            if args.action in {"live", "qualify"} or (args.action == "now" and inventory is None):
                report = scan_live(qualification=args.action == "qualify", config=config)
            else:
                report = scan_now(inventory=inventory, config=config) if args.action == "now" else smoke()
            if args.output:
                write_report(args.output, report)
        print(encode(report))
        return 2 if report.get("operation_status") == "BLOCKED_OR_UNQUALIFIED" else 0
    except (ContractError, OSError) as error:
        from .screening import safe_error
        print(encode({"status": "REJECTED", "reason": safe_error(error) if isinstance(error, ContractError)
                      else "INPUT_OR_OUTPUT_FILE_UNAVAILABLE"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
