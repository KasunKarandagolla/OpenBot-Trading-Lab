#!/usr/bin/env bash
# Independent checkout and outputs. No server/trade/private API action exists.
set -euo pipefail
cd "$(dirname "$0")/.."
run_id="${1:-}"
[[ "$run_id" =~ ^[a-z0-9][a-z0-9-]{2,40}$ ]] || { echo 'Use a new lowercase run ID' >&2; exit 2; }
task_root="$PWD"
repro="$task_root/work/master-reproductions/$run_id"
[[ ! -e "$repro" ]] || { echo 'Preserve existing run; choose a new ID' >&2; exit 2; }
mkdir -p "$(dirname "$repro")"
git clone --quiet --shared "$task_root" "$repro"
git -C "$repro" checkout --quiet --detach HEAD
python3 - "$repro" "$task_root" <<'PY'
from pathlib import Path
import shutil,sys
target=Path(sys.argv[1]);original=Path(sys.argv[2]);out=target/'evidence/master-audit'
keep={'registration.json','ablation-registration.json','ablation-mechanical-amendment.json','ablation-attribution-supplement.json'}
for p in out.iterdir():
    if p.name in keep:continue
    if p.is_dir():shutil.rmtree(p)
    else:p.unlink()
raw=original/'user_data/data/bonus'
if raw.exists():
    shutil.copytree(raw,target/'user_data/data/bonus')
    shutil.copyfile(original/'evidence/master-audit/source-identity.json',out/'source-identity.json')
PY
cd "$repro"
image='freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7'
native() {
  docker run --rm --entrypoint python -v "$repro:/lab" -v /etc/ssl/certs/ca-certificates.crt:/run/proxy-ca.pem:ro \
    -e SSL_CERT_FILE=/run/proxy-ca.pem -e REQUESTS_CA_BUNDLE=/run/proxy-ca.pem -w /lab "$image" "$@"
}
python3 scripts/master_preflight.py source-001
native scripts/master_book_probe.py book-001
if [[ ! -f evidence/master-audit/source-identity.json ]]; then
  native scripts/master_native.py acquire > evidence/master-audit/native-acquisition.txt 2>&1
  native scripts/master_verify_sources.py
fi
python3 scripts/master_preservation.py
python3 scripts/master_restore_test_sources.py
mkdir -p user_data/runtime
docker compose -f deploy/freqtrade/compose.yaml --profile tools --profile ui --profile paper config --format json > user_data/runtime/compose-safety.json
native scripts/master_review.py
native scripts/master_funding_probe.py
native scripts/master_run_ablations.py
native scripts/master_compare.py
native -m unittest discover -s tests -v > evidence/master-audit/tests-full.txt 2>&1
python3 scripts/master_charts.py
echo "Completed isolated research evidence: $repro/evidence/master-audit"
