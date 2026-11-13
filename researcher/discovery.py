"""One bounded smoke observation. No family detector, ranking or trading path."""
from dataclasses import asdict
from .basis import BasisMCP
from .contracts import Coverage, ContractError, ResearchReport, digest, encode, now_utc
from .observations import candle_observation
from .settings import MANIFEST, load_config, provider_status
from .transport import ProviderError


def smoke(client=None) -> ResearchReport:
    config = load_config()
    client = client or BasisMCP()
    report = {
        "schema_version": "openbot.research-smoke.v1", "created_at_utc": now_utc(),
        "mode": "PAUSE_UNQUALIFIED", "trade_authorization": False, "new_orders_created": 0,
        "manifest_sha256": digest(MANIFEST.read_bytes()),
        "coverage": asdict(Coverage(None, None, 0, 0, {"1h": 0, "15m": 0}, 0, 0,
                                   "UNKNOWN_EXCHANGE_INVENTORY_HTTP_451")),
        "context": {"policy": "ADVISORY_NON_VETO", "btc": "UNVERIFIED", "eth": "UNVERIFIED"},
        "shortlist": [], "watches": [], "near_misses": [], "observations": [],
        "source_faults": [], "provider_status": provider_status(config),
        "limitations": ["No quiet-tail qualification", "No independent source oracle",
                        "No detectors enabled", "Earliest source availability UNKNOWN"],
    }
    try:
        if not config["providers"]["basis"]["operations"]["market_candles"]["enabled"]:
            raise ContractError("CAPABILITY_DISABLED")
        client.connect()
        data = client.call("market_candles", {"symbol": "BTCUSDT", "exchange": "binance",
                           "market": "futures", "timeframe": "1h", "bars": 3, "withDerivatives": False})
        metadata = client.http.receipts[-1]
        evidence = candle_observation(data, requested_symbol="BTCUSDT", timeframe="1h",
            received_at=metadata["received_at_utc"],
            schema_hash=digest(encode(client.tools["market_candles"]["inputSchema"]).encode()),
            response_hash=metadata["response_sha256"])
        report["observations"].append(asdict(evidence))
        report["mode"] = "TARGETED_RESEARCH"
        report["operation_status"] = "LIVE_TESTED_NARROW"
    except (ProviderError, ContractError, KeyError, TypeError, ValueError) as error:
        report["operation_status"] = "BLOCKED_OR_UNQUALIFIED"
        # Never print remote message text or exception values from arbitrary sources.
        code = str(error) if isinstance(error, ContractError) else "PROVIDER_SCHEMA_CHANGED"
        report["source_faults"].append({"code": code})
    report["transport_receipts"] = client.http.receipts
    return report
