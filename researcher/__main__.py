"""python -m researcher: explicit, read-only operator commands."""
import argparse
from pathlib import Path
from .contracts import ContractError, encode
from .discovery import smoke
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
    scan = sub.add_parser("scan"); scan.add_argument("action", choices=["smoke"])
    scan.add_argument("--output", help="new JSON file below work/; never overwrites")
    args = parser.parse_args()
    try:
        config = load_config()
        if args.command == "config":
            report = validate_config(config)
        elif args.command == "provider":
            report = provider_status(config)
        else:
            report = smoke()
            if args.output:
                write_report(args.output, report)
        print(encode(report))
        return 2 if report.get("operation_status") == "BLOCKED_OR_UNQUALIFIED" else 0
    except (ContractError, FileExistsError):
        print(encode({"status": "REJECTED", "reason": "CONFIG_OR_OUTPUT_VALIDATION_FAILED"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
