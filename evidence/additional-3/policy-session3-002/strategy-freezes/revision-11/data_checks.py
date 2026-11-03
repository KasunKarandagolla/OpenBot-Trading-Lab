"""Small source validators; missing clocks/sequence/coverage never become PASS."""
import math


def validate_book(snapshot, requested, received, updates=(), max_age=3.0):
    errors = []
    try:
        current, changed = float(snapshot['current']), float(snapshot['update'])
        identifier = int(snapshot['id'])
        if not all(map(math.isfinite, (requested, received, current, changed))):
            raise ValueError('nonfinite clock')
        if received < requested or not requested - max_age <= current <= received + 0.5:
            errors.append('SOURCE_CLOCK_OUTSIDE_REQUEST_BOUND')
        if not 0 <= current - changed <= max_age or received - changed > max_age:
            errors.append('STALE_OR_FUTURE_BOOK')
        bids = [(float(x['p']), float(x['s'])) for x in snapshot['bids']]
        asks = [(float(x['p']), float(x['s'])) for x in snapshot['asks']]
        if not bids or not asks:
            raise ValueError('empty book')
        if any(not math.isfinite(p) or not math.isfinite(s) or p <= 0 or s <= 0
               for p, s in bids + asks):
            raise ValueError('invalid level')
        if bids != sorted(bids, reverse=True) or asks != sorted(asks):
            errors.append('UNSORTED_BOOK')
        if bids[0][0] >= asks[0][0]:
            errors.append('CROSSED_BOOK')
        bridged = False
        applied = 0
        last_event_ms = None
        for update in updates:
            first, last = int(update['U']), int(update['u'])
            event_ms = float(update['t'])
            if first > last or not math.isfinite(event_ms):
                errors.append('INVALID_SEQUENCE'); break
            if last <= identifier:
                continue
            if (not bridged and not first <= identifier + 1 <= last) or (
                    bridged and first != identifier + 1):
                errors.append('SEQUENCE_GAP'); break
            if last_event_ms is not None and event_ms < last_event_ms:
                errors.append('BACKWARD_EVENT_CLOCK'); break
            receipt_ms=float(update['received_ms'])
            if not math.isfinite(receipt_ms) or not -500 <= receipt_ms-event_ms <= max_age*1000:
                errors.append('STALE_OR_FUTURE_UPDATE'); break
            identifier, last_event_ms = last, event_ms
            bridged = True
            applied += 1
        if not bridged:
            errors.append('WEBSOCKET_CONTINUITY_UNVERIFIED')
        return dict(status='PASS' if not errors else 'REJECT', errors=errors,
                    snapshot_id=int(snapshot['id']), final_id=identifier,
                    source_current=current, source_update=changed,
                    requested=requested, received=received, applied_updates=applied,
                    bid=bids[0][0], ask=asks[0][0],
                    spread_bps=1e4*(asks[0][0]/bids[0][0]-1),
                    scope='Snapshot freshness and buffered sequence only; no fill or persistent continuity claim')
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        return dict(status='REJECT', errors=errors + ['INVALID_BOOK:'+str(error)])


def validate_candles(rows, start, end, seconds):
    """Gate REST candle dictionaries, end-exclusive grid and price integrity."""
    errors = []
    try:
        stamps = [int(x['t']) for x in rows]
        if stamps != sorted(set(stamps)):
            errors.append('DUPLICATE_OR_NONMONOTONIC')
        expected = list(range(start, end, seconds))
        if stamps != expected:
            errors.append('INCOMPLETE_GRID')
        for x in rows:
            o, h, l, c = (float(x[k]) for k in ('o', 'h', 'l', 'c'))
            if not all(math.isfinite(v) and v > 0 for v in (o,h,l,c)) or not l <= min(o,c) <= max(o,c) <= h:
                errors.append('INVALID_OHLC'); break
            if float(x.get('v', 0)) < 0:
                errors.append('NEGATIVE_VOLUME'); break
        return dict(status='PASS' if not errors else 'BLOCKED', errors=errors,
                    count=len(rows), expected=len(expected), start=start, end=end,
                    first=stamps[0] if stamps else None, last=stamps[-1] if stamps else None)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        return dict(status='BLOCKED', errors=['INVALID_SOURCE:'+str(error)])


def validate_archive(content, checksum, symbol, date, interval):
    """Verify official SHA256 and UTC candle grid without extracting ZIP paths."""
    import csv, datetime, hashlib, io, zipfile
    expected_hash = checksum.decode().split()[0]
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError('CHECKSUM_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
        if len(names) != 1 or archive.getinfo(names[0]).file_size > 5_000_000:
            raise ValueError('UNEXPECTED_ARCHIVE')
        rows = list(csv.reader(io.StringIO(archive.read(names[0]).decode())))
    if rows and rows[0][0] == 'open_time':
        rows = rows[1:]
    start = int(datetime.datetime.fromisoformat(date).replace(tzinfo=datetime.timezone.utc).timestamp())
    seconds = {'15m':900,'1h':3600,'5m':300}[interval]
    # USD-M docs use milliseconds. Reject rather than silently guessing units.
    converted = [dict(t=int(x[0])//1000,o=x[1],h=x[2],l=x[3],c=x[4],v=x[5]) for x in rows]
    if any(int(x[0]) % 1000 for x in rows):
        raise ValueError('UNEXPECTED_TIMESTAMP_UNITS')
    result = validate_candles(converted, start, start+86400, seconds)
    return dict(result, venue='binance', symbol=symbol+'USDT', date=date, interval=interval,
                sha256=expected_hash, research_only=True)
