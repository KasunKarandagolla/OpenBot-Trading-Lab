"""Bounded, explicit remote partitions and auditable scalar observations.

The R0 path executes the registered finite width probe, not certified CORE or
strategy predicates. Full CORE requirements remain visible and disabled.
"""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
import time
from typing import Protocol

from .contracts import (ContractError, Evidence, Fidelity, ScanBatchReceipt, digest,
                        encode, number, symbol, utc)
from .observations import WIDTHS, screen_receipt
from .transport import ProviderError


def partitions(names, size=50):
    names = tuple(names)
    if type(size) is not int or not 1 <= size <= 50 or len(names) != len(set(names)):
        raise ContractError("EXPLICIT_PARTITION_MEMBERSHIP")
    for name in names:
        symbol(name)
    return tuple(names[i:i + size] for i in range(0, len(names), size))


def closed_cutoff(at, timeframe):
    width = WIDTHS[timeframe]
    epoch = int(utc(at).timestamp())
    return datetime.fromtimestamp(epoch - epoch % width, timezone.utc).isoformat()


@dataclass(frozen=True)
class RemotePack:
    id: str
    version: str
    timeframe: str
    expression: str
    column_id: str
    units: str
    required_closed_bars: int
    precision_absolute: str
    supported_symbols: tuple[str, ...]
    full_core_qualified: bool = False

    @property
    def formula_hash(self):
        return digest(encode(asdict(self)).encode())


class CapabilityRegistry:
    """Only reviewed, versioned finite probes can reach a remote compiler.

    Optional sparse functions do not share a request with this baseline. Adding
    a pack requires code review and tests; it cannot come from provider prose.
    """
    def __init__(self, config):
        self.packs = {}
        for pack_id in ("CORE_1H", "CORE_15M"):
            spec = config["packs"][pack_id]
            column = spec["observation_columns"][0]
            if (not column["observation_probe_enabled"] or column["production_enabled"]
                    or column["schema_test"] != "PASS_SESSION1"
                    or column["source_semantics"] != "PROVIDER_REPORTED_CLOSED_OHLC_WINDOW"
                    or column["required_closed_bars"] != 3
                    or column["expression"] != "(highest(high,3)-lowest(low,3))/close"):
                raise ContractError("UNQUALIFIED_REMOTE_COLUMN")
            self.register(RemotePack(pack_id, spec["version"], spec["timeframe"],
                column["expression"], column["id"], column["units"], column["required_closed_bars"],
                column["precision_absolute"], tuple(config["external_discovery"]["observed_symbols"])))

    def register(self, pack):
        if pack.id in self.packs or pack.full_core_qualified:
            raise ContractError("REMOTE_PACK_REGISTRATION")
        self.packs[pack.id] = pack


class RemoteScreenSource(Protocol):
    def screen(self, names: tuple[str, ...], pack: RemotePack) -> tuple[dict, dict]: ...


class BasisScreenSource:
    """Uses the Session 1 runtime client, session and allowlist unchanged."""
    def __init__(self, client):
        self.client = client

    def screen(self, names, pack):
        args = {"exchange": "binance", "market": "futures", "quote": "USDT",
            "manualSymbols": list(names), "universeSize": 20 if len(names) <= 20 else 50,
            "timeframe": pack.timeframe, "lookback": 300, "logic": "all", "limit": 60,
            "rules": [{"left": {"kind": "formula", "expression": pack.expression},
                       "operator": "atOrAbove", "right": 0}]}
        before = len(self.client.http.receipts)
        try:
            data = self.client.call("screener_run", args)
        except ProviderError as error:
            if len(self.client.http.receipts) > before:
                raise ProviderError(safe_error(error), self.client.http.receipts[-1]) from None
            raise
        metadata = dict(self.client.http.receipts[-1])
        metadata["schema_sha256"] = digest(encode(self.client.tools["screener_run"]["inputSchema"]).encode())
        return data, metadata


class RequestBudget:
    """Serial pacing, call/byte ceilings, bounded recovery and a quota stop.

    No guessed provider credits. A 429 ends this run, preserving Retry-After
    in the transport receipt; the engine does not sleep and retry the denial.
    """
    def __init__(self, max_calls=8, *, retry_calls=2, interval_seconds=1,
                 max_response_bytes=8 * 1024 * 1024, clock=time.monotonic, sleeper=time.sleep):
        if (type(max_calls) is not int or not 1 <= max_calls <= 40 or type(retry_calls) is not int
                or not 0 <= retry_calls <= max_calls or not 0 <= interval_seconds <= 10
                or type(max_response_bytes) is not int or max_response_bytes <= 0):
            raise ContractError("SCREEN_BUDGET_REQUIRED")
        self.max_calls, self.retry_limit = max_calls, retry_calls
        self.interval, self.byte_limit = interval_seconds, max_response_bytes
        self.clock, self.sleeper = clock, sleeper
        self.calls = self.retries = self.bytes = 0
        self.last_started = None
        self.stopped_reason = None

    def acquire(self, recovery=False):
        if self.stopped_reason:
            raise ProviderError(self.stopped_reason)
        if self.calls >= self.max_calls or (recovery and self.retries >= self.retry_limit):
            raise ProviderError("REQUEST_BUDGET_EXHAUSTED")
        if self.bytes >= self.byte_limit:
            self.stopped_reason = "RESPONSE_BYTE_BUDGET_EXHAUSTED"
            raise ProviderError(self.stopped_reason)
        if self.last_started is not None:
            delay = self.interval - (self.clock() - self.last_started)
            if delay > 0:
                self.sleeper(delay)
        self.last_started = self.clock()
        self.calls += 1
        self.retries += int(recovery)

    def record(self, metadata):
        self.bytes += metadata.get("response_bytes") or 0

    def stop(self, reason):
        self.stopped_reason = reason

    def report(self):
        return {"screen_requests_attempted": self.calls, "recovery_requests": self.retries,
            "screen_response_bytes": self.bytes, "screen_request_limit": self.max_calls,
            "min_request_interval_seconds": self.interval, "concurrency": 1,
            "stopped_reason": self.stopped_reason, "charged_quota_units": None,
            "sustainable_cadence": "UNQUALIFIED", "scheduling_enabled": False}


def failed_receipt(names, pack, reason, metadata=None):
    metadata = metadata or {}
    return ScanBatchReceipt("basis", pack.id, pack.timeframe, tuple(names),
        failed_symbols={n: reason for n in names}, provider_error=reason,
        response_bytes=metadata.get("response_bytes") or 0, elapsed_ms=metadata.get("elapsed_ms") or 0,
        source_hash=metadata.get("response_sha256"))


def normalize_screen(names, data, metadata, *, pack, instruments, cutoff):
    """Validate the exact response contract before admitting any scalar.

    Aggregate provider counts include fillers. They cannot certify any missing
    requested ID. Truncated partitions contribute zero qualified observations.
    """
    if not isinstance(data, dict):
        raise ContractError("SCREEN_SCHEMA")
    rules = data.get("rules")
    if (not isinstance(rules, list) or len(rules) != 1 or not isinstance(rules[0], dict)
            or not isinstance(rules[0].get("left"), dict) or not isinstance(rules[0].get("right"), dict)
            or not isinstance(rules[0].get("id"), str) or not rules[0]["id"]
            or rules[0].get("left", {}).get("kind") != "formula"
            or rules[0].get("left", {}).get("expression") != pack.expression
            or rules[0].get("operator") != "atOrAbove"
            or rules[0].get("right", {}).get("kind") != "constant"
            or number(rules[0].get("right", {}).get("value")) != 0):
        raise ContractError("RETURNED_FORMULA_MISMATCH")
    for key in ("screened", "evaluated", "returned", "matched", "couldNotEvaluate"):
        if type(data.get(key)) is not int or data[key] < 0:
            raise ContractError("SCREEN_COUNT_SCHEMA")
    if (data["screened"] != data["evaluated"] + data["couldNotEvaluate"]
            or data["matched"] > data["evaluated"] or data["returned"] > data["matched"]
            or (not data.get("truncated") and data["returned"] != data["matched"])):
        raise ContractError("SCREEN_HIDDEN_TRUNCATION_OR_COUNTS")
    # Finite nonnegative pass-through must return every evaluable row, regardless
    # of sort/rank. Empty or negative results cannot mean zero opportunities.
    if data["matched"] != data["evaluated"]:
        raise ContractError("FINITE_EXPORT_DROPPED_EVALUATED_ROWS")
    receipt = screen_receipt(names, data, timeframe=pack.timeframe, metadata=metadata)
    receipt = replace(receipt, method=pack.id)
    rows = {r["symbol"]: r for r in data["results"]}
    observed, valid, failed, cutoffs = [], [], dict(receipt.failed_symbols), {}
    width = WIDTHS[pack.timeframe]
    for name in receipt.evaluated_symbols:
        row = rows[name]
        end = receipt.source_cutoffs[name]
        reason = None
        try:
            value = number(row["values"][0]["left"])
            if (value < 0 or number(row["values"][0]["right"]) != 0
                    or row["values"][0].get("ruleId") != rules[0].get("id")
                    or row["values"][0].get("matched") is not True):
                reason = "INVALID_READING_SEMANTICS"
            elif utc(end) != utc(cutoff):
                reason = "STALE_SOURCE_CUTOFF" if utc(end) < utc(cutoff) else "AFTER_FROZEN_CUTOFF"
            if reason:
                failed[name] = reason
                continue
            start = (utc(end) - timedelta(seconds=width)).isoformat()
            # Output timestamp covers last closed bar. The 3-bar input history
            # is requested but not individually attested by screener_run.
            evidence = Evidence(id=digest((metadata["response_sha256"] + pack.formula_hash + name).encode()),
                instrument=instruments[name], measurement_id=pack.column_id, value=value, units=pack.units,
                timeframe=pack.timeframe, window_start_utc=start, window_end_utc=end,
                known_at_utc=metadata["received_at_utc"], available_at_utc=None,
                received_at_utc=metadata["received_at_utc"], provider="basis",
                source_scope="PROVIDER_REPORTED_BINANCE_FUTURES_IDENTITY_UNVERIFIED",
                source_schema_hash=metadata["schema_sha256"], source_response_hash=metadata["response_sha256"],
                formula_hash=pack.formula_hash, complete=False, verdict="SUPPORTED",
                fidelity=Fidelity.EXACT_REPORTED, temporal_status="CLOSED_CURRENT")
            observed.append({**asdict(evidence), "formula_version": pack.version,
                "implementation_feasibility": "NATIVE_REMOTE", "claim_qualification": "UNVERIFIED",
                "independent_source_accuracy": "UNVERIFIED", "history_status": "UNVERIFIED_PROVIDER_LOOKBACK",
                "required_closed_bars": pack.required_closed_bars, "requested_history_bars": 300,
                "observed_history_bars": None, "precision_absolute": pack.precision_absolute,
                "window_semantics": "LAST_OUTPUT_BAR; INPUT_HISTORY_NOT_ATTESTED",
                "strategy_predicate": False})
            valid.append(name)
            cutoffs[name] = end
        except (ContractError, KeyError, TypeError, ValueError):
            failed[name] = "INVALID_READING_SEMANTICS"
    receipt = replace(receipt, evaluated_symbols=tuple(valid), failed_symbols=failed, source_cutoffs=cutoffs)
    return receipt, observed


def calculation_report(receipt, pack, *, provider_counts=None):
    return {**asdict(receipt), "calculation_id": pack.column_id, "formula_version": pack.version,
        "formula_sha256": pack.formula_hash, "implementation_feasibility": "NATIVE_REMOTE",
        "fidelity": "EXACT_REPORTED", "qualification": "UNVERIFIED",
        "independent_source_accuracy": "UNVERIFIED", "valid_remote_core_evaluated": 0,
        "history_status": "UNVERIFIED_PROVIDER_LOOKBACK", "matched_symbols": list(receipt.evaluated_symbols),
        "missing_symbols": [n for n in receipt.requested_symbols if n not in receipt.returned_symbols],
        "provider_aggregate_counts_including_fillers": provider_counts,
        "zero_opportunities_established": False}


class PartitionEngine:
    def __init__(self, source: RemoteScreenSource, budget: RequestBudget, *, partition_size=50):
        partitions((), partition_size)
        self.source, self.budget, self.partition_size = source, budget, partition_size

    def run(self, inventory, pack, cutoff):
        instruments = {i.native_symbol: i for i in inventory.instruments}
        supported = tuple(n for n in inventory.symbols if n in pack.supported_symbols)
        unsupported = tuple(n for n in inventory.symbols if n not in pack.supported_symbols)
        attempts, effective, observations, dispatched = [], [], [], []

        def execute(names, recovery=False):
            metadata, data, acquired = {}, None, False
            try:
                self.budget.acquire(recovery)
                acquired = True
                dispatched.extend(names)
                data, metadata = self.source.screen(names, pack)
                self.budget.record(metadata)
                receipt, values = normalize_screen(names, data, metadata, pack=pack,
                    instruments=instruments, cutoff=cutoff)
            except (ContractError, KeyError, TypeError, ValueError, AttributeError, IndexError) as error:
                # Use fixed internal codes only; never serialize arbitrary remote
                # error text, session IDs, keys, or raw exception messages.
                code = safe_error(error)
                if isinstance(error, ProviderError) and error.receipt:
                    metadata = error.receipt
                    if acquired:
                        self.budget.record(metadata)
                receipt, values = failed_receipt(names, pack, code, metadata), []
                if code in {"HTTP_403", "HTTP_451", "HTTP_429", "ROUTE_DISABLED", "REQUEST_BUDGET_EXHAUSTED"}:
                    self.budget.stop(code)
            counts = ({key: data[key] if type(data.get(key)) is int and data[key] >= 0 else None
                       for key in ["screened", "evaluated", "matched", "returned", "couldNotEvaluate"]}
                      if isinstance(data, dict) else None)
            row_times = {}
            if isinstance(data, dict) and isinstance(data.get("results"), list):
                for row in data["results"]:
                    if isinstance(row, dict) and row.get("symbol") in names and type(row.get("observationTime")) is int:
                        row_times[row["symbol"]] = row["observationTime"]
            attempts.append({**calculation_report(receipt, pack, provider_counts=counts),
                "dispatched": acquired, "provider_reported_bar_open_seconds": row_times})
            # Tool failure or truncation gets finite smaller partitions. A known
            # denial, sparse function or missing ID never triggers an open loop.
            retryable = receipt.truncated or receipt.provider_error == "MCP_TOOL_ERROR"
            if (retryable and len(names) > 1 and not self.budget.stopped_reason
                    and self.budget.retries + 2 <= self.budget.retry_limit
                    and self.budget.calls + 2 <= self.budget.max_calls):
                split = len(names) // 2
                execute(names[:split], True)
                execute(names[split:], True)
            else:
                effective.append(receipt)
                observations.extend(values)

        for part in partitions(supported, self.partition_size):
            execute(part)
        evaluated = tuple(n for r in effective for n in r.evaluated_symbols)
        failures = {n: reason for r in effective for n, reason in r.failed_symbols.items()}
        failures.update({n: "UNVERIFIED_PROVIDER_SYMBOL_SCOPE" for n in unsupported})
        if set(evaluated) | set(failures) != set(inventory.symbols) or set(evaluated) & set(failures):
            raise ContractError("EFFECTIVE_PARTITION_ACCOUNTING")
        return {
            "pack_id": pack.id, "timeframe": pack.timeframe, "cutoff_utc": cutoff,
            "formula_version": pack.version, "formula_sha256": pack.formula_hash,
            "operating_scope": "NARROW_PROVIDER_REPORTED_OBSERVATION_ONLY",
            "inventory_mode": inventory.mode, "eligible_contracts": inventory.report()["eligible_contracts"],
            "provisionally_identified_contracts": list(inventory.provisional_symbols),
            "planned_symbols": list(inventory.symbols),
            "requested_symbols": list(dict.fromkeys(dispatched)),
            "not_requested_symbols": [n for n in inventory.symbols if n not in dispatched],
            "evaluated_symbols": list(evaluated), "failed_symbols": failures,
            "recognized_symbols": sorted({n for r in effective for n in r.recognized_symbols}),
            "returned_symbols": sorted({n for r in effective for n in r.returned_symbols}),
            "matched_symbols": list(evaluated),
            "missing_symbols": sorted({n for r in effective for n in r.requested_symbols
                                       if n in dispatched and n not in r.returned_symbols}),
            "provider_added_fillers": sorted({n for a in attempts for n in a["filler_symbols"]}),
            "truncated_attempts": sum(a["truncated"] for a in attempts),
            "source_cutoffs": {n: t for r in effective for n, t in r.source_cutoffs.items()},
            "valid_remote_core_evaluated": 0, "qualified_method_predicates_evaluated": 0,
            "calculation": pack.column_id, "calculation_coverage": [calculation_report(r, pack) for r in effective],
            "attempts": attempts, "observations": observations,
            "zero_opportunities_established": False,
        }


def safe_error(error):
    # Contract errors are all internal symbolic codes. Do not trust even an
    # exception's text unless it is one of those fixed codes.
    code = str(error)
    allowed = {
        "HTTP_403", "HTTP_451", "HTTP_429", "HTTP_500", "HTTP_502", "HTTP_503", "HTTP_504",
        "ROUTE_DISABLED", "REQUEST_BUDGET_EXHAUSTED", "RESPONSE_BYTE_BUDGET_EXHAUSTED",
        "NETWORK_OR_TLS_FAILURE", "RESPONSE_SIZE_LIMIT", "MCP_TOOL_ERROR", "MCP_RPC_ERROR",
        "MALFORMED_JSON", "MCP_ENVELOPE_MISMATCH", "MCP_TOOLS_SCHEMA", "READ_ONLY_ANNOTATION_CHANGED",
        "SCREEN_SCHEMA", "SCREEN_COUNT_SCHEMA", "SCREEN_COUNTS_INCONSISTENT", "DUPLICATE_PROVIDER_ROW",
        "SCREEN_SCOPE_MISMATCH", "RETURNED_FORMULA_MISMATCH", "SCREEN_HIDDEN_TRUNCATION_OR_COUNTS",
        "FINITE_EXPORT_DROPPED_EVALUATED_ROWS", "UNREGISTERED_FORMULA", "TOOL_ARGUMENT_SCHEMA",
        "RESEARCH_TOOL_NOT_ALLOWED", "MCP_PROTOCOL_OR_CAPABILITY", "MCP_DATA_OBJECT_REQUIRED",
        "INVENTORY_PROVENANCE_REQUIRED", "INVENTORY_FRESHNESS_POLICY", "INVENTORY_FUTURE_CAPTURE",
        "INVENTORY_NOT_KNOWN_AT_SCAN", "INVENTORY_JSON_INVALID", "INVENTORY_SIZE_LIMIT",
        "DUPLICATE_JSON_KEY", "NONSTANDARD_JSON_NUMBER", "EXCHANGE_INFO_SCHEMA",
        "EXCHANGE_INSTRUMENT_SCHEMA", "DUPLICATE_INVENTORY_SYMBOL", "INVALID_UTC", "UTC_OFFSET_REQUIRED",
        "INSTRUMENT_FILTER_SCHEMA", "DUPLICATE_OR_INVALID_FILTER", "QUANTITY_RANGE", "LISTING_TIME_INVALID",
        "NONFINITE_OR_NONPOSITIVE_NUMBER", "INVALID_NUMBER", "BOOLEAN_IS_NOT_NUMBER",
        "EXACT_NATIVE_SYMBOL_REQUIRED", "OUTPUT_MUST_BE_NEW_JSON_UNDER_WORK", "IMMUTABLE_REFERENCE_DRIFT",
    }
    return code if isinstance(error, ContractError) and code in allowed else "PROVIDER_OR_CONTRACT_FAILURE"


def coherent_observations(observations, *, timeframe, cutoff):
    """Explicit join guard for later consumers; no cross-timeframe time coercion."""
    selected = list(observations)
    if any(o["timeframe"] != timeframe or utc(o["window_end_utc"]) != utc(cutoff)
           or o["temporal_status"] != "CLOSED_CURRENT" for o in selected):
        raise ContractError("INCOHERENT_TEMPORAL_JOIN")
    return selected
