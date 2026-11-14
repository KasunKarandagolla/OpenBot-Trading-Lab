"""Strict executed-data adapters and deterministic specialist reducers.

No network or implicit OHLC conversion. These algorithms do not establish a
provider's entitlement, tape completeness, or Binance production capability.
"""
from dataclasses import dataclass
from decimal import Decimal as D, ROUND_FLOOR
from .contracts import ContractError, number, symbol, utc, digest, encode

VERSION = 'executed-specialists-6a.1'


@dataclass(frozen=True)
class SpecialistEnvelope:
    native_symbol: str
    venue: str
    contract_type: str
    units: str
    start: str
    end: str
    known_at: str
    available_at: str
    received_at: str
    source_hash: str
    coverage: str
    mode: str
    payload: dict

    def __post_init__(self):
        symbol(self.native_symbol)
        if (self.venue!='BINANCE_USDM' or self.contract_type!='LINEAR_USDT_PERPETUAL'
                or not self.units or not self.source_hash or not isinstance(self.payload,dict)
                or self.coverage not in {'COMPLETE','PARTIAL','SAMPLED','MODELED'}
                or self.mode not in {'LIVE','AUTHENTIC_REPLAY','SYNTHETIC'}
                or not utc(self.start)<utc(self.end)<=utc(self.known_at)<=utc(self.available_at)<=utc(self.received_at)):
            raise ContractError('SPECIALIST_ENVELOPE_SCOPE_OR_TIME')


def adapt_specialist(raw):
    if not isinstance(raw,dict) or set(raw)!=set(SpecialistEnvelope.__dataclass_fields__):
        raise ContractError('STRICT_SPECIALIST_ENVELOPE_SCHEMA')
    return SpecialistEnvelope(**raw)


@dataclass(frozen=True)
class Trade:
    id: str
    at: str
    price: D
    base: D
    aggressor: str

    def __post_init__(self):
        object.__setattr__(self,'price',number(self.price,positive=True))
        object.__setattr__(self,'base',number(self.base,positive=True))


@dataclass(frozen=True)
class TapeWindow:
    native_symbol: str
    venue: str
    contract_type: str
    start: str
    end: str
    available_at: str
    received_at: str
    source_hash: str
    coverage: str
    tick: D
    trades: tuple[Trade, ...]
    mode: str
    units: str = 'BASE_ASSET'

    def __post_init__(self):
        symbol(self.native_symbol)
        if (not self.venue or self.contract_type != 'LINEAR_USDT_PERPETUAL' or not self.source_hash
                or self.units != 'BASE_ASSET' or self.coverage not in {'COMPLETE','PARTIAL','SAMPLED'}
                or self.mode not in {'SYNTHETIC','AUTHENTIC_REPLAY','LIVE'}
                or not utc(self.start) < utc(self.end) <= utc(self.available_at) <= utc(self.received_at)):
            raise ContractError('TAPE_SCOPE_OR_PROVENANCE')
        tick = number(self.tick, positive=True)
        object.__setattr__(self,'tick',tick)
        ids = set(); prior = utc(self.start)
        for t in self.trades:
            if (not isinstance(t, Trade) or not t.id or t.id in ids or t.aggressor not in {'BUY','SELL'}
                    or not prior <= utc(t.at) < utc(self.end)):
                raise ContractError('EXECUTED_TAPE_SEQUENCE_REQUIRED')
            p = number(t.price, positive=True); number(t.base, positive=True)
            if p % tick:
                raise ContractError('TRADE_TICK_ALIGNMENT')
            prior = utc(t.at); ids.add(t.id)

    def require_complete(self):
        if self.coverage != 'COMPLETE':
            raise ContractError('SOURCE_CAPABILITY_REQUIRED_COMPLETE_EXECUTED_TAPE')

    @property
    def id(self):
        return digest(encode(self).encode())


def adapt_tape(raw):
    """Strict schema. An OHLC row, composite or missing coverage cannot pass."""
    fields = set(TapeWindow.__dataclass_fields__)
    if not isinstance(raw, dict) or set(raw) != fields:
        raise ContractError('STRICT_TAPE_SCHEMA_REQUIRED')
    data = dict(raw)
    data['trades'] = tuple(Trade(**r) for r in data['trades'])
    return TapeWindow(**data)


def price_bins(tape, *, width, origin=D(0), units='BASE_ASSET'):
    tape.require_complete()
    width = number(width, positive=True); origin = number(origin)
    if width % tape.tick or origin % tape.tick or units not in {'BASE_ASSET','USDT_QUOTE'}:
        raise ContractError('PROFILE_BIN_OR_UNITS')
    volumes = {}
    for t in tape.trades:
        k = int(((t.price-origin)/width).to_integral_value(rounding=ROUND_FLOOR))
        v = t.base if units == 'BASE_ASSET' else t.base*t.price
        row = volumes.setdefault(k, {'BUY':D(0), 'SELL':D(0)})
        row[t.aggressor] += v
    if not volumes:
        raise ContractError('NO_EXECUTED_TRADES_IN_WINDOW')
    if max(volumes)-min(volumes) > 10000:
        raise ContractError('BOUNDED_PROFILE_BIN_COUNT_REQUIRED')
    return {k: volumes.get(k, {'BUY':D(0),'SELL':D(0)}) for k in range(min(volumes), max(volumes)+1)}


def trade_value(tape):
    """Actual executed first and second moments, distinct from bar residuals."""
    tape.require_complete()
    volume=sum((t.base for t in tape.trades),D(0))
    if not volume:return {'status':'SOURCE_UNKNOWN','reason':'ZERO_EXECUTED_VOLUME'}
    mean=sum((t.price*t.base for t in tape.trades),D(0))/volume
    # Centered sum avoids a small negative caused by cancellation of E[p²]-E[p]².
    variance=sum(((t.price-mean)**2*t.base for t in tape.trades),D(0))/volume
    return {'status':'COMPUTED','vwap_executed':mean,'trade_weighted_variance':variance,
        'trade_weighted_sigma':variance.sqrt(),'tape_id':tape.id,
        'units':'PRICE_USDT_PER_BASE; VARIANCE_PRICE_SQUARED','coverage':tape.coverage}


def true_profile(tape, *, width, origin=D(0), units='BASE_ASSET'):
    bins = price_bins(tape, width=width, origin=origin, units=units)
    v = {k:r['BUY']+r['SELL'] for k,r in bins.items()}; total = sum(v.values(),D(0))
    poc = min(v, key=lambda k:(-v[k],k)); lo = hi = poc; covered = v[poc]
    while covered < D('.7')*total:
        left, right = v.get(lo-1), v.get(hi+1)
        if left is not None and (right is None or left >= right):
            lo -= 1; covered += v[lo]
        else:
            hi += 1; covered += v[hi]
    width, origin = number(width), number(origin)
    definition = {'version':VERSION,'venue':tape.venue,'native_symbol':tape.native_symbol,
        'window_start':tape.start,'window_end':tape.end,'known_at':tape.end,
        'available_at':tape.available_at,'received_at':tape.received_at,
        'bin_origin':origin,'bin_width':width,'units':units,'coverage':tape.coverage,
        'source_hash':tape.source_hash,'mode':tape.mode,
        'va_algorithm':'CONTIGUOUS_70_PERCENT_GREEDY_ADJACENT_TIE_LOWER; POC_TIE_LOWER'}
    return {**definition,'id':digest(encode(definition).encode()),'poc_bin':poc,
        'poc_interval':(origin+poc*width,origin+(poc+1)*width),
        'val':origin+lo*width,'vah':origin+(hi+1)*width,'value_volume':covered,
        'total_volume':total,'bins':v,'true_profile':True,'production_supported':False}


def profile_nodes(profile, *, separation=3):
    if not profile.get('true_profile') or profile['coverage'] != 'COMPLETE' or separation < 3:
        raise ContractError('TRUE_COMPLETE_PROFILE_REQUIRED')
    v = profile['bins']; keys = sorted(v)
    smooth = {k:(v[k-1]+v[k]+v[k+1])/3 for k in keys[1:-1]}
    result = []
    for kind, sign in [('HVN',1),('LVN',-1)]:
        candidates = [k for k in smooth if k-1 in smooth and k+1 in smooth
            and sign*smooth[k] > sign*smooth[k-1] and sign*smooth[k] >= sign*smooth[k+1]]
        selected = []
        for k in sorted(candidates,key=lambda k:(-sign*smooth[k],k)):
            if all(abs(k-j) >= separation for j in selected):selected.append(k)
        for k in sorted(selected):
            result.append({'id':digest(encode([profile['id'],kind,k,'MEAN3',separation]).encode()),
                'kind':kind,'bin':k,'profile_id':profile['id'],'smoothing':'MEAN3_NO_EDGE_PADDING',
                'minimum_separation':separation,'known_at':profile['known_at']})
    return result


def first_profile_revisit(profile, later):
    later.require_complete()
    if (later.native_symbol != profile['native_symbol'] or later.venue != profile['venue']
            or utc(later.start) != utc(profile['window_end'])):
        raise ContractError('NAKED_POC_CONTIGUOUS_HISTORY_REQUIRED')
    lo, hi = profile['poc_interval']
    hit = next((t for t in later.trades if lo <= t.price < hi), None)
    return {'profile_id':profile['id'],'status':'FIRST_REVISIT' if hit else 'NAKED_THROUGH_COMPLETE_WINDOW',
            'first_trade_id':hit.id if hit else None,'known_at':hit.at if hit else later.end,
            'available_at':later.available_at}


def profile_analysis(profile,*,later=None,separation=3):
    return {'nodes':profile_nodes(profile,separation=separation),
        'naked_poc':first_profile_revisit(profile,later) if later is not None else
            {'status':'SOURCE_CAPABILITY_REQUIRED','reason':'CONTIGUOUS_LATER_EXECUTED_HISTORY'}}


def footprint(tape, *, width, origin=D(0), ratio=D(3), minimum=D(1), stack=3):
    bins = price_bins(tape,width=width,origin=origin)
    ratio,minimum=number(ratio,positive=True),number(minimum,positive=True)
    if ratio < 1 or type(stack) is not int or stack < 3:
        raise ContractError('FOOTPRINT_TRIAL_PARAMETERS')
    rows=[]
    for side,step in [('BUY',-1),('SELL',1)]:
        hits=[]
        for k,r in bins.items():
            opposing=bins.get(k+step)
            if opposing is None:continue  # No denominator outside covered range.
            numerator=r[side];denominator=opposing['SELL' if side=='BUY' else 'BUY']
            if numerator >= minimum and (denominator==0 or numerator >= ratio*denominator):hits.append(k)
        runs=[];run=[]
        for k in hits:
            if run and k!=run[-1]+1:
                if len(run)>=stack:runs.append(tuple(run))
                run=[]
            run.append(k)
        if len(run)>=stack:runs.append(tuple(run))
        rows.append({'side':side,'qualifying_bins':hits,'stacks':runs})
    return {'rows':rows,'units':'EXECUTED_BASE','tape_id':tape.id,'zero_denominator':'ABSOLUTE_MINIMUM_REQUIRED_NO_INFINITY',
            'diagonal':'BUY_AT_P_VS_SELL_P_MINUS_BIN; SELL_AT_P_VS_BUY_P_PLUS_BIN'}


def aggression_attempts(attempts, response, *, direction, lo, hi, max_progress, minimum_aggression):
    """Comparable complete executions, then later price response; no intent."""
    if direction not in {-1,1} or len(attempts)<2:
        raise ContractError('COMPARABLE_REPEATED_ATTEMPTS_REQUIRED')
    lo,hi,max_progress,minimum_aggression=map(number,(lo,hi,max_progress,minimum_aggression))
    if lo>hi or max_progress<0 or minimum_aggression<=0:
        raise ContractError('AGGRESSION_REFERENCE_BOUNDS')
    all_tapes=[*attempts,response];first=attempts[0];prior=utc(first.start)
    durations=[];rows=[]
    for t in all_tapes:
        t.require_complete()
        if (t.native_symbol!=first.native_symbol or t.venue!=first.venue or t.tick!=first.tick
                or utc(t.start)<prior or not t.trades):raise ContractError('ATTEMPT_SCOPE_OR_ORDER')
        prior=utc(t.end)
    side='BUY' if direction==1 else 'SELL'
    for t in attempts:
        durations.append((utc(t.end)-utc(t.start)).total_seconds())
        aggression=sum((x.base for x in t.trades if x.aggressor==side and lo<=x.price<=hi),D(0))
        progress=max(D(0),direction*(t.trades[-1].price-t.trades[0].price))
        rows.append({'aggression':aggression,'progress':progress,'source_id':t.id})
    if len(set(durations))!=1:raise ContractError('ATTEMPTS_DURATION_MISMATCH')
    later_response=direction*(response.trades[-1].price-attempts[-1].trades[-1].price)<0
    absorption=all(r['aggression']>=minimum_aggression and r['progress']<=max_progress for r in rows) and later_response
    exhaustion=all(b['aggression']<a['aggression'] and b['progress']<a['progress'] for a,b in zip(rows,rows[1:]))
    return {'absorption_candidate':absorption,'exhaustion_candidate':exhaustion,
            'later_opposing_response':later_response,'attempts':rows,'institutional_identity':None,
            'rival':'DELAYED_BREAKOUT_OR_ORDINARY_TWO_WAY_EXECUTION'}


def liquidations(rows, *, native_symbol, venue, start, end, coverage, source_hash):
    symbol(native_symbol)
    if coverage not in {'COMPLETE','SAMPLED','MODELED'} or not source_hash or utc(start)>=utc(end):
        raise ContractError('LIQUIDATION_COVERAGE_REQUIRED')
    if coverage=='MODELED':
        return {'classification':'MODELED_CLUSTERS_NOT_OBSERVED','observed_notional_usdt':None,'coverage':coverage}
    total=D(0);ids=set()
    for r in rows:
        if (r['native_symbol']!=native_symbol or r['venue']!=venue or r['id'] in ids
                or not utc(start)<=utc(r['at'])<utc(end) or r['kind']!='OBSERVED_FORCED_EXECUTION'):
            raise ContractError('FORCED_ORDER_IDENTITY_OR_WINDOW')
        total+=number(r['price'],positive=True)*number(r['base'],positive=True);ids.add(r['id'])
    return {'classification':'OBSERVED_FORCED_EXECUTIONS','observed_notional_usdt':total,
            'coverage':coverage,'notional_units':'USDT','source_hash':source_hash,
            'market_total_estimate':None,'known_at':end}
