"""Versioned selected/oracle analytics for blueprint §6; never a broad feed.

Decimal arithmetic, complete closed windows and source identity are required.
None means undefined; it is never a favorable zero or a fabricated observation.
"""
from decimal import Decimal as D, ROUND_FLOOR
from statistics import median
from .contracts import ContractError, number, symbol, utc
from .numerics import (validate_bars, anchored_value, confirmed_swings,
                       lag_trained_beta, relative_return)

VERSION = 'measurements-6a.1'


def tick_price(price, tick, *, rounding=ROUND_FLOOR):
    p, t = number(price, positive=True), number(tick, positive=True)
    return (p/t).to_integral_value(rounding=rounding)*t


def value_extension(bars, *, anchor_ms, anchor_known_at, atr_ref, baseline=16):
    """Close residuals against expanding Q/V; evaluation excluded from sigma.

    Population RMS *about the past residual mean* is a close statistic, not
    trade-weighted VWAP variance. A complete zero-volume prefix is undefined.
    """
    v = anchored_value(bars, anchor_ms=anchor_ms, anchor_known_at=anchor_known_at)
    scale = number(atr_ref, positive=True)
    q = volume = D(0)
    residuals = []
    for b in bars:
        q += b.quote_volume; volume += b.base_volume
        residuals.append(b.close-q/volume if volume else None)
    past = residuals[-baseline-1:-1]
    sigma = None
    if baseline < 2:
        raise ContractError('RESIDUAL_BASELINE_REQUIRED')
    if len(past) == baseline and all(x is not None for x in past):
        mean = sum(past, D(0))/baseline
        sigma = (sum(((x-mean)**2 for x in past), D(0))/baseline).sqrt()
    return {**v, 'distance_atr': residuals[-1]/scale if residuals[-1] is not None else None,
            'z_close_residual': residuals[-1]/sigma if sigma and residuals[-1] is not None else None,
            'sigma_past_close_residual': sigma, 'baseline': baseline,
            'band_kind': 'PAST_BAR_CLOSE_RESIDUAL_POPULATION_SIGMA',
            'trade_weighted_variance': None, 'evaluation_excluded': True}


def flow_divergence(bars, *, anchor_ms, anchor_known_at):
    anchored_value(bars, anchor_ms=anchor_ms, anchor_known_at=anchor_known_at)
    cvd = []; total = D(0)
    for b in bars:
        total += 2*b.buy_quote-b.quote_volume; cvd.append(total)
    swings = confirmed_swings(bars); result = []
    for kind, direction in [('SWING_LOW', 1), ('SWING_HIGH', -1)]:
        prior = None
        for s in (s for s in swings if s['kind'] == kind):
            if prior and direction*(s['price']-prior['price']) < 0 and direction*(cvd[s['index']]-cvd[prior['index']]) > 0:
                result.append({'direction': direction, 'pivot_ids': (prior['id'], s['id']),
                    'known_at': s['known_at'], 'available_at': max(
                        (b.available_at or b.received_at for b in bars[:s['known_index']+1]), key=utc),
                    'cvd_at_pivots': (cvd[prior['index']], cvd[s['index']]),
                    'anchor_ms': anchor_ms, 'units': 'USDT_QUOTE_DELTA',
                    'fidelity': 'BAR_AGGRESSOR_DIVERGENCE_NOT_FOOTPRINT'})
            prior = s
    return result


def residual_series(asset,benchmark,*,n=32):
    """Same lag-trained regression, log prices computed once per selected pair."""
    validate_bars(asset); validate_bars(benchmark)
    relative_return(asset, benchmark, horizon=1)
    ar=[(b.close/a.close).ln() for a,b in zip(asset,asset[1:])]
    br=[(b.close/a.close).ln() for a,b in zip(benchmark,benchmark[1:])]
    rows=[None]*len(asset)
    for k in range(n,len(ar)):
        y,x=ar[k-n:k],br[k-n:k];my=sum(y,D(0))/n;mx=sum(x,D(0))/n
        variance=sum(((v-mx)**2 for v in x),D(0))
        if not variance:continue
        beta=sum(((v-mx)*(u-my) for v,u in zip(x,y)),D(0))/variance;alpha=my-beta*mx
        rows[k+1]={'beta':beta,'alpha':alpha,'residual':ar[k]-alpha-beta*br[k],
            'training_end':asset[k].end,'evaluation_end':asset[k+1].end,'n':n}
    return rows


def persistent_residual(asset, benchmark, *, n=32, observations=3):
    if observations < 2 or len(asset) < n+1+observations:
        raise ContractError('INSUFFICIENT_HISTORY')
    return residual_persistence(residual_series(asset,benchmark,n=n)[-observations:])


def residual_persistence(rows):
    if any(r is None for r in rows):
        return {'status': 'SOURCE_UNKNOWN', 'reason': 'ZERO_BENCHMARK_VARIANCE', 'direction': 0, 'rows': rows}
    signs = [1 if r['residual'] > 0 else -1 if r['residual'] < 0 else 0 for r in rows]
    direction = signs[0] if len(set(signs)) == 1 else 0
    return {'status': 'COMPUTED', 'direction': direction, 'rows': rows,
            'independent_later_observations': len(rows), 'empirically_useful': False}


def sector_strength(native_symbol, residuals, memberships, *, at, minimum=5):
    """Membership rows contain exact perp identities and dated validity."""
    symbol(native_symbol); utc(at)
    active = [m for m in memberships if m['venue'] == 'BINANCE_USDM'
              and m['contract_type'] == 'PERPETUAL' and m['quote'] == 'USDT'
              and utc(m['known_at']) <= utc(at)
              and utc(m['valid_from']) <= utc(at) < utc(m['valid_until'])]
    own = {m['sector'] for m in active if m['native_symbol'] == native_symbol}
    result = []
    for sector in sorted(own):
        peers = {m['native_symbol'] for m in active if m['sector'] == sector}
        peers.discard(native_symbol)
        values = [number(residuals[n]) for n in sorted(peers) if n in residuals]
        result.append({'sector': sector, 'peer_count': len(values),
            'status': 'COMPUTED' if len(values) >= minimum and native_symbol in residuals else 'SOURCE_UNKNOWN',
            'residual_from_peer_median': number(residuals[native_symbol])-median(values)
                if len(values) >= minimum and native_symbol in residuals else None})
    return result or [{'status': 'SOURCE_CAPABILITY_REQUIRED', 'reason': 'DATED_CONTRACT_MEMBERSHIP_REQUIRED'}]


def oi_decomposition(before, after, *, multiplier):
    """Linear base-per-native units only; exact log mark contribution."""
    keys = ('venue', 'native_symbol', 'contract_type', 'native_units')
    if (any(before[k] != after[k] for k in keys) or before['contract_type'] != 'LINEAR_USDT_PERPETUAL'
            or before['native_units'] != 'CONTRACTS' or utc(before['at']) >= utc(after['at'])
            or any(r['at'] != r['mark_at'] for r in (before, after))):
        raise ContractError('OI_IDENTITY_UNITS_OR_MARK_ALIGNMENT')
    symbol(before['native_symbol']); multiplier = number(multiplier, positive=True)
    native = [number(r['native'], positive=True) for r in (before, after)]
    marks = [number(r['mark'], positive=True) for r in (before, after)]
    base = [x*multiplier for x in native]; usd = [x*p for x,p in zip(base, marks)]
    return {'delta_native': native[1]-native[0], 'delta_base': base[1]-base[0],
        'delta_usdt': usd[1]-usd[0], 'log_base_contribution': (base[1]/base[0]).ln(),
        'log_mark_contribution': (marks[1]/marks[0]).ln(), 'log_usdt_change': (usd[1]/usd[0]).ln(),
        'opening_side': None, 'position_direction': 'NOT_IDENTIFIABLE_FROM_AGGREGATE_OI'}


def funding_basis(row):
    if row['rate_kind'] not in {'NEXT_PREDICTED', 'SETTLED'} or row['units'] not in {'FRACTION','PERCENT'}:
        raise ContractError('FUNDING_KIND_OR_UNITS')
    if type(row['interval_seconds']) is not int or row['interval_seconds'] <= 0:
        raise ContractError('FUNDING_ACTUAL_INTERVAL_REQUIRED')
    if row['mark_at'] != row['index_at']:
        raise ContractError('BASIS_CLOCK_ALIGNMENT')
    utc(row['mark_at']); utc(row['settlement_at'])
    rate = number(row['rate'])/(100 if row['units'] == 'PERCENT' else 1)
    return {'rate_fraction': rate, 'rate_kind': row['rate_kind'],
        'interval_seconds': row['interval_seconds'], 'settlement_at': row['settlement_at'],
        'basis_fraction': number(row['mark'], positive=True)/number(row['index'], positive=True)-1,
        'settled_carry': rate if row['rate_kind'] == 'SETTLED' else None}


def catalyst(row, *, native_symbol, at):
    symbol(native_symbol)
    if (not row['source_url'].startswith('https://') or not row['publisher'] or not row['response_hash']
            or row['kind'] not in {'ANNOUNCEMENT','SCHEDULED','REPORTED_EVENT'}
            or not utc(row['published_at']) <= utc(row['first_known_at']) <= utc(row['received_at'])):
        raise ContractError('CATALYST_SOURCE_OR_TIMES')
    mapping = row['contracts']
    impacted = any(m['native_symbol'] == native_symbol and m['venue'] == 'BINANCE_USDM'
        and m['contract_type'] == 'PERPETUAL' and m['quote'] == 'USDT'
        and utc(m['mapping_known_at']) <= utc(at) for m in mapping)
    return {'status': 'SUPPORTED' if impacted and utc(row['received_at']) <= utc(at) else 'SOURCE_UNKNOWN',
        'publisher': row['publisher'], 'source_url': row['source_url'], 'kind': row['kind'],
        'published_at': row['published_at'], 'first_known_at': row['first_known_at'],
        'causal_price_effect': None, 'external_text_is_data_only': True}
