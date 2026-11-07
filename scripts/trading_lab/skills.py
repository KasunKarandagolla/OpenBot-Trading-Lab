"""Bounded research-skill compatibility checks; never native agent or order authority."""
import argparse
import hashlib
import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys

from binance_research_data import DataError, INTERVAL_MS
import openbot_current_market as market
from trading_lab.charts import validate_request, confirmed_swings
from trading_lab.public import milliseconds, validate_bars, write_new

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / 'integrations/openbot/skills/v2'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def schema_check(value, filename):
    from jsonschema import Draft202012Validator, FormatChecker
    spec = market.load(filename)
    Draft202012Validator.check_schema(spec)
    errors = list(Draft202012Validator(spec, format_checker=FormatChecker()).iter_errors(value))
    if errors:
        raise DataError('SKILL_SCHEMA_INVALID:' + '/'.join(map(str, errors[0].absolute_path)))


def check_pack():
    if PACK.is_symlink() or any(p.is_symlink() for p in PACK.rglob('*')):
        raise DataError('PACK_SYMLINK_REJECTED')
    contract = market.load(PACK / 'contract.json')
    if contract['program_baseline'] != 'd133b3bf91ab51765d9446e4e82f0bc38c0bae94':
        raise DataError('PROGRAM_BASELINE_MISMATCH')
    expected = market.load(PACK / 'baseline-manifest.json')
    original = {a['directory']: a for a in expected['agents']}
    counts, unique, checked = {}, set(), 0
    if {p.name for p in (PACK / 'agents').iterdir()} != set(original):
        raise DataError('OWNER_SET_MISMATCH')
    for owner in contract['assignments']:
        name = owner['owner']
        folder = PACK / 'agents' / name
        migration = market.load(folder / 'MIGRATION.json')
        if sha(folder / 'MIGRATION.json') != owner['migration_sha256']:
            raise DataError('MIGRATION_HASH_MISMATCH')
        old = original[name]
        old_files = {(s['skill_id'], f['relative_filename']): f['sha256'] for s in old['skills'] for f in s['files']}
        skills = {p.name for p in (folder / 'skills').iterdir()}
        if skills != set(owner['skills']) or skills != {s['skill_id'] for s in old['skills']}:
            raise DataError('OWNERSHIP_REALLOCATION')
        found = {(f['skill_id'], f['file']) for f in migration['files']}
        if found != set(old_files) or len(found) != len(migration['files']):
            raise DataError('ORIGINAL_FILE_SET_MISMATCH')
        expected_paths = set()
        for f in migration['files']:
            p = folder / 'skills' / f['skill_id'] / f['file']
            expected_paths.add(p)
            if (p.is_symlink() or f['original_pr19_sha256'] != old_files[f['skill_id'], f['file']]
                    or sha(p) != f['new_sha256'] or p.stat().st_nlink != 1):
                raise DataError('SKILL_HASH_OR_SHARED_LINK')
            if p.suffix == '.json':
                from jsonschema import Draft202012Validator
                Draft202012Validator.check_schema(market.load(p))
            checked += 1
        if set(p for p in (folder / 'skills').rglob('*') if p.is_file()) != expected_paths:
            raise DataError('UNMANIFESTED_SKILL_FILE')
        counts[name] = len(skills)
        if counts[name] != old['scope_assignments'] or counts[name] != owner['count']:
            raise DataError('ASSIGNMENT_COUNT_MISMATCH')
        unique.update(skills)
    if sum(counts.values()) != 27 or len(unique) != 9 or checked != 55:
        raise DataError('PACK_COUNTS')
    for path, digest in contract['files'].items():
        if sha(ROOT / path) != digest:
            raise DataError('PROGRAM_CONTRACT_DRIFT:' + path)
    return dict(status='PASS', assignments=27, owners=counts, unique_skill_ids=9,
                skill_files=checked, contract_sha256=sha(PACK / 'contract.json'),
                installed_activation='PENDING_OWNER_APPROVAL', execution_authority='NONE')


def bootstrap(owner):
    check_pack()
    contract = market.load(PACK / 'contract.json')
    if owner not in [a['owner'] for a in contract['assignments']]:
        raise DataError('ORIGINAL_OWNER_REQUIRED')
    return dict(owner=owner, card=(PACK / 'agents' / owner / 'BOOTSTRAP.md').read_text(),
                contract_sha256=sha(PACK / 'contract.json'), native_listener='NOT_VERIFIED',
                execution_authority='NONE')


def verified_packet(packet):
    packet = Path(packet)
    seal = market.verify(packet)
    identity = market.load(packet / 'candidate.json')
    # The old packet verifier checks seals; validate semantics independently as well.
    for tf in market.LIMITS:
        source = market.load(packet / 'candles' / (tf + '.json'))
        if (source.get('venue') != 'binance' or source.get('market_type') != market.MARKET
                or source['symbol'] != identity['symbol'] or source['candidate_id'] != identity['candidate_id']
                or source['as_of_ms'] != identity['as_of_ms']
                or source['source'].get('venue') != 'binance'
                or source['source'].get('market_type') != market.MARKET):
            raise DataError('SOURCE_IDENTITY_OR_VENUE')
        rows = validate_bars(source['bars'], tf, identity['as_of_ms'], 20)
        if len(rows) != len(source['bars']):
            raise DataError('SOURCE_FUTURE_BAR')
    return seal, identity


def validate_envelope(request, now, packet=None, packet_sha=None):
    schema_check(request, PACK / 'schemas/shared-request.schema.json')
    if not request['created_at_ms'] <= now < request['expires_at_ms'] <= request['created_at_ms'] + 600000:
        raise DataError('REQUEST_EXPIRED_FUTURE_OR_TTL')
    if len(json.dumps(request, allow_nan=False).encode()) > 64 * 1024:
        raise DataError('REQUEST_SIZE_LIMIT')
    if request['kind'] in {'CHART', 'GATE'}:
        if packet is None:
            raise DataError('SEALED_PACKET_REQUIRED')
        seal, identity = verified_packet(packet)
        if packet_sha is not None and seal['packet_sha256'] != packet_sha:
            raise DataError('PACKET_SHA_PRECONDITION')
        payload = request['payload']
        if payload['candidate_id'] != identity['candidate_id']:
            raise DataError('REQUEST_CANDIDATE_MISMATCH')
        if request['kind'] == 'CHART':
            chart = payload['chart']
            validate_request(chart, identity)
            tf = '1h' if chart['timeframe'] == '4h' else chart['timeframe']
            if not (Path(packet) / 'candles' / (tf + '.json')).is_file():
                raise DataError('CHART_FEED_NOT_CAPTURED:' + chart['timeframe'])
        elif payload.get('proposal') is not None:
            plan = payload['proposal']
            if plan['packet_sha256'] != seal['packet_sha256'] or plan['symbol'] != identity['symbol']:
                raise DataError('PROPOSAL_IDENTITY_MISMATCH')
            if plan['decision'] != 'NO_OPPORTUNITY' and not 0 <= now - identity['as_of_ms'] <= 180000:
                raise DataError('STALE_OR_FUTURE_CANDLES')
    return request


def chart_envelope(packet, run_id, request_id, *, timeframe='5m', visible_candles=120,
                   overlays=(), purpose, revision=1, now=None):
    now = milliseconds() if now is None else now
    _, identity = verified_packet(packet)
    chart = dict(request_id=request_id, candidate_id=identity['candidate_id'], symbol=identity['symbol'],
                 venue='BINANCE_PUBLIC_USDM', cutoff_ms=identity['as_of_ms'], timeframe=timeframe,
                 visible_candles=visible_candles, overlays=list(overlays), volume=True,
                 purpose=purpose, revision=revision)
    request = dict(schema='openbot.shared.request.v2', request_id=request_id + '-r' + str(revision),
                   kind='CHART', created_at_ms=now, expires_at_ms=now + 600000,
                   payload=dict(run_id=run_id, candidate_id=identity['candidate_id'], chart=chart))
    return validate_envelope(request, now, packet)


def quality_observations(packet):
    seal, identity = verified_packet(packet)
    features = market.load(Path(packet) / 'features.json')
    formation = identity.get('hypothesis')
    # Do not create a second opportunity score or invent a pending formation.
    state = 'SETUP_FOR_REVIEW' if identity['review_type'] == 'SETUP_FOR_REVIEW' and formation else 'NO_OPPORTUNITY'
    sources = {tf: market.load(Path(packet) / 'candles' / (tf + '.json')) for tf in market.LIMITS}
    return dict(schema='openbot.research-quality.v2', candidate_id=identity['candidate_id'],
                cutoff_ms=identity['as_of_ms'], packet_sha256=seal['packet_sha256'],
                state=state, shortlisted=True, qualified_for_execution=False,
                reason_codes=['FROZEN_FORMATION_FOR_REVIEW' if state == 'SETUP_FOR_REVIEW' else 'NO_UNEXPIRED_FROZEN_SETUP'],
                observations={k: features.get(k) for k in ['regime_1h', 'regime_4h', 'atr_1h_frac',
                    'rvol_5m_prior_48', 'taker_buy_quote_share_5m']},
                source_windows={tf: dict(source_sha256=s['source']['sha256'], first_open_ms=s['bars'][0][0],
                    last_available_ms=s['bars'][-1][6] + 1) for tf, s in sources.items()},
                btc_context='NOT_AUTOMATICALLY_SUPPLIED', news=features.get('news_macro', 'NOT_FETCHED'),
                recipe='FROZEN_LOCAL_RECOVERY_V1', execution_authority='NONE')


def verify_flow(rows, provenance, cutoff_ms):
    """Bounded Binance aggregate prints; no boundary proofs => no signed-flow claim."""
    unavailable = dict(status='UNAVAILABLE', signed_delta_base=None, eligible_for_strategy=False)
    if provenance.get('venue') != 'binance' or provenance.get('market_type') != market.MARKET:
        return {**unavailable, 'status': 'CROSS_VENUE_CONTEXT', 'reason': 'VENUE_MISMATCH'}
    if provenance.get('fidelity') != 'BINANCE_AGG_TRADES':
        return {**unavailable, 'reason': 'KLINE_PROXY_IS_NOT_TRADE_PRINTS'}
    if (not isinstance(rows, list) or not 1 <= len(rows) <= 10000
            or provenance.get('units') != 'BASE_ASSET'
            or provenance.get('source_sha256') != hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()):
        return {**unavailable, 'reason': 'SOURCE_HASH_UNITS_OR_BOUNDS'}
    try:
        ids = [r['a'] for r in rows]
        stamps = [r['T'] for r in rows]
        if (any(type(x) is not int for x in ids + stamps) or any(type(r['m']) is not bool for r in rows)
                or any(not provenance['start_ms'] <= x <= provenance['end_ms'] <= cutoff_ms for x in stamps)
                or stamps != sorted(stamps) or any(b != a + 1 for a, b in zip(ids, ids[1:]))
                or provenance.get('aggressor_semantics') != 'BUYER_IS_MAKER'):
            raise ValueError
        quantities = [Decimal(str(r['q'])) for r in rows]
        if any(not q.is_finite() or q <= 0 for q in quantities):
            raise ValueError
        if provenance.get('start_boundary_verified') is not True or provenance.get('end_boundary_verified') is not True:
            return {**unavailable, 'status': 'PARTIAL_COVERAGE', 'reason': 'WINDOW_BOUNDARIES_UNPROVEN'}
        delta = sum((-q if r['m'] else q for q, r in zip(quantities, rows)), Decimal(0))
        return dict(status='FULL_WINDOW', signed_delta_base=str(delta), eligible_for_strategy=True,
                    reason='VERIFIED_AGGREGATE_PRINT_WINDOW', units='BASE_ASSET', rows=len(rows))
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return {**unavailable, 'status': 'PARTIAL_COVERAGE', 'reason': 'CLOCK_GAP_SIDE_OR_QUANTITY'}


def validate_assessment(packet, assessment, revisions):
    schema_check(assessment, PACK / 'schemas/vision-assessment.schema.json')
    seal, identity = verified_packet(packet)
    if (assessment['candidate_id'] != identity['candidate_id'] or assessment['packet_sha256'] != seal['packet_sha256']
            or assessment['cutoff_ms'] != identity['as_of_ms']):
        raise DataError('ASSESSMENT_IDENTITY')
    pixels = False
    for evidence in assessment['images']:
        target = Path(revisions) / (evidence['request_id'] + '-r' + str(evidence['revision']))
        if target.is_symlink() or (target / 'chart.png').is_symlink():
            raise DataError('IMAGE_SYMLINK')
        receipt = market.load(target / 'receipt.json')
        request = market.load(target / 'request.json')
        validate_request(request, identity)
        tf = '1h' if request['timeframe'] == '4h' else request['timeframe']
        source = market.load(Path(packet) / 'candles' / (tf + '.json'))
        if (receipt['packet_sha256'] != seal['packet_sha256']
                or receipt['source_sha256'] != source['source']['sha256']):
            raise DataError('IMAGE_PACKET_OR_SOURCE_BINDING')
        expected_request = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        if receipt['request_sha256'] != expected_request:
            raise DataError('IMAGE_REQUEST_HASH')
        for key in ['image_sha256', 'packet_sha256', 'source_sha256', 'cutoff_ms', 'last_available_ms']:
            if evidence[key] != receipt[key]:
                raise DataError('IMAGE_RECEIPT_MISMATCH:' + key)
        if (sha(target / 'chart.png') != receipt['image_sha256'] or evidence['last_available_ms'] > identity['as_of_ms']
                or evidence['symbol'] != identity['symbol'] or evidence['timeframe'] != request['timeframe']
                or evidence['cutoff_ms'] != request['cutoff_ms']):
            raise DataError('IMAGE_HASH_SYMBOL_OR_TIME')
        width = INTERVAL_MS[request['timeframe']]
        expected_last = request.get('end_ms', identity['as_of_ms']) // width * width
        if (receipt['last_available_ms'] != expected_last or receipt['cutoff_ms'] != identity['as_of_ms']
                or receipt['visible_candles'] != request['visible_candles']
                or receipt['first_open_ms'] != expected_last - request['visible_candles'] * width):
            raise DataError('IMAGE_BAR_WINDOW_MISMATCH')
        if evidence['pixels_seen']:
            if evidence['delivery'] == 'NO_PIXELS':
                raise DataError('PIXELS_NOT_DELIVERED')
            if evidence['delivery'] == 'NATIVE_ATTACHMENT' and not all(evidence[k] for k in ['attachment_id', 'message_id']):
                raise DataError('NATIVE_ATTACHMENT_RECEIPT_REQUIRED')
            pixels = True
    if not pixels and any(c['classification'] == 'VISIBLE' for c in assessment['observations']):
        raise DataError('VISUAL_CLAIM_WITHOUT_PIXELS')
    seen_ids = {e['request_id'] + '-r' + str(e['revision']) for e in assessment['images'] if e['pixels_seen']}
    if any(c['classification'] == 'VISIBLE' and c['evidence_id'] not in seen_ids for c in assessment['observations']):
        raise DataError('VISUAL_CLAIM_IMAGE_NOT_SEEN')
    bars = [market.load(Path(packet) / 'candles' / (tf + '.json')) for tf in market.LIMITS]
    for claim in assessment['observations']:
        if claim['price'] is not None:
            if claim['classification'] != 'NUMERIC_VERIFIED':
                raise DataError('PRECISE_PRICE_REQUIRES_NUMERIC_EVIDENCE')
            if claim['feature'] == 'CONFIRMED_SWING':
                import pandas as pd
                from binance_research_data import KLINE_COLUMNS
                swing = claim['swing']
                source = market.load(Path(packet) / 'candles' / (swing['timeframe'] + '.json'))
                frame = pd.DataFrame(source['bars'], columns=KLINE_COLUMNS)
                frame['date'] = pd.to_datetime(frame.open_time, unit='ms', utc=True)
                frame['available_at_ms'] = frame.close_time + 1
                for name in ['high', 'low']: frame[name] = pd.to_numeric(frame[name])
                levels = confirmed_swings(frame)
                if (claim['source_sha256'] != source['source']['sha256']
                        or claim['available_at_ms'] != swing['known_at_ms']
                        or not any(level['pivot_open_ms'] == swing['pivot_open_ms']
                                   and level['known_at_ms'] == swing['known_at_ms'] <= identity['as_of_ms']
                                   and level['kind'] == swing['kind']
                                   and Decimal(str(level['price'])) == Decimal(claim['price']) for level in levels)):
                    raise DataError('SWING_CONFIRMATION_OR_PRICE_MISMATCH')
                continue
            matches = [b for s in bars if s['source']['sha256'] == claim['source_sha256']
                       for b in s['bars'] if b[6] + 1 == claim['available_at_ms']]
            if not matches or not any(Decimal(claim['price']) in [Decimal(str(x)) for x in b[1:5]] for b in matches):
                raise DataError('PRECISE_LEVEL_NOT_IN_CITED_BAR')
    return dict(status='PASS', scope='SCHEMA_SOURCE_AND_RECEIPT_CHECKS',
                native_delivery_verified=False, pixel_delivery_independently_verified=False,
                limitation='Metadata assertions do not prove actual inference pixel delivery', order_authorized=False)


def reconcile(recommendation, gate, *, risk_verified=False, contradiction='NONE', proposal=None):
    if recommendation not in {'TRADE', 'WATCH', 'NO_TRADE'} or contradiction not in {'NONE', 'CAUTION', 'INVALIDATES'}:
        raise DataError('RESEARCH_DECISION_OR_CONTRADICTION')
    reasons = []
    if not risk_verified:
        reasons.append('AGENT_NOT_VERIFIED')
    if recommendation != 'TRADE':
        reasons.append('NO_EXECUTABLE_PROPOSAL')
    if contradiction == 'INVALIDATES':
        reasons.append('THESIS_INVALIDATED')
    if gate.get('status') != 'PASS':
        reasons.append('GATE_' + str(gate.get('status', 'UNKNOWN')))
    if proposal is None:
        reasons.append('NO_EXECUTABLE_PROPOSAL')
    else:
        schema_check(proposal, ROOT / 'research/openbot_current/order-intent.schema.json')
        if proposal['decision'] == 'NO_OPPORTUNITY':
            reasons.append('NO_EXECUTABLE_PROPOSAL')
    return dict(decision='NO_ACTION' if reasons else 'RESEARCH_REVIEW_ONLY', recommendation=recommendation,
                reasons=sorted(set(reasons)), execution_authority='NONE', order_authorized=False,
                readiness='EXECUTION_BLOCKED_CREDENTIAL_BOUNDARY')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('check')
    p = actions.add_parser('bootstrap'); p.add_argument('--agent', required=True)
    p = actions.add_parser('quality'); p.add_argument('packet', type=Path)
    p = actions.add_parser('request'); p.add_argument('packet', type=Path)
    p.add_argument('--run-id', required=True); p.add_argument('--request-id', required=True)
    p.add_argument('--timeframe', default='5m'); p.add_argument('--visible-candles', type=int, default=120)
    p.add_argument('--overlays', nargs='*', default=[]); p.add_argument('--purpose', required=True)
    p.add_argument('--revision', type=int, default=1); p.add_argument('--output', type=Path, required=True)
    p = actions.add_parser('validate'); p.add_argument('request', type=Path); p.add_argument('--packet', type=Path)
    p.add_argument('--packet-sha')
    p = actions.add_parser('assess'); p.add_argument('packet', type=Path); p.add_argument('assessment', type=Path); p.add_argument('revisions', type=Path)
    p = actions.add_parser('chart'); p.add_argument('packet', type=Path); p.add_argument('request', type=Path); p.add_argument('out', type=Path)
    args = parser.parse_args()
    if args.action == 'check': result = check_pack()
    elif args.action == 'bootstrap': result = bootstrap(args.agent)
    elif args.action == 'quality': result = quality_observations(args.packet)
    elif args.action == 'request':
        result = chart_envelope(args.packet, args.run_id, args.request_id, timeframe=args.timeframe,
                                visible_candles=args.visible_candles, overlays=args.overlays,
                                purpose=args.purpose, revision=args.revision)
        write_new(args.output, result)
    elif args.action == 'validate':
        validate_envelope(market.load(args.request), milliseconds(), args.packet, args.packet_sha)
        result = dict(status='PASS', order_authorized=False)
    elif args.action == 'chart':
        from trading_lab.charts import render
        request = validate_envelope(market.load(args.request), milliseconds(), args.packet)
        if request['kind'] != 'CHART': raise DataError('CHART_ENVELOPE_REQUIRED')
        result = render(args.packet, request['payload']['chart'], args.out)
    else: result = validate_assessment(args.packet, market.load(args.assessment), args.revisions)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (DataError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status':'BLOCKED', 'reason':str(error) if isinstance(error, DataError) else type(error).__name__}))
        sys.exit(1)
