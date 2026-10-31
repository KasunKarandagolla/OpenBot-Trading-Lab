# Operator commands and native equivalents

Run from repository root in Linux/WSL2. Install Docker/Compose, Git and Python 3 first. See the root README for explanations, source restrictions, paper downtime and passwords. No engine or paper process is started by installation/tests.

```bash
python3 scripts/init_runtime.py
docker compose -f deploy/freqtrade/compose.yaml config --quiet
docker compose -f deploy/freqtrade/compose.yaml run --rm freqtrade --version
docker compose -f deploy/freqtrade/compose.yaml run --rm freqtrade test-pairlist \
  --config /lab/configs/scanner.json --print-json
docker compose -f deploy/freqtrade/compose.yaml run --rm --entrypoint python freqtrade \
  /lab/scripts/scan_export.py
```

For the exporter, capture the native stdout first at `user_data/logs/scan-native.log`; `./scripts/lab.sh scan` does this automatically. Native top-60 candidates are filtered to at most 20 current crypto contracts by the adapter; it never invokes `trade` or order APIs. Age uses public launch metadata, not deep candles.

After source-rights review, use `./scripts/lab.sh download`, which checks an empty sample directory and runs these bounded operations:

```bash
docker compose -f deploy/freqtrade/compose.yaml run --rm --entrypoint python freqtrade \
  /lab/scripts/save_contracts.py
docker compose -f deploy/freqtrade/compose.yaml run --rm freqtrade download-data \
  --config /lab/configs/research.json --datadir /lab/user_data/data/research/gate \
  --trading-mode futures --timeframes 15m 1h --timerange 20260726-20261030
docker compose -f deploy/freqtrade/compose.yaml run --rm --entrypoint python freqtrade \
  /lab/scripts/seal_data.py
docker compose -f deploy/freqtrade/compose.yaml run --rm --entrypoint python freqtrade \
  /lab/scripts/validate_data.py
```

Range restriction removes only observations outside the frozen UTC range; original acquisition and sealed hashes are recorded. Funding's native file schema is `date,funding_rate`; it is not OHLCV and negative rates are valid. File timeframe is 1h for engine compatibility; observed event cadence is 8h. Mark volume is normally zero and is not liquidity evidence. No candle gaps are repaired. Existing immutable sample hashes are checked before each backtest. If the fixed start ages beyond Gate's 10,000 most recent candle retention, do not substitute an archive or new dates silently: preserve the source sample or preregister a separate run.

```bash
docker compose -f deploy/freqtrade/compose.yaml run --rm --no-deps freqtrade backtesting \
  --config /lab/configs/research.json --datadir /lab/user_data/data/research/gate \
  --strategy TrendPullbackBaselineV1 --timerange 20260730-20261030 --fee 0.0006 \
  --enable-protections --cache none --export trades \
  --backtest-directory /lab/user_data/backtest_results
./scripts/lab.sh report
./scripts/lab.sh lookahead
./scripts/lab.sh test
```

Use the wrapper for the pre-backtest hash validation and current Compose-config safety test. Never change a frozen strategy to improve an already inspected result. Native lookahead diagnostics deliberately change backtest wallet/stake and disable protections to reduce false positives; they remain offline simulations and are not the performance run.

UI and paper use a private local API overlay, different public configs and mutually exclusive port 8080:

```bash
docker compose -f deploy/freqtrade/compose.yaml stop paper
docker compose -f deploy/freqtrade/compose.yaml --profile ui up -d ui
# Visit http://127.0.0.1:8080 and sign in as owner using private api.json.
docker compose -f deploy/freqtrade/compose.yaml stop ui
# Only if deliberately operating paper simulation:
docker compose -f deploy/freqtrade/compose.yaml --profile paper up -d paper
docker compose -f deploy/freqtrade/compose.yaml logs --tail 100 paper
docker compose -f deploy/freqtrade/compose.yaml stop paper
```

Public templates have no real/testnet exchange keys. UI secrets are generated locally with 0600 permissions. All services run the pre-engine guard. Do not bypass the entrypoint or inject `FREQTRADE__` environment overrides. Official API authentication is required for protected endpoints; `/api/v1/ping` and the static UI entry point may be public locally. API authorization is owner administration, not an agent read-only boundary. Forced entry is disabled.

Stop before backups. Copy `user_data/paper.sqlite`, frozen strategy/config/protocol and the private API config to owner-controlled backup storage. Verify restoration before extended operation. Stopping does not close paper trades; Freqtrade cannot manage them during sleep, power loss or process outage. DB recovery and long-running reliability remain owner-host acceptance items.

## Cloud execution details

Codex Cloud uses a session HTTP proxy and additional CA. A local ignored `work/compose.cloud.yaml` mounted the system CA read-only and supplied the reachable proxy hostname. A private ignored `user_data/runtime/cloud.json` added the inherited proxy, `requests_trust_env`, `aiohttp_trust_env` and CA path to CCXT. TLS verification remained enabled. This does not change source geography or bypass exchange denials.

Docker VFS on the approximately 8 GB Cloud filesystem duplicates large image layers per container. After initial concurrent containers exhausted disk, temporary runs reused **one** official-image runner via `LAB_EXEC_CONTAINER=openbot-s1-runner ./scripts/lab.sh ...`. That optional variable uses `docker exec` against an already running owner-selected container. The normal path remains Compose run. The runner had no exchange credentials; only proxy variables were passed explicitly. UI and paper Compose services were separately exercised after removing the runner to free space. Cloud configuration/hostnames/credentials are not deployed to the owner machine.

If reproducing in another managed Cloud session, follow its current network skill and CA settings; do not reuse old proxy addresses. No TLS disabling, host-network workaround or unrestricted exchange credential forwarding is needed. Owner-host installation, browser rendering, jurisdiction and persistent operation require separate verification.

Rollback: stop both services, preserve DB/data/private config, check out the previous approved commit or base SHA `2343053ce68f6fff4525c5b67771ea445deb3779`. Remove only this project's disposable containers with `docker compose -f deploy/freqtrade/compose.yaml down`. Never prune unrelated Docker state or delete the only research/DB copy.
