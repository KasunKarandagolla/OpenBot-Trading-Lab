"""Atomic paper account checkpoint + consumed-close events; no exchange access."""
from datetime import datetime,timezone
import json
import math
from policy_state import StateStore


class PaperState(StateStore):
    def checkpoint(self,clock,equity,trades,flat):
        if not math.isfinite(equity) or equity<=0:raise ValueError('invalid account equity')
        day=datetime.fromtimestamp(clock,timezone.utc).date().isoformat()
        # One transaction: a crash cannot consume a loss event without its streak checkpoint.
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old=self.get('account')
            if old is None:
                if not flat:raise ValueError('account baseline unavailable with exposure')
                old=dict(day=day,day_start=equity,peak=equity,loss_streak=0,cooldown_until=0,last_close=0,baseline='FLAT_FIRST_OBSERVATION')
            if clock<old.get('asof',0):raise ValueError('account clock rewind')
            if old['day']!=day:
                sec=clock%86400
                if not flat and sec>60:raise ValueError('missed exposed UTC rollover')
                old.update(day=day,day_start=equity,baseline='UTC_MTM' if sec<=60 else 'FLAT_FIRST_OBSERVATION')
            for t in sorted(trades,key=lambda t:t.close_date_utc.timestamp() if t.close_date_utc else 0):
                if not t.close_date_utc:continue
                stamp=t.close_date_utc.timestamp()
                if stamp>clock:raise ValueError('future close in account state')
                if stamp<old['last_close']:continue
                net=float(t.close_profit_abs or 0);key=f'closed:{t.id}:{stamp}'
                inserted=self.db.execute('INSERT OR IGNORE INTO events VALUES (?,?)',(key,json.dumps(dict(net=net,closed_at=stamp)))).rowcount
                if not inserted:continue
                if net<0:
                    old['loss_streak']+=1
                    if old['loss_streak']>=3:old['cooldown_until']=stamp+3600
                else:old['loss_streak']=0
                old['last_close']=max(stamp,old['last_close'])
            old['peak']=max(old['peak'],equity);old['asof']=clock
            self.db.execute('INSERT INTO kv VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v',('account',json.dumps(old,allow_nan=False)))
        return old
