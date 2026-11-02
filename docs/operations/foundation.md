# Additional Session 1: operate the native research foundation

The owner's latest five-additional-session direction supersedes the original tiny/synthetic-only roadmap. This session implements research and disposable startup checks. Persistent owner-host trading requires a separate decision and operational qualification.

## Setup and complete run

Use Docker Engine/Desktop + Compose v2, Python 3 and Git. Check out `codex/additional-1-unified-research`, pull the Compose image, then:

```bash
docker compose -f deploy/freqtrade/compose.yaml pull
./scripts/lab-foundation.sh run owner-research-001
```

The wrapper uses the pinned official image/digest in Compose, creates one temporary container, mounts the existing CA bundle with TLS verification enabled and removes its own container on exit. No exchange credentials are forwarded. Cloud Docker's configured reachable proxy is retained; a proxy hostname usable only outside Docker is insufficient. Native synchronous Requests needs `requests_trust_env`; native async CCXT needs the configured CA file. Both are supplied by this workflow.

The command has bounded data/markets and no paid dependency. It can take several minutes. Current source availability and public rate limits can change. If the image is not local, pull requires additional time/disk. A new run ID is mandatory. Source preservation/reuse avoids redownloading an identical retained historical sample. Binance 451 is recorded once per run and Gate continues; there is no regional workaround or venue blending.

## Actions and files

Every action is available as `./scripts/lab-foundation.sh ACTION RUN_ID`. Use `register` only for a new run; then `doctor`, `preflight`, `scan`, `acquire`, `assess`, `schedule`, `backtest`, `events`, `report`, `export`, `lookahead`, `ui-smoke`, `dryrun-smoke`. `validate` rechecks preserved sources. `events-replay` reparses retained sources without network access and preserves the original briefing. `backtest` preserves completed portfolios and uses separate logs/directories for a deliberate incomplete retry. A failure is a diagnostic, not authorization to alter dates, filters or strategy thresholds.

`register` captures source hashes before outcomes. Mechanical source changes require a committed previous version, retained failure and an explicit hash-chained source amendment. The session's original registration, failed CA/scope/import attempts, initial optional-source test failure, 30-second stopped-state startup timeout and false-positive reader rejection remain in evidence. The successful rerun `session1-003` uses the final code without amendments.

| File under `evidence/additional-1/RUN_ID/` | Meaning |
|---|---|
| `registration.json`, `source-amendments/` | Frozen inputs and any explicitly recorded mechanical changes |
| `environment-checks.json`, `venue-access.json` | Native version/Compose safety and exact venue-access observations |
| `scan.json`, native pairlist log | Current cheap universe, shortlist and rejected examples |
| `opportunities.json` | At most five serious current checks, both recipes/sides, closed data and quote clocks |
| `data-manifest.json`, `data-validation.json` | Contract identity, original acquisition clocks, source hashes, continuity and funding coverage |
| `source-reuse.json`, `source-vault.json` | Verified copy provenance and private source-bundle checksum |
| `schedule.json`, `market-ranking.csv` | Existing causal absolute-return/activity ranking for the five-survivor historical sample |
| `historical-opportunities.json`, `casebook.json` | Every historical router candidate/veto, entry plans, native joins and separately labeled subsequent paths |
| `native-results/`, `native-provenance/`, `trade-ledgers/` | Actual native portfolios, exact arguments/hashes and fills/costs |
| `economic-report.json`, `source-funding-audit.json` | Independent order accounting, event/quantity funding bounds and economic limitations |
| `event-briefing*.json` | Thin RSS/iCalendar/official-reference briefing; UNKNOWN clearance |
| `lookahead-summary.json`, native logs/CSVs | Measured native diagnostic with actual sample sizes and exporter limitation |
| `ui-smoke.json`, `dryrun-smoke.json` | HTTP/native-result check and stopped-state startup; both processes stopped |
| `openbot/` | Only the bounded schema-validated ordinary reader files |

## Private source recovery

Raw data stay out of Git under the existing source-use policy. A sealed sample plus a manifest must be copied off this ephemeral workspace. The delivered private ZIP contains recent source-vault bundles, recovered original sources, current/event sources and native ZIPs, with an index of checksums. Keep it private; no commercial/raw redistribution clearance is asserted.

For a recent source-vault archive:

```bash
python3 scripts/foundation_restore.py /path/to/foundation-session1-003.tar.gz work/restored-003
# Verify succeeded before copying; target must be absent.
mkdir -p user_data/data/foundation
test ! -e user_data/data/foundation/session1-003 && cp -a work/restored-003/source user_data/data/foundation/session1-003
./scripts/lab-foundation.sh validate session1-003
```

The restore tool rejects an existing destination, traversal, symlinks and special files, then verifies every candle/funding hash. It never overwrites a preserved dataset. The archive is normalized only to the registered UTC boundaries; there is no price interpolation or fabricated bar. A later new run can reuse the restored identical cohort automatically. The original July–October sample has a separate archive and manifest; its 20 files matched every old hash before missing prior test-source copies were restored. Already present sources are checked and never overwritten.

Full tests in the pinned runner use:

```bash
docker compose -f deploy/freqtrade/compose.yaml --profile tools --profile ui --profile paper config --format json > user_data/runtime/compose-safety.json
# Inside the pinned runner, /lab is the repository:
python -m unittest discover -s tests -v
```

One legacy test requires the original raw files; without that private source it is genuinely blocked, not evidence of a passing replay. Focused current-cohort tests are run automatically with `FOUNDATION_RUN_ID` selected by the wrapper. The independently registered known-defect replay is `python scripts/replay_funding_repair.py run NEW_RUN_ID` inside the pinned runner after exact old-source restoration; it writes only a new `funding-replay/` evidence directory and refuses reuse.

## Recipe and cost interpretation

The three versioned parent strategies are unchanged. The original router is the native control. The new M0 subclasses the audit's frozen-invalidation strategy: keep the original regime/rank/entry/stop/2R target/holding rules, remove the old ADX/opposing-hourly early exit, and accept a newly closed post-entry price breach of the frozen stop as invalidation. Native stop execution generally acts first. M1 inherits this exit and the existing half-at-1R adjustment; it uses the same event-once native funding subclass in research only.

The original router's fixed 2R policy is implemented explicitly. ICT/SMC/profile annotations do not become undisclosed mandatory gates. Current signed long/short context is research ranking, while historical absolute ranking remains unchanged and disclosed. A gainer is not automatically a reversal/short opportunity. The Market Researcher must state the strongest contrary evidence and distinguish invalidation from caution.

The shared October native fee scenario is **0.00075/side**, conservatively above observed current public generic **0.0005/side**. No historical/account-tier verification is claimed. The old-source funding replay holds its original **0.0006/side** fixed to isolate the funding change. Native P&L includes actual source funding; independent Decimal order accounting and source-event quantity bounds are separate checks.

The inherited entry geometry retains its frozen **0.0035 total cost allowance**. At the 0.00075 fee scenario, adding the original 0.002 friction and 0.0003 adverse-funding allowances would total 0.0038. Thus its displayed admission reward/risk is the frozen research assumption, not a newly verified current all-in execution guarantee. Numerical entry thresholds were not silently retuned. Native net and the separate 1.5/5/10/20 bp turnover stresses are reported honestly; operational admission must resolve this allowance consistently before promotion. Full account MTM, midnight equity, pending exposure, actual fills and restart behavior remain unqualified.

Funding repair assumes an event occurs before an identical-clock exit, values it with native Freqtrade and attaches its cursor to that native trade object. It does not modify installed engine modules. Source bounds retain both event/fill priorities. No cursor persistence/restart guarantee is made.

## Stop, inspect, rollback

The complete research wrapper removes its own temporary container. `ui-smoke` generates temporary local auth, verifies protected HTTP/native history, stops the webserver and deletes its private auth overlay. Graphical rendering is not observed. `dryrun-smoke` creates a disposable SQLite database with native `initial_state=stopped`; zero simulated trades and shutdown are verified. It is not a forward-paper test.

```bash
docker ps --filter name=openbot-foundation-
./scripts/lab.sh paper-down
./scripts/lab.sh ui-down
# If an interrupted research wrapper left its OWN disposable container:
docker rm -f openbot-foundation-owner-research-001
# Preserve data/private bundles/SQLite/config before rollback:
git switch --detach 29c07b80e8d3b15fb60f097a84eee30d730ffa40
```

The reviewed operational baseline remains selectable through the old guarded `./scripts/lab.sh paper-up` command only after a separate owner decision. This session does not run it. Starting the old service requires local API initialization (`python3 scripts/init_runtime.py`), checked freezes, venue/host eligibility and an awake host. The new routers and M1 are absent from that guard's allowlist. Stopping a paper engine pauses management and does not guarantee closure; preserve and inspect existing state. Do not point OpenBot at any Freqtrade admin API or writable directory.
