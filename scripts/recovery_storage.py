"""Losslessly compress CLOSED simulated account files when the workspace is full."""
import gzip
import hashlib
from recovery_common import *

def compact():
    rows=[]
    for p in sorted(WORK.rglob('*.sqlite')):
        raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest();compressed=gzip.compress(raw,compresslevel=6,mtime=0)
        if hashlib.sha256(gzip.decompress(compressed)).hexdigest()!=digest:raise ValueError('compression validation')
        q=p.with_suffix(p.suffix+'.gz')
        if q.exists():raise ValueError('preserve existing compressed state')
        # Both validated representations remain in memory during replacement;
        # on write failure restore the original. No account worker is running.
        p.unlink()
        try:
            with q.open('xb') as f:f.write(compressed)
            if hashlib.sha256(gzip.decompress(q.read_bytes())).hexdigest()!=digest:raise ValueError('stored compressed state differs')
        except Exception:
            q.unlink(missing_ok=True);p.write_bytes(raw);raise
        rows.append(dict(original=str(p.relative_to(ROOT)),stored=str(q.relative_to(ROOT)),original_sha256=digest,
                         original_bytes=len(raw),compressed_bytes=len(compressed)))
    write(OUT/'compressed-closed-state.json',dict(files=rows,lossless_verified=True,
        reason='Bounded workspace capacity;only completed research account SQLite files compressed,not deleted. Private archive transparently restores original paths/bytes.'))
    print(len(rows),sum(r['original_bytes']-r['compressed_bytes'] for r in rows),'bytes reclaimed')

if __name__=='__main__':compact()
