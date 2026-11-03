#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
image='freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7'
action=${1:-help}
runner="openbot-session4-$$"
args=(run -d --rm --name "$runner" --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" --mount "type=bind,src=$PWD,dst=/lab" -w /lab -e PYTHONPATH=/lab/scripts)
if [[ -n ${CODEX_PROXY_CERT:-} ]]; then
  args+=(--mount 'type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/codex-ca.crt,readonly' -e SSL_CERT_FILE=/run/codex-ca.crt -e REQUESTS_CA_BUNDLE=/run/codex-ca.crt)
fi
if [[ $action == help ]]; then
  echo 'Usage: lab-session4.sh research NEW_RUN_ID | replay NEW_LABEL BASE_VARIANT | paper limit|market [45..240 seconds] | restart limit|market [seconds] | tests'
  exit 0
fi
docker "${args[@]}" --entrypoint sleep "$image" infinity >/dev/null
trap 'docker rm -f "$runner" >/dev/null 2>&1 || true' EXIT
run() { docker exec "$runner" python "$@"; }
case "$action" in
  research)
    run_id=${2:?use a new bounded lowercase run ID}
    [[ $run_id =~ ^[a-z0-9][a-z0-9-]{2,32}$ ]] || exit 2
    for step in 'session4_market.py acquire' 'session4_research.py prepare' 'session4_research.py portfolios' 'session4_execution.py' 'session4_report.py report'; do
      read -r -a command <<< "$step"
      docker exec -e "SESSION4_RUN_ID=$run_id" "$runner" python "scripts/${command[0]}" "${command[@]:1}"
    done
    ;;
  replay)
    run scripts/session4_research.py native "${2:?new result label}" "${3:?base variant}"
    ;;
  paper|restart)
    run scripts/session4_runtime.py templates
    # No fallback to stale metadata if this public refresh fails.
    run scripts/session4_runtime.py refresh
    extra=(); [[ $action == restart ]] && extra+=(--restart)
    run scripts/session4_runtime.py "${2:?limit or market}" "${3:-150}" "${extra[@]}"
    ;;
  tests)
    run scripts/session4_runtime.py templates
    docker exec "$runner" python -m unittest discover -s tests -p test_session4.py -v
    ;;
  *) echo 'Unknown bounded session4 action' >&2; exit 2 ;;
esac
