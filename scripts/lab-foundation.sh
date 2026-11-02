#!/usr/bin/env bash
# Disposable official native runner, removed on exit. No persistent paper start.
set -euo pipefail
cd "$(dirname "$0")/.."
action="${1:-}"
run_id="${2:-}"
[[ "$run_id" =~ ^[a-z0-9][a-z0-9-]{2,40}$ ]] || { echo 'Usage: scripts/lab-foundation.sh {run|ACTION} NEW_RUN_ID' >&2; exit 2; }
image='freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7'
mkdir -p user_data/runtime
docker compose -f deploy/freqtrade/compose.yaml --profile tools --profile ui --profile paper config --quiet
docker compose -f deploy/freqtrade/compose.yaml --profile tools --profile ui --profile paper config --format json > user_data/runtime/foundation-compose.json
runner="openbot-foundation-$run_id"
if [[ -n "${LAB_FOUNDATION_CONTAINER:-}" ]]; then
  runner="$LAB_FOUNDATION_CONTAINER"
else
  ca_bundle="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
  docker run -d --name "$runner" --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
    --entrypoint sleep -v "$PWD:/lab" -v "$ca_bundle:/run/research-ca.pem:ro" \
    -e SSL_CERT_FILE=/run/research-ca.pem -e REQUESTS_CA_BUNDLE=/run/research-ca.pem -w /lab "$image" infinity >/dev/null
  trap 'docker rm -f "$runner" >/dev/null' EXIT
fi
native() { docker exec "$runner" python scripts/foundation.py "$@"; }
if [[ "$action" == run ]]; then
  for step in register doctor preflight scan acquire assess schedule backtest events report export lookahead ui-smoke dryrun-smoke; do
    echo "Foundation step: $step"
    native "$step" "$run_id"
  done
  docker exec "$runner" python -m unittest discover -s tests -p test_foundation_session1.py -v
else
  native "$action" "$run_id"
fi
