# Fresh-market validation: historical research only

This draft is stacked on PR14 at `ccb2f4adb8d11605d8d33156f86acc769ba68e39`. All original files and evidence remain byte-identical. Leave the PR unmerged until owner review. No bot, exchange account, paper service or deployment was activated.

## What this runner can claim

Official Binance USD-M monthly archive data, January1–May1 2026 end exclusive, BTC/ETH/XRP/DOGE. Four months of complete15m/1h/5m and1h mark candles plus actual funding events; official ZIP checksums and CSV hashes. Data are for the owner's personal, non-production historical research under Binance Vision CC BY-NC-SA4.0 terms. Derived data reports carry that attribution and licence. No commercial/live rights are inferred.

Binance exchangeInfo returned451. A captured public CCXT **test fixture** supplies separate Binance ticks, lots and minimums for an explicitly unqualified offline scenario. It is not historical exchangeInfo. BTC's fixture minimum50USDT exceeds the25USDT cap, so it cannot submit. Never weaken the minimum or increase the cap to manufacture trades. The inherited risk helper's `verified=true` means the fixture schema was checked **only**; `economic_qualified=false` and `verification_scope` state the limit. The historical-only strategy requires explicit fixture scenario mode and refuses live/dry-run/hyperopt. Binance's native bundled leverage-tier snapshot is also not historical; leverage stays1x. Every result remains **PARTIAL_COST_MODEL / INSUFFICIENT_ECONOMIC_VALIDATION**.

The earlier Gate control is source-sealed, not re-created from Binance prices. Prior owner-private Gate bundles were not supplied in this session. Their hashes and restore instructions remain in `docs/operations/deep-failure-diagnosis.md`; they are unnecessary for the new scenario.

## Restore the new private inputs

Keep the delivered `OpenBot-Fresh-Market-Private-Inputs.tar.gz` outside the checkout. Read its exact SHA256 in `evidence/validation_next/run-001/private-input-bundle.json`. From this branch:

```bash
python scripts/validation_next_archive.py restore /path/OpenBot-Fresh-Market-Private-Inputs.tar.gz . --sha256 EXACT_RECEIPT_SHA256
./scripts/lab-validation-next.sh tests
```

Restore uses the existing audited archive preflight: whole-archive and per-file hashes, path/symlink restrictions and refusal to replace different existing files. The archive contains only `user_data/data/validation_next/` and `work/validation_next/`, including native ZIPs, exact configs, logs, derived features and plans. No credentials. Existing identical files are retained. A manifest alone cannot restore archive sources after provider revisions, so keep the bundle.

The pinned image is in `scripts/lab-validation-next.sh`: Freqtrade2026.10, CCXT4.5.90. Managed cloud users must preserve the environment proxy/CA configuration. The wrapper starts one disposable research container and removes it on exit; it never invokes `freqtrade trade`.

## Reproduction without overwriting evidence

Completed native labels, command labels and the one-shot holdout receipt are immutable. An already completed label intentionally errors. To reproduce a portfolio, use a separate copy of this checkout and preserve the copied original results elsewhere before selecting a **new output namespace in a reviewed copy**. Do not delete or overwrite the delivered evidence. The exact native argv and configuration hashes are in each `native/*/provenance.json`; configs and result ZIPs are restored under `work/validation_next/native/`.

The implementation entry points are:

```bash
./scripts/lab-validation-next.sh data
./scripts/lab-validation-next.sh prepare convert
./scripts/lab-validation-next.sh prepare development
./scripts/lab-validation-next.sh native development v4-transfer --detail
./scripts/lab-validation-next.sh native development passive-transfer --detail
./scripts/lab-validation-next.sh native development parent-target --detail
./scripts/lab-validation-next.sh report
./scripts/lab-validation-next.sh checks
```

`data` verifies existing archive hashes before reuse; it requests only the80 registered monthly sources if absent. `prepare convert` is for a fresh namespace before registration; do not regenerate converted sources or contract receipts underneath a completed experiment. `--detail` keeps identical15m decisions and uses genuine5m execution; it is not a new5m entry rule. `--through` requires one fixture tick beyond the entry, which still cannot establish queue priority. `--fee .0015` adds10bp per side to base5bp. Only these declared fees are accepted. The38bp admission reserve is not charged again as cash.

`validation_next_evaluate.py validation`, then `freeze`, then `holdout` implement the registered evaluation sequence. **Do not call `holdout` again**: it uses an exclusive-create receipt and refuses a second opening. The April block is consumed by this experiment; it can never again be called untouched. No rule changes followed validation/holdout.

## Exact funding and execution clocks

The pinned funding data loader floors timestamps to seconds. Runs without the `-exactclock` suffix are preserved as **INVALID_NATIVE_FUNDING_CLOCK**, never included in final economics. The corrected adapter restores actual immutable source event times after native loading; it does not alter installed Freqtrade or invent rates. Independent coverage compares events with raw Feather source, and cash is reconciled from price/quantity, both fees and signed funding. Valuation uses the last hourly mark **OPEN**, not the current hourly close. Exact exchange settlement mark and the economic meaning of millisecond publication offsets remain unknown.

Two earlier pre-portfolio failures are retained: the initial funding file label differed from the pinned native1h filename convention, and the native end-boundary validation row lacked cached OHLCV. File naming and raw boundary-column preservation were corrected without future signals or altered thresholds. See `technical-corrections.json`.

Order removal is observed at the native lifecycle method; an old Order object can still say `open` after removal. On5m detail runs the configured5m timeout must produce5m terminal ages. Main15m execution has only15m cancellation resolution. Range touch and trade-through cannot establish historical partial fills, queue priority, spread or actual intrabar order.

## Checks and limits

`regression-and-validation.json` records the broad suite's actual nonzero exit code and every error/skip. The two old registration failures remain closed; no historical seal was rewritten. Missing old private input files are errors/prerequisites, never reported as passes. The focused new suite and raw-source prefix checks use the delivered new inputs. Exact raw-prefix recomputation checks every feature column and cross-pair rankings; generic lookahead analysis of a replay schedule alone cannot prove schedule construction causal.

Partitions: development Jan11–Mar1, validation Mar2–Apr1, final Apr2–May1 UTC, ends exclusive.24h gaps and end-of-block maximum-hold purging prevent overlapping outcomes; all pairs share clocks. Warmup precedes scoring. The reserved Gate Nov17–Dec1 window remains future and untouched.

## Stop, rollback and recovery

There is no active trading process to stop. A research wrapper removes its container even after errors. A failed command leaves its attempt, log and output intact; inspect the exception before running a new isolated attempt. Never use repair as an excuse to retune on the consumed holdout. Preserve both private data bundles and draft evidence before changing checkout.

```bash
git switch --detach ccb2f4adb8d11605d8d33156f86acc769ba68e39
```

No reset, deletion, merge or deployment is needed. The next owner action is to review the draft's negative results and historical metadata limitation before authorizing any prospective research; persistent paper prerequisites remain unresolved.

## Storage recovery recorded in this delivery

The VFS daemon copied roughly1.9GB of writable/init layers per full research container. Creating another full-image utility container exhausted the7.9GB execution disk during holdout evidence export. A tiny temporary utility image was used to recover only two unreferenced failed-container copies, after matching them against Docker layerdb references; no research source/evidence was deleted. The existing saved holdout portfolios were retained. The remaining frozen commands resumed under the same open-count1 receipt. The interrupted structural ZIP and recovery ZIP contain exactly equal complete trade objects. This is recorded in `holdout-recovery.json` and `holdout-recovery-equivalence.json`.

On a similar VFS host, keep enough space for the full writable/init copies and **run one full research container at a time**. Do not start another full-image helper while a research container is active. Runtime containers and the temporary utility image were removed at handoff. Image caching alone can still consume severalGB under VFS; the new private research inputs themselves are much smaller and bounded by the archive tool's500MB raw-input cap.

The three largest derived ledgers are stored losslessly as `.json.gz`; `compressed-ledgers.json` records both compressed and uncompressed SHA256s. Use Python `gzip.open` or `gzip -dc` to inspect them. The report command regenerates ordinary JSON from sealed native inputs; compression changes no values or economic results.
