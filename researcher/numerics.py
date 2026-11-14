"""Blueprint §6 deterministic primitives for small selected verification samples.

No network, symbol enumeration or candle persistence. Prices/volumes are Decimal;
missing history raises an explicit ContractError instead of inventing a value.
"""
from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from functools import cached_property
from .contracts import ContractError, digest, encode, number, symbol, utc
from .observations import WIDTHS, iso_seconds

D = Decimal
ZERO = D(0)


@dataclass(frozen=True)
class Bar:
    native_symbol: str
    timeframe: str
    open_ms: int
    open: D
    high: D
    low: D
    close: D
    base_volume: D
    quote_volume: D
    buy_base: D
    buy_quote: D
    trades: int
    source_hash: str
    received_at: str
    volume_units: str = "BASE_ASSET_AND_USDT_QUOTE"
    available_at: str | None = None

    @property
    def end_ms(self):
        return self.open_ms + WIDTHS[self.timeframe] * 1000

    @property
    def end(self):
        return iso_seconds(self.end_ms // 1000)

    @cached_property
    def id(self):
        # Stable across retrievals and appended future data, with exact identity.
        return digest(encode([self.native_symbol, self.timeframe, self.open_ms,
            self.open, self.high, self.low, self.close, self.base_volume,
            self.quote_volume, self.buy_base, self.buy_quote, self.trades]).encode())


def validate_bars(bars, *, cutoff=None, require_current=False):
    if not bars or len(bars) > 300:
        raise ContractError("BOUNDED_HISTORY_REQUIRED")
    first = bars[0]
    symbol(first.native_symbol)
    if first.timeframe not in WIDTHS:
        raise ContractError("TIMEFRAME_UNSUPPORTED")
    width = WIDTHS[first.timeframe] * 1000
    for i, b in enumerate(bars):
        if (b.native_symbol != first.native_symbol or b.timeframe != first.timeframe
                or type(b.open_ms) is not int or b.open_ms <= 0 or b.open_ms % width
                or (i and b.open_ms != bars[i-1].end_ms)):
            raise ContractError("MISSING_OR_MISALIGNED_BARS")
        o, h, l, c = [number(v, positive=True) for v in (b.open, b.high, b.low, b.close)]
        if h < max(o, c, l) or l > min(o, c, h):
            raise ContractError("OHLC_INCONSISTENT")
        if b.volume_units != "BASE_ASSET_AND_USDT_QUOTE":
            raise ContractError("INVALID_VOLUME_UNITS")
        v, q, bv, bq = [number(v) for v in (b.base_volume, b.quote_volume, b.buy_base, b.buy_quote)]
        if (min(v, q, bv, bq) < 0 or bv > v or bq > q
                or type(b.trades) is not int or b.trades < 0
                or (v == 0) != (q == 0)):
            raise ContractError("INVALID_TAKER_OR_VOLUME")
        if not b.source_hash or utc(b.received_at) < utc(b.end):
            raise ContractError("BAR_PROVENANCE_OR_FORMING")
        if b.available_at and not utc(b.end) <= utc(b.available_at) <= utc(b.received_at):
            raise ContractError("BAR_AVAILABILITY_ORDER")
        if cutoff and utc(b.end) > utc(cutoff):
            raise ContractError("FUTURE_BAR")
    if require_current and (not cutoff or utc(bars[-1].end) != utc(cutoff)):
        raise ContractError("STALE_OR_INCOMPLETE_BAR_TAIL")
    return bars


def parse_klines(rows, *, native_symbol, timeframe, cutoff, receipt, requested_bars):
    if (not isinstance(rows, list) or not rows or len(rows) > requested_bars
            or not 1 <= requested_bars <= 300):
        raise ContractError("KLINE_SCHEMA_OR_COUNT")
    bars = []
    for r in rows:
        if not isinstance(r, list) or len(r) != 12 or type(r[0]) is not int or type(r[6]) is not int:
            raise ContractError("KLINE_SCHEMA_OR_COUNT")
        if r[6] != r[0] + WIDTHS[timeframe] * 1000 - 1:
            raise ContractError("KLINE_CLOSE_SEMANTICS")
        b = Bar(native_symbol, timeframe, r[0], *[number(r[j]) for j in (1,2,3,4,5,7,9,10)],
                r[8], receipt["response_sha256"], receipt["received_at_utc"])
        bars.append(b)
    validate_bars(bars, cutoff=cutoff, require_current=True)
    return bars


def require_count(items, n):
    if type(n) is not int or n <= 0 or len(items) < n:
        raise ContractError("INSUFFICIENT_HISTORY")


def true_ranges(bars):
    validate_bars(bars)
    return [None] + [max(b.high-b.low, abs(b.high-p.close), abs(b.low-p.close))
                    for p, b in zip(bars, bars[1:])]


def wilder_atr(bars, n=14):
    require_count(bars, n+1)
    tr = true_ranges(bars)
    out = [None] * len(bars)
    out[n] = sum(tr[1:n+1], ZERO) / n
    for i in range(n+1, len(bars)):
        out[i] = ((n-1)*out[i-1] + tr[i]) / n
    return out


def normalized_width(bars, n=16, tick=D("0.00000001")):
    validate_bars(bars)
    require_count(bars, n)
    tick = number(tick, positive=True)
    tail = bars[-n:]
    return (max(b.high for b in tail)-min(b.low for b in tail))/max(bars[-1].close, tick)


def past_percentile(value, baseline, *, required=128):
    require_count(baseline, required)
    if len(baseline) != required:
        raise ContractError("PERCENTILE_BASELINE_LENGTH")
    value = number(value)
    baseline = [number(v) for v in baseline]
    return (sum(v < value for v in baseline) + D("0.5")*sum(v == value for v in baseline))/required


def compression(bars, n=16, baseline=128, tick=D("0.00000001")):
    # Entire measured n-bar window excluded from historical reference windows.
    validate_bars(bars)
    require_count(bars, 2*n+baseline-1)
    tick=number(tick,positive=True)
    stop = len(bars)-n
    def width_at(end):
        window=bars[end-n:end]
        return (max(b.high for b in window)-min(b.low for b in window))/max(bars[end-1].close,tick)
    previous = [width_at(end) for end in range(stop-baseline+1, stop+1)]
    value = width_at(len(bars))
    return {"width": value, "past_percentile": past_percentile(value, previous, required=baseline),
            "baseline_windows": baseline, "measured_window_excluded": True}


def efficiency(bars, n=16):
    validate_bars(bars)
    require_count(bars, n+1)
    c = [b.close for b in bars[-n-1:]]
    denominator = sum((abs(b-a) for a,b in zip(c,c[1:])), ZERO)
    return abs(c[-1]-c[0])/denominator if denominator else None


def overlap(previous, current, tick):
    validate_bars([previous,current])
    return max(ZERO, min(previous.high,current.high)-max(previous.low,current.low))/max(
        min(previous.high-previous.low, current.high-current.low), number(tick,positive=True))


def displacement(previous, current, atr_previous, tick):
    validate_bars([previous,current])
    atr_previous, tick = number(atr_previous,positive=True), number(tick,positive=True)
    span = max(current.high-current.low,tick)
    tr = max(current.high-current.low, abs(current.high-previous.close), abs(current.low-previous.close))
    return {"tr_atr_previous": tr/atr_previous, "body_fraction": abs(current.close-current.open)/span,
            "close_location": (current.close-current.low)/span,
            "signed_progress_atr": (current.close-previous.close)/atr_previous}


def confirmed_swings(bars, *, left=2, right=2):
    validate_bars(bars)
    if left not in {2,3,4} or right not in {2,3,4}:
        raise ContractError("SWING_TRIAL_WIDTH")
    out = []
    for k in range(left,len(bars)-right):
        for kind, field, above in [("SWING_HIGH","high",True),("SWING_LOW","low",False)]:
            p = getattr(bars[k],field)
            before = [getattr(b,field) for b in bars[k-left:k]]
            after = [getattr(b,field) for b in bars[k+1:k+right+1]]
            yes = (p>max(before) and p>=max(after)) if above else (p<min(before) and p<=min(after))
            if yes:
                out.append({"kind":kind,"price":p,"pivot_bar_id":bars[k].id,"index":k,
                    "known_index":k+right,"known_at":bars[k+right].end,
                    "available_at":bars[k+right].available_at,
                    "id":digest(encode([kind,bars[k].id,left,right]).encode())})
    return sorted(out,key=lambda x:(x["known_index"],x["kind"]))


def swing_ladder(swings):
    highs=[s for s in swings if s["kind"]=="SWING_HIGH"]
    lows=[s for s in swings if s["kind"]=="SWING_LOW"]
    if len(highs)<2 or len(lows)<2:
        return "UNKNOWN"
    h,l=highs[-2:],lows[-2:]
    if h[-1]["price"]>h[0]["price"] and l[-1]["price"]>l[0]["price"]:
        return "HH_HL"
    if h[-1]["price"]<h[0]["price"] and l[-1]["price"]<l[0]["price"]:
        return "LH_LL"
    return "MIXED"


def distance(price, lo, hi, atr):
    price,lo,hi=[number(v) for v in (price,lo,hi)]
    if lo>hi: raise ContractError("REFERENCE_BOUNDS")
    return max(lo-price,price-hi,ZERO)/number(atr,positive=True)


def first_obstacle(price, direction, references, *, at, native_symbol, timeframe):
    price=number(price,positive=True)
    if direction not in {-1,1}: raise ContractError("DIRECTION_REQUIRED")
    valid=[]
    for r in references:
        if r.native_symbol!=native_symbol or r.timeframe!=timeframe:
            raise ContractError("OBSTACLE_IDENTITY_MISMATCH")
        if utc(r.known_at)>utc(at) or utc(r.available_at)>utc(at) or utc(r.valid_until)<utc(at):
            continue
        edge=r.lo if direction==1 else r.hi
        if direction*(edge-price)>0: valid.append((abs(edge-price),r.id))
    return min(valid) if valid else None


def touch_episodes(bars, *, lo, hi, atr, buffer, retreat=D("0.5")):
    validate_bars(bars)
    atr,buffer,retreat=number(atr,positive=True),number(buffer),number(retreat,positive=True)
    if buffer<0 or lo>hi: raise ContractError("REFERENCE_BOUNDS")
    armed=True
    episodes=[]
    for b in bars:
        touched=b.high>=lo-buffer and b.low<=hi+buffer
        if touched and armed:
            episodes.append({"bar_id":b.id,"known_at":b.end})
            armed=False
        # A later fully separated bar is needed: no same-bar retreat ordering.
        elif not touched and max(lo-b.high,b.low-hi,ZERO)>=retreat*atr:
            armed=True
    return episodes


def relative_quote_volume(bars, n=32):
    validate_bars(bars)
    require_count(bars,n+1)
    baseline=median(b.quote_volume for b in bars[-n-1:-1])
    return bars[-1].quote_volume/baseline if baseline>0 else None


def bar_delta(bar):
    validate_bars([bar])
    q,b=bar.quote_volume,bar.base_volume
    return {"delta_quote":2*bar.buy_quote-q,"delta_base":2*bar.buy_base-b,
            "imbalance_quote":(2*bar.buy_quote-q)/q if q else None,
            "fidelity":"EXCHANGE_REPORTED_BAR_AGGRESSOR","footprint":False}


def anchored_value(bars, *, anchor_ms, anchor_known_at):
    validate_bars(bars)
    if (bars[0].open_ms!=anchor_ms or utc(anchor_known_at).timestamp()*1000>anchor_ms):
        raise ContractError("ANCHOR_NOT_PREDECLARED_OR_INCOMPLETE")
    base=sum((b.base_volume for b in bars),ZERO)
    return {"vwap_whole_bars":sum((b.quote_volume for b in bars),ZERO)/base if base else None,
            "cvd_quote":sum((2*b.buy_quote-b.quote_volume for b in bars),ZERO),
            "exact_trade_weighted_variance":None,"true_profile":False}


def relative_return(asset, benchmark, *, horizon=16):
    require_count(asset,horizon+1); require_count(benchmark,horizon+1)
    validate_bars(asset);validate_bars(benchmark)
    if [(b.timeframe,b.open_ms) for b in asset]!=[(b.timeframe,b.open_ms) for b in benchmark]:
        raise ContractError("RELATIVE_ALIGNMENT")
    ra=(asset[-1].close/asset[-horizon-1].close).ln()
    rb=(benchmark[-1].close/benchmark[-horizon-1].close).ln()
    return ra-rb


def lag_trained_beta(asset, benchmark, n=32):
    require_count(asset,n+2);require_count(benchmark,n+2)
    relative_return(asset,benchmark,horizon=1)
    a=[(b.close/p.close).ln() for p,b in zip(asset,asset[1:])][-n-1:]
    b=[(c.close/p.close).ln() for p,c in zip(benchmark,benchmark[1:])][-n-1:]
    ya,xb=a[:-1],b[:-1]
    my,mx=sum(ya,ZERO)/n,sum(xb,ZERO)/n
    var=sum(((x-mx)**2 for x in xb),ZERO)
    if not var:return None
    beta=sum(((x-mx)*(y-my) for x,y in zip(xb,ya)),ZERO)/var
    alpha=my-beta*mx
    return {"beta":beta,"alpha":alpha,"residual":a[-1]-alpha-beta*b[-1],
            "training_end":asset[-2].end,"evaluation_end":asset[-1].end,"n":n}


def selected_measurements(bars, tick):
    validate_bars(bars)
    result={"sample_bars":len(bars),"cutoff":bars[-1].end,"precision":"DECIMAL_SOURCE_PRICES",
            "execution_scope":"LOCAL_SELECTED_VERIFICATION_ONLY","availability":"EARLIEST_PUBLICATION_UNKNOWN"}
    calls={"atr14":lambda:wilder_atr(bars)[-1],"width16":lambda:normalized_width(bars,16,tick),"width3":lambda:normalized_width(bars,3,tick),
           "compression16_128":lambda:compression(bars,16,128,tick),"efficiency16":lambda:efficiency(bars),
           "quote_rvol32":lambda:relative_quote_volume(bars),"delta":lambda:bar_delta(bars[-1]),
           "swings":lambda:confirmed_swings(bars),
           "overlap":lambda:overlap(bars[-2],bars[-1],tick)}
    for key,fn in calls.items():
        try: result[key]={"status":"COMPUTED","value":fn()}
        except (ContractError,IndexError):result[key]={"status":"INSUFFICIENT_HISTORY","value":None}
    return result
