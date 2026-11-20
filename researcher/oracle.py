"""Tiny selected-tail arithmetic oracle, never an operational market scanner.

These checks compare independent arithmetic with one provider's own returned
prices. They cannot independently authenticate the source or ATR seed/history.
"""
from decimal import Decimal
from .contracts import ContractError, number


def check_tail_fixture(fixture):
    series = fixture["series"]
    times = series["close"]["tailTimes"]
    if len(times) < 4 or any(b - a != 3600 for a, b in zip(times, times[1:])):
        raise ContractError("ORACLE_TAIL_CLOCK")
    for name in ["high", "low", "volume", "width", "prior_high", "prior_low", "lag", "median",
                 "quantile", "atr", "prior_compare", "flow_identity"]:
        if series[name].get("tailTimes") != times or len(series[name].get("tail", [])) != len(times):
            raise ContractError("ORACLE_UNALIGNED_TAIL")
    prices = {name: [number(v) for v in series[name]["tail"]] for name in ["close", "high", "low"]}
    c, h, l = [prices[name] for name in ["close", "high", "low"]]
    checks = {}

    def compare(name, expected, start, tolerance=Decimal("1e-9")):
        observed = series[name]["tail"][start:]
        errors = [abs(number(actual) - reference) for actual, reference in zip(observed, expected)]
        if len(errors) != len(times) - start:
            raise ContractError("ORACLE_EXPECTED_LENGTH")
        checks[name] = {"comparisons": len(errors), "max_absolute_error": str(max(errors)),
                        "absolute_tolerance": str(tolerance), "passed": all(e <= tolerance for e in errors)}

    compare("width", [(max(h[i-2:i+1])-min(l[i-2:i+1]))/c[i] for i in range(2,len(c))], 2, Decimal("1e-12"))
    compare("prior_high", [max(h[i-3:i]) for i in range(3,len(c))], 3)
    compare("prior_low", [min(l[i-3:i]) for i in range(3,len(c))], 3)
    compare("lag", c[:-1], 1)
    medians = [sorted(c[i-2:i+1])[1] for i in range(2,len(c))]
    compare("median", medians, 2)
    compare("quantile", medians, 2)  # odd length, q=.5 only; not general interpolation proof
    compare("prior_compare", [Decimal(int(c[i]>c[i-1])) for i in range(1,len(c))], 1)
    atr = [number(v) for v in series["atr"]["tail"]]
    conditional = [(13*atr[i-1]+max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])))/14
                   for i in range(1,len(c))]
    compare("atr", conditional, 1)
    checks["atr"]["limit"] = "RECURRENCE_ONLY_VENDOR_INITIAL_SEED_NOT_INDEPENDENTLY_TESTED"
    compare("flow_identity", [Decimal(0)]*len(c), 0, Decimal("1e-9"))
    for name in ["no_event_bars", "no_event_value"]:
        checks[name] = {"comparisons": 1, "passed": series[name].get("defined") == 0 and not series[name].get("tail"),
                        "limit": "UNDEFINED_OUTPUT_NOT_ZERO; OBSERVED_WINDOW_ONLY"}
    return {"classification": "SAME_SOURCE_INDEPENDENT_ARITHMETIC_ONLY",
            "independent_source_oracle": "BLOCKED_BINANCE_HTTP_451", "checks": checks,
            "numeric_comparisons": sum(c["comparisons"] for c in checks.values()),
            "all_checks_passed": all(c["passed"] for c in checks.values()),
            "does_not_qualify": ["exchange authenticity", "volume units", "ATR seed", "general quantile convention",
                                 "causal multi-event lifecycle", "quiet tail", "historical arbitrary as_of"]}
