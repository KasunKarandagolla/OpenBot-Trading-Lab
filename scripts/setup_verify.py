"""Verify exact frozen source/input identity before a historical replay."""
from setup_common import *
def verify():
    f=read(OUT/'freeze.json')
    for file,h in f['decision_source_hashes'].items():
        if sha(ROOT/file)!=h:raise ValueError('source seal differs '+file)
    if sha(OUT/'plans.json')!=f['plans_manifest']:raise ValueError('plan registration changed')
    if sha(OUT/'features.json')!=f['features_manifest']:raise ValueError('feature registration changed')
    if sha(OUT/'data-development.json')!=f['source_manifest']:raise ValueError('source registration changed')
    for kind,files in read(OUT/'features.json').items():
        for pair,h in files.items():
            if sha(WORK/'features'/kind/(slug(pair)+'.pkl'))!=h:raise ValueError('feature cache differs')
    for variant,r in read(OUT/'plans.json').items():
        if sha(WORK/'plans'/(variant+'.json'))!=r['sha256']:raise ValueError('plan cache differs')
    for item in read(OUT/'data-development.json')['files']:
        if sha(ROOT/item['path'])!=item['sha256']:raise ValueError('market source differs')
    for path,h in f.get('profile_source_hashes',{}).items():
        if sha(ROOT/path)!=h:raise ValueError('profile source differs '+path)
    for path,h in f.get('causal_checkpoint_hashes',{}).items():
        p=ROOT/path
        actual=sha(p) if p.exists() else __import__('hashlib').sha256(__import__('gzip').decompress(Path(str(p)+'.gz').read_bytes())).hexdigest()
        if actual!=h:raise ValueError('causal checkpoint differs '+path)
    print('Exact frozen decision sources, plans, features and market sources verified',flush=True)
if __name__=='__main__':verify()
