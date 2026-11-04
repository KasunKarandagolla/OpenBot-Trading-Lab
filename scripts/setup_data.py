"""Reuse the verified Gate acquisition adapter in an isolated source namespace."""
from setup_common import *
import recovery_data as adapter
def acquire():
    adapter.OUT=OUT;adapter.DATA=DATA;adapter.pairs=pairs
    adapter.WINDOWS={'development':(protocol()['source_start'],protocol()['end_exclusive'])}
    adapter.acquire('development')
    m=read(OUT/'data-development.json')
    m.update(evaluation=protocol()['evaluation_start']+'/'+protocol()['end_exclusive'],
             protocol_sha256=sha(ROOT/'research/setup/protocol.json'))
    write(OUT/'data-development.json',m)
if __name__=='__main__':acquire()
