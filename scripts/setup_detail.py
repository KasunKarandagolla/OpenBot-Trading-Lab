"""Bounded real1m fill sensitivity, never tick/queue evidence."""
from concurrent.futures import ThreadPoolExecutor
from setup_common import *
import recovery_data as adapter
def acquire():
    adapter.DATA=DATA;adapter.OUT=OUT;adapter.pairs=pairs
    tasks=[('development',p,'1m','futures','2026-10-29','2026-11-03') for p in pairs()]
    def job(t):
        try:adapter.fetch_one(*t);return dict(pair=t[1],status='READY')
        except Exception as e:return dict(pair=t[1],status='UNAVAILABLE',error=str(e))
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(job,tasks))
    write(OUT/'detail.json',dict(source='PUBLIC_GATE_ACTUAL_1M',start='2026-10-29',end_exclusive='2026-11-03',results=results,
        limitation='Five recent days;not the entire63day evaluation;range feasibility does not establish queue or withinminute ordering'))
if __name__=='__main__':acquire()
