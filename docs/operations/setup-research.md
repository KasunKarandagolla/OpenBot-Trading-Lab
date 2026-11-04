# Setup research: reproduce, inspect and roll back

This is historical research only. It cannot start live, testnet or persistent
paper trading. No new profitable policy is selected. All 2,844 starting files,
production configs, V3/V4 rules and earlier evidence remain unchanged.

## Read the result

Start with `evidence/setup/owner-report.md`, then the `run-002/portfolio-table.md`,
economic report, decision casebook and self-review record. `run-001` preserves the
initial v1 comparison. Version1.1 restores the inherited6ATR objective bound;
it is a disclosed post-result development correction. Neither cohort is unseen.
The added V4 structure lane is the owner's retained frozen default; the V4
reference lane is also retained, distinctly named. All portfolios share Gate
source prices/funding, Sep1–Nov3 UTC exclusive,1000USDT,1x, max2 positions and
the25USDT ceiling. Constant-risk runs target0.25USDT under that same ceiling.

## Restore the private inputs

Raw Gate data, causal feature/plan caches, source receipts, native ZIPs and
simulated SQLite state are in the delivered private backup. Git manifests alone
cannot restore them. Use the pinned Docker image from `deploy/freqtrade/compose.yaml`.
Copy the downloaded backup to `work/Setup-Private-Backup.tar.gz`, then:

```bash
python scripts/setup_archive.py restore work/Setup-Private-Backup.tar.gz work/owner-restore
python scripts/setup_archive.py hydrate work/owner-restore .
./scripts/lab-setup.sh tests
./scripts/lab-setup.sh native setup --replay-id owner-check
./scripts/lab-setup.sh native v4-structure --replay-id owner-check
./scripts/lab-setup.sh report
./scripts/lab-setup.sh export
```

Use a new replay ID for another check. Existing completed results refuse
overwrite. Restoration rejects unsafe paths, links, duplicates, oversized
archives and differing existing files. The replay verifies frozen source,
feature, plan and source-data hashes before running the official engine. The
new replay lives beside the original; it does not replace the original result.
`report` reconciles order quantities, gross movement, actual native fees and each
signed source funding event, then calculates separate cost stress.

Python on the host needs only the standard library for archive restoration.
Tests/backtesting run in the exact pinned official Freqtrade2026.10 / CCXT4.5.90
image. The wrapper creates a disposable local container and removes it on exit.
It binds no ports. It does not require editing configurations or exchange keys.

The already completed `matrix` action is a finite registered comparison, not
hyperoptimization. Reusing earlier complete records requires their same freeze;
the V4-control extension changed the final registration seal, so use named
`native ... --replay-id ...` commands to verify specific portfolios. To recreate
the *initial* v1 matrix exactly, use an isolated checkout of commit `5f582a0`
and its private input namespace. Do not change the final checkout's frozen
source just to satisfy an old seal.

`acquire` supports a separate, bounded public Gate source namespace if originals
are absent. Rolling availability can change; replacement data are not byte-
identical restoration and must receive a new research registration. Do not
overwrite the delivered inputs. The approved historical windows endNov3; the
reserved Nov17–Dec1 holdout must remain untouched.

## OpenBot and operation boundaries

Copy only `run-002/openbot/research-snapshot.json` and its manifest into the
separate read-only research environment. It validates against the existing
foundation schema. Four strategy research skills are under
`research/setup/skills/`. Do not expose lab directories, native ZIP/configs,
SQLite, credentials, Docker sockets or Freqtrade administration to an agent.
No agent runtime/bridge or owner-host isolation claim is made here.

`hypothetical-leverage.json` contains1/10/20x arithmetic using current public
contract tiers. Actual execution stays1x. Gap losses, historical maintenance
tiers and exact settlement marks remain assumptions/limitations, not observed
liquidation or exchange-fill evidence.

## Roll back

The research wrapper normally stops itself. Check for any remaining
`openbot-setup-*` disposable container with `docker ps` and stop only that named
container if necessary. Preserve the private backup, then switch an isolated
checkout back to `542c0d804185ca28c08453711e421de42a793edc`. No production
configuration migration, database migration, merge or trading activation is
required or authorized.
