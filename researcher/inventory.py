"""Read-only inventory sources. A provider symbol is never an eligibility fact."""
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Protocol

from .contracts import ContractError, Instrument, digest, number, symbol, utc
from .transport import ENDPOINTS, MAX_BYTES, ProviderError, PublicHTTP

INVENTORY_URL = ENDPOINTS["binance_inventory"]
MAX_AGE_SECONDS = 86400


def json_document(body):
    """Reject duplicate keys, nonstandard numbers and oversize snapshot files."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ContractError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    if len(body) > MAX_BYTES:
        raise ContractError("INVENTORY_SIZE_LIMIT")
    def invalid(_):
        raise ContractError("NONSTANDARD_JSON_NUMBER")
    try:
        return json.loads(body, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, UnicodeError):
        raise ContractError("INVENTORY_JSON_INVALID") from None


def read_document(path):
    with Path(path).open("rb") as stream:
        return stream.read(MAX_BYTES + 1)


@dataclass(frozen=True)
class InventorySnapshot:
    source_id: str
    source_url: str
    captured_at_utc: str
    received_at_utc: str
    content_sha256: str
    instruments: tuple[Instrument, ...]
    mode: str
    eligible_symbols: tuple[str, ...] = ()
    provisional_symbols: tuple[str, ...] = ()
    excluded: dict[str, str] = field(default_factory=dict)
    faults: tuple[str, ...] = ()
    complete_source_snapshot: bool = False
    freshness: str = "UNKNOWN"
    max_age_seconds: int = MAX_AGE_SECONDS

    def __post_init__(self):
        names = tuple(i.native_symbol for i in self.instruments)
        if (len(names) != len(set(names)) or set(self.eligible_symbols) & set(self.provisional_symbols)
                or set(names) != set(self.eligible_symbols) | set(self.provisional_symbols)):
            raise ContractError("INVENTORY_MEMBERSHIP")
        if self.mode not in {"VERIFIED_INVENTORY", "PARTIAL_INVENTORY"}:
            raise ContractError("INVENTORY_MODE")
        if self.mode == "VERIFIED_INVENTORY" and (not self.complete_source_snapshot
                or self.freshness != "FRESH" or self.provisional_symbols or self.faults):
            raise ContractError("INCOMPLETE_UNIVERSE_CANNOT_BE_VERIFIED")
        if utc(self.captured_at_utc) > utc(self.received_at_utc):
            raise ContractError("INVENTORY_FUTURE_CAPTURE")

    @property
    def symbols(self):
        return tuple(i.native_symbol for i in self.instruments)

    def at(self, scan_time):
        """Recheck freshness when reusing an in-memory or cached source object."""
        if utc(self.received_at_utc) > utc(scan_time):
            raise ContractError("INVENTORY_NOT_KNOWN_AT_SCAN")
        if self.freshness == "UNVERIFIED" or (utc(scan_time) - utc(self.captured_at_utc)).total_seconds() <= self.max_age_seconds:
            return self
        return replace(self, mode="PARTIAL_INVENTORY", freshness="STALE",
            eligible_symbols=(), provisional_symbols=self.symbols,
            instruments=tuple(replace(i, identity_status="UNVERIFIED") for i in self.instruments),
            faults=tuple(dict.fromkeys((*self.faults, "STALE_INVENTORY"))))

    def report(self):
        return {
            "mode": self.mode, "source_id": self.source_id, "source_url": self.source_url,
            "captured_at_utc": self.captured_at_utc, "received_at_utc": self.received_at_utc,
            "content_sha256": self.content_sha256, "freshness": self.freshness,
            "max_age_seconds": self.max_age_seconds,
            "source_snapshot_complete": self.complete_source_snapshot,
            "eligible_contracts": len(self.eligible_symbols) if self.mode == "VERIFIED_INVENTORY" else None,
            "verified_eligible_subset": list(self.eligible_symbols),
            "provisionally_identified_contracts": list(self.provisional_symbols),
            "inventory_seen": len(self.symbols), "excluded": self.excluded, "faults": self.faults,
            "instruments": self.instruments,
        }


class InventorySource(Protocol):
    def load(self, received_at: str) -> InventorySnapshot: ...


def official_snapshot(payload, *, manifest, content_hash, received_at):
    """Parse official exchangeInfo without inferring multiplier or listing facts.

    A complete file may still have unresolved eligible rows. Such a file yields
    PARTIAL_INVENTORY, with each unresolved symbol retained and fields disclosed.
    COIN is the official underlyingType classification admitted by this adapter;
    unrecognized classifications require review rather than suffix inference.
    """
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != "openbot.inventory-source.v1"
            or manifest.get("source_kind") not in {"OWNER_OFFICIAL_SNAPSHOT", "OFFICIAL_LIVE"}
            or manifest.get("source_url") != INVENTORY_URL
            or manifest.get("authorized_capture") is not True
            or not isinstance(manifest.get("lawful_source_statement"), str)
            or not manifest["lawful_source_statement"].strip()
            or type(manifest.get("complete_exchange_info")) is not bool
            or manifest.get("payload_sha256") != content_hash):
        raise ContractError("INVENTORY_PROVENANCE_REQUIRED")
    captured = utc(manifest.get("captured_at_utc"))
    received = utc(received_at)
    age = (received - captured).total_seconds()
    max_age = manifest.get("max_age_seconds", MAX_AGE_SECONDS)
    if type(max_age) is not int or not 1 <= max_age <= MAX_AGE_SECONDS or age < 0:
        raise ContractError("INVENTORY_FRESHNESS_POLICY")
    fresh = age <= max_age
    if not isinstance(payload, dict) or not isinstance(payload.get("symbols"), list) or not payload["symbols"]:
        raise ContractError("EXCHANGE_INFO_SCHEMA")
    if len(payload["symbols"]) > 10000:
        raise ContractError("INVENTORY_ROW_LIMIT")
    instruments, eligible, provisional, excluded, seen = [], [], [], {}, set()
    for row in payload["symbols"]:
        if not isinstance(row, dict):
            raise ContractError("EXCHANGE_INSTRUMENT_SCHEMA")
        native = symbol(row.get("symbol"))
        if native in seen:
            raise ContractError("DUPLICATE_INVENTORY_SYMBOL")
        seen.add(native)
        # Explicitly known noneligible facts exclude; absent facts never do.
        mismatch = next((key for key, expected in [("contractType", "PERPETUAL"),
                        ("quoteAsset", "USDT"), ("marginAsset", "USDT"), ("status", "TRADING")]
                        if row.get(key) is not None and row[key] != expected), None)
        if mismatch:
            excluded[native] = "INELIGIBLE_" + mismatch.upper()
            continue
        if row.get("underlyingType") in {"INDEX", "PREMARKET", "COMMODITY", "STOCK"}:
            excluded[native] = "INELIGIBLE_UNDERLYINGTYPE_" + row["underlyingType"]
            continue
        unsupported = [key for key in ["contractType", "quoteAsset", "marginAsset", "status"] if row.get(key) is None]
        classification = "CRYPTO" if row.get("underlyingType") == "COIN" else None
        if classification is None:
            unsupported.append("underlying_class")
        filters = row.get("filters", [])
        if not isinstance(filters, list) or any(not isinstance(f, dict) for f in filters):
            raise ContractError("INSTRUMENT_FILTER_SCHEMA")
        by_type = {}
        for item in filters:
            kind = item.get("filterType")
            if not isinstance(kind, str) or kind in by_type:
                raise ContractError("DUPLICATE_OR_INVALID_FILTER")
            by_type[kind] = item
        tick, quantity = None, {}
        if "PRICE_FILTER" in by_type:
            tick = number(by_type["PRICE_FILTER"].get("tickSize"), positive=True)
        else:
            unsupported.append("tick_size")
        for kind in ["LOT_SIZE", "MARKET_LOT_SIZE"]:
            if kind in by_type:
                item = by_type[kind]
                rules = {key: number(item.get(key), positive=True) for key in ["minQty", "maxQty", "stepSize"]}
                if rules["minQty"] > rules["maxQty"]:
                    raise ContractError("QUANTITY_RANGE")
                quantity[kind] = rules
        if "LOT_SIZE" not in quantity:
            unsupported.append("quantity_rules")
        onboard = row.get("onboardDate")
        if onboard is not None:
            if type(onboard) is not int or onboard <= 0:
                raise ContractError("LISTING_TIME_INVALID")
            try:
                onboard = datetime.fromtimestamp(onboard / 1000, timezone.utc).isoformat()
            except (ValueError, OverflowError, OSError):
                raise ContractError("LISTING_TIME_INVALID") from None
            if utc(onboard) > captured:
                unsupported.append("listing_in_future")
        else:
            unsupported.append("onboard_at_utc")
        # No parsing numeric prefixes as multipliers. Use only an explicit fact.
        multiplier = row.get("contractMultiplier")
        if multiplier is not None:
            multiplier = number(multiplier, positive=True)
        else:
            unsupported.append("contract_multiplier")
        essential = set(unsupported) - {"onboard_at_utc", "contract_multiplier"}
        verified = not essential and fresh
        instrument = Instrument(native, "BINANCE_USDM", quote=row.get("quoteAsset"),
            settlement=row.get("marginAsset"), contract_type=row.get("contractType"),
            contract_multiplier=multiplier, tick_size=tick, quantity_rules=quantity,
            onboard_at_utc=onboard, metadata_hash=digest(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()),
            identity_status="EXCHANGE_VERIFIED" if verified else "UNVERIFIED",
            trading_status=row.get("status"), underlying_class=classification,
            source_id=manifest["source_kind"], captured_at_utc=manifest["captured_at_utc"],
            unsupported_fields=tuple(unsupported),
            exchange_rules=tuple(json.loads(json.dumps(filters))),
            listing_metadata={key: row[key] for key in ("baseAsset", "pair", "onboardDate", "deliveryDate",
                "pricePrecision", "quantityPrecision", "underlyingType", "underlyingSubType") if key in row})
        instruments.append(instrument)
        (eligible if verified else provisional).append(native)
    complete = manifest["complete_exchange_info"]
    faults = () if fresh else ("STALE_INVENTORY",)
    mode = "VERIFIED_INVENTORY" if complete and fresh and not provisional else "PARTIAL_INVENTORY"
    return InventorySnapshot(manifest["source_kind"], INVENTORY_URL, manifest["captured_at_utc"],
        received_at, content_hash, tuple(instruments), mode, tuple(eligible), tuple(provisional),
        excluded, faults, complete, "FRESH" if fresh else "STALE", max_age)


@dataclass(frozen=True)
class OwnerOfficialSnapshot:
    payload_path: Path
    provenance_path: Path

    def load(self, received_at):
        body = read_document(self.payload_path)
        return official_snapshot(json_document(body),
            manifest=json_document(read_document(self.provenance_path)), content_hash=digest(body),
            received_at=received_at)


class OfficialBinanceInventory:
    """Enable only on an authorized host with no recorded route denial.

    Cloud's recorded 451 blocks this adapter before HTTP. The caller cannot
    clear that decision with a command-line flag. A distinct compliant host
    must establish its own access evidence; no alternative hosts or routing.
    """
    def __init__(self, http=None, *, access_denial=451):
        self.http = http or PublicHTTP()
        self.access_denial = access_denial

    def load(self, received_at):
        if self.access_denial in {403, 451}:
            raise ProviderError("RECORDED_BINANCE_ACCESS_DENIAL")
        response = self.http.request("binance_inventory")
        captured = response.receipt["received_at_utc"]
        manifest = {"schema_version": "openbot.inventory-source.v1", "source_kind": "OFFICIAL_LIVE",
            "source_url": INVENTORY_URL, "authorized_capture": True,
            "lawful_source_statement": "Public official metadata on the authorized host",
            "complete_exchange_info": True, "captured_at_utc": captured,
            "payload_sha256": digest(response.body), "max_age_seconds": MAX_AGE_SECONDS}
        return official_snapshot(json_document(response.body), manifest=manifest,
            content_hash=digest(response.body), received_at=captured)


def provisional_inventory(names, *, source_id, source_url, captured_at, received_at, content_hash):
    names = tuple(names)
    if not names or len(names) != len(set(names)):
        raise ContractError("PROVISIONAL_SYMBOL_SET")
    instruments = tuple(Instrument(symbol(n), "BINANCE_USDM", source_id=source_id,
        captured_at_utc=captured_at, unsupported_fields=("contract_type", "quote", "settlement",
        "trading_status", "underlying_class", "tick_size", "quantity_rules", "onboard_at_utc", "contract_multiplier")) for n in names)
    return InventorySnapshot(source_id, source_url, captured_at, received_at, content_hash,
        instruments, "PARTIAL_INVENTORY", provisional_symbols=names,
        faults=("AUTHORITATIVE_INVENTORY_UNAVAILABLE",), freshness="UNVERIFIED")


class InventorySources:
    """Shared interface for future independently qualified permitted adapters.

    Qualification is code-reviewed registration, never a trust flag accepted
    from a third-party symbol-list response. No alternative is qualified today.
    """
    def __init__(self):
        self.sources: dict[str, InventorySource] = {}

    def register(self, source_id, source: InventorySource):
        if source_id in self.sources:
            raise ContractError("DUPLICATE_INVENTORY_SOURCE")
        self.sources[source_id] = source

    def load(self, source_id, received_at):
        if source_id not in self.sources:
            raise ContractError("INVENTORY_SOURCE_NOT_REGISTERED")
        return self.sources[source_id].load(received_at)
