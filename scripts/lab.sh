#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
compose=(docker compose -f deploy/freqtrade/compose.yaml)
# Cloud-only proxy trust override is local and never committed.
if [[ -f work/compose.cloud.yaml ]]; then compose+=(-f work/compose.cloud.yaml); fi
mkdir -p user_data/{runtime,data/research,data/cache,backtest_results,logs}
ft() {
 local args=("$@")
 if [[ "$1" != --version && -f user_data/runtime/cloud.json ]]; then args+=(--config /lab/user_data/runtime/cloud.json); fi
 if [[ -n "${LAB_EXEC_CONTAINER:-}" ]]; then docker exec "$LAB_EXEC_CONTAINER" python /lab/scripts/guard.py "${args[@]}";
 else "${compose[@]}" run --rm --no-deps freqtrade "${args[@]}"; fi
}
py() {
 if [[ -n "${LAB_EXEC_CONTAINER:-}" ]]; then docker exec "$LAB_EXEC_CONTAINER" python "$@";
 else "${compose[@]}" run --rm --no-deps --entrypoint python freqtrade "$@"; fi
}
research=(--config /lab/configs/research.json --datadir /lab/user_data/data/research/gate)
case "${1:-}" in
 research-download)
   test -f evidence/session-1/source-rights.md
   if find user_data/data/session-2 -name '*.feather' -print -quit 2>/dev/null | rg -q .; then
     echo 'Session 2 data already exist; preserving them. Use research-all to verify and run.' >&2; exit 2
   fi
   py /lab/scripts/save_contracts.py
   ft download-data --config /lab/configs/research.json --datadir /lab/user_data/data/session-2/gate --trading-mode futures --timeframes 15m 1h --timerange 20260726-20261030
   py /lab/scripts/data_session2.py
   ;;
 research-all) py /lab/scripts/research_session2.py run ;;
 compare) py /lab/scripts/research_session2.py compare ;;
 strategy-info)
   case "${2:-}" in TrendPullbackBaselineV1|VWAPTrendContinuationV1|LiquiditySweepReversalV1) ;;
     *) echo 'Unknown registered strategy' >&2; exit 2;; esac
   py /lab/scripts/research_session2.py info "$2"
   ;;
 research-lookahead)
   py /lab/scripts/data_session2.py --verify
   for spec in 'vwap VWAPTrendContinuationV1' 'sweep LiquiditySweepReversalV1'; do
     read -r suffix name <<< "$spec"
     ft lookahead-analysis --config "/lab/configs/research-${suffix}.json" --datadir /lab/user_data/data/session-2/gate --timerange 20260730-20261030 --fee 0.0006 --minimum-trade-amount 5 --targeted-trade-amount 20 --lookahead-analysis-exportfilename "/lab/user_data/lookahead-${suffix}.csv" > "evidence/session-2/lookahead-${suffix}.txt" 2>&1
   done
   ;;
 doctor)
   "${compose[@]}" config --quiet
   ft --version
   py /lab/scripts/check_project.py
   ;;
 scan)
   ft test-pairlist --config /lab/configs/scanner.json --print-json | tee user_data/logs/scan-native.log
   py /lab/scripts/scan_export.py
   ;;
 download)
   test -f evidence/session-1/source-rights.md
   if find user_data/data/research -name '*.feather' -print -quit | rg -q .; then
     echo 'Research data already exist. Preserving sample; validate it, or use a separate clone for a new download.' >&2; exit 2
   fi
   py /lab/scripts/save_contracts.py
   ft download-data "${research[@]}" --trading-mode futures --timeframes 15m 1h --timerange 20260726-20261030
   py /lab/scripts/seal_data.py
   py /lab/scripts/validate_data.py
   ;;
 validate) py /lab/scripts/validate_data.py ;;
 backtest)
   py /lab/scripts/validate_data.py --verify
   ft backtesting "${research[@]}" --strategy TrendPullbackBaselineV1 --timerange 20260730-20261030 --fee 0.0006 --enable-protections --cache none --export trades --backtest-directory /lab/user_data/backtest_results
   ;;
 lookahead)
   py /lab/scripts/validate_data.py --verify
   ft lookahead-analysis "${research[@]}" --strategy TrendPullbackBaselineV1 --timerange 20260730-20261030 --fee 0.0006 --minimum-trade-amount 20 --targeted-trade-amount 40 --lookahead-analysis-exportfilename /lab/user_data/lookahead.csv
   ;;
 report) py /lab/scripts/report.py ;;
 ui-up)
   python3 scripts/init_runtime.py
   "${compose[@]}" stop paper
   "${compose[@]}" --profile ui up -d ui
   ;;
 ui-down) "${compose[@]}" stop ui ;;
 paper-up)
   python3 scripts/init_runtime.py
   py /lab/scripts/check_project.py
   "${compose[@]}" stop ui
   "${compose[@]}" --profile paper up -d paper
   ;;
 paper-down) "${compose[@]}" stop paper ;;
 logs) "${compose[@]}" logs --tail 100 ui paper ;;
 test) "${compose[@]}" config --format json > user_data/runtime/compose-safety.json; py -m unittest discover -s /lab/tests -v ;;
 *) echo 'Usage: ./scripts/lab.sh {research-download|research-all|compare|strategy-info NAME|research-lookahead|doctor|scan|download|validate|backtest|lookahead|report|ui-up|ui-down|paper-up|paper-down|logs|test}' >&2; exit 2 ;;
esac
