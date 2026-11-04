"""Reuse the verified Gate acquisition adapter in an isolated source namespace."""
from setup_common import *
import recovery_data as adapter
def acquire():
    if RUN_ID=='run-003':
        # Matched replay must use the sealed archive. It may not silently replace
        # it with newly downloaded full-universe history before shortlisting.
        for row in read(ROOT/'evidence/setup/run-002/data-development.json')['files']:
            if not (ROOT/row['path']).exists() or sha(ROOT/row['path'])!=row['sha256']:raise ValueError('restore verified PR11 source archive first')
        print('Sealed offline inputs ready; no broad history acquisition or provider calls')
        return
    adapter.OUT=OUT;adapter.DATA=DATA;adapter.pairs=pairs
    adapter.WINDOWS={'development':(protocol()['source_start'],protocol()['end_exclusive'])}
    adapter.acquire('development')
    m=read(OUT/'data-development.json')
    m.update(evaluation=protocol()['evaluation_start']+'/'+protocol()['end_exclusive'],
             protocol_sha256=sha(ROOT/'research/setup/protocol.json'))
    write(OUT/'data-development.json',m)
if __name__=='__main__':acquire()
