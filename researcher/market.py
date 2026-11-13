"""Cheap aggregate current observations, never historical structural evidence."""
from datetime import datetime, timezone
from .contracts import ContractError, digest, number, symbol, utc
from .inventory import json_document
from .transport import ProviderError, PublicHTTP


def milliseconds(value):
    if type(value) is not int or value <= 0:
        raise ContractError("MARKET_TIMESTAMP_REQUIRED")
    try:
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        raise ContractError("MARKET_TIMESTAMP_INVALID") from None


def normalize_market(rows, *, kind, inventory, captured_at, response_hash):
    if kind not in {"ticker", "book", "premium"} or not isinstance(rows, list):
        raise ContractError("MARKET_SNAPSHOT_SCHEMA")
    expected, seen, observations, failures, fillers = set(inventory.symbols), set(), [], {}, []
    for row in rows:
        if not isinstance(row, dict):
            raise ContractError("MARKET_ROW_SCHEMA")
        name = symbol(row.get("symbol"))
        if name in seen:
            raise ContractError("DUPLICATE_MARKET_ROW")
        seen.add(name)
        if name not in expected:
            fillers.append(name)
            continue
        try:
            source_time = milliseconds(row["closeTime"] if kind == "ticker" else row["time"])
            age = (utc(captured_at) - utc(source_time)).total_seconds()
            if age < 0 or age > (300 if kind == "ticker" else 60):
                raise ContractError("STALE_OR_FUTURE_MARKET_SNAPSHOT")
            values = {}
            if kind == "ticker":
                start = milliseconds(row["openTime"])
                if not 86399 <= (utc(source_time) - utc(start)).total_seconds() <= 86401:
                    raise ContractError("ROLLING_24H_WINDOW_MISMATCH")
                values = {k: number(row[k]) for k in ["priceChangePercent", "quoteVolume", "volume"]}
                values["lastPrice"] = number(row["lastPrice"], positive=True)
                if values["quoteVolume"] < 0 or values["volume"] < 0:
                    raise ContractError("NEGATIVE_VOLUME")
            elif kind == "book":
                bid, ask = number(row["bidPrice"], positive=True), number(row["askPrice"], positive=True)
                if ask < bid:
                    raise ContractError("CROSSED_BOOK")
                values = {"bid": bid, "ask": ask, "spread_bps": 10000 * (ask - bid) / ((ask + bid) / 2)}
            else:
                values = {"markPrice": number(row["markPrice"], positive=True),
                    "lastFundingRate": number(row["lastFundingRate"]),
                    "nextFundingTime_utc": milliseconds(row["nextFundingTime"])}
                # Funding interval is not supplied by this endpoint.
                values["funding_interval_hours"] = None
            observations.append({"native_symbol": name, "kind": kind, "values": values,
                "source_time_utc": source_time, "received_at_utc": captured_at,
                "source_response_sha256": response_hash, "source_scope": "OFFICIAL_BINANCE_USDM",
                "fidelity": "EXACT_REPORTED", "structural_coverage": False,
                "inventory_mode": inventory.mode})
        except (ContractError, KeyError, TypeError):
            failures[name] = "INVALID_OR_STALE_MARKET_ROW"
    missing = sorted(expected - seen)
    return {"kind": kind, "observations": observations, "missing_symbols": missing,
        "failed_symbols": failures, "filler_symbols": fillers,
        "requested_symbols": list(inventory.symbols), "returned_symbols": sorted(expected & seen),
        "evaluated_symbols": [o["native_symbol"] for o in observations],
        "synchronized_closed_bar_cross_section": False}


class OfficialMarketPulse:
    def __init__(self, http=None, *, access_denial=451):
        self.http = http or PublicHTTP()
        self.access_denial = access_denial

    def read(self, inventory):
        if self.access_denial in {403, 451}:
            raise ProviderError("RECORDED_BINANCE_ACCESS_DENIAL")
        results = []
        for kind in ("ticker", "book", "premium"):
            response = self.http.request("binance_" + kind)
            results.append(normalize_market(json_document(response.body), kind=kind, inventory=inventory,
                captured_at=response.receipt["received_at_utc"], response_hash=digest(response.body)))
        return results
