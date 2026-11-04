# Integrated market, entry and exit research

This branch is a historical research experiment based on unmerged PR #12
`e2739dcbb6e48016a13a314f3a21507ed181cb60`. It does not activate paper, live or
testnet trading. The new classes refuse every mode except backtesting. Freqtrade
retains all orders, portfolio accounting, sizing, protective stops and funding.

## Result and boundaries

The integrated candidate is **REJECTED for promotion**. None of the nonempty
challengers beat V4. The first-obstacle/context combination abstained on all
56 original selected V4 opportunities. Genuine 5m response code works, but none
of its economically qualified responses passed the frozen shortlist: its
economic contribution is **INSUFFICIENT / NOT ESTABLISHED**.

Read [the owner report](../../evidence/integrated/run-001/owner-report.md),
[economic evidence](../../evidence/integrated/run-001/economic-report.json),
[trial protocol](../../research/integrated/protocol.json),
[final checks](../../evidence/integrated/run-001/final-verification.json) and
[test results](../../evidence/integrated/run-001/regression.json).

All 3,324 pre-existing tracked files, including 3,065 evidence files, remain
byte-identical. The original source hashes and initial decision seal remain
preserved. A separately recorded v 2 seal adds a missing-boolean fail-closed fix
and stronger input checks after the first matrix; all 196 historical market
reads remain exactly equal. Final-seal native V4/integrated replays are retained.
No threshold was tuned or losing trial discarded.

## Inputs and version

The original private archive was unavailable. Public Gate REST reacquisition
recovered all **56 byte-identical sealed files**: 15m/1h last-trade candles,
hourly marks and actual funding events, August 22–November 3 UTC, end exclusive.
The 14-market current-survivor cohort is unchanged. Metadata was separately
captured from current public contracts; historical specifications remain unknown.

Gate refused August 5m history because of its rolling 10,000-point retention.
The fixed fallback October 5–November 3 UTC has 8,352 real 5m candles per market,
116,928 total. All 70 series and their hashes/coverage are in
`evidence/integrated/run-001/data.json`. No 5m candle was generated from 15m data.
The native 5m strategy uses 5m as its **primary** timeframe, with completed
15m/1h/4h context; it does not claim that timeframe-detail generates entries.

The pinned image is:
`freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7`.
Actual runtime: Python 3.14.10, Freqtrade 2026.10, CCXT 4.5.90. Host Python 3.12.14
was used for stdlib archival/audit tasks. The native provenance records exact
arguments, config hashes, staged modules, ZIP hashes and interpreter versions.

## Reproduce without replacing sealed evidence

Use Docker, Git and Python 3. Keep the owner-private input bundle provided with
this handoff. Its SHA256 is in `evidence/integrated/run-001/private-backup.json`.
Restore into this checkout using the recorded checksum:

```bash
python scripts/integrated_archive.py restore OpenBot-Integrated-Private-Inputs.tar.gz . --sha256 5a82c65ebbe06cf4ecbef8e11c02ab090b3687676cd5a31cbad4a105ef16b5f6
./scripts/lab-integrated.sh verify
./scripts/lab-integrated.sh tests
./scripts/lab-integrated.sh regression
./scripts/lab-integrated.sh checks
./scripts/lab-integrated.sh native control-v4 --replay-id owner-check
./scripts/lab-integrated.sh native control-pr12 --replay-id owner-check
./scripts/lab-integrated.sh native entry-passive --replay-id owner-check
./scripts/lab-integrated.sh native thesis-exit --replay-id owner-check
./scripts/lab-integrated.sh native ema-context --replay-id owner-check
./scripts/lab-integrated.sh native integrated --replay-id owner-check
./scripts/lab-integrated.sh report
```

Use a new replay ID each time. Completed result directories refuse overwrite.
The archive restore checks its own checksum, every member checksum, scope and
existing files; no overwrite is permitted. No API key or account is needed for
these offline replays. Metadata/candles are loaded from the saved source files.

`acquire` and `prepare` are the original source/plan construction commands.
`prepare` intentionally refuses an already completed registration. A reviewer
rebuilding the decisions should do so in an isolated copy with a separate output
namespace; do not remove sealed registration/evidence to make a command pass.
Reacquisition alone cannot promise that a rolling endpoint still serves old data.

Only one Docker worker should run at a time on a small VFS-backed workspace.
The first concurrent startup attempts exhausted this session's 8GiB disk before
creating any challenger result. The failed attempts and storage recovery are
recorded in `runtime-issues.json`. Every actual native result is retained.

## What the comparisons isolate

- `control-v4`: exact preserved V4 rules and reconstructed 56 selected plans.
- `control-pr12`: exact 14 sealed PR #12 READY plans and original native strategy.
- `market-selector`: fixed V4 opportunities, same entry/exit, new context and
  nearest-obstacle admission. Its combined gate contribution is confounded.
- `ema-context`: replace the three raw EMA predicates and hourly shortlist veto
  with aligned confirmed hourly structure, retaining other predicates and the
  ranking formula. Eligibility and ranking change together; this is not a
  causal claim about EMA alone.
- `entry-passive`: same V4 trigger, stop and target, 0.15ATR retracement limit,
  five-minute configured expiry, no chasing. Nonfills remain in denominators.
- `thesis-exit`: same V4 plans, initial stops and targets; defended frozen VWAP
  failure plus opposing confirmed local structure replaces continuation exit.
  All 45 filled entry keys remain identical in this comparison.
- `take-profit`: nearest known nonproxy objective, with the original after-cost
  room and six-ATR checks. All plans reject, so no filled-entry target effect
  can be estimated.
- `integrated`: predetermined context, passive price, structural exit and first
  objective combination. Zero trades measures abstention, not successful trading.
- `five-*`: shared prospectively registered defended opportunities. 15m-response,
  first 5m-response and passive prices share the frozen stop/objective. These
  opportunities are distinct from the archived V4 selected fills.

The 38 bp allowance is admission/risk geometry, never a second ledger fee.
Primary native fees are 7.5 bp/side; separate native 17.5 bp/side replays and
one-tick trade-through checks are preserved. Additional 5/10/20 bp turnover
subtractions are explicitly ledger sensitivities, not reconstructed fills.

## Limits that remain material

This is repeatedly inspected development, not independent validation. No
November 17–December 1 future holdout was accessed. Current-survivor membership,
historical contract changes, bid/ask spreads, queue priority, real partial fills
and authentic signed flow remain unverified. Genuine profile economics are not
tested. The native filled-trade sample is small and correlated.

For the main 15m replays, a five-minute configured expiry is checked at native
15m steps: a modeled range touch can occur later within the same candle. Order
timestamps do not reconstruct that unknown subbar path. The positive controls
and passive policy therefore retain optimistic fill assumptions. No claim of
precise five-minute queue/expiry execution is made. The separate 5m policies have
zero admitted trades and do not resolve this issue for the main 15m portfolios.

Funding is reconciled against every event in the recovered source using its
actual timestamp and preceding hourly mark OPEN; the exact settlement mark and
independent venue-wide completeness remain unknown. No new actual partial or
runner was attempted. No same-candle initial stop/target collision was found in
the reconciled fills; native stop ordering remains a model assumption.

Two inherited tests still reject their old source registrations. They are shown
as errors, not converted to passes: the V 3 config registration and the older
paper guard's `causal_structure.py` freeze. Parent bytes remain unchanged. One
optional historical tape fixture is unavailable. The first missing-fixture test
attempt is preserved, then real-source and native mechanics fixtures were rerun
with explicitly documented input bindings.

## Disable or roll back

No service is activated and no operational allowlist was extended. Stop invoking
the new research wrapper, retain the private archive, then switch back to
`codex/pr11-causal-fixes` or detach at
`e2739dcbb6e48016a13a314f3a21507ed181cb60`. Do not merge this PR or enable paper
trading merely because software tests pass. There is no new persistent runtime
to stop. Parent evidence, original controls and source archives remain intact.
