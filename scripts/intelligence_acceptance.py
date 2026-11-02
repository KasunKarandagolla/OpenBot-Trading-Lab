"""Read-only final evidence checks; no network, source acquisition or backtests.

Usage: python3 scripts/intelligence_acceptance.py intelligence-003 intelligence-001
Native command logs must already be copied into each evidence directory.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from foundation_common import ROOT,read,sha,verify,write


def diagnostic(out):
    names=['IntelligenceRegimeV2','IntelligenceTargetV2','IntelligenceEntryV2']
    statuses={}
    for path in out.glob('*command.txt'):
        for name,code in re.findall(r'Native lookahead (Intelligence\w+V2) exit (\d+)',path.read_text()):
            statuses[name]=int(code)
    checks=[]
    for name in names:
        path=out/(name+'-lookahead.csv'); log=out/(name+'-lookahead.txt')
        with path.open(newline='') as file: rows=list(csv.DictReader(file))
        text=log.read_text()
        status='INSUFFICIENT_SIGNALS' if not rows or 'too few trades' in text else 'BIAS_DETECTED' if any(r['has_bias'].lower()=='true' for r in rows) else 'NO_DETECTED_BIAS_IN_REPORTED_SAMPLE'
        checks.append(dict(strategy=name,command_exit=statuses.get(name),status=status,
            total_signals=sum(int(r.get('total_signals') or 0) for r in rows),csv_rows=rows,
            log_sha256=sha(log),csv_sha256=sha(path)))
    result=dict(checks=checks,all_commands_exited_zero=all(c['command_exit']==0 for c in checks),
        all_variants_diagnostically_qualified=all(c['status']=='NO_DETECTED_BIAS_IN_REPORTED_SAMPLE' for c in checks),
        interpretation='A zero command exit is not a passing diagnostic when no signals were analyzed. Tiny development samples do not prove universal absence of bias.')
    write(out/'diagnostic-qualification.json',result)
    return result


def main(current,control):
    out,_,spec=verify(current); previous,_,_=verify(control)
    portfolios=[]
    for name in spec['strategies']:
        a=read(previous/'native-results'/(name+'.json'))['strategy'][name]['trades']
        b=read(out/'native-results'/(name+'.json'))['strategy'][name]['trades']
        portfolios.append(dict(strategy=name,trades=len(b),all_native_trade_fields_identical=a==b))
    checks=[]
    for path in sorted((ROOT/'evidence').rglob('artifact-hashes.sha256')):
        if 'additional-2' in path.parts: continue
        lines=[line.split(maxsplit=1) for line in path.read_text().splitlines() if line.strip()]
        good=sum((ROOT/name.strip().lstrip('*')).exists() and sha(ROOT/name.strip().lstrip('*'))==digest for digest,name in lines)
        checks.append(dict(manifest=str(path.relative_to(ROOT)),entries=len(lines),passed=good))
    freezes=[]
    for name in ['session-1','session-2','session-3','bonus']:
        path=ROOT/'evidence'/name/'freeze.sha256'
        rows=[line.split(maxsplit=1) for line in path.read_text().splitlines() if line.strip()]
        freezes.append(dict(manifest=str(path.relative_to(ROOT)),entries=len(rows),all_match=all(sha(ROOT/name.strip())==digest for digest,name in rows)))
    economics=read(out/'economic-report.json')
    diagnoses={current:diagnostic(out),control:diagnostic(previous)}
    snapshot=read(out/'openbot/research-snapshot.json'); manifest=read(out/'openbot/manifest.json')
    reader_ok=sha(out/'openbot/research-snapshot.json')==manifest['snapshot_sha256'] and len(snapshot['candidates'])<=200 and (out/'openbot/research-snapshot.json').stat().st_size<=1000000 and snapshot['orders_created'] is False
    tests=(ROOT/'evidence/additional-2/tests-full.txt').read_text()
    tests_ok=bool(re.search(r'Ran 137 tests.*\n\nOK\s*$',tests,re.S))
    okay=all(p['all_native_trade_fields_identical'] for p in portfolios) and all(c['entries']==c['passed'] for c in checks) and all(f['all_match'] for f in freezes) and economics['all_order_accounting_reconciles'] and economics['repaired_source_funding_within_bounds'] and reader_ok and tests_ok
    obj=dict(schema_version=2,engineering_evidence_checks='PASS' if okay else 'FAIL',
        economic_qualification='BLOCKED',native_trade_field_replay=portfolios,prior_artifacts=checks,prior_freezes=freezes,
        independent_order_accounting_reconciles=economics['all_order_accounting_reconciles'],
        repaired_funding_within_source_bounds=economics['repaired_source_funding_within_bounds'],
        bounded_reader_hash_check=reader_ok,tests_full_137_pass=tests_ok,diagnostics=diagnoses,
        persistent_paper_started=False,orders_created=False,
        limitations=['October already inspected; current-survivor membership','No historical genuine flow/news/depth/queue or original receipt clocks',
            '15m range fills cannot prove sub-bar five-minute expiry','Entry native lookahead has insufficient samples; never count zero samples as no bias',
            'One positive routed trade is not an economic edge; reserved future holdout untouched'])
    write(ROOT/'evidence/additional-2/acceptance.json',obj)
    print(json.dumps(dict(engineering=obj['engineering_evidence_checks'],portfolios=len(portfolios),
        native_trade_records=sum(p['trades'] for p in portfolios),prior_artifact_entries=sum(c['entries'] for c in checks),
        reader_records=len(snapshot['candidates']),economic_qualification='BLOCKED'),indent=2))
    if not okay: raise SystemExit(1)


if __name__=='__main__': main(*sys.argv[1:])
