# Historical deep-diagnosis recovery and replay

Parent: PR13 `ade410ec625be51f8dbcb7194b98965d8286daf7`. Research branch: `codex/deep-failure-diagnosis`. Keep the draft PR unmerged until separately reviewed. This procedure never starts a trading bot.

## Restore both owner input bundles

Use a checkout of this branch. Docker must support the pinned image in `scripts/lab-diagnosis.sh`. Only one research container is needed; run commands sequentially if the Docker storage driver copies image layers. In this cloud session the runtime was Freqtrade 2026.10 / Python 3.14.10 / CCXT 4.5.90. The image digest is sealed in every native provenance record. Follow your managed environment's proxy and CA-trust configuration when pulling/building; the wrapper mounts the host certificate bundle for research requests.

Raw candles, feature caches and native ZIP/SQLite/config exports are private owner downloads. Tracked evidence is available from the repository. Do not redownload recent data and silently substitute it for sealed files.

```bash
python scripts/integrated_archive.py restore /path/OpenBot-Integrated-Private-Inputs.tar.gz . \
  --sha256 5a82c65ebbe06cf4ecbef8e11c02ab090b3687676cd5a31cbad4a105ef16b5f6
python scripts/diagnosis_archive.py restore /path/OpenBot-Deep-Diagnosis-Private-Inputs.tar.gz . \
  --sha256 a1a5cc89bfa1c89294232c86ded5445a3072ba9b1c08799e2941b233638fc3ee
./scripts/lab-diagnosis.sh verify
```

The archive tools validate checksum, scope, traversal/link restrictions, every member's size/hash and all existing destination bytes before writing. Identical existing files are retained; different files are refused, never overwritten. The diagnosis bundle is incremental and intentionally does not duplicate the parent bundle. A complete 596-file scratch restore and 596-file existing-tree hydration were verified with zero overwrites. Source pickles belong only to these verified owner research bundles; do not substitute untrusted serialized inputs.

## Reproduce a bounded native comparison

Use new replay IDs. The runner refuses a completed label and never overwrites an old native result. Its output stays under `evidence/diagnosis/run-001/native/` and `work/diagnosis/native/`. The original plans/features are restored rather than reselected from revised inputs.

```bash
./scripts/lab-diagnosis.sh native development v4 --replay-id owner-check
./scripts/lab-diagnosis.sh native development conditional-entry --replay-id owner-check
./scripts/lab-diagnosis.sh native development thesis-compatible --replay-id owner-check
./scripts/lab-diagnosis.sh native-v2 development passive-30m --replay-id owner-check
./scripts/lab-diagnosis.sh native development v4 --short --detail --replay-id owner-check
```

`native-v2` is mandatory for the 30-minute expiry arm: the original sealed runner inherited the five-minute native config, so its five original expiry-arm records are invalid implementations. The explicit addendum retains them and fixes only new attempt configs; price depth, opportunity set, stop, target and registered expiry hypothesis do not change. V2 also records actual unfilled-order removal. Original native Order.status may remain open after removal and is not a reliable terminal clock. The recorded corrected runs carry `expiry-corrected` IDs.

`--short --detail` means genuine 5m execution detail on fixed Oct5–Nov3 dates using completed 15m entry decisions. It does not change the signal timeframe. `--through` requires one native tick beyond entry for a range fill. `--fee .00175` adds 10bp per side to the base7.5bp. None supplies real queue depth, spread or historical contract metadata.

The historical-only class rejects live, dry-run and hyperopt modes even if dry_run is true. Do not invoke `freqtrade trade`, insert credentials, start persistent paper processes, increase leverage, alter the 25USDT/two-position controls or remove the obstacle gate as part of this procedure.

## Checks and analysis

```bash
./scripts/lab-diagnosis.sh tests
./scripts/lab-diagnosis.sh validate
```

The focused diagnosis suite has 13 tests; the combined suite has 142 distinct checks. Expect 139 passes, two preserved inherited errors and one optional authentic-tape skip on the sealed inputs. The validation driver returns success when it observes exactly the documented inherited errors and no assertion/unexpected failures; that status does not mean all 142 tests pass. Inspect regression.json/text for the actual count. `registration-diagnosis.json` records expected/current/prior hashes and ancestry; no seal or activation review is rewritten.

The exact executed 50-job matrix and six-job repair/observer sequence are in execution-logs.tar.gz and execution-history.json. The separately run first corrected full-development expiry trial makes five corrected expiry records total. Two additional unchanged observer replays make 57 records overall, including invalid trials and repeated controls. The 1,542 reconciled ledger records overlap; they are not independent observations.

Do not rerun the fixed matrix into completed labels. To recreate a complete run from raw inputs, use a separate checkout/run namespace and preserve its own preregistration, hashes and outputs. The original preparation and source seals are explicit; changed code or inputs fail native verification. Calling report/analysis generators in place would replace derived current-session files and break the delivery seal, so use a copied checkout for regenerated analysis. No prior PR13 output is written by the diagnosis scripts.

Charts can be regenerated from the restored, hash-indexed actual-candle JSON inputs using a local virtual environment with `matplotlib==3.10.7` and `python scripts/diagnosis_charts.py`. They are SVG exports with known geometry and a shaded future region. The temporary plotting environment is not included in the bundle; dependency installation/version is retained in logs. Exact SVG bytes can vary with rendering metadata; the numerical input hashes identify the source case.

## Review, rollback and next research step

Start at evidence/diagnosis/run-001/owner-report.md and economic-report.json. Check the failed hypotheses as well as positive controls. The 112 new source files cover an already-inspected August window and a one-day November extension. Independent validation is NOT COMPLETED; the future reserved Nov17–Dec1 holdout was not accessed.

Rollback is to leave this draft PR unmerged and use the verified parent checkout:

```bash
git switch --detach ade410ec625be51f8dbcb7194b98965d8286daf7
```

Preserve local work first if present. All parent files remain byte-identical; no activation or service requires reversal. Do not reset or delete old evidence. The next recommendation is one frozen, historical evaluation of V4/continuation-only/compatibility on completed reserved dates, with no further development tuning. It remains a research task, not execution permission.
