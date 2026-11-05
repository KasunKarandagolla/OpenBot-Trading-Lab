#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

image=freqtradeorg/freqtrade@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7
local_data=user_data/data/local_recovery
mkdir -p "$local_data/runtime"
if [[ "${1:-}" == scan || "${1:-}" == replay ]] && [[ "${2:-}" == holdout ]]; then
    if [[ ! -s "$local_data/validation/native-combined-through/result.json" ]]; then
        printf 'Complete the combined validation replay before opening holdout.\n' >&2
        exit 2
    fi
fi
replay_env=()
if [[ "${1:-}" == replay ]]; then
    replay_env=(-e "FREQTRADE__USER_DATA_DIR=/lab/$local_data/runtime")
fi
runtime=(docker run --rm --pull=never --network=none --cap-drop=ALL
    --security-opt=no-new-privileges --user "$(id -u):$(id -g)"
    -e MPLCONFIGDIR=/tmp/openbot-matplotlib
    "${replay_env[@]}"
    -v "$PWD:/lab:ro" -v "$PWD/$local_data:/lab/$local_data"
    -w /lab --entrypoint python "$image")

case "${1:-}" in
    convert) "${runtime[@]}" scripts/local_recovery_convert.py ;;
    freeze) "${runtime[@]}" scripts/local_recovery_backtest.py freeze ;;
    scan) "${runtime[@]}" scripts/local_recovery_scan.py "${@:2}" ;;
    replay) "${runtime[@]}" scripts/local_recovery_backtest.py "${@:2}" ;;
    charts) "${runtime[@]}" scripts/local_recovery_charts.py "${@:2}" ;;
    pilot) "${runtime[@]}" scripts/local_recovery_visual_pilot.py "${@:2}" ;;
    report) "${runtime[@]}" scripts/local_recovery_report.py "${@:2}" ;;
    test) "${runtime[@]}" -m unittest discover -s tests -p "${2:-test_local_recovery.py}" -v ;;
    *) printf 'Usage: %s {convert|freeze|scan|replay|charts|pilot|report|test}\n' "$0" >&2; exit 2 ;;
esac
