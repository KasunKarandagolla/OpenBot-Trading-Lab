#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
image='freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7'
runner="openbot-setup-$$"
docker run -d --rm --name "$runner" --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" --mount "type=bind,src=$PWD,dst=/lab" \
  --mount type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/codex-ca.crt,readonly \
  -w /lab -e PYTHONPATH=/lab/scripts -e SSL_CERT_FILE=/run/codex-ca.crt \
  -e REQUESTS_CA_BUNDLE=/run/codex-ca.crt --entrypoint sleep "$image" infinity >/dev/null
trap 'docker rm -f "$runner" >/dev/null 2>&1 || true' EXIT
action=${1:?tests|acquire|prepare|native|matrix|report|export};shift
case "$action" in
  tests) docker exec "$runner" python -m unittest discover -s tests -p test_setup.py -v ;;
  acquire) docker exec "$runner" python scripts/setup_data.py ;;
  prepare) docker exec "$runner" python scripts/setup_prepare.py ;;
  native) docker exec "$runner" python scripts/setup_verify.py
          docker exec "$runner" python scripts/setup_native.py "$@" ;;
  matrix) docker exec "$runner" python scripts/setup_verify.py
          docker exec "$runner" python scripts/setup_matrix.py ;;
  report) docker exec "$runner" python scripts/setup_report.py ;;
  export) docker exec "$runner" python scripts/setup_export.py ;;
  *) echo 'Unknown historical-only action' >&2;exit 2 ;;
esac
