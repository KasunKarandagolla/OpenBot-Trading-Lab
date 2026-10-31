#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Registration writes reviewed source descriptors using the owner's checkout.
if [[ "${1:-}" == cohort-register ]]; then
 exec python3 scripts/research_session3.py "$@"
fi
if [[ "${1:-}" == test ]]; then
 mkdir -p user_data/runtime
 docker compose -f deploy/freqtrade/compose.yaml --profile tools --profile ui --profile paper config --format json > user_data/runtime/compose-safety.json
fi
# Separate additive research service; never starts paper, UI or order endpoints.
if [[ -n "${LAB_EXEC_CONTAINER:-}" ]]; then
 exec docker exec "$LAB_EXEC_CONTAINER" python /lab/scripts/research_session3.py "$@"
fi
exec docker compose -f deploy/freqtrade/compose.session3.yaml run --rm --no-deps research3 "$@"
