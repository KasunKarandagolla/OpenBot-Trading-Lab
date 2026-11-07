"""Validated, offline chart revisions over sealed source bars; reuse local candles."""
from pathlib import Path
import hashlib
import json
import re

from binance_research_data import DataError, KLINE_COLUMNS, INTERVAL_MS
from openbot_current_market import load, verify
from trading_lab.public import write_new, validate_bars

OVERLAYS = {'vwap', 'ema20', 'ema50', 'confirmed_swings'}
FIELDS = {'request_id', 'candidate_id', 'symbol', 'venue', 'cutoff_ms', 'timeframe',
          'visible_candles', 'overlays', 'volume', 'purpose', 'revision', 'start_ms', 'end_ms', 'focus_zone'}


def utc_milliseconds(series):
    # Pandas 3 preserves ms/us/ns dtype units; raw astype(int64) is not always ns.
    return series.map(lambda stamp: stamp.value // 1_000_000)


def validate_request(request, identity):
    if not isinstance(request, dict) or set(request) - FIELDS:
        raise DataError('CHART_UNKNOWN_FIELD')
    required = FIELDS - {'start_ms', 'end_ms', 'focus_zone'}
    if not required <= set(request):
        raise DataError('CHART_REQUIRED_FIELD')
    if (not re.fullmatch('[A-Za-z0-9-]{1,64}', request['request_id'])
            or request['candidate_id'] != identity['candidate_id']
            or request['symbol'] != identity['symbol']
            or request['venue'] != 'BINANCE_PUBLIC_USDM'
            or type(request['cutoff_ms']) is not int
            or request['cutoff_ms'] != identity['as_of_ms']):
        raise DataError('CHART_IDENTITY_VENUE_OR_CUTOFF')
    if request['timeframe'] not in {'4h', '1h', '15m', '5m', '1m'}:
        raise DataError('CHART_TIMEFRAME_UNSUPPORTED')
    if (type(request['visible_candles']) is not int or not 20 <= request['visible_candles'] <= 200
            or type(request['revision']) is not int or not 1 <= request['revision'] <= 4
            or type(request['volume']) is not bool
            or not isinstance(request['purpose'], str) or not 1 <= len(request['purpose']) <= 240
            or not isinstance(request['overlays'], list) or len(request['overlays']) > 3
            or len(set(request['overlays'])) != len(request['overlays'])
            or set(request['overlays']) - OVERLAYS):
        raise DataError('CHART_BOUNDS_OR_OVERLAYS')
    start, end = request.get('start_ms', 0), request.get('end_ms', identity['as_of_ms'])
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= identity['as_of_ms']:
        raise DataError('CHART_RANGE_AFTER_CUTOFF')
    if 'focus_zone' in request:
        zone = request['focus_zone']
        if (not isinstance(zone, list) or len(zone) != 2
                or any(type(x) not in (int, float) for x in zone)
                or not 0 < zone[0] < zone[1] or not all(__import__('math').isfinite(x) for x in zone)):
            raise DataError('CHART_FOCUS_ZONE_INVALID')


def confirmed_swings(frame):
    """Two bars on each side; confirmation availability is explicit, never centered lookahead."""
    result = []
    for i in range(2, len(frame)-2):
        window = frame.iloc[i-2:i+3]
        for column, side in [('high', 'resistance'), ('low', 'support')]:
            value = float(frame.iloc[i][column])
            extreme = window[column].max() if column == 'high' else window[column].min()
            if value == extreme and (window[column] == value).sum() == 1:
                result.append({'kind': side, 'price': value,
                               'pivot_open_ms': int(frame.iloc[i].date.value // 1_000_000),
                               'known_at_ms': int(frame.iloc[i+2].available_at_ms)})
    return result


def render(packet, request, output):
    # Heavy dependencies are loaded only inside the offline research runtime.
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as dates
    from master_charts import candles
    from local_recovery_convert import aggregate

    packet, output = Path(packet), Path(output)
    seal = verify(packet)
    identity = load(packet/'candidate.json')
    validate_request(request, identity)
    tf = request['timeframe']
    source_tf = '1h' if tf == '4h' else tf
    if not (packet/'candles'/(source_tf+'.json')).is_file():
        raise DataError('CHART_FEED_NOT_CAPTURED:' + tf)
    source = load(packet/'candles'/(source_tf+'.json'))
    rows = source['bars']
    validate_bars(rows, source_tf, identity['as_of_ms'], 20)
    frame = pd.DataFrame(rows, columns=KLINE_COLUMNS)
    for name in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
        frame[name] = pd.to_numeric(frame[name])
    frame['date'] = pd.to_datetime(frame.open_time, unit='ms', utc=True)
    frame['available_at_ms'] = frame.close_time + 1
    if tf == '4h':
        quotes=frame.groupby(frame.date.dt.floor('4h')).quote_volume.sum().rename('quote_volume')
        frame = aggregate(frame, '4h').merge(quotes,left_on='date',right_index=True,validate='one_to_one')
        frame = frame.loc[frame.components.eq(4)].copy()
        frame['available_at_ms'] = utc_milliseconds(frame.date) + INTERVAL_MS[tf]
    frame = frame.loc[frame.available_at_ms.le(identity['as_of_ms'])].copy()
    overlays = request['overlays']
    for length in [20, 50]:
        if 'ema'+str(length) in overlays:
            frame['ema'+str(length)] = frame.close.ewm(span=length, adjust=False, min_periods=length).mean()
    if 'vwap' in overlays:
        day = frame.date.dt.floor('D')
        frame['vwap'] = frame.groupby(day).quote_volume.cumsum() / frame.groupby(day).volume.cumsum().replace(0, np.nan)
        # Do not label a truncated session as full-day VWAP.
        for _, group in frame.groupby(day):
            if group.date.iloc[0] != group.date.iloc[0].floor('D'):
                frame.loc[group.index, 'vwap'] = np.nan
    swings = confirmed_swings(frame) if 'confirmed_swings' in overlays else []
    start, end = request.get('start_ms', 0), request.get('end_ms', identity['as_of_ms'])
    display = frame.loc[(utc_milliseconds(frame.date) >= start) & (frame.available_at_ms <= end)].tail(request['visible_candles'])
    if len(display) != request['visible_candles']:
        raise DataError('CHART_INSUFFICIENT_VISIBLE_CANDLES')
    if any(display[name].isna().any() for name in overlays if name in display.columns):
        raise DataError('CHART_INDICATOR_WARMUP_OR_SESSION_INCOMPLETE')
    encoded = json.dumps(request, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    request_hash = hashlib.sha256(encoded).hexdigest()
    target = output/(request['request_id']+'-r'+str(request['revision']))
    if target.exists():
        receipt = load(target/'receipt.json')
        if (receipt['request_sha256'] != request_hash or receipt['packet_sha256'] != seal['packet_sha256']
                or hashlib.sha256((target/'chart.png').read_bytes()).hexdigest() != receipt['image_sha256']):
            raise DataError('CHART_REVISION_REUSE_OR_TAMPER')
        return receipt
    output.mkdir(parents=True, exist_ok=True)
    revisions = list(output.glob(request['request_id']+'-r*'))
    if len(revisions) >= 4 or request['revision'] != len(revisions)+1:
        raise DataError('CHART_REVISION_SEQUENCE_OR_CAP')
    rendered=list(output.glob('*/chart.png'))
    if len(rendered)>=12 or sum(p.stat().st_size for p in rendered)>=24*1024*1024:
        raise DataError('CHART_CANDIDATE_REVISION_OR_BYTE_BUDGET')
    target.mkdir()
    fig, axes = plt.subplots(2 if request['volume'] else 1, 1, figsize=(16, 9),
                             height_ratios=[4, 1] if request['volume'] else None,
                             sharex=True, layout='constrained', squeeze=False)
    price = axes[0, 0]
    candles(price, display, INTERVAL_MS[tf]//60_000)
    price.set_ylabel('Price (USDT)')
    for name, color in [('ema20', '#2855a4'), ('ema50', '#b06712')]:
        if name in overlays:
            price.plot(display.date, display[name], label=name.upper(), color=color, linewidth=1)
    plotted_levels=[]
    for level in swings[-6:]:
        known = pd.Timestamp(level['known_at_ms'], unit='ms', tz='UTC')
        if known <= display.date.iloc[-1]:
            plotted_levels.append(level)
            price.hlines(level['price'], max(known, display.date.iloc[0]), display.date.iloc[-1],
                         color='#6e598b', linestyle=':', linewidth=1, label=level['kind'])
    if 'focus_zone' in request:
        price.set_ylim(*request['focus_zone'])
    else:
        price.margins(y=.06)
    width = pd.Timedelta(milliseconds=INTERVAL_MS[tf])
    price.set_xlim(display.date.iloc[0]-width/2, display.date.iloc[-1]+width/2)
    last = display.iloc[-1]
    price.set_title(f"{tf} | {len(display)} completed candles | O {last.open:g} H {last.high:g} L {last.low:g} C {last.close:g}", loc='left')
    handles, labels = price.get_legend_handles_labels()
    if handles:
        distinct = dict(zip(labels, handles))
        price.legend(distinct.values(), distinct.keys(), loc='upper left', fontsize=9)
    if request['volume']:
        volume = axes[1, 0]
        volume.bar(display.date, display.volume, width=INTERVAL_MS[tf]/86400_000*.7,
                   color=np.where(display.close >= display.open, '#168274', '#c15155'))
        volume.set_ylabel('Base units')
        volume.set_title('Published candle volume; trade-print CVD / footprint NOT AVAILABLE', loc='left', fontsize=10)
        volume.grid(alpha=.18)
    axes[-1, 0].xaxis.set_major_locator(dates.AutoDateLocator(minticks=5, maxticks=9))
    axes[-1, 0].xaxis.set_major_formatter(dates.DateFormatter('%d %b\n%H:%M UTC', tz=display.date.dt.tz))
    fig.suptitle(f"{identity['symbol']} | Binance PUBLIC USD-M research | as of {identity['as_of']}\n{request['purpose']}", fontsize=14)
    image = target/'chart.png'
    fig.savefig(image, dpi=120, facecolor='white')
    plt.close(fig)
    if image.stat().st_size > 4*1024*1024:
        raise DataError('CHART_IMAGE_BYTE_LIMIT')
    receipt = {'candidate_id': identity['candidate_id'], 'request_id': request['request_id'],
               'revision': request['revision'], 'request_sha256': request_hash, 'packet_sha256': seal['packet_sha256'],
               'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(), 'source_sha256': source['source']['sha256'],
               'image': target.name+'/chart.png', 'width': 1920, 'height': 1080, 'visible_candles': len(display),
               'first_open_ms': int(display.date.iloc[0].value//1_000_000),
               'last_available_ms': int(display.available_at_ms.iloc[-1]), 'cutoff_ms': identity['as_of_ms'],
               'levels': plotted_levels, 'focus_zone_crops_candles': 'focus_zone' in request,
               'quality': {'candle_count': 'PASS', 'timestamp_cutoff': 'PASS', 'overlays_max_three': 'PASS',
                           'pixel_readability': 'PENDING_VISUAL_REVIEW', 'native_pixel_receipt': 'PENDING_OPENBOT_OWNER_RUN',
                           'insight_gained': 'PENDING_AGENT_REVISION', 'unsupported_claims': 'NOT_EVALUATED'}}
    write_new(target/'request.json', request)
    write_new(target/'receipt.json', receipt)
    return receipt
