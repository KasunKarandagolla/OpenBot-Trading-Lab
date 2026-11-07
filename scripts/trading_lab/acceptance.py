"""Real-source SCAN replay -> shadow Shared CHART/GATE/READINESS; no native claims."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from binance_research_data import DataError
import openbot_current_market as market
from trading_lab.public import milliseconds, write_new
from trading_lab.workflow import Inbox, stage_run, atomic_reply
from trading_lab.skills import chart_envelope, quality_observations, reconcile, sha


def demonstrate(run, shadow):
    run, shadow = Path(run), Path(shadow)
    if shadow.exists(): raise DataError('NEW_SHADOW_DIRECTORY_REQUIRED')
    capture = market.load(run / 'raw/capture.json')
    for label, source in capture['sources'].items():
        if (urlsplit(source['url']).hostname != 'fapi.binance.com'
                or sha(run / 'raw' / (label + '.json')) != source['sha256']):
            raise DataError('RAW_PUBLIC_SOURCE_HASH_OR_HOST')
    index = market.load(run / 'index.json')
    # Deterministic candidate selection independent of future path or attractiveness.
    candidate = sorted(p['candidate_id'] for p in index['packets'])[0]
    packet = run / 'packets' / candidate
    shared = shadow / 'OpenBot/Shared';shared.mkdir(parents=True)
    staged = stage_run(run, shared, 'skills-v2-acceptance')
    inbox = Inbox(shared / 'TradingLab-Workflow-v2')
    replies = []
    for revision, tf, count, overlays, purpose in [
        (1, '5m', 120, ['confirmed_swings'], 'Which confirmed pre-known levels bound the recent move?'),
        (2, '15m', 20, ['vwap'], 'Does price location relative to the complete UTC-session VWAP alter the hypothesis?')]:
        request = chart_envelope(packet, 'skills-v2-acceptance', 'acceptance-views',
                                 timeframe=tf, visible_candles=count, overlays=overlays,
                                 purpose=purpose, revision=revision)
        path = inbox.root / 'requests' / (request['request_id'] + '.json');atomic_reply(path, request)
        first = inbox.handle(path);second = inbox.handle(path)
        if first != second: raise DataError('NONDETERMINISTIC_BRIDGE_REPLAY')
        replies.append(first)
    now = milliseconds()
    for kind, payload in [('GATE', dict(run_id='skills-v2-acceptance', candidate_id=candidate)), ('READINESS', {})]:
        key = 'acceptance-' + kind.lower()
        request = dict(schema='openbot.shared.request.v2', request_id=key, kind=kind,
                       created_at_ms=now, expires_at_ms=now+600000, payload=payload)
        path = inbox.root / 'requests' / (key+'.json');atomic_reply(path,request);replies.append(inbox.handle(path))
    errors = []
    request = chart_envelope(packet, 'skills-v2-acceptance', 'acceptance-no-1m', purpose='Negative control')
    request['payload']['chart']['timeframe'] = '1m'
    path = inbox.root/'requests'/(request['request_id']+'.json');atomic_reply(path,request)
    try: inbox.handle(path)
    except DataError as error: errors.append(str(error))
    else: raise DataError('UNCAPTURED_1M_DID_NOT_FAIL')
    gate = next(r['result'] for r in replies if r['request_id']=='acceptance-gate')
    report = dict(schema='openbot.skills.acceptance.v2', source_as_of=capture['as_of'],
                  source_as_of_ms=capture['as_of_ms'], observed_at_ms=milliseconds(),
                  mode='HISTORICAL_RESEARCH_REPLAY_NO_CURRENT_PROPOSAL',
                  actual_public_capture=dict(exchange_instruments=capture['exchange_symbol_count'],
                  cheap_context_count=capture['broad_context_count'], public_responses=len(capture['sources']),
                  ranked_symbols=capture['ranked'], raw_source_hashes_verified=True),
                  staged=staged, candidate_id=candidate, packet_sha256=market.verify(packet)['packet_sha256'],
                  quality=quality_observations(packet), bridge_replies=replies, negative_controls=errors,
                  director=reconcile('NO_TRADE', gate, risk_verified=False),
                  native_agent_application='BLOCKED_NO_SUPPORTED_LOCAL_SCRIPTS_CONNECTION',
                  native_message_ids=[], native_attachment_ids=[],
                  chart_request_origin='CODEX_OPERATOR_NOT_ORIGINAL_OPENBOT_VISION',
                  chart_pixel_review='SEPARATE_ACTUAL_VIEW_REQUIRED', orders_submitted=0,
                  installed_activation='PENDING_OWNER_APPROVAL')
    write_new(shadow/'acceptance.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('shadow',type=Path);args=p.parse_args()
    print(json.dumps(demonstrate(args.run,args.shadow),indent=2,allow_nan=False));return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (DataError,OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'status':'BLOCKED','reason':str(error) if isinstance(error,DataError) else type(error).__name__}));sys.exit(1)
