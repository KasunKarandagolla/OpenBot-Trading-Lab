#!/usr/bin/env bash
set -euo pipefail
umask 077
if (( $# < 2 || $# > 3 )); then
  echo 'Usage: bash scripts/lab-shared-worker.sh EXISTING_MATPLOTLIB_CACHE OPENBOT_SHARED [MAX_SECONDS]' >&2
  exit 2
fi
repo="$(cd "$(dirname "$0")/.." && pwd -P)"
cache="$(realpath -e "$1")"
shared="$(realpath -e "$2")"
test -d "$cache/matplotlib"
test "$(basename "$shared")" = Shared
test "$(basename "$(dirname "$shared")")" = OpenBot
mkdir -p "$shared/TradingLab-Workflow-v2"
# Public Internet access; only this add-on namespace is writable/mounted.
# No home directory, credential file, OpenBot profile, socket or shell RPC mount.
exec docker run --rm --pull=never --read-only --tmpfs /tmp \
  --cap-drop=ALL --security-opt=no-new-privileges --user "$(id -u):$(id -g)" \
  -e PYTHONDONTWRITEBYTECODE=1 -e MPLCONFIGDIR=/tmp/mpl -e PYTHONPATH=/chart-deps:/lab/scripts \
  --mount "type=bind,source=$cache,target=/chart-deps,readonly" \
  --mount "type=bind,source=$repo,target=/lab,readonly" \
  --mount "type=bind,source=$shared/TradingLab-Workflow-v2,target=/shared/TradingLab-Workflow-v2" \
  --workdir /lab --entrypoint python \
  freqtradeorg/freqtrade@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7 \
  -m trading_lab.workflow serve /shared/TradingLab-Workflow-v2 --max-seconds "${3:-300}"
