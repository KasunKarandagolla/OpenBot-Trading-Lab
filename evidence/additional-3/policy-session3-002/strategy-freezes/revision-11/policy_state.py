"""Single native-engine writer, durable account checkpoints and event deduplication."""
import sqlite3
import json
from pathlib import Path

class StateStore:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path,timeout=10)
        self.db.executescript('PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY,v TEXT NOT NULL); CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT NOT NULL); CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY,pair TEXT,side TEXT,at REAL,expires REAL,payload TEXT NOT NULL);')
        self.db.commit()
    def get(self,k,default=None):
        r=self.db.execute('SELECT v FROM kv WHERE k=?',(k,)).fetchone()
        return json.loads(r[0]) if r else default
    def put(self,k,value):
        with self.db: self.db.execute('INSERT INTO kv VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v',(k,json.dumps(value,allow_nan=False)))
    def event(self,id,payload):
        with self.db:
            cur=self.db.execute('INSERT OR IGNORE INTO events VALUES (?,?)',(id,json.dumps(payload,allow_nan=False)))
        return cur.rowcount==1
    def plan(self,id,pair,side,at,expires,payload):
        with self.db: self.db.execute('INSERT OR IGNORE INTO plans VALUES (?,?,?,?,?,?)',(id,pair,side,at,expires,json.dumps(payload,allow_nan=False)))
    def find_plan(self,pair,side,clock):
        r=self.db.execute('SELECT payload FROM plans WHERE pair=? AND side=? AND at<=? AND expires>? ORDER BY at DESC LIMIT 1',(pair,side,clock,clock)).fetchone()
        return json.loads(r[0]) if r else None
    def checkpoint(self,clock,equity,trades,flat):
        from datetime import datetime, timezone
        day=datetime.fromtimestamp(clock,timezone.utc).date().isoformat()
        old=self.get('account')
        if old is None:
            if not flat: raise ValueError('account baseline unavailable with exposure')
            old=dict(day=day,day_start=equity,peak=equity,loss_streak=0,cooldown_until=0,last_close=0,baseline='FLAT_FIRST_OBSERVATION')
        if old['day']!=day:
            # Only the first process observation within a minute of UTC midnight
            # can reset an exposed account. Missing midnight fails closed.
            sec=clock%86400
            if not flat and sec>60: raise ValueError('missed UTC MTM rollover; require reviewed recovery')
            old.update(day=day,day_start=equity,baseline='UTC_MTM' if sec<=60 else 'FLAT_FIRST_OBSERVATION')
        for t in sorted(trades,key=lambda t:t.close_date_utc.timestamp() if t.close_date_utc else 0):
            if not t.close_date_utc: continue
            stamp=t.close_date_utc.timestamp()
            key=f'closed:{t.id}:{stamp}'
            if not self.event(key,dict(net=float(t.close_profit_abs or 0),closed_at=stamp)): continue
            if float(t.close_profit_abs or 0)<0:
                old['loss_streak']+=1
                if old['loss_streak']>=3: old['cooldown_until']=stamp+3600
            else: old['loss_streak']=0
            old['last_close']=max(stamp,old['last_close'])
        old['peak']=max(old['peak'],equity); old['asof']=clock
        self.put('account',old)
        return old
    def close(self): self.db.close()
