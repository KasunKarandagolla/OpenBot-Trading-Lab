#!/usr/bin/env bash
# Public capture, offline build, optional validated Shared staging. No signing.
set -euo pipefail
umask 077
if (( $# < 2 || $# > 3 )); then
  echo 'Usage: bash scripts/lab-five-agent.sh NEW_RUN_DIRECTORY EXISTING_MATPLOTLIB_CACHE [OPENBOT_SHARED]' >&2
  exit 2
fi
repo="$(cd "$(dirname "$0")/.." && pwd -P)"
cache="$(realpath -e "$2")"
test -d "$cache/matplotlib"
mkdir -- "$1"
run="$(cd "$1" && pwd -P)"
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$repo/scripts" \
  /usr/bin/python3 -m trading_lab.workflow capture "$run/raw" --universe 24 --shortlist 4 > "$run/capture-summary.json"
docker run --rm --pull=never --network=none --read-only --tmpfs /tmp \
  --cap-drop=ALL --security-opt=no-new-privileges --user "$(id -u):$(id -g)" \
  -e PYTHONDONTWRITEBYTECODE=1 -e MPLCONFIGDIR=/tmp/mpl -e PYTHONPATH=/chart-deps:/lab/scripts \
  --mount "type=bind,source=$cache,target=/chart-deps,readonly" \
  --mount "type=bind,source=$repo,target=/lab,readonly" \
  --mount "type=bind,source=$run,target=/run" --workdir /lab --entrypoint python \
  freqtradeorg/freqtrade@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7 \
  -m trading_lab.workflow build /run/raw /run/packets > "$run/build-summary.txt"
if (( $# == 3 )); then
  env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$repo/scripts" \
    /usr/bin/python3 -m trading_lab.workflow stage "$run" "$3" "$(basename "$run")" > "$run/stage-receipt.json"
fi
cat "$run/index.json"
