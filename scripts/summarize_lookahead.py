"""Summarize native CSV and retained native table when its CSV row is absent."""
import csv
import re
import sys
from foundation_common import paths, read, write, sha


def main(run_id):
    out, _ = paths(run_id); rows = []
    for record in read(out/'lookahead-checks.json')['checks']:
        name = record['strategy']; log = out/(name+'-lookahead.txt'); csv_path = out/(name+'-lookahead.csv')
        exported = list(csv.DictReader(csv_path.open())) if csv_path.exists() else []
        result = dict(record, csv_sha256=sha(csv_path) if csv_path.exists() else None, exported_rows=len(exported))
        if exported:
            item = exported[0]
            result.update(signals=int(item['total_signals']), has_bias=item['has_bias'] != 'False', evidence='NATIVE_CSV')
        else:
            match = re.search(r'│\s*[^│]+\s*│\s*'+re.escape(name)+r'\s*│\s*(No|Yes)\s*│\s*(\d+)\s*│\s*(\d+)\s*│\s*(\d+)\s*│', log.read_text())
            if match:
                result.update(signals=int(match.group(2)), has_bias=match.group(1) != 'No', evidence='RETAINED_NATIVE_TEXT_TABLE',
                    export_limitation='Pinned native exporter wrote a header-only CSV for this inherited strategy; actual table and log retained')
            else:
                result.update(signals=0, has_bias=None, evidence='INSUFFICIENT_OR_FAILED_NATIVE_DIAGNOSTIC')
        rows.append(result)
    write(out/'lookahead-summary.json', dict(checks=rows,
        qualified=False, limits='Inspected development diagnostic with small samples; external causal ranking also requires prefix invariance. No universal no-leakage claim.'))
    print(rows)


if __name__ == '__main__': main(sys.argv[1])
