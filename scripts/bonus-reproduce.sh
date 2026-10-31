#!/usr/bin/env bash
# New isolated checkout and output tree; preserve committed primary evidence.
set -euo pipefail
cd "$(dirname "$0")/.."
run_id="${1:-}"
if [[ ! "$run_id" =~ ^[a-z0-9][a-z0-9-]{2,40}$ ]]; then
  echo 'Usage: ./scripts/bonus-reproduce.sh new-run-id' >&2
  exit 2
fi
repro_path="work/bonus-reproductions/$run_id"
if [[ -e "$repro_path" ]]; then
  echo 'Reproduction ID already exists; preserve it and use a new ID.' >&2
  exit 2
fi
mkdir -p "$repro_path"
git archive HEAD | tar -x -C "$repro_path"
python3 - "$repro_path" <<'PY'
from pathlib import Path
import shutil,sys
original=Path.cwd();target=original/sys.argv[1];out=target/'evidence/bonus'
# Remove only archived copies of bonus outputs in the newly created checkout.
for p in list(out.iterdir()):
    if p.name in {'freeze.sha256','registration.json','source-compatibility.md'}:continue
    if p.is_dir():shutil.rmtree(p)
    else:p.unlink()
net=original/'user_data/runtime/cloud.json'
if net.exists():
    (target/'user_data/runtime').mkdir(parents=True,exist_ok=True)
    shutil.copyfile(net,target/'user_data/runtime/cloud.json')
# Prefer retained exact source bytes. Otherwise the public acquisition runs anew.
raw=original/'user_data/data/bonus'
if raw.exists():
    shutil.copytree(raw,target/'user_data/data/bonus')
    for name in ['source-manifest.json','detail-manifest.json']:
        p=original/'evidence/bonus'/name
        if p.exists():shutil.copyfile(p,out/name)
print('Isolated reproduction:',target)
PY
cd "$repro_path"
mkdir -p user_data/runtime
docker compose -f deploy/freqtrade/compose.yaml --profile tools --profile ui --profile paper config --format json > user_data/runtime/compose-safety.json
for action in acquire restore-prior-raw schedule run economics reconcile funding-audit test; do
  ./scripts/lab-bonus.sh "$action"
done
