#!/usr/bin/env bash
set -euo pipefail
umask 077

if (( $# < 2 || $# > 3 )); then
    echo 'Usage: bash scripts/lab-openbot-current.sh NEW_RUN_DIRECTORY MATPLOTLIB_CACHE [OPENBOT_SHARED]' >&2
    exit 2
fi

repo="$(cd "$(dirname "$0")/.." && pwd -P)"
deps="$(realpath -e "$2")"
test -d "$deps/matplotlib"
mkdir -- "$1"
run="$(cd "$1" && pwd -P)"
mkdir -- "$run/packets"
script=scripts/openbot_current_market.py
image=freqtradeorg/freqtrade@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7

env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$repo/$script" capture "$run/raw" |
    tee "$run/capture-summary.json"
docker run --rm --pull=never --network=none --cap-drop=ALL --security-opt=no-new-privileges \
    --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 -e MPLCONFIGDIR=/tmp/openbot-matplotlib \
    -e PYTHONPATH=/chart-deps --mount "type=bind,source=$deps,target=/chart-deps,readonly" \
    --mount "type=bind,source=$repo,target=/lab,readonly" \
    --mount "type=bind,source=$run/raw,target=/raw,readonly" \
    --mount "type=bind,source=$run/packets,target=/packets" \
    --workdir /lab --entrypoint python "$image" "$script" build /raw /packets |
    tee "$run/build-summary.json"

if (( $# == 3 )); then
    packets=("$run/packets/"*/)
    test "${#packets[@]}" = 1
    env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$repo/$script" stage "${packets[0]}" "$3" |
        tee "$run/wsl-stage-receipt.json"
fi
