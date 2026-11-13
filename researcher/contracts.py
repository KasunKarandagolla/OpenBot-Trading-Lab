"""Canonical research contracts. Unknowns are explicit; numbers use Decimal."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
import re
from typing import Any, TypedDict


class ContractError(ValueError):
    pass


class Fidelity(StrEnum):
    EXACT_REPORTED = "EXACT_REPORTED"
    SYNCHRONIZED_REMOTE_RECONSTRUCTION = "SYNCHRONIZED_REMOTE_RECONSTRUCTION"
    PROXY_ONLY = "PROXY_ONLY"
    INCOMPLETE_HISTORY = "INCOMPLETE_HISTORY"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class Feasibility(StrEnum):
    NATIVE_REMOTE = "NATIVE_REMOTE"
    REMOTE_RECONSTRUCTED = "REMOTE_RECONSTRUCTED"
    PROXY_ONLY = "PROXY_ONLY"
    TARGETED_ONLY = "TARGETED_ONLY"
    UNSUPPORTED = "UNSUPPORTED"
    UNVERIFIED = "UNVERIFIED"
    DEFINITION_PENDING = "DEFINITION_PENDING"


class ProviderEvidence(StrEnum):
    LIVE_TESTED_NARROW = "LIVE_TESTED_NARROW"
    DOC_CONFIRMED = "DOC_CONFIRMED"
    VENDOR_ADVERTISED = "VENDOR_ADVERTISED"
    UNVERIFIED = "UNVERIFIED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"


def utc(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        raise ContractError("INVALID_UTC") from None
    if result.utcoffset() != timezone.utc.utcoffset(result):
        raise ContractError("UTC_OFFSET_REQUIRED")
    return result


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def number(value: Any, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise ContractError("BOOLEAN_IS_NOT_NUMBER")
    try:
        result = Decimal(str(value))
    except ArithmeticError:
        raise ContractError("INVALID_NUMBER") from None
    if not result.is_finite() or (positive and result <= 0):
        raise ContractError("NONFINITE_OR_NONPOSITIVE_NUMBER")
    return result


def symbol(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z0-9_]{2,32}", value):
        raise ContractError("EXACT_NATIVE_SYMBOL_REQUIRED")
    return value


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def encode(value: Any) -> str:
    def default(obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        raise TypeError(type(obj).__name__)
    return json.dumps(value, default=default, sort_keys=True, indent=2, allow_nan=False)


@dataclass(frozen=True)
class Instrument:
    native_symbol: str
    venue: str
    quote: str | None = None
    settlement: str | None = None
    contract_type: str | None = None
    contract_multiplier: Decimal | None = None
    tick_size: Decimal | None = None
    quantity_rules: dict = field(default_factory=dict)
    onboard_at_utc: str | None = None
    metadata_hash: str | None = None
    identity_status: str = "UNVERIFIED"
    trading_status: str | None = None
    underlying_class: str | None = None
    source_id: str | None = None
    captured_at_utc: str | None = None
    unsupported_fields: tuple[str, ...] = ()

    def __post_init__(self):
        symbol(self.native_symbol)
        if self.identity_status not in {"UNVERIFIED", "EXCHANGE_VERIFIED"}:
            raise ContractError("IDENTITY_STATUS")
        if self.identity_status == "EXCHANGE_VERIFIED":
            if (self.venue != "BINANCE_USDM" or self.quote != "USDT"
                    or self.settlement != "USDT" or self.contract_type != "PERPETUAL"
                    or not self.metadata_hash or not self.quantity_rules
                    or self.tick_size is None or self.trading_status != "TRADING"
                    or self.underlying_class != "CRYPTO" or not self.source_id or not self.captured_at_utc):
                raise ContractError("INCOMPLETE_EXCHANGE_IDENTITY")
            number(self.tick_size, positive=True)
        if self.contract_multiplier is not None:
            number(self.contract_multiplier, positive=True)
        if self.captured_at_utc is not None:
            utc(self.captured_at_utc)


@dataclass(frozen=True)
class Capability:
    provider: str
    operation: str
    scope: str
    timeframe: str | None
    evidence: ProviderEvidence
    feasibility: Feasibility
    enabled: bool = False
    authentication: str = "NONE"
    entitlement: str = "UNKNOWN"
    free_automation_terms: str = "UNVERIFIED"
    quota: dict = field(default_factory=dict)
    oracle_status: str = "UNVERIFIED"

    def __post_init__(self):
        ProviderEvidence(self.evidence)
        Feasibility(self.feasibility)
        if self.enabled and (self.evidence != ProviderEvidence.LIVE_TESTED_NARROW
                             or self.feasibility == Feasibility.UNVERIFIED):
            raise ContractError("UNPROVEN_CAPABILITY_ENABLED")


@dataclass(frozen=True)
class Evidence:
    id: str
    instrument: Instrument
    measurement_id: str
    value: Decimal | None
    units: str
    timeframe: str
    window_start_utc: str | None
    window_end_utc: str | None
    known_at_utc: str | None
    available_at_utc: str | None
    received_at_utc: str
    provider: str
    source_scope: str
    source_schema_hash: str
    source_response_hash: str
    formula_hash: str | None
    complete: bool
    verdict: str
    fidelity: Fidelity
    temporal_status: str
    fault_code: str | None = None

    def __post_init__(self):
        Fidelity(self.fidelity)
        received = utc(self.received_at_utc)
        times = [utc(t) for t in (self.window_start_utc, self.window_end_utc,
                  self.known_at_utc, self.available_at_utc) if t is not None]
        if any(t > received for t in times) or any(b < a for a, b in zip(times, times[1:])):
            raise ContractError("CAUSAL_TIMESTAMP_ORDER")
        if self.verdict not in {"SUPPORTED", "CONTRADICTED", "UNKNOWN"}:
            raise ContractError("VERDICT")
        if not self.units or not self.source_scope or not self.source_schema_hash or not self.source_response_hash:
            raise ContractError("PROVENANCE_REQUIRED")
        if self.value is None and (not self.fault_code or self.verdict != "UNKNOWN"):
            raise ContractError("MISSING_VALUE_REQUIRES_REASON")
        if self.value is not None:
            number(self.value)
        if self.temporal_status not in {"CLOSED_CURRENT", "CLOSED_STALE", "FORMING", "UNKNOWN_TIME", "GAP_UNOBSERVED"}:
            raise ContractError("TEMPORAL_STATUS")
        if self.temporal_status.startswith("CLOSED") and (not self.window_start_utc or not self.window_end_utc):
            raise ContractError("CLOSED_WINDOW_REQUIRED")


@dataclass(frozen=True)
class ScanBatchReceipt:
    provider: str
    method: str
    timeframe: str
    requested_symbols: tuple[str, ...]
    evaluated_symbols: tuple[str, ...] = ()
    returned_symbols: tuple[str, ...] = ()
    failed_symbols: dict[str, str] = field(default_factory=dict)
    filler_symbols: tuple[str, ...] = ()
    recognized_symbols: tuple[str, ...] = ()
    source_cutoffs: dict[str, str] = field(default_factory=dict)
    truncated: bool = False
    response_bytes: int = 0
    elapsed_ms: int = 0
    quota_usage: dict = field(default_factory=lambda: {"charged_units": None})
    provider_error: str | None = None
    source_hash: str | None = None

    def __post_init__(self):
        for names in (self.requested_symbols, self.evaluated_symbols, self.returned_symbols,
                      self.filler_symbols, self.recognized_symbols):
            if len(names) != len(set(names)):
                raise ContractError("DUPLICATE_SYMBOL")
            for name in names:
                symbol(name)
        requested, evaluated, failed = map(set, (self.requested_symbols, self.evaluated_symbols, self.failed_symbols))
        if (not evaluated <= requested or not failed <= requested or evaluated & failed
                or evaluated | failed != requested or set(self.filler_symbols) & requested
                or not set(self.recognized_symbols) <= requested
                or not set(self.returned_symbols) <= requested
                or not set(self.source_cutoffs) <= requested):
            raise ContractError("COVERAGE_SET_ACCOUNTING")
        if self.provider_error and evaluated:
            raise ContractError("ERROR_CANNOT_CERTIFY_EVALUATION")
        for cutoff in self.source_cutoffs.values():
            utc(cutoff)
        if self.response_bytes < 0 or self.elapsed_ms < 0:
            raise ContractError("INVALID_RESOURCE_COUNTS")


@dataclass(frozen=True)
class Coverage:
    eligible_contracts: int | None
    inventory_seen: int | None
    cheap_market_observed: int
    valid_remote_core_evaluated: int
    method_predicate_evaluated: dict
    qualified_specialist_evaluated: int
    targeted_verified: int
    denominator_status: str
    all_market_structurally_covered: bool = False

    def __post_init__(self):
        if self.all_market_structurally_covered:
            raise ContractError("SESSION1_CANNOT_CLAIM_FULL_COVERAGE")
        counts = [self.eligible_contracts, self.inventory_seen, self.cheap_market_observed,
                  self.valid_remote_core_evaluated, self.qualified_specialist_evaluated,
                  self.targeted_verified, *self.method_predicate_evaluated.values()]
        if any(c is not None and (type(c) is not int or c < 0) for c in counts):
            raise ContractError("INVALID_COVERAGE_COUNTS")


class ResearchReport(TypedDict):
    schema_version: str
    created_at_utc: str
    mode: str
    manifest_sha256: str
    coverage: dict
    observations: list[dict]
    shortlist: list[dict]
    watches: list[dict]
    near_misses: list[dict]
    context: dict
    source_faults: list[dict]
    provider_status: dict
    limitations: list[str]
    trade_authorization: bool
    new_orders_created: int
    operation_status: str
    transport_receipts: list[dict]
