"""Validate and print owner-specific v3 load cards; no persistent installer."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from collections import Counter

ROOT=Path(__file__).resolve().parents[2]
PACK=ROOT/'integrations/openbot/skills/v3'
COUNTS={'astrabot-lead':9,'trading-lab-director':6,'trading-lab-market-researcher':6,
        'chart-vision-analyst':1,'independent-risk-reviewer':5}


def check():
    manifest=json.loads((PACK/'manifest.json').read_text())
    assignments=manifest['assignments']
    if len({(a['owner'],a['skill']) for a in assignments})!=27:raise ValueError('DUPLICATE_OWNER_ASSIGNMENT')
    if Counter(a['owner'] for a in assignments)!=COUNTS or len({a['skill'] for a in assignments})!=9:
        raise ValueError('OWNER_ASSIGNMENTS_MISMATCH')
    if any(p.is_symlink() for p in PACK.rglob('*')):raise ValueError('SKILL_SYMLINK')
    paths=set();originals=0;references=0
    for item in manifest['files']:
        relative=Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('UNSAFE_SKILL_PATH')
        path=PACK/relative
        if relative in paths or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('SKILL_HASH_OR_INVENTORY')
        if path.stat().st_nlink!=1:raise ValueError('SHARED_OWNER_LINK')
        paths.add(relative)
        if 'original_path' in item:
            if hashlib.sha256((ROOT/item['original_path']).read_bytes()).hexdigest()!=item['original_sha256']:
                raise ValueError('ORIGINAL_SOURCE_DRIFT')
            originals+=1
        if path.suffix=='.md':
            # Original router uses backtick references; new router uses Markdown links.
            links=re.findall(r'`((?:references|cases|schemas)/[^`]+)`|\]\(((?:references|cases|schemas)/[^)]+)\)',path.read_text())
            for pair in links:
                target=path.parent/next(v for v in pair if v)
                if not target.is_file() or not target.resolve().is_relative_to(PACK.resolve()):
                    raise ValueError('UNRESOLVED_SKILL_REFERENCE:'+str(target))
                references+=1
    actual={p.relative_to(PACK) for p in (PACK/'agents').glob('*/skills/**/*') if p.is_file()}
    if actual!=paths or originals!=55:raise ValueError('UNMANIFESTED_OR_MISSING_ORIGINAL_MEMBER')
    for a in assignments:
        text=(PACK/a['entry']).read_text()
        if not text.startswith('---\n') or f'name: {a["skill"]}\n' not in text:
            raise ValueError('INVALID_FRONTMATTER')
    return dict(status='PASS',assignments=27,owners=COUNTS,unique_skills=9,
                original_members=originals,v3_members=len(paths),resolved_references=references,
                concept_spans=len(json.loads((PACK/'concept-matrix.json').read_text())),
                installed='NOT_INSTALLED',native_injection='NOT_VERIFIED',execution_authority='NONE')


def bootstrap(owner):
    receipt=check()
    if owner not in COUNTS:raise ValueError('ORIGINAL_OWNER_REQUIRED')
    m=json.loads((PACK/'manifest.json').read_text())
    return dict(**receipt,owner=owner,load_paths=[str(PACK/a['entry']) for a in m['assignments'] if a['owner']==owner],
                card=(PACK/'agents'/owner/'BOOTSTRAP.md').read_text(),
                manifest_sha256=hashlib.sha256((PACK/'manifest.json').read_bytes()).hexdigest())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['check','bootstrap'])
    p.add_argument('--agent',choices=sorted(COUNTS));a=p.parse_args()
    print(json.dumps(check() if a.action=='check' else bootstrap(a.agent),indent=2))
