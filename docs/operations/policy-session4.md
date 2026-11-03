# Session 4 bounded paper and research runbook

Use this branch stacked on PR #8. The exact parent is
`c0ec703a3ae7e94ab704d7d833c1e3f51733c3ce`. Scope is Freqtrade/CCXT trading;
OpenBot integration remains separately owned. Read the [owner report](../../evidence/session4/owner-report.md)
and [evidence index](../../evidence/session4/README.md) before interpreting results.

## Pinned environment

Docker with local socket access, Bash and Python 3 are sufficient. No exchange
keys or additional Python installs are required. All native commands use:

```bash
docker pull freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7
./scripts/lab-session4.sh tests
```

The wrapper mounts the repository at `/lab`, drops capabilities, uses the host
UID and removes its disposable container on exit. In managed Cloud it supplies
the combined public CA bundle and preserves configured proxy settings. No TLS
verification is disabled. No paper process survives a wrapper run.

## Reproduce the delivered historical result

Raw sources and native ZIPs are excluded from Git. Verify the delivered archive's
SHA256 against `run-001/private-backup.json`; restore into an empty staging
directory, then copy only absent files. The restorer verifies all members before
writing, rejects traversal/symlinks and refuses overwrites:

```bash
python scripts/session4_archive.py restore Session4-Private-Backup.tar.gz work/restored-session4
cp -an work/restored-session4/user_data/. user_data/
cp -an work/restored-session4/work/. work/
./scripts/lab-session4.sh replay owner-reference reference
```

Choose a fresh result label. Existing completed portfolios are never overwritten.
The delivered `reference-reproduce` repeats the same 82 entries and +0.92314130
native rounded USDT. Independent Decimal economics is +0.92314132557 USDT;
per-trade native rounding differences remain below 0.0000001 USDT.

For a newly registered acquisition/evaluation with the same fixed protocol:

```bash
./scripts/lab-session4.sh research owner-s4-001
```

Use a new ID. Current Gate membership/liquidity and rolling endpoint retention
will differ; this is a new qualified experiment, not a promise of byte-identical
reacquisition. The fixed July–November calendar is historical development. A new
run must retain missing-source coverage. Never substitute zero funding or infer
membership for delisted/unavailable markets. The reserved November 17–December 1
period is outside every supplied command.

The exact session commands inside the disposable pinned runner were:

```bash
python scripts/session4_market.py acquire
# retained engineering/source attempts, then causal inputs:
python scripts/session4_research.py prepare
python scripts/session4_research.py portfolios
python scripts/session4_research.py native reference-risk reference --risk
python scripts/session4_research.py native structure-risk structure --risk
python scripts/session4_research.py native reference-through reference --through
python scripts/session4_research.py native structure-through structure --through
python scripts/session4_research.py native structure-open structure --open-only
python scripts/session4_research.py native structure-market structure --market
python scripts/session4_research.py native reference-reproduce reference
python scripts/session4_execution.py
python scripts/session4_report.py report
python scripts/session4_capture.py
```

`amendments/` records engineering repairs and their before-outcome boundaries.
Every native attempt has separate output, config, risk state and event paths.
The source cache is actual captured CCXT Gate contract/tier metadata; order,
price, mark and candle methods are never replaced. Historical tiers are not
inferred from current metadata.

## Bounded real native paper modes

```bash
./scripts/lab-session4.sh paper limit 150
./scripts/lab-session4.sh paper market 150
./scripts/lab-session4.sh restart limit 90
```

Each public refresh must succeed before the wrapper starts a new worker. It
updates only mutable `user_data/runtime/session4/` metadata. Historical sources
and evidence stay intact. The reviewed configurations remain Gate-only, dry-run,
isolated 1x, two positions, 25 USDT initial notional, no credentials/force entry,
no DCA, no exchange-side stops and no unauthenticated API. Expired metadata,
incomplete marks or account evidence inhibit entry. Do not reset an exposed
account DB to bypass recovery.

`scripts/guard.py` dispatches only the exact reviewed V4 config/module set to a
bounded native trade command. A deadline is checked before launch and enforced
by a native alarm plus an outer timeout. CLI/config/environment overrides remain
rejected. `guard-review.json` records the deliberate extension of the original
guard freeze; all other frozen hashes are verified unchanged. Legacy workflows
retain their original strategy permissions. Session 3 registration verifiers
still correctly reject this changed branch as their original exact source seal.

The session additionally invoked the direct bounded runner with an actual recent
contract snapshot while public sources were failing, to establish outage behavior:

```bash
python scripts/session4_runtime.py templates
python scripts/session4_runtime.py limit 240
python scripts/session4_runtime.py market 180
python scripts/session4_runtime.py limit 75 --restart
```

These workers reached RUNNING and then stopped with zero orders. Public prices
were unavailable. `runtime/limit-restart.json` honestly reports
`public_data_observed=false`; the first two initial producer records' similarly
named flag only detected startup and is explicitly disqualified in the evidence
index. Never cite them as fresh-price or forward-fill evidence.

Pending entry expiry is five minutes at the native loop clock; partial entries
cancel/crystallize through native timeout. Native exit timeout is five minutes;
stops and deterministic target/time management remain available. A temporary
source failure does not grant fresh-entry authority. Native protective stops
still require a running process and a usable observed price; no guaranteed
exchange-side protection is represented.

## Validation and preservation

```bash
python -m unittest discover -s tests -p test_session4.py -v
python -m unittest discover -s tests -p test_intelligence.py -v
python -m unittest discover -s tests -p test_session3_structure.py -v
```

Run these inside the pinned runner. Current counts are 13,20,5 passing tests.
The exact parent checkout passes all 32 frozen policy-mechanics tests. The
current branch's old exact-registration test refuses changed source as designed;
the retained output records that one error rather than suppressing it. Controlled
native tests cover callback failure at 1x/10x/20x, long/short stops, tick precision,
market/limit dry-order transitions, cancellation, SQL recovery, missing marks,
funding/partial state and atomic checkpoint rollback. Actual forward fills remain
unobserved. Parent preservation and backup verification are recorded separately.

## Session 5 acceptance and rollback

The first operational acceptance is healthy owner-host public data and one
unforced observed paper lifecycle, with a precise no-fill result when no valid
opportunity occurs. Complete minute execution sensitivity, true prospective
Gate flow/book observations, authenticated FreqUI, exposed-account recovery,
supervision, alerts and bounded storage. Economic qualification requires new
predeclared evidence; the inspected development result cannot approve profitability.
Persistent operation is reserved for separate owner approval.

Deadline expiry requests native graceful cleanup and cancellation of pending
simulated orders. Ctrl-C removes the wrapper container and can interrupt that
cleanup; persist and reconcile pending state on restart. Stopping does not close an open position.
Preserve trade/account databases before changing versions. To inspect the exact
frozen parent without merging or altering these results:

```bash
git switch --detach c0ec703a3ae7e94ab704d7d833c1e3f51733c3ce
```

No existing PR is merged and no persistent service/unit/cron entry is installed.
