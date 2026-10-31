#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec docker compose -f deploy/freqtrade/compose.bonus.yaml run --rm --no-deps bonus "$@"
