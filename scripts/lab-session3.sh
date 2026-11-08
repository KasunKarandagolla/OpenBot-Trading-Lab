#!/usr/bin/env bash
# Owner-invoked research only. No resident process, account calls or activation.
set -euo pipefail
cd "$(dirname "$0")/.."
s3_python=${LAB_PY:-python3}
s3_image=freqtradeorg/freqtrade@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7
export PYTHONPATH="$PWD/scripts:$PWD/tests"
export MPLCONFIGDIR=${MPLCONFIGDIR:-/tmp/openbot-s3-matplotlib}
s3_state=${S3_STATE_ROOT:-/tmp/openbot-v3-owner-research}
mkdir -p user_data/data/session3-native-runtime
native() {
    local strategy=$1 begin=$2 end=$3 out=$4 plans=${5:-} mode=${6:-through} fee=${7:-0.0005}
    case "$strategy" in BreakoutAcceptanceRetest|SweepReclaimReversal|BreakoutImmediate|SweepReclaimEarly|TrendPullbackBaselineV1|VWAPTrendContinuationV1|LiquiditySweepReversalV1) ;; *) printf 'Unknown research strategy\n' >&2; return 2;; esac
    local s3_job_key
    s3_job_key=$(printf '%s' "$out" | sha256sum)
    s3_job_key=${s3_job_key:0:16}
    local s3_job_dir="user_data/data/session3-native-runtime/$s3_job_key"
    mkdir -p "$s3_job_dir"
    local args=(scripts/session3_native.py "$strategy" --start "$begin" --end "$end" --out "$out" --mode "$mode" --fee "$fee")
    if [[ -n "$plans" ]]; then args+=(--plans "$plans"); fi
    docker run --rm --pull=never --network=none --cap-drop=ALL --security-opt=no-new-privileges \
        --user "$(id -u):$(id -g)" \
        -e FREQTRADE__USER_DATA_DIR="/lab/$s3_job_dir" \
        -e PYTHONPATH=/lab/scripts:/lab/user_data/strategies:/lab/research/session3_v3 \
        -v "$PWD:/lab:ro" -v "$PWD/user_data/data:/lab/user_data/data" \
        -v "$PWD/evidence/session3:/lab/evidence/session3" \
        -w /lab --entrypoint python "$s3_image" "${args[@]}"
}
case "${1:-}" in
    skills) "$s3_python" -m trading_lab.skills_v3 "${@:2}" ;;
    restore) "$s3_python" scripts/session3_restore.py "${@:2}" ;;
    prepare)
        docker run --rm --pull=never --network=none --cap-drop=ALL --security-opt=no-new-privileges \
            --user "$(id -u):$(id -g)" -v "$PWD:/lab:ro" \
            -v "$PWD/user_data/data:/lab/user_data/data" -w /lab --entrypoint python \
            "$s3_image" scripts/local_recovery_convert.py ;;
    scan|watch|tick|list|status|history|backup|refresh)
        "$s3_python" -m trading_lab.rehearsal --root "$s3_state" "$@" ;;
    replay)
        "$s3_python" -m trading_lab.rehearsal --root "$s3_state" "$@" ;;
    experiments) "$s3_python" scripts/session3_experiments.py "${@:2}" ;;
    native) native "${@:2}" ;;
    gate) "$s3_python" scripts/session3_gate.py "${@:2}" ;;
    verify) "$s3_python" scripts/session3_verify.py "${@:2}" ;;
    report) "$s3_python" scripts/session3_report.py "${@:2}" ;;
    matrix) "$s3_python" scripts/session3_matrix.py "${@:2}" ;;
    test)
        export OPENBOT_REAL_PACKET=${OPENBOT_REAL_PACKET:-$PWD/evidence/skills-v2/20261107/packet/AKEUSDT-20261107T091337-3bb65ec7d8}
        test -f "$OPENBOT_REAL_PACKET/MANIFEST.json"
        "$s3_python" -m unittest test_openbot_current test_binance_research_data test_local_recovery \
            test_trading_lab_workflow test_skill_integration test_watchlist test_session3_v3 -v ;;
    *) printf 'Usage: %s {skills|restore|prepare|scan|watch|replay|tick|list|history|status|backup|refresh|experiments|native|gate|verify|report|matrix|test}\n' "$0" >&2; exit 2 ;;
esac
