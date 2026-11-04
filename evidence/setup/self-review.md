# Three separate self-review passes

## Pass1 — trading mechanism and meaningful levels

Inspected the actual ordered recognizer and real accepted/rejected cases before
reviewing their subsequent outcomes. SOL Sep11 18:15UTC is an external-high short
reversal; SOL Sep29 13:15UTC is an accepted/retested range breakout. BTC Sep23
03:30UTC continuation is rejected at the first obstacle; BTC Sep2 02:30UTC shows
an invalidated defended zone. These entry-time facts and separate future results
are retained in run-002/casebook.json, without selecting a showcase by profit.

Found and fixed: a previously crossed swing could masquerade as a later shift;
now the pre-sweep swing must still be ahead and actually crossed on a later bar.
A gap-invalidated anchor could rearm; its identity is now consumed. The initial
v1 implementation omitted the parent's6ATR horizon bound, accepting some real
but implausibly distant objectives. Preserved the whole initial21-portfolio
comparison and registered/replayed v1.1 with the bound restored. No other
numeric setup threshold was tuned to results. Final positive/false behavior
fixtures and14 real-source prefix checks pass.

Remaining: strict continuation produces no selected historical entries; no
continuation profit claim is possible. Full-profile economics remain NOT TESTED.
One complete real8h reference profile is validated against32 source candles,
but its actual receipt is today, not invented historical availability. Market
structure/volume patterns are price hypotheses, never evidence of hidden stops
or institutional intent. The new workflow loses before transaction costs.

## Pass2 — causal execution and economic attribution

Checked feature availability, prior session completeness, confirmed-pivot clocks,
1h/4h merging, first-fill holding clocks, native callbacks, legal lots, margin,
fees, funding and portfolio overlap. Reconciled every native order's entry/exit
quantity, price PnL, fee and signed source-event funding against raw funding/mark
files. Checked long/short native SQLite partial cancellation/restart/final exit,
idempotent fill events and monotone protection. Exact replay reproduces all five
complete final trade objects. An existing old policy-suite registration failure
was reproduced on the untouched starting worktree; frozen files were not edited
to disguise it.

Found and fixed in reporting: cached shortlist reuse dropped cheap-scan counters;
the report now independently derives them from the actual feature frames. Made
same-entry target/management effects separate from portfolio-capacity effects.
Clarified that reference-mode V4 and the owner's retained structure-mode V4 are
different frozen controls; added the exact unchanged structure lane plus native
fee/risk comparisons. The initial primary seal and control-extension registration
are both retained. The challenger rules/initial plans did not change in that
extension. Also added per-plan execution states; an individual native veto that
was not instrumented is explicitly UNKNOWN rather than an invented reason.

Remaining: five final trades and nine calendar weeks do not support broad
inference. Three ranking nulls have0.25 p-value resolution. Candidate barrier
paths are diagnostics, not hypothetical cash portfolios. No primary objective
partial was triggered historically. Real1m coverage spans only the final five
days, with zero corrected-primary fills. Queue priority, partial-order frequency,
intrabar gaps/ordering and exact settlement marks remain unknown. Funding uses
source clocks and preceding hourly source-mark OPENs. The admission allowance
is not charged as a second fee. Development variants and replays are not
independent observations, and their portfolio returns are never added.

## Pass3 — integrity, operation and claims

Compared all 2,844 starting tracked files with their starting Git blobs: zero
changes. V3/V4, original EMA, earlier reports, production settings and reserved
holdout remain untouched. The new class refuses live/dry-run/hyperopt and1x is
the only executable leverage. The native protective bound persists independently
of thesis-close callbacks;15h caps first fill even if a malformed plan asks longer.
Legacy 24h hourly V4 research remains unchanged and is not called compliant.

Verified the real scanner→shortlist→plan→native fill→thesis/time/stop exit→report
workflow, source/input seals, exact replay, schema-valid read-only export, four
distinct skills and safe private restore/hydration. No extra execution engine,
dashboard, agent runtime/admin bridge, paid data or trading service was added.
The runner now verifies all source/feature/plan/data hashes before replay. Final
report claims explicitly disclose zero strict-continuation fills, no historical
objective partials, incomplete profile cohort, source/spec limitations and the
negative economic result. Owner commands require no configuration editing.

Remaining: owner-host isolation, persistent operation, real exchange fill/stop
behavior and future profitability are untested. OpenBot receives only a manual
sanitized evidence copy. Full historical reference tape is missing for the
profile portfolio. No strategy promotion or merge is justified. The final handoff
includes the actual backup restore result and disposable-process shutdown proof.

Final artifact check: the88,360,503-byte private backup contains619 files. All619 were restored and then hydrated into a fresh directory with zero overwrites. Temporary verification copies and the disposable worker were removed; Docker reported no running containers.
