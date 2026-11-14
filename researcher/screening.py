"""Bounded, explicit remote partitions and auditable scalar observations.

The R0 path executes the registered finite width probe, not certified CORE or
strategy predicates. Full CORE requirements remain visible and disabled.
"""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
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
    columns: tuple = ()

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
            "rules": [{"left": {"kind": "formula", "expression": c[1]},
                       "operator": "atOrAbove", "right": 0}
                       for c in (pack.columns or ((pack.column_id,pack.expression,pack.units,pack.required_closed_bars),))]}
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
    if pack.columns:
        return normalize_columns(names,data,metadata,pack=pack,instruments=instruments,cutoff=cutoff)
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
            observed[-1]['source_closed_close']=row.get('last')
            valid.append(name)
            cutoffs[name] = end
        except (ContractError, KeyError, TypeError, ValueError):
            failed[name] = "INVALID_READING_SEMANTICS"
    receipt = replace(receipt, evaluated_symbols=tuple(valid), failed_symbols=failed, source_cutoffs=cutoffs)
    return receipt, observed


def normalize_columns(names,data,metadata,*,pack,instruments,cutoff):
    """Export compatible finite columns, reusing the scalar source validator.

    Missing/undefined columns invalidate that row's complete pack. No OR
    fallback can turn an unavailable input into a false detector result.
    """
    if (not isinstance(data,dict) or not isinstance(data.get('rules'),list)
            or len(data['rules'])!=len(pack.columns) or not isinstance(data.get('results'),list)):
        raise ContractError('SCREEN_SCHEMA')
    from .core import CORE, EXPORT_SCALE, export_expression
    from .pack_contracts import VERSION as ANALYTICAL_PACK_VERSION
    closes=[j for j,c in enumerate(pack.columns) if c[0]=='close' and c[1]==export_expression(CORE['close'].expression)]
    receipts=[];observed=[]
    for j,(label,expression,units,history) in enumerate(pack.columns):
        rows=[]
        for row in data['results']:
            if isinstance(row,dict) and row.get('symbol') not in names:
                # Fillers are never admitted observations. Their unavailable
                # optional values cannot poison requested-symbol arithmetic.
                readings=row.get('values',[])
                rows.append({**row,'values':readings[j:j+1] if isinstance(readings,list) else []})
                continue
            if not isinstance(row,dict) or not isinstance(row.get('values'),list) or len(row['values'])!=len(pack.columns):
                raise ContractError('SCREEN_SCHEMA')
            projected_row={**row,'values':[row['values'][j]]}
            if closes:
                close=number(row['values'][closes[0]]['left'],positive=True)/EXPORT_SCALE
                if abs(close-number(row['last']))>D('0.0000500001'):
                    raise ContractError('SOURCE_PRICE_MISMATCH')
                projected_row['last']=close
            rows.append(projected_row)
        projected={**data,'rules':[data['rules'][j]],'results':rows}
        scalar=replace(pack,columns=(),expression=expression,column_id=label,units=units,required_closed_bars=history)
        receipt,values=normalize_screen(names,projected,metadata,pack=scalar,instruments=instruments,cutoff=cutoff)
        if label in CORE and expression==export_expression(CORE[label].expression):
            values=[{**o,'value':number(o['value'])/EXPORT_SCALE,'encoded_provider_value':o['value'],
                'export_scale':EXPORT_SCALE,'precision_absolute':'1e-10',
                'export_rounding':'PROVIDER_4_DECIMALS_BEFORE_SCALE_DECODE'} for o in values]
            if label=='quote_rvol32':
                values=[{**o,'value':o['value']-1 if o['value']>0 else None,
                    'verdict':'SUPPORTED' if o['value']>0 else 'UNKNOWN',
                    'null_reason':None if o['value']>0 else 'ZERO_QUOTE_VOLUME_BASELINE',
                    'participation_not_required_for_price_family':True} for o in values]
        elif pack.version in {'packs-6a.1',ANALYTICAL_PACK_VERSION}:
            from .pack_contracts import column_by_export
            column=column_by_export(expression)
            if column:
                decoded=[]
                for o in values:
                    value=number(o['value'])/EXPORT_SCALE
                    if column.encoding=='POSITIVE_MINUS_ONE':value=value-1 if value>0 else None
                    decoded.append({**o,'value':value,'encoded_provider_value':o['value'],
                        'export_scale':EXPORT_SCALE,'verdict':'UNKNOWN' if value is None else 'SUPPORTED',
                        'null_reason':column.null if value is None else None,'production_qualified':False})
                values=decoded
        receipts.append(receipt);observed.extend(values)
    valid=set.intersection(*(set(r.evaluated_symbols) for r in receipts))
    errors={n:reason for r in receipts for n,reason in r.failed_symbols.items()}
    receipt=replace(receipts[0],evaluated_symbols=tuple(n for n in names if n in valid),
                    failed_symbols={n:errors.get(n,'INCOMPLETE_CORE_ROW') for n in names if n not in valid})
    return receipt,[o for o in observed if o['instrument']['native_symbol'] in valid]


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
    def __init__(self, source: RemoteScreenSource, budget: RequestBudget, *, partition_size=50,deferred_tool_recovery=False):
        partitions((), partition_size)
        self.source, self.budget, self.partition_size = source, budget, partition_size
        self.deferred_tool_recovery=deferred_tool_recovery

    def run(self, inventory, pack, cutoff):
        instruments = {i.native_symbol: i for i in inventory.instruments}
        supported = tuple(n for n in inventory.symbols if n in pack.supported_symbols)
        unsupported = tuple(n for n in inventory.symbols if n not in pack.supported_symbols)
        attempts, effective, observations, dispatched, pending = [], [], [], [], []

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
                if code in {"HTTP_403", "HTTP_451", "HTTP_429", "ROUTE_DISABLED", "REQUEST_BUDGET_EXHAUSTED", "PROVIDER_BUSY_COOLDOWN"}:
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
            if self.deferred_tool_recovery and not recovery and receipt.provider_error=='MCP_TOOL_ERROR' and not self.budget.stopped_reason:
                pending.append((names,receipt))
                return
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
        # Retry distinct transient-fault partitions after healthy work, rather
        # than spending both recovery credits on the first failing half-group.
        # Truncation still needs finite bisection. Never retry denials or clocks.
        for names,receipt in pending:
            if (not self.budget.stopped_reason and self.budget.retries<self.budget.retry_limit
                    and self.budget.calls<self.budget.max_calls):execute(names,True)
            else:effective.append(receipt)
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
            "recovery_policy":"DEFER_DISTINCT_TOOL_FAULTS; BISECT_TRUNCATION" if self.deferred_tool_recovery else "BOUNDED_BISECTION",
        }


def safe_error(error):
    # Contract errors are all internal symbolic codes. Do not trust even an
    # exception's text unless it is one of those fixed codes.
    code = str(error)
    allowed = {
        'PROVIDER_BUSY_COOLDOWN',
        'CLOSED_HISTORY_REQUIRED','CLOSED_BAR_CUTOFF_MISMATCH','ORACLE_FORMULA_NOT_IMPLEMENTED',
        'OFFLINE_SOURCE_UNAVAILABLE','OFFLINE_REPLAY_SCOPE','SOURCE_QUALIFICATION_CONTRACT',
        'LIVE_SOURCE_QUALIFICATION_REQUIRED','RESOURCE_PLAN_CONTRACT','NO_SAVED_RESEARCH_REPORT',
        'LOCAL_ONLY_ANALYTICAL_PROBE','EXACT_ELIGIBLE_CONTRACT_REQUIRED',
        'CUTOFF_AFTER_EVALUATION','SOURCE_NOT_AVAILABLE_AT_EVALUATION',
        'ZERO_OR_UNDEFINED_REFERENCE_ATR','BALANCE_BASELINE_WINDOW',
        'TAPE_SCOPE_OR_PROVENANCE','EXECUTED_TAPE_SEQUENCE_REQUIRED','TRADE_TICK_ALIGNMENT',
        'STRICT_TAPE_SCHEMA_REQUIRED','SOURCE_CAPABILITY_REQUIRED_COMPLETE_EXECUTED_TAPE',
        'PROFILE_BIN_OR_UNITS','NO_EXECUTED_TRADES_IN_WINDOW','BOUNDED_PROFILE_BIN_COUNT_REQUIRED',
        'SPECIALIST_ENVELOPE_SCOPE_OR_TIME','STRICT_SPECIALIST_ENVELOPE_SCHEMA',
        'TRUE_COMPLETE_PROFILE_REQUIRED','NAKED_POC_CONTIGUOUS_HISTORY_REQUIRED',
        'FOOTPRINT_TRIAL_PARAMETERS','COMPARABLE_REPEATED_ATTEMPTS_REQUIRED',
        'AGGRESSION_REFERENCE_BOUNDS','ATTEMPT_SCOPE_OR_ORDER','ATTEMPTS_DURATION_MISMATCH',
        'LIQUIDATION_COVERAGE_REQUIRED','FORCED_ORDER_IDENTITY_OR_WINDOW',
        'RESIDUAL_BASELINE_REQUIRED','OI_IDENTITY_UNITS_OR_MARK_ALIGNMENT',
        'FUNDING_KIND_OR_UNITS','FUNDING_ACTUAL_INTERVAL_REQUIRED','BASIS_CLOCK_ALIGNMENT',
        'CATALYST_SOURCE_OR_TIMES','UNKNOWN_METHODOLOGY','INDEPENDENT_CONFIRMED_IMPULSE_REQUIRED',
        'ZERO_IMPULSE','PRESELECTED_COMPLETED_CRT_REFERENCE_REQUIRED','PREDECLARED_SESSION_REQUIRED',
        'INCOMPLETE_SESSION_BALANCE','PRIMARY_TIMING_SOURCE_REQUIRED','TIMING_WINDOW',
        'PROFILE_MIGRATION_SCOPE_MISMATCH','DEPTH_IDENTITY_UNITS','STALE_DEPTH',
        'ORDERED_DEPTH_REQUIRED','SPECIALIST_METHOD_ADAPTER_REQUIRED','UNQUALIFIED_ANALYTICAL_ROUTE_A',
        'REGISTERED_DSL_NODE_REQUIRED','DSL_FIELD','DSL_POSITIVE_LAG','DSL_BOUNDED_WINDOW',
        'UNREGISTERED_DSL_OPERATION','DUPLICATE_PACK_COLUMN','PACK_DEPENDENCY_CYCLE',
        'PACK_DEPENDENCY_MISSING','SOURCE_CAPABILITY_REQUIRED','BUDGET_SCENARIO',
        'SESSION5_CAPABILITY_BOUNDARY','SOURCE_PRICE_MISMATCH','RESEARCH_DB_CORRUPT',
        'RESEARCH_DB_CORRUPT_OR_BUSY','RESEARCH_DB_VERSION_UNSUPPORTED','NOT_A_RESEARCH_DATABASE',
        'RESEARCH_WRITER_BUSY','RESEARCH_SNAPSHOT_CORRUPT','RESEARCH_CUTOFF_REGRESSION',
        'HISTORY_BEFORE_CURRENT_CONTRACT_LISTING','CONTRACT_IDENTITY_CHANGED',
        'TARGETED_BOUNDED_REF_REQUIRED',
        'FACT_PROVENANCE', 'BENCHMARK_HISTORY_REQUIRED', 'AMBIGUOUS_CONTEXT_SOURCE',
        'CONTEXT_STRUCTURE_SCHEMA', 'STRUCTURE_CARD_CONTRACT', 'NULL_AND_OPPOSING_RIVAL_REQUIRED',
        'CONFLICTING_STRUCTURE_DUPLICATE', 'AMBIGUOUS_RESEARCH_FACT', 'EVENT_NOT_AVAILABLE',
        'QUERY_CONTRACT', 'QUERY_BUDGET', 'QUERY_RESPONSE_SCOPE_OR_FRESHNESS',
        'MAX_SHORTLIST_FIVE', 'SPECIALIST_SCOPE_MISMATCH', 'SESSION4_CAPABILITY_BOUNDARY',
        'ANCHOR_NOT_PREDECLARED_OR_INCOMPLETE', 'BAR_AVAILABILITY_ORDER', 'BAR_PROVENANCE_OR_FORMING',
        'BOUNDED_CLOSED_SAMPLE_REQUIRED', 'BOUNDED_HISTORY_REQUIRED', 'DIRECTION_REQUIRED',
        'DUPLICATE_INVENTORY_SOURCE', 'DUPLICATE_INVENTORY_SYMBOL', 'DUPLICATE_JSON_KEY',
        'DUPLICATE_MARKET_ROW', 'DUPLICATE_OR_INVALID_FILTER', 'EVENT_CAUSAL_TIME',
        'EVENT_SOURCE_REQUIRED', 'EXCHANGE_INFO_SCHEMA', 'EXCHANGE_INSTRUMENT_SCHEMA',
        'FUTURE_BAR', 'HTTP_400', 'HTTP_418',
        'HYPOTHESIS_REFERENCE', 'HYPOTHESIS_UNKNOWN_EVIDENCE', 'IMMUTABLE_LEDGER_CONFLICT',
        'INCOMPLETE_TAIL_LIQUIDITY_DENOMINATOR', 'INCOMPLETE_UNIVERSE_CANNOT_BE_VERIFIED', 'INSTRUMENT_FILTER_SCHEMA',
        'INSUFFICIENT_HISTORY', 'INSUFFICIENT_INDEPENDENT_TAIL_MEMBERS', 'INVALID_TAKER_OR_VOLUME',
        'INVALID_VOLUME_UNITS', 'INVENTORY_FRESHNESS_POLICY', 'INVENTORY_FUTURE_CAPTURE',
        'INVENTORY_JSON_INVALID', 'INVENTORY_MEMBERSHIP', 'INVENTORY_MODE',
        'INVENTORY_NOT_KNOWN_AT_SCAN', 'INVENTORY_PROVENANCE_REQUIRED', 'INVENTORY_ROW_LIMIT',
        'INVENTORY_SIZE_LIMIT', 'INVENTORY_SOURCE_NOT_REGISTERED', 'KLINES_REQUIRE_VERIFIED_IDENTITY',
        'KLINE_CLOSE_SEMANTICS', 'KLINE_SCHEMA_OR_COUNT', 'LEDGER_MUST_BE_UNDER_WORK',
        'LEDGER_NONCHRONOLOGICAL_EVENT', 'LIFECYCLE_TIME_REGRESSION', 'LISTING_TIME_INVALID',
        'LIVE_INVENTORY_PARTIAL', 'MISSING_OR_MISALIGNED_BARS', 'NEGATIVE_VOLUME',
        'NONSTANDARD_JSON_NUMBER', 'OHLC_INCONSISTENT', 'ORACLE_FORMULA_NOT_IMPLEMENTED',
        'ORACLE_FORMULA_WINDOW_CHANGED', 'ORACLE_INCOMPLETE_INDEPENDENT_WINDOW', 'ORACLE_INSUFFICIENT_WARMUP',
        'ORACLE_SOURCE_CUTOFF_MISMATCH', 'ORACLE_SOURCE_IDENTITY', 'ORACLE_TAIL_CLOCK',
        'ORACLE_UNALIGNED_TAIL', 'PERCENTILE_BASELINE_LENGTH', 'PROVISIONAL_SYMBOL_SET',
        'QUANTITY_RANGE', 'RECORDED_BINANCE_ACCESS_DENIAL', 'REFERENCE_BAR_IDENTITY',
        'REFERENCE_BOUNDS', 'REFERENCE_CAUSAL_TIME', 'REFERENCE_IDENTITY_OR_BOUNDS',
        'REFERENCE_LIFECYCLE_STATE', 'REFERENCE_NOT_AVAILABLE', 'RELATIVE_ALIGNMENT',
        'SELECTED_SAMPLE_BUDGET_EXHAUSTED', 'STALE_OR_INCOMPLETE_BAR_TAIL', 'STALE_TAIL_INVENTORY',
        'STALE_TAIL_LIQUIDITY', 'SWING_TRIAL_WIDTH', 'TAIL_LIQUIDITY_SOURCE',
        'TAIL_REQUIRES_VERIFIED_INVENTORY_AND_LIQUIDITY', 'TIMEFRAME_UNSUPPORTED',
    } | {
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
