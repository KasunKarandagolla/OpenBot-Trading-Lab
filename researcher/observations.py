"""Validate the narrow observed Basis candle/screen contracts, not detectors."""
from datetime import datetime, timedelta, timezone
from .contracts import ContractError, Evidence, Fidelity, Instrument, ScanBatchReceipt, number, symbol, utc

WIDTHS = {"15m": 900, "1h": 3600}


def iso_seconds(value):
    if type(value) is not int or value < 0:
        raise ContractError("BAR_TIME_SECONDS_REQUIRED")
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def candle_observation(data, *, requested_symbol, timeframe, received_at, schema_hash, response_hash):
    symbol(requested_symbol)
    width = WIDTHS[timeframe]
    if (data.get("symbol") != requested_symbol or data.get("exchange") != "binance"
            or data.get("market") != "futures" or data.get("timeframe") != timeframe):
        raise ContractError("PROVIDER_INSTRUMENT_MISMATCH")
    if type(data.get("closedBars")) is not int or not 1 <= data["closedBars"] <= 65:
        raise ContractError("CLOSED_HISTORY_REQUIRED")
    bar = data["lastClosedCandle"]
    start = utc(iso_seconds(bar["time"]))
    if bar["time"] % width:
        raise ContractError("BAR_OPEN_ALIGNMENT")
    end = start + timedelta(seconds=width)
    source = data["evidence"]
    loaded, received = utc(source["loadedAtUtc"]), utc(received_at)
    if (source.get("barSeconds") != width or utc(source["asOfUtc"]) != end
            or loaded < end or loaded > received or end > received):
        raise ContractError("CLOSED_BAR_CUTOFF_MISMATCH")
    o, h, l, c = [number(bar[k], positive=True) for k in ("open", "high", "low", "close")]
    if h < max(o, l, c) or l > min(o, h, c) or number(data["lastClose"]) != c or number(source["lastClose"]) != c:
        raise ContractError("OHLC_INCONSISTENT")
    # 'fresh' is provider language. Own time test checks latest completed window.
    stale = (received - end).total_seconds() >= width
    instrument = Instrument(requested_symbol, "BINANCE_USDM", identity_status="UNVERIFIED")
    return Evidence(
        id="basis:" + response_hash, instrument=instrument,
        measurement_id="PROVIDER_REPORTED_CLOSED_CLOSE", value=c,
        units="USDT_PER_NATIVE_CONTRACT_PRICE_UNIT_PROVIDER_REPORTED",
        timeframe=timeframe, window_start_utc=start.isoformat(), window_end_utc=end.isoformat(),
        # Earliest publication is unknown. loadedAt is only a conservative known-by time.
        known_at_utc=loaded.isoformat(), available_at_utc=None, received_at_utc=received_at,
        provider="basis", source_scope="PROVIDER_REPORTED_BINANCE_FUTURES_IDENTITY_UNVERIFIED",
        source_schema_hash=schema_hash, source_response_hash=response_hash,
        formula_hash=None, complete=True, verdict="SUPPORTED", fidelity=Fidelity.EXACT_REPORTED,
        temporal_status="CLOSED_STALE" if stale else "CLOSED_CURRENT")


def screen_receipt(requested, data, *, timeframe, metadata):
    """Provider-reported scalar execution only, never certified method coverage.

    Do not distribute an aggregate evaluated count across missing identities.
    Truncation invalidates the partition for qualified coverage.
    """
    requested = tuple(requested)
    if len(requested) != len(set(requested)):
        raise ContractError("DUPLICATE_REQUEST")
    for name in requested:
        symbol(name)
    if data.get("exchange") != "binance" or data.get("market") != "futures" or data.get("quote") != "USDT" or data.get("timeframe") != timeframe:
        raise ContractError("SCREEN_SCOPE_MISMATCH")
    rows = data.get("results")
    if not isinstance(rows, list) or type(data.get("truncated")) is not bool:
        raise ContractError("SCREEN_SCHEMA")
    names = [symbol(row["symbol"]) for row in rows]
    if len(names) != len(set(names)):
        raise ContractError("DUPLICATE_PROVIDER_ROW")
    if (type(data.get("returned")) is not int or data["returned"] != len(rows)
            or type(data.get("evaluated")) is not int or data["evaluated"] < len(rows)
            or data.get("screened", -1) < data["evaluated"]):
        raise ContractError("SCREEN_COUNTS_INCONSISTENT")
    returned = tuple(n for n in names if n in requested)
    evaluated, failed, cutoffs = [], {}, {}
    for native in requested:
        row = next((r for r in rows if r["symbol"] == native), None)
        reason = None
        if row is None:
            reason = "MISSING_ID_NO_EVALUATION_PROOF"
        elif data["truncated"]:
            reason = "TRUNCATED_PARTITION"
        else:
            try:
                number(row["last"], positive=True)
                readings = row["values"]
                if len(readings) != len(data["rules"]):
                    raise ContractError("MISSING_READING")
                for reading in readings:
                    number(reading["left"])
                    number(reading["right"])
                observed = row["observationTime"]
                if type(observed) is not int or observed % WIDTHS[timeframe]:
                    raise ContractError("SCREEN_CLOCK")
                end = utc(iso_seconds(observed)) + timedelta(seconds=WIDTHS[timeframe])
                if end > utc(metadata["received_at_utc"]):
                    raise ContractError("FORMING_OR_FUTURE_SCREEN")
                cutoffs[native] = end.isoformat()
            except (ContractError, KeyError, TypeError):
                reason = "INVALID_SCALAR_OR_CLOCK"
        if reason:
            failed[native] = reason
        else:
            evaluated.append(native)
    return ScanBatchReceipt(
        "basis", "UNQUALIFIED_FINITE_SCALAR_PROBE", timeframe, requested,
        evaluated_symbols=tuple(evaluated), returned_symbols=returned, failed_symbols=failed,
        filler_symbols=tuple(n for n in names if n not in requested),
        recognized_symbols=returned, source_cutoffs=cutoffs, truncated=data["truncated"],
        response_bytes=metadata["response_bytes"], elapsed_ms=metadata["elapsed_ms"],
        source_hash=metadata["response_sha256"])
