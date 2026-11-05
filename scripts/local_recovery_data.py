"""Acquire the registered monthly Binance Vision panel with the existing verifier."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path

from binance_research_data import (
    ARCHIVE_BASE, DataError, archive_url, discover_archive_symbols, fetch_verified,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/local_recovery/protocol.json"
WORK = ROOT / "user_data/data/local_recovery"
STREAMS = (("klines", "1h"), ("klines", "15m"), ("klines", "5m"),
           ("markPriceKlines", "1h"), ("fundingRate", None))
ARCHIVE_CAP = 2 * 1024 * 1024
TOTAL_CAP = 2 * 1024**3


def protocol():
    return json.loads(PROTOCOL.read_text())


def monthly_url(kind, symbol, timeframe, month):
    if kind == "fundingRate":
        return archive_url(kind, symbol, month=month)
    # Use the daily URL validator for identity, then address the monthly object.
    archive_url(kind, symbol, timeframe=timeframe, date=f"{month}-01")
    return (f"{ARCHIVE_BASE}/monthly/{kind}/{symbol}/{timeframe}/"
            f"{symbol}-{timeframe}-{month}.zip")


def download(job):
    symbol, (kind, tf), month = job
    url = monthly_url(kind, symbol, tf, month)
    identity = dict(symbol=symbol, kind=kind, timeframe=tf, month=month)
    try:
        receipt = fetch_verified(url, WORK / "archives" / kind / symbol,
                                 max_archive_bytes=ARCHIVE_CAP, timeout=15)
    except (DataError, OSError) as exc:
        return dict(**identity, url=url, error=str(exc))
    receipt["cache_path"] = str(Path(receipt["cache_path"]).relative_to(ROOT))
    return dict(**identity, **receipt)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temp.replace(path)


def acquire():
    spec = protocol()
    jobs = list(product(spec["symbols"], STREAMS, spec["source_months"]))
    if len(set(jobs)) != len(jobs) or len(jobs) * ARCHIVE_CAP > TOTAL_CAP:
        raise DataError("source schedule duplicates a job or exceeds the registered cap")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(download, jobs))
    sources = [row for row in results if "error" not in row]
    errors = [row for row in results if "error" in row]
    write_json(WORK / "sources.json", {
        "venue": "Binance Vision USD-M", "terms": spec["archive_terms"],
        "sources": sources, "errors": errors,
        "verified_bytes": sum(row["bytes"] for row in sources),
        "cache_hits": sum(row["cache_hit"] for row in sources),
        "budget": {"archive_bytes": ARCHIVE_CAP, "total_bytes": TOTAL_CAP},
    })
    print(f"archive_jobs={len(jobs)} verified={len(sources)} errors={len(errors)}", flush=True)
    for row in errors:
        print(row["error"], flush=True)
    return bool(errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["acquire", "inventory"])
    args = parser.parse_args()
    if args.action == "acquire":
        raise SystemExit(acquire())
    inventory = discover_archive_symbols()
    write_json(WORK / "archive-inventory.json", inventory)
    print({key: value for key, value in inventory.items() if not isinstance(value, list)})


if __name__ == "__main__":
    main()
