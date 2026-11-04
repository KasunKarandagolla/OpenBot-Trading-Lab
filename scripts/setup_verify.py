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
    print('Exact frozen decision sources, plans, features and market sources verified',flush=True)
if __name__=='__main__':verify()
