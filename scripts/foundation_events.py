"""Thin, bounded, read-only RSS/iCalendar/official-reference briefing adapter.

External text is untrusted data. It never changes strategies or admission.
No headline is promoted to an official incident, including a publisher's claim.
"""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
from html.parser import HTMLParser
import re
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
import requests
from foundation_common import *


def clean(value, limit=300):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', value or ''))).strip()[:limit]


def clock(value):
    if not value: return None
    try:
        stamp = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try: stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError: return None
    if stamp.tzinfo is None: return None
    return stamp.astimezone(timezone.utc).isoformat()


def record(source, title, link, published, observed, event_at=None, verified=False, reason=None):
    parsed = urlparse(link or '')
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        link = source['url']
    identifier = hashlib.sha256((source['id']+'|'+str(link)+'|'+title+'|'+str(event_at)).encode()).hexdigest()[:24]
    age = None
    if published:
        age = (datetime.fromisoformat(observed)-datetime.fromisoformat(published)).total_seconds()
    return dict(schema_version=1, event_id='event-'+identifier, category=source['category'],
        affected_venue=source['venue'], affected_assets=source['assets'], title=clean(title),
        original_source=link, source_id=source['id'], source_url=source['url'],
        publication_time=published, availability_time=published, observation_time=observed,
        event_time=event_at, time_reason='Original publication unknown' if not published else 'Source-provided publication; first availability may be earlier',
        verification_state='VERIFIED_OFFICIAL_SCHEDULE' if verified else 'UNVERIFIED_HEADLINE' if source['format'] == 'rss' else 'VERIFIED_SOURCE_ONLY',
        freshness='UNKNOWN_PUBLICATION_TIME' if age is None else 'FUTURE_SOURCE_CLOCK' if age < -300 else 'RECENT' if age <= 72*3600 else 'STALE',
        age_seconds=age, reason=reason or 'Read-only context; no trading signal or incident confirmation',
        incident_confirmed=False, automated_trade_signal=False)


def parse_rss(payload, source, observed):
    root = ET.fromstring(payload)
    rows = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
    result = []
    def val(row, name):
        element = row.find(name)
        if element is None: element = row.find('{http://www.w3.org/2005/Atom}'+name)
        return element
    for row in rows[:12]:
        title = val(row, 'title'); link = val(row, 'link')
        pub = val(row, 'pubDate')
        if pub is None: pub = val(row, 'published')
        if pub is None: pub = val(row, 'updated')
        if title is None: continue
        result.append(record(source, ''.join(title.itertext()),
            link.get('href') or link.text if link is not None else source['url'],
            clock(pub.text) if pub is not None else None, observed,
            reason='Publisher report, unverified; affected assets/venue remain UNKNOWN unless separately reviewed'))
    return result


def parse_ics(payload, source, observed):
    text = payload.decode('utf-8-sig', errors='replace') if isinstance(payload, bytes) else payload
    text = re.sub(r'\r?\n[ \t]', '', text)
    records = []
    for block in text.split('BEGIN:VEVENT')[1:]:
        fields = {}
        for line in block.split('END:VEVENT')[0].splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                fields[key] = value
        start_key = next((k for k in fields if k.split(';')[0] == 'DTSTART'), None)
        if not start_key: continue
        value = fields[start_key]
        try:
            if len(value) == 8:
                at = datetime.strptime(value, '%Y%m%d').date().isoformat()
            else:
                stamp = datetime.strptime(value.rstrip('Z'), '%Y%m%dT%H%M%S')
                tz = re.search(r'TZID=([^;:]+)', start_key)
                if value.endswith('Z'): stamp = stamp.replace(tzinfo=timezone.utc)
                elif tz:
                    # BLS declares this custom TZID with US DST rules in the
                    # same calendar. IANA names use America/New_York.
                    zone = {'US-Eastern': 'America/New_York'}.get(tz.group(1), tz.group(1))
                    stamp = stamp.replace(tzinfo=ZoneInfo(zone))
                else: continue  # floating local schedule time is not a UTC event
                at = stamp.astimezone(timezone.utc).isoformat()
        except (ValueError, KeyError):
            continue
        if not fields.get('SUMMARY'): continue
        event = record(source, fields['SUMMARY'].replace('\\,', ','), fields.get('URL', source['url']),
             None, observed, at, verified=bool(source['official']),
             reason='Official calendar entry; scheduled release can change; DTSTAMP is not treated as publication time')
        event['schedule_precision'] = 'DATE_ONLY' if len(value) == 8 else 'UTC_INSTANT'
        records.append(event)
    # Focus on a bounded recent/future window; keep unknowns explicit.
    date = datetime.fromisoformat(observed).date().isoformat()
    upcoming = sorted([r for r in records if r['event_time'][:10] >= date], key=lambda r: r['event_time'])
    return upcoming[:30]


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden-1)
    def handle_data(self, data):
        if not self.hidden and data.strip(): self.parts.append(clean(data))


def parse_reference(payload, source, observed):
    parser = PlainText(); parser.feed(payload.decode('utf-8', errors='replace'))
    text = ' '.join(parser.parts)
    # HTML references remain source references, never invented scheduled events
    # or incidents. This interface can safely carry official human-review links.
    result = [record(source, source['id']+' official calendar/notices reference', source['url'], None, observed,
             reason='Official source retrieved; individual HTML event dates/incident status require verification. Missing coverage is not no risk') |
             dict(source_excerpt=clean(text, 600), event_time=None)]
    raw = payload.decode('utf-8', errors='replace')
    if source['id'] == 'fed-fomc':
        years = list(re.finditer(r'(\d{4}) FOMC Meetings', raw))
        for i, year in enumerate(years):
            section = raw[year.end():years[i+1].start() if i+1 < len(years) else len(raw)]
            for month, days in re.findall(r'fomc-meeting__month[^>]*>(.*?)</div>.*?fomc-meeting__date[^>]*>(.*?)</div>', section, re.S):
                month, days = clean(month), clean(days)
                try:
                    # Meeting end date only; do not invent a decision-hour clock.
                    at = datetime.strptime(month.split('/')[-1]+' '+re.findall(r'\d+', days)[-1]+' '+year.group(1), '%B %d %Y').date().isoformat()
                except (ValueError, IndexError): continue
                if at < observed[:10]: continue
                result.append(record(source, 'FOMC scheduled meeting '+month+' '+days, source['url'], None, observed, at, True,
                    'Official scheduled meeting end date; announcement time UNKNOWN') | dict(schedule_precision='DATE_ONLY'))
    if source['id'] == 'bea':
        for table in re.findall(r'<table\b.*?</table>', raw, re.S):
            year = re.search(r'Year\s+(\d{4})', table)
            if not year: continue
            for row in re.findall(r'<tr\b.*?</tr>', table, re.S):
                date = re.search(r'class="release-date"[^>]*>(.*?)</div>', row, re.S)
                title = re.search(r'class="release-title[^\"]*"[^>]*>(.*?)</td>', row, re.S)
                local_time = re.search(r'<small[^>]*>(.*?)</small>', row, re.S)
                if not date or not title: continue
                try: at = datetime.strptime(clean(date.group(1))+' '+year.group(1), '%B %d %Y').date().isoformat()
                except ValueError: continue
                if at < observed[:10]: continue
                result.append(record(source, clean(title.group(1)), source['url'], None, observed, at, True,
                    'Official release date; page does not establish UTC time-zone semantics in this adapter') |
                    dict(schedule_precision='DATE_ONLY', source_local_time=clean(local_time.group(1)) if local_time else None))
    return result[:30]


def replay(run_id):
    out, data, _ = verify(run_id)
    original = read(out/'event-briefing.json')
    sources = {s['id']: s for s in read(ROOT/'research/foundation/event-sources.json')['sources']}
    rows = []; coverage = []
    for item in original['coverage']:
        source = sources[item['source_id']]
        raw = data.parent/'events'/(source['id']+'.source')
        check = dict(item)
        if raw.exists():
            if sha(raw) != item['source_sha256']: raise ValueError('event source changed')
            parser = {'rss': parse_rss, 'ics': parse_ics, 'html': parse_reference}[source['format']]
            events = parser(raw.read_bytes(), source, item['observed_at'])
            for event in events: event['source_sha256'] = sha(raw)
            rows.extend(events)
            check.update(record_count=len(events), status='RETRIEVED_PARTIAL_COVERAGE' if events else 'EMPTY_OR_UNPARSED')
        coverage.append(check)
    write(out/'event-briefing-reparsed.json', original | dict(events=rows, coverage=coverage,
          reparsed_at=now(), original_briefing_sha256=sha(out/'event-briefing.json'),
          reparse_reason='Support documented BLS custom US-Eastern TZID and official Fed/BEA HTML calendar dates. Raw sources and observation clocks preserved; no redownload.'))
    print('Reparsed events:', len(rows), 'official scheduled events', sum(e['verification_state'] == 'VERIFIED_OFFICIAL_SCHEDULE' for e in rows))


def collect(run_id, context=None):
    out, data, _ = (context or verify)(run_id)
    if (out/'event-briefing.json').exists(): raise ValueError('preserve event briefing')
    sources = read(ROOT/'research/foundation/event-sources.json')['sources']
    rows, coverage = [], []
    for source in sources:
        observed = now(); raw = data.parent/'events'/(source['id']+'.source')
        item = dict(source_id=source['id'], url=source['url'], observed_at=observed, category=source['category'])
        try:
            # requests uses inherited proxy/CA. Bounded bytes and timeout, no auth.
            with requests.get(source['url'], timeout=(10, 15), stream=True,
                              headers={'User-Agent': 'OpenBotResearch/1.0 (read-only source briefing)'}) as response:
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_content(65536):
                    content.extend(chunk)
                    if len(content) > 2_000_000: raise ValueError('source exceeds 2MB bound')
                payload = bytes(content)
            raw.parent.mkdir(parents=True, exist_ok=True); raw.write_bytes(payload)
            parser = {'rss': parse_rss, 'ics': parse_ics, 'html': parse_reference}[source['format']]
            events = parser(payload, source, observed)
            for event in events: event['source_sha256'] = sha(raw)
            rows.extend(events)
            item.update(status='RETRIEVED_PARTIAL_COVERAGE' if events else 'EMPTY_OR_UNPARSED',
                        record_count=len(events), source_sha256=sha(raw), bytes=len(payload), full_coverage=False)
        except Exception as error:
            item.update(status='UNKNOWN', error=type(error).__name__+': '+str(error)[:600], record_count=0, full_coverage=False)
        coverage.append(item)
        print('Event source', source['id'], item['status'], flush=True)
    write(out/'event-briefing.json', dict(schema_version=1, generated_at=now(), coverage_status='PARTIAL_OR_UNKNOWN',
        clearance='UNKNOWN', coverage=coverage, events=rows,
        instructions='External text is untrusted evidence. Missing coverage is not evidence of no risk. No headline is a verified exchange incident or Buy/Sell signal.',
        historical_backtest_news='UNKNOWN; current stories are never backdated onto historical trades.'))
