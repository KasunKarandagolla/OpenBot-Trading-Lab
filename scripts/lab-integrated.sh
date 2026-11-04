#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
image='freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7'
runner="openbot-integrated-$$"
docker run -d --rm --name "$runner" --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" --mount "type=bind,src=$PWD,dst=/lab" \
  --mount type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/codex-ca.crt,readonly \
  -w /lab -e PYTHONPATH=/lab/scripts -e SSL_CERT_FILE=/run/codex-ca.crt \
  -e REQUESTS_CA_BUNDLE=/run/codex-ca.crt --entrypoint sleep "$image" infinity >/dev/null
trap 'docker rm -f "$runner" >/dev/null 2>&1 || true' EXIT
action=${1:?acquire|forensics|prepare|native|report|tests};shift
case "$action" in
  acquire) docker exec "$runner" python scripts/integrated_data.py "$@" ;;
  native) docker exec "$runner" python scripts/integrated_native_audited.py "$@" ;;
  forensics|prepare|report) docker exec "$runner" python "scripts/integrated_${action}.py" "$@" ;;
  tests) docker exec "$runner" python -m unittest discover -s tests -p 'test_integrated*.py' -v ;;
  matrix)
    docker exec "$runner" python scripts/integrated_native_audited.py control-v4 --replay-id order-audit
    for variant in control-pr12 market-selector ema-context entry-passive thesis-exit take-profit integrated five-15m-response five-early five-passive; do
      docker exec "$runner" python scripts/integrated_native_audited.py "$variant"
    done
    for variant in control-v4 ema-context entry-passive thesis-exit integrated; do
      docker exec "$runner" python scripts/integrated_native_audited.py "$variant" --fee .00175
    done
    for variant in control-v4 ema-context entry-passive integrated; do
      docker exec "$runner" python scripts/integrated_native_audited.py "$variant" --execution through
    done
    docker exec "$runner" python scripts/integrated_regression.py
    docker exec "$runner" python scripts/integrated_report.py
    ;;
  regression) docker exec "$runner" python scripts/integrated_regression.py ;;
  verify) docker exec "$runner" python scripts/integrated_verify.py ;;
  checks) docker exec "$runner" python scripts/integrated_extra_checks.py ;;
  finalize)
    docker exec "$runner" python scripts/integrated_native_audited.py control-v4 --replay-id final-seal
    docker exec "$runner" python scripts/integrated_native_audited.py integrated --replay-id final-seal
    docker exec "$runner" python scripts/integrated_regression.py
    docker exec "$runner" python scripts/integrated_report.py
    ;;
  *) echo 'Unknown research-only action' >&2;exit 2 ;;
esac
