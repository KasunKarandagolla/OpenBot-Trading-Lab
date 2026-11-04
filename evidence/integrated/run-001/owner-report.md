# Owner decision: retain V4 as research control; reject the integrated challenger

**4 November 2026. Research only. No profitability or paper-readiness claim.**

The requested integrated market reader, entry-price alternatives, structural
thesis exit and genuine 5m response path are implemented and independently
testable. **None improved on frozen V4 in the comparable native development
experiment.** The strict combined candidate admitted no trades. Do not promote it.

| Same 14-market native portfolio | Submitted / filled / unfilled orders | Net USDT | Native extra 10 bp/side |
|---|---:|---:|---:|
| Frozen V4 |46 /45 /1|+3.473272|+1.423486|
| Frozen PR #12 |14 /14 /0|−0.246954|Not replayed; ledger−0.871369|
| Contextual EMA/structure alternative |62 /61 /1|−0.730953|−3.549154|
| Passive 0.15ATR entry |46 /36 /10|+1.257884|−0.396053|
| Structural thesis exit |46 /45 /1|+2.668069|+0.617939|
| Context selector / first-objective target / integrated |0 each|0 each|Integrated 0|

September 1–November 3 UTC, end exclusive;1,000 USDT wallet,1×, maximum two
positions,25 USDT cap, native 7.5 bp/side and recorded funding. Each row is a
separate portfolio. The new native 17.5 bp/side runs are actual replays;
5/10/20 bp turnover sensitivities are separately identified in the JSON report.

**What now works.** Freqtrade can run the isolated historical challengers with
source seals, causal market explanations, frozen locations, actual native order
records, nonfill accounting and independent fee/funding reconciliation. V4 and
PR #12 fresh replays reproduce all 45 and 14 complete archived trade objects exactly.
The order observer also leaves V4 trades unchanged. A missing-boolean handling
bug found after the first matrix was fixed under a separate seal; all 196
historical market reads remain exactly equal, with final-seal replays retained.

**What the losses taught us.** The 59-trade forensic dataset and 3,665 rejected,
expired or invalidated event records separate decision-time facts from future
paths. Protective exits account for 23 V4 and 5 PR #12 losses; this does not prove
their stops were wrong. Fees/funding turn two V4 gross winners into net losers.
Waiting for structural thesis failure reduced net by 0.805202 USDT on exactly the
same 45 entry keys. Passive pricing missed more fills and lost 2.215388 USDT versus
V4. The contextual alternative changes both eligibility and ranking, so its
4.204225 USDT deficit cannot be attributed to EMA alone.

The auxiliary MFE calculation excludes the exit candle. It falls below realized
movement in 12 V4 and 2 PR #12 records. Native extrema use a different bookkeeping
window; including the exit candle can include post-exit prices. Definitions and
bounds are now explicit. Exact accessible peak profit remains unknown. Wrong
regime, lateness and target causality are not assigned merely from a losing P&L.

**Why the integrated/5m results are insufficient.** The first-objective rule
rejects all 56 original V4 selected plans. Its zero return is abstention, not an
improved trading edge. Genuine Gate 5m data cover October 5–November 3 only:
116,928 candles,307 location candidates,235 registered opportunities. Two early
responses pass geometry before ranking; neither passes the frozen shortlist.
All three 5m portfolios therefore have zero orders. No 5m profitability claim is
possible. The shorter cohort is separate from the full-period V4 comparison.

**Robustness and gaps.** One-tick trade-through reduces V4 to 43 fills/+2.891918
and passive entry to 35/+1.071384. An extra 20 bp/side ledger charge makes V4
−0.626301. Passive entry becomes−0.567210 without its largest winner. All tested
nonempty portfolios have weekly-block uncertainty intervals spanning zero, and
results vary across markets/months. These are correlated, repeatedly inspected
development observations. Main 15m range-touch fills cannot establish exact
five-minute expiry, real spreads or queue priority. Funding uses preceding
hourly mark OPEN. Genuine historical flow/profile, sweep/MSS/FVG entries,
breakout early-entry, progress timers, legal partials/runners and independent
validation remain unfinished or untested. The reserved future holdout was
untouched.

**Verification and delivery.** 23 native records/617 independently reconciled
trade records include overlapping alternatives and repeats. 119/122 broad checks
pass; two inherited source-registration errors remain and one optional tape
fixture is unavailable. Seven supplementary native funding, stop/target ordering
and archive-safety checks pass: 126 passes across 129 distinct checks. The
340-file private bundle was fully restored and hydrated with zero overwrites. All 3,324
starting files, including 3,065 evidence files, remain byte-identical. The first
failed Docker startups and test attempts are retained. No real/testnet order,
persistent paper process, paid service, execution permission, leverage increase
or merge was enabled.

Use the [restore/replay/rollback runbook](../../../docs/operations/integrated-research.md).
Key evidence: [economics](economic-report.json), [trade forensics](forensics-trades.json),
[tests](regression.json), [preservation and clocks](final-verification.json),
[source manifests](data.json), [backup receipt](private-backup.json).

```bash
./scripts/lab-integrated.sh verify
./scripts/lab-integrated.sh native control-v4 --replay-id owner-check
./scripts/lab-integrated.sh native entry-passive --replay-id owner-check
```

Inputs must first be checksum-restored from the provided private bundle. Stop
using the new wrapper and return to PR #12's branch to disable this work; nothing
persistent was activated. The separate PR targets `codex/pr11-causal-fixes`.

**Judgment: REJECTED for integrated promotion; INSUFFICIENT 5m economic evidence.**
Keep V4 solely as an unqualified research control. Recommended owner-approved
next action: commission one separately preregistered study of obstacle relevance
and shortlist exclusions on a distinct permissible historical period. Do not
activate trading or relax gates just to create a positive development result.
