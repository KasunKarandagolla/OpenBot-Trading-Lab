#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
image='freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7'
runner="openbot-recovery-$$"
docker run -d --rm --name "$runner" --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" --mount "type=bind,src=$PWD,dst=/lab" \
  --mount type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/codex-ca.crt,readonly \
  -w /lab -e PYTHONPATH=/lab/scripts -e SSL_CERT_FILE=/run/codex-ca.crt \
  -e REQUESTS_CA_BUNDLE=/run/codex-ca.crt --entrypoint sleep "$image" infinity >/dev/null
trap 'docker rm -f "$runner" >/dev/null 2>&1 || true' EXIT
action=${1:?tests|diagnose|replay|report|matrix};shift
case "$action" in
  tests) docker exec "$runner" python -m unittest discover -s tests -p test_recovery.py -v ;;
  diagnose) docker exec "$runner" python scripts/recovery_diagnose.py paths ;;
  replay) docker exec "$runner" python scripts/recovery_native.py "$@" ;;
  report) docker exec "$runner" python scripts/recovery_report.py
          docker exec "$runner" python scripts/recovery_sources.py ;;
  matrix) docker exec "$runner" python scripts/recovery_experiments.py "${1:?primary|null|execution}" ;;
  *) echo 'Unknown research-only action' >&2;exit 2 ;;
esac
