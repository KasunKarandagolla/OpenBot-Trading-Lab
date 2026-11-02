"""Disposable native startup/FreqUI smoke checks; never persistent paper."""
import base64
import json
from pathlib import Path
import secrets
import shutil
import signal
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from foundation_common import *


def doctor(run_id):
    import ccxt
    import freqtrade
    from guard import validate
    from session3_common import sanitized_env
    out, _, _ = verify(run_id)
    for name in ('research.json', 'research-vwap.json', 'research-sweep.json', 'paper.json'):
        cfg = read(ROOT/'configs'/name)
        cfg.pop('api_server', None)  # local auth is verified only by UI smoke
        validate(cfg)
    sanitized_env()
    compose = read(ROOT/'user_data/runtime/foundation-compose.json')
    checks = []
    for name, service in compose['services'].items():
        if service.get('image') != IMAGE: raise ValueError('unpinned Compose image')
        for port in service.get('ports', []):
            if port.get('host_ip') != '127.0.0.1': raise ValueError('API publication must be loopback')
        checks.append(name)
    write(out/'environment-checks.json', dict(schema_version=1, checked_at=now(), engine=freqtrade.__version__,
        ccxt=ccxt.__version__, compose_services=checks, pinned_image=IMAGE, configuration_safety='PASS',
        exchange_keys='ABSENT', sandbox=False, native_dry_run=True, persistent_paper_started=False))
    print('Environment/Compose/frozen configs: PASS')


def ui_smoke(run_id):
    out, _, _ = verify(run_id)
    temp = ROOT/'work/foundation-ui'/run_id; temp.mkdir(parents=True)
    results = temp/'backtest_results'; results.mkdir()
    native = ROOT/'user_data/backtest_results/foundation'/run_id/'TrendPullbackBaselineV1'
    for path in native.glob('*'):
        if path.is_file(): shutil.copyfile(path, results/path.name)
    cfg = read(config(run_id, 'TrendPullbackBaselineV1'))
    cfg['user_data_dir'] = str(temp)
    cfg['api_server'] = dict(enabled=True, listen_ip_address='127.0.0.1', listen_port=8080, verbosity='error',
        enable_openapi=False, CORS_origins=[], username='local-research', password=secrets.token_urlsafe(32),
        jwt_secret_key=secrets.token_hex(32), ws_token=secrets.token_hex(32))
    path = temp/'ui-private.json'; write(path, cfg); path.chmod(0o600)
    records = []
    def call(route, expected=200, headers=None, method='GET'):
        req = urllib.request.Request('http://127.0.0.1:8080'+route, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as r: status, body = r.status, r.read()
        except urllib.error.HTTPError as e: status, body = e.code, e.read()
        records.append(dict(path=route, status=status, expected=expected, pass_check=status == expected))
        if status != expected: raise ValueError('UI HTTP check failed: '+route)
        return body
    log = (out/'ui-smoke.txt').open('x')
    process = subprocess.Popen(['freqtrade', 'webserver', '--config', str(path)], stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(40):
            if process.poll() is not None: raise ValueError('FreqUI exited during startup')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8080/api/v1/ping', timeout=1): break
            except (OSError, urllib.error.URLError): time.sleep(.5)
        html = call('/')
        if b'<html' not in html.lower(): raise ValueError('FreqUI HTML missing')
        import re
        for asset in re.findall(rb'(?:src|href)=[\"\']([^\"\']+\.(?:js|css))', html):
            if asset.startswith(b'/'): call(asset.decode())
        call('/api/v1/version', 401)
        api = cfg['api_server']
        credential = base64.b64encode((api['username']+':'+api['password']).encode()).decode()
        token = json.loads(call('/api/v1/token/login', headers={'Authorization': 'Basic '+credential}, method='POST'))['access_token']
        headers = {'Authorization': 'Bearer '+token}
        version = json.loads(call('/api/v1/version', headers=headers))
        history = json.loads(call('/api/v1/backtest/history', headers=headers))
        if not history: raise ValueError('native backtest missing in UI')
        from urllib.parse import urlencode
        item = history[0]
        result = json.loads(call('/api/v1/backtest/history/result?'+urlencode({'filename': item['filename'], 'strategy': item['strategy']}), headers=headers))
        count = result['backtest_result']['strategy'][item['strategy']]['total_trades']
        expected = read(out/'native-results/TrendPullbackBaselineV1.json')['strategy']['TrendPullbackBaselineV1']['total_trades']
        if count != expected: raise ValueError('UI/native count mismatch')
        write(out/'ui-smoke.json', dict(schema_version=1, observed_at=now(), checks=records, engine=version,
            native_trade_count=count, graphical_rendering='UNOBSERVED_HTTP_ONLY', auth_tokens_exported=False))
    finally:
        process.send_signal(signal.SIGINT) if process.poll() is None else None
        try: process.wait(timeout=15)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
        log.close(); path.unlink(missing_ok=True)
    print('FreqUI authenticated HTTP/native-result smoke: PASS; service stopped')


def dryrun_smoke(run_id):
    out, _, _ = verify(run_id)
    cfg = read(config(run_id, 'TrendPullbackBaselineV1'))
    temp = ROOT/'work/foundation-dryrun'/run_id; temp.mkdir(parents=True)
    database = temp/'disposable.sqlite'
    cfg.update(initial_state='stopped', db_url='sqlite:///'+str(database), cancel_open_orders_on_exit=True)
    cfg.pop('api_server', None)
    cfg['exchange']['pair_whitelist'] = ['BTC/USDT:USDT']
    path = temp/'config.json'; write(path, cfg)
    assert cfg['dry_run'] is True and not cfg['force_entry_enable'] and not cfg['position_adjustment_enable']
    assert all(not cfg['exchange'].get(k) for k in ('key', 'secret', 'password', 'uid'))
    with (out/'dryrun-smoke.txt').open('x') as log:
        process = subprocess.Popen(['freqtrade', 'trade', '--config', str(path)], stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(60):
                if process.poll() is not None: raise ValueError('native dry-run startup exited early')
                if database.exists() and 'STOPPED' in (out/'dryrun-smoke.txt').read_text(): break
                time.sleep(.5)
            else: raise ValueError('native stopped-state startup not observed within 30s')
        finally:
            if process.poll() is None: process.send_signal(signal.SIGINT)
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
    with sqlite3.connect(database) as db:
        trades = db.execute('SELECT COUNT(*) FROM trades').fetchone()[0]
    if trades: raise ValueError('stopped startup unexpectedly created a simulated trade')
    write(out/'dryrun-smoke.json', dict(schema_version=1, observed_at=now(), dry_run=True, initial_state='stopped',
        simulated_trade_count=trades, exchange_credentials=False, service_stopped=process.poll() is not None,
        exit_code=process.returncode, scope='Disposable native keyless startup, no persistent owner-host trading',
        operational_readiness='STARTUP_ONLY_NOT_ECONOMIC_OR_RECOVERY_QUALIFICATION'))
    print('Native keyless dry-run stopped-state startup: PASS; zero trades; stopped')
