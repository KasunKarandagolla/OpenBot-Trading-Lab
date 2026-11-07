"""Persistent OFFLINE lifecycle and fail-closed signed-service boundary.

No credentials are loaded. A production-capable SDK is deliberately not instantiated
inside an agent's OS principal. The simulator is never exchange execution evidence.
"""
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import time

DEMO_HOST = 'demo-fapi.binance.com'
READ_ROUTES = ('/fapi/v3/balance', '/fapi/v3/account', '/fapi/v3/positionRisk',
               '/fapi/v1/openOrders', '/fapi/v1/openAlgoOrders', '/fapi/v1/order',
               '/fapi/v1/algoOrder', '/fapi/v1/leverageBracket', '/fapi/v1/positionSide/dual',
               '/fapi/v1/symbolConfig', '/fapi/v1/commissionRate')


class ExecutionBlocked(RuntimeError):
    pass


def readiness():
    return {'status': 'BLOCKED', 'reason': 'EXECUTION_BLOCKED_CREDENTIAL_BOUNDARY',
            'default_mode': 'READ_ONLY', 'signed_read_only_verified': False,
            'trade_authorization': 'PENDING_SEPARATE_OWNER_APPROVAL',
            'orders_submitted': 0, 'host': DEMO_HOST,
            'required_boundary': 'Separate OS/service principal inaccessible to Windows and WSL agents; reviewed capability API',
            'native_signed_connector': 'NOT_CONFIGURED'}


class SignedServiceStub:
    """Unconditionally blocked; a JSON attestation/flag cannot turn signing on."""
    def __init__(self, host=DEMO_HOST):
        if host != DEMO_HOST:
            raise ExecutionBlocked('DEMO_HOST_ALLOWLIST_REJECTED')
        for name, value in os.environ.items():
            if value and ('proxy' in name.lower() or name.upper() in {'BINANCE_BASE_URL', 'BASE_PATH', 'FAPI_BASE_URL'}):
                raise ExecutionBlocked('NETWORK_OVERRIDE_REJECTED')

    def request(self, method, path, params=None):
        raise ExecutionBlocked('EXECUTION_BLOCKED_CREDENTIAL_BOUNDARY')


def conditional_confirmed(trigger, bar, now_ms):
    """An opening order may only follow an actual completed 5m confirmation."""
    if (trigger.get('order_after_confirmation') is not True
            or trigger.get('kind') not in {'CLOSED_5M_ABOVE', 'CLOSED_5M_BELOW'}
            or bar.get('host') != DEMO_HOST or bar.get('interval_ms') != 300_000
            or type(bar.get('open_ms')) is not int or bar['open_ms'] % 300_000
            or bar.get('available_ms') != bar['open_ms']+300_000
            or not trigger['not_before_ms'] < bar['available_ms'] <= now_ms < trigger['expires_at_ms']):
        return False
    value, boundary = Decimal(str(bar['close'])), Decimal(str(trigger['price']))
    return value > boundary if trigger['kind'] == 'CLOSED_5M_ABOVE' else value < boundary


class OfflineVenue:
    """Scripted exchange responses for fault tests; IDs carry SIMULATED prefixes."""
    offline = True
    def __init__(self):
        self.entries, self.protections, self.closes = {}, {}, {}
        self.position = Decimal(0)
        self.reject_stop = False
        self.timeout_entry = False
        self.timeout_close = False
        self.entry_calls = 0

    def submit_entry(self, client_id, plan):
        self.entry_calls += 1
        if client_id in self.entries:
            raise RuntimeError('SIMULATED_DUPLICATE_ENTRY')
        order = {'id': 'SIMULATED-'+client_id, 'status': 'NEW', 'filled': '0'}
        self.entries[client_id] = order
        if self.timeout_entry:
            raise TimeoutError('SIMULATED_AMBIGUOUS_ACK')
        return order

    def query_entry(self, client_id):
        return self.entries.get(client_id)

    def fill(self, client_id, amount, *, terminal=False):
        entry = self.entries[client_id]
        self.position += Decimal(str(amount))-Decimal(entry['filled'])
        entry.update(filled=str(amount), status='FILLED' if terminal else 'PARTIALLY_FILLED')

    def stop(self, client_id, plan):
        if self.reject_stop:
            raise RuntimeError('SIMULATED_STOP_REJECTION')
        self.protections[client_id] = {'algoId': 'SIMULATED-STOP-'+client_id,
            'symbol': plan['symbol'], 'side': 'SELL' if plan['side'] == 'LONG' else 'BUY',
            'orderType': 'STOP_MARKET', 'triggerPrice': plan['stop'], 'algoStatus': 'NEW',
            'workingType': 'MARK_PRICE', 'closePosition': True, 'positionSide': 'BOTH'}

    def query_stop(self, client_id):
        return self.protections.get(client_id)

    def cancel_entry(self, client_id):
        order = self.entries.get(client_id)
        if order and order['status'] != 'FILLED':
            order['status'] = 'CANCELED'

    def close_only(self, client_id, amount):
        # Amount is bounded by a fresh owned-position query; cannot reverse.
        if client_id in self.closes:
            return self.closes[client_id]
        if not 0 < amount <= self.position:
            raise RuntimeError('SIMULATED_CLOSE_WOULD_REVERSE')
        self.position -= amount
        receipt = {'id': 'SIMULATED-CLOSE-'+client_id, 'filled': str(amount), 'status': 'FILLED', 'reduceOnly': True}
        self.closes[client_id] = receipt
        if self.timeout_close:
            raise TimeoutError('SIMULATED_CLOSE_ACK_UNKNOWN')
        return receipt


class OfflineManager:
    """One-way, one-symbol, full-position protection replay. No network transport."""
    def __init__(self, path, venue):
        if type(venue) is not OfflineVenue:
            raise ExecutionBlocked('OFFLINE_SIMULATOR_REQUIRED')
        self.venue = venue
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=2)
        self.db.execute('pragma journal_mode=WAL')
        self.db.execute('pragma synchronous=FULL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS jobs
            (id TEXT PRIMARY KEY, plan TEXT NOT NULL, state TEXT NOT NULL, filled TEXT NOT NULL DEFAULT '0',
             created INTEGER NOT NULL, expires INTEGER NOT NULL, close_intent INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY, job TEXT, state TEXT, at INTEGER, reason TEXT);
            CREATE TABLE IF NOT EXISTS controls (id INTEGER PRIMARY KEY CHECK(id=1), stop_new INTEGER NOT NULL);
            INSERT OR IGNORE INTO controls VALUES (1,0);''')

    def _event(self, job, state, now, reason):
        self.db.execute('update jobs set state=? where id=?', (state, job))
        self.db.execute('insert into events(job,state,at,reason) values (?,?,?,?)', (job,state,now,reason))

    def stop_new_entries(self):
        self.db.execute('update controls set stop_new=1 where id=1')

    def propose(self, plan, risk, now):
        if risk.get('status') != 'PASS' or plan.get('engine_mode') != 'OFFLINE_SIMULATION':
            raise ExecutionBlocked('OFFLINE_RISK_PASS_REQUIRED')
        if (plan.get('margin_type') != 'ISOLATED' or plan.get('position_side') != 'BOTH'
                or plan.get('side') not in {'LONG','SHORT'} or plan.get('decision') not in {'LIMIT','MARKET'}
                or not 0 < Decimal(plan['entry'])*Decimal(plan['quantity']) <= 25
                or not 0 < plan['hold_seconds'] <= 15*3600 or self.venue.position):
            raise ExecutionBlocked('OFFLINE_MODE_SIZE_OR_EXISTING_POSITION')
        key = hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()[:28]
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute('insert into jobs(id,plan,state,created,expires) values (?,?,?,?,?)',
                            (key,json.dumps(plan,sort_keys=True),'PROPOSED',now,plan['expires_at_ms']))
            self._event(key,'PROPOSED',now,'SIMULATED_PLAN')
            self._event(key,'RISK_PASSED',now,'SUPPLIED_OFFLINE_RISK_RESULT')
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise
        return key

    def approve_offline(self, job, now):
        # This cannot record or stand in for owner consent to any real Demo transaction.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute('select state,expires from jobs where id=?',(job,)).fetchone()
            if row is None or row[0]!='RISK_PASSED' or now>=row[1]:
                raise ExecutionBlocked('DUPLICATE_OR_EXPIRED_OFFLINE_APPROVAL')
            self._event(job,'OWNER_APPROVED',now,'SIMULATED_APPROVAL_NOT_TRANSACTION_CONSENT')
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK');raise

    def step(self, job, now, *, emergency=False):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute('select plan,state,filled,created,expires,close_intent from jobs where id=?',(job,)).fetchone()
            if row is None:
                raise ExecutionBlocked('UNKNOWN_OFFLINE_JOB')
            plan,state,filled,created,expires,closing=row
            plan=json.loads(plan)
            halted=self.db.execute('select stop_new from controls').fetchone()[0]
            if state in {'CLOSED','EXPIRED','CANCELED','FAILED','RISK_PASSED','PROPOSED'}:
                self.db.execute('COMMIT');return state
            if state=='OWNER_APPROVED':
                if now>=expires:
                    self._event(job,'EXPIRED',now,'ENTRY_TTL')
                elif halted:
                    self._event(job,'CANCELED',now,'STOP_NEW_ENTRIES')
                elif self.venue.position or self.db.execute(
                        "select count(*) from jobs where id!=? and state in ('SUBMITTED','ACKNOWLEDGED','PARTIAL_FILL','FILLED','PROTECTION_CONFIRMED','MANAGING','UNKNOWN')",(job,)).fetchone()[0]:
                    self._event(job,'FAILED',now,'PREEXISTING_POSITION')
                else:
                    # Commit intent BEFORE submission; a crash cannot cause a repeated entry.
                    self._event(job,'SUBMITTED',now,'SIMULATED_SUBMIT_INTENT')
                    self.db.execute('COMMIT')
                    try:self.venue.submit_entry(job,plan)
                    except TimeoutError:pass
                    return 'SUBMITTED'
            else:
                order=self.venue.query_entry(job)
                if order is None:
                    self._event(job,'UNKNOWN',now,'NO_QUERY_RESULT_NEVER_RESUBMIT')
                else:
                    if halted and order['status'] in {'NEW','PARTIALLY_FILLED'}:
                        self.venue.cancel_entry(job)
                        order=self.venue.query_entry(job)
                    filled=Decimal(order['filled'])
                    self.db.execute('update jobs set filled=? where id=?',(str(filled),job))
                    if filled<0 or filled>Decimal(plan['quantity']) or self.venue.position>Decimal(plan['quantity']):
                        self.stop_new_entries();self._event(job,'UNKNOWN',now,'POSITION_RECONCILIATION_MISMATCH')
                    elif closing:
                        self._reconcile_close(job,now)
                    elif filled:
                        self._event(job,'FILLED' if order['status']=='FILLED' else 'PARTIAL_FILL',now,'SIMULATED_QUERY')
                        stop=self.venue.query_stop(job)
                        if stop is None and state not in {'MANAGING','PROTECTION_CONFIRMED'}:
                            try:self.venue.stop(job,plan)
                            except (RuntimeError,TimeoutError):pass
                            stop=self.venue.query_stop(job)
                        valid=(stop is not None and stop.get('algoStatus')=='NEW'
                               and stop.get('symbol')==plan['symbol'] and stop.get('positionSide')=='BOTH'
                               and stop.get('workingType')=='MARK_PRICE' and stop.get('closePosition') is True
                               and stop.get('orderType')=='STOP_MARKET'
                               and stop.get('side')==('SELL' if plan['side']=='LONG' else 'BUY')
                               and Decimal(stop.get('triggerPrice','0'))==Decimal(plan['stop']))
                        if valid:
                            self._event(job,'PROTECTION_CONFIRMED',now,'SIMULATED_STOP_QUERY_MATCH')
                            self._event(job,'MANAGING',now,'SIMULATED_PROTECTED_POSITION')
                        else:
                            self.stop_new_entries();self.venue.cancel_entry(job)
                            self._event(job,'UNKNOWN',now,'PROTECTION_MISSING_OR_MISMATCH')
                        deadline=now>=created+plan['hold_seconds']*1000
                        target=(plan['side']=='LONG' and Decimal(plan.get('observed_price',plan['entry']))>=Decimal(plan['tp1'])
                                or plan['side']=='SHORT' and Decimal(plan.get('observed_price',plan['entry']))<=Decimal(plan['tp1']))
                        if emergency or deadline or target or not valid:
                            if plan.get('preapproved_emergency_flatten') is True:
                                self.venue.cancel_entry(job)
                                self.db.execute('update jobs set close_intent=1 where id=?',(job,))
                                self._event(job,'UNKNOWN',now,'SIMULATED_CLOSE_INTENT')
                                self.db.execute('COMMIT')
                                try:self.venue.close_only(job,self.venue.position)
                                except TimeoutError:pass
                                return 'UNKNOWN'
                            self.stop_new_entries();self._event(job,'UNKNOWN',now,'FLATTEN_POLICY_NOT_APPROVED_ALERT_REQUIRED')
                    elif now>=expires or emergency or halted:
                        self.venue.cancel_entry(job)
                        checked=self.venue.query_entry(job)
                        self._event(job,'CANCELED' if checked and checked['status']=='CANCELED' else 'UNKNOWN',now,'SIMULATED_CANCEL_QUERY')
                    else:
                        self._event(job,'ACKNOWLEDGED',now,'SIMULATED_ORDER_QUERY')
            state=self.db.execute('select state from jobs where id=?',(job,)).fetchone()[0]
            self.db.execute('COMMIT');return state
        except BaseException:
            if self.db.in_transaction:self.db.execute('ROLLBACK')
            raise

    def _reconcile_close(self,job,now):
        result=self.venue.closes.get(job)
        if result and result['status']=='FILLED' and self.venue.position==0:
            self._event(job,'CLOSED',now,'SIMULATED_CLOSE_AND_FLAT_POSITION_QUERY')
        else:
            self.stop_new_entries();self._event(job,'UNKNOWN',now,'CLOSE_UNKNOWN_NEVER_REPEAT')
