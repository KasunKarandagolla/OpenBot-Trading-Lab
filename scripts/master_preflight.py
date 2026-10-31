"""Bounded public-only acquisition audit. Never sends orders or uses API keys.

python scripts/master_preflight.py RUN_ID
Raw source bytes remain in ignored work/. Immutable coverage evidence is additive.
"""
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'research'))
from master_audit.data_checks import validate_archive, validate_candles

GATE = 'https://api.gateio.ws/api/v4/futures/usdt/'
VISION = 'https://data.binance.vision/data/futures/um/daily/'
TERMS = 'https://raw.githubusercontent.com/binance/binance-public-data/master/TERMS_AND_CONDITIONS.md'


class Acquisition:
    def __init__(self, run_id):
        import re
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,40}', run_id):
            raise ValueError('invalid ID')
        self.out = ROOT/'evidence/master-audit'/run_id
        self.out.mkdir()  # immutable run, refuse reuse
        self.raw = ROOT/'work/master-audit'/run_id
        self.raw.mkdir(parents=True)
        self.protocol = json.loads((ROOT/'research/master_audit/protocol.json').read_text())
        self.records = []
        self.lock = threading.Lock()
        self.total = self.requests = 0

    def get(self, url):
        with self.lock:
            self.requests += 1
            if self.requests > self.protocol['limits']['max_requests']:
                raise ValueError('REQUEST_BUDGET')
        started = time.time()
        row = dict(url=url, requested=started)
        data = b''
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'OpenBot-independent-read-only-audit/1'})
            with urllib.request.urlopen(req, timeout=self.protocol['limits']['timeout_seconds']) as response:
                data = response.read(self.protocol['limits']['request_max_bytes']+1)
                row.update(http_status=response.status, date_header=response.headers.get('Date'))
            if len(data) > self.protocol['limits']['request_max_bytes']:
                raise ValueError('RESPONSE_BUDGET')
        except urllib.error.HTTPError as error:
            row.update(http_status=error.code, error=str(error), failure_body=error.read(300).decode(errors='replace'))
        except Exception as error:
            row['error'] = type(error).__name__+':'+str(error)
        row.update(received=time.time(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        with self.lock:
            self.total += len(data)
            if self.total > self.protocol['limits']['total_max_bytes']:
                raise ValueError('TOTAL_BUDGET')
            self.records.append(row)
        if data:
            (self.raw/row['sha256']).write_bytes(data)
        return row, data

    def gate_sample(self, item):
        symbol, date, kind = item
        contract = symbol+'_USDT'
        start = int(dt.datetime.fromisoformat(date).replace(tzinfo=dt.timezone.utc).timestamp())
        end = start+86400
        if kind == 'funding':
            path = 'funding_rate?'+urllib.parse.urlencode(dict(contract=contract,limit=1000,**{'from':start,'to':end-1}))
        else:
            path = 'candlesticks?'+urllib.parse.urlencode(dict(contract=('mark_' if kind=='mark' else '')+contract,
                interval='1h' if kind=='mark' else kind, **{'from':start,'to':end-1}))
        request, data = self.get(GATE+path)
        result = dict(venue='gate', symbol=contract,date=date,kind=kind,request=request,status='BLOCKED')
        try:
            if 'error' in request:
                return result
            rows = json.loads(data)
            if kind == 'funding':
                # Funding interval itself can vary historically. A one-day sample
                # is availability only, never a proof of full event coverage.
                selected = [x for x in rows if start<=int(x['t'])<end]
                times = sorted(int(x['t']) for x in selected)
                result.update(status='PARTIAL' if times else 'BLOCKED',count=len(times),
                              source_returned_count=len(rows),first=times[0] if times else None,
                              last=times[-1] if times else None,
                              limitation='Event availability; historical schedule and complete cohort not proven')
            else:
                # Source order retained separately; normalized stable UTC order.
                ordered = sorted(rows,key=lambda x:int(x['t']))
                result.update(validate_candles(ordered,start,end,{'15m':900,'1h':3600,'5m':300,'mark':3600}[kind]))
            return result
        except Exception as error:
            result['error'] = str(error)
            return result

    def run(self):
        # Terms are fetched and inspected BEFORE archive bytes.
        term_record, terms = self.get(TERMS)
        allowed = (term_record.get('http_status') == 200 and
                   b'purely personal non-production research' in terms and
                   b'live proprietary trading execution' in terms)
        rights = dict(source=TERMS, request=term_record, scope='PERSONAL_NONPRODUCTION_RESEARCH_ONLY',
                      recognized_terms=allowed, legal_entitlement_assumed=False,
                      excerpts=[s for s in terms.decode(errors='replace').splitlines() if s.startswith(('**4.1.','**4.2.'))])
        contracts_record, contracts_raw = self.get(GATE+'contracts')
        tickers_record, tickers_raw = self.get(GATE+'tickers')
        contracts = json.loads(contracts_raw) if contracts_record.get('http_status')==200 else []
        tickers = json.loads(tickers_raw) if tickers_record.get('http_status')==200 else []
        eligible = {x['name']:x for x in contracts if x.get('status')=='trading' and not x.get('in_delisting') and not x.get('is_pre_market') and x.get('contract_type')==''}
        top = sorted([x for x in tickers if x.get('contract') in eligible],
                     key=lambda x:float(x.get('volume_24h_quote',0)),reverse=True)[:20]
        shortlist = [x['contract'] for x in top]
        panel_meta = [{k:v for k,v in eligible.get(s+'_USDT',{}).items() if k in
                       ('name','launch_time','create_time','quanto_multiplier','funding_interval','status','taker_fee_rate','maker_fee_rate','order_size_min','order_price_round','config_change_time')}
                      |{'requested_symbol':s+'_USDT','currently_eligible':s+'_USDT' in eligible}
                      for s in self.protocol['panel']]
        # Initial source availability only: no outcome or strategy calculation.
        tasks = [(s,d,k) for s in self.protocol['panel'] for d in self.protocol['historical_samples']
                 for k in self.protocol['required_sources']]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            gate = list(executor.map(self.gate_sample,tasks))
        archives = []
        if allowed:
            for symbol in self.protocol['panel']:
                date = self.protocol['historical_samples'][-1]
                base = VISION+f'klines/{symbol}USDT/15m/{symbol}USDT-15m-{date}.zip'
                checksum_record, checksum = self.get(base+'.CHECKSUM')
                archive_record, archive = self.get(base)
                item = dict(venue='binance',symbol=symbol+'USDT',date=date,kind='15m',
                            checksum_request=checksum_record,archive_request=archive_record,status='BLOCKED')
                try:
                    if 'error' in checksum_record or 'error' in archive_record:
                        raise ValueError('SOURCE_HTTP_FAILURE')
                    item.update(validate_archive(archive,checksum,symbol,date,'15m'))
                except Exception as error:
                    item['error'] = str(error)
                archives.append(item)
        result = dict(registered_protocol_sha256=hashlib.sha256((ROOT/'research/master_audit/protocol.json').read_bytes()).hexdigest(),
                      observed_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),rights=rights,
                      gate_scan=dict(eligible=len(eligible),shortlisted=shortlist,metadata_request=contracts_record,
                                     tickers_request=tickers_record,ticker_source_clock='UNKNOWN_SCREENING_ONLY'),
                      panel_metadata=panel_meta,gate_samples=gate,binance_samples=archives,
                      summary=dict(gate_checks=len(gate),gate_pass=sum(x['status']=='PASS' for x in gate),
                                   binance_checks=len(archives),binance_pass=sum(x['status']=='PASS' for x in archives)),
                      data_status='PARTIAL',economic_status='BLOCKED',
                      blockers=['Two sampled dates are not a complete multi-symbol cohort',
                                'Historical listing/delisting roster is not reconstructed',
                                'Gate websocket continuity requires separate bounded check',
                                'Binance prices never substitute for Gate fills/funding'],
                      requests=self.records,bytes=self.total)
        (self.out/'coverage.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result['summary']))
        print('Raw sources:',self.raw)


if __name__ == '__main__':
    Acquisition(sys.argv[1]).run()
