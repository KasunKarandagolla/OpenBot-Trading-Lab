"""Opt-in, bounded source probes. Not used by the normal smoke command.

Raw source objects remain in ignored work/. This tool does not certify detectors.
Run: python -m researcher.qualify samples --output work/samples-001
"""
import argparse
import json
from pathlib import Path
from .basis import BasisMCP
from .contracts import ContractError, digest, encode
from .observations import candle_observation, screen_receipt
from .settings import ROOT, load_config
from .transport import ProviderError, PublicHTTP


def run(profile, directory):
    directory = Path(directory).absolute()
    if ".." in directory.parts or not directory.is_relative_to(ROOT / "work") or any(p.is_symlink() for p in [directory, *directory.parents]):
        raise ContractError("PROBE_OUTPUT_UNDER_WORK_REQUIRED")
    directory.mkdir(parents=True, exist_ok=False)
    config = load_config()
    client = BasisMCP(PublicHTTP(max_requests=40), qualification=True)
    outcomes = []

    def save(label, tool, args):
        try:
            data = client.call(tool, args)
            receipt = {**client.http.receipts[-1], "tool": tool, "arguments": args,
                       "stored_object_sha256": digest(encode(data).encode())}
            (directory / (label + ".json")).write_text(encode(data) + "\n")
            (directory / (label + ".receipt.json")).write_text(encode(receipt) + "\n")
            outcomes.append({"probe": label, "status": "LIVE_TESTED_NARROW", "receipt": receipt})
            return data, receipt
        except ProviderError as error:
            outcomes.append({"probe": label, "status": "FAILED", "code": str(error),
                             "receipt": client.http.receipts[-1] if client.http.receipts else {}})
            if str(error) in {"HTTP_403", "HTTP_451", "HTTP_429", "REQUEST_BUDGET_EXHAUSTED"}:
                raise
            return None, None

    try:
        tools = client.connect()
        (directory / "read_tools.json").write_text(encode(tools) + "\n")
        if profile == "schema":
            save("functions", "catalog_search", {"kind": "formula", "limit": 100})
            save("variables", "catalog_search", {"kind": "variable", "limit": 100})
        elif profile == "footer":
            base = {"exchange": "binance", "market": "futures", "quote": "USDT",
                    "manualSymbols": ["BTCUSDT", "ETHUSDT"], "universeSize": 20,
                    "timeframe": "1h", "lookback": 300, "logic": "any", "limit": 60}
            finite = {"left": {"kind": "formula", "expression": "(highest(high,3)-lowest(low,3))/close"},
                      "operator": "atOrAbove", "right": 0}
            poison = {"left": {"kind": "formula", "expression": config["qualification_failure_expression"]},
                      "operator": "above", "right": 0}
            for label, rules in [("finite", [finite]), ("poison", [finite, poison]), ("recovery", [finite])]:
                data, meta = save(label, "screener_run", {**base, "rules": rules})
                if data:
                    receipt = screen_receipt(base["manualSymbols"], data, timeframe="1h", metadata=meta)
                    (directory / (label + ".coverage.json")).write_text(encode(receipt) + "\n")
        elif profile == "formulas":
            save("functions", "catalog_search", {"kind": "formula", "limit": 100})
            data, _ = save("candles", "market_candles", {"exchange": "binance", "market": "futures",
                           "symbol": "BTCUSDT", "timeframe": "1h", "bars": 65, "withDerivatives": False})
            if not data:
                raise ProviderError("FORMULA_SOURCE_UNAVAILABLE")
            for label, spec in config["qualification_formulas"].items():
                save(label, "formula_evaluate", {"ref": data["ref"], "expression": spec["expression"],
                                                "reduce": "tail", "includeForming": False})
        elif profile == "samples":
            # Representative requested spellings, NOT independently eligible/quiet/young samples.
            for name in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "FILUSDT", "1000PEPEUSDT"]:
                for tf in ["15m", "1h"]:
                    label = name + "_" + tf
                    data, meta = save(label, "market_candles", {"exchange": "binance", "market": "futures",
                           "symbol": name, "timeframe": tf, "bars": 17, "withDerivatives": False})
                    if data:
                        obs = candle_observation(data, requested_symbol=name, timeframe=tf,
                            received_at=meta["received_at_utc"],
                            schema_hash=digest(encode(tools["market_candles"]["inputSchema"]).encode()),
                            response_hash=meta["response_sha256"])
                        (directory / (label + ".observation.json")).write_text(encode(obs) + "\n")
                        save(label + "_width", "formula_evaluate", {"ref": data["ref"],
                            "expression": "(highest(high,3)-lowest(low,3))/close", "reduce": "last", "includeForming": False})
    except (ProviderError, ContractError, KeyError, TypeError):
        outcomes.append({"status": "STOPPED", "code": "PROVIDER_OR_CONTRACT_FAILURE"})
    summary = {"profile": profile, "qualification": "UNVERIFIED",
               "independent_source_oracle": "BLOCKED_HTTP_451", "quiet_tail": "BLOCKED_CURRENT_INVENTORY",
               "outcomes": outcomes, "http_receipts": client.http.receipts,
               "trade_authorization": False}
    (directory / "summary.json").write_text(encode(summary) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=["schema", "footer", "formulas", "samples"])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    summary = run(args.profile, args.output)
    print(encode({"output": args.output, "qualification": summary["qualification"],
                  "requests": len(summary["http_receipts"]), "outcomes": len(summary["outcomes"])}))
    return int(any(o.get("status") == "STOPPED" for o in summary["outcomes"]))


if __name__ == "__main__":
    raise SystemExit(main())
