# PR11 causal corrections — completed historical research handoff

The six requested changes are implemented and mechanically verified. One new
matched native replay completed: **14 fills, −0.246954 USDT after fees/funding**.
This improves on frozen setup-v1.1's −1.351729 USDT, remains below frozen V4
structure's +3.473272 USDT, and does not justify promotion. Volume Profile
economics remain **NOT TESTED**. Historical signed Order Flow remains UNKNOWN.

The separate branch is `codex/pr11-causal-fixes`, starting at PR11
`f0ef4453144869ca013ad156fdd46c81b767af2c`. Decision implementation is committed
through `5786ec7afccf3c687b673e6aa64af9bbec7b18d1`; the backup writer correction
is `fbab8e831ae67a95b246b3def4c3ffe7984ea83f`. The final branch adds this evidence
and documentation. Its exact diff is [the comparison to the starting commit](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/compare/f0ef4453144869ca013ad156fdd46c81b767af2c...codex/pr11-causal-fixes).
All53 decision-source hashes match the source sealed before the native outcome.
No decision rule was patched in response to the new return.

| Requested gap | Implementation and fixture evidence | Native/economic status |
|---|---|---|
| Shortlist before deep work | `setup_screen.py`, `setup_checkpoint.py`, `setup_candidate.py`; 50-pair early-stop/dedup, dropped WATCH/position, late-entry and checkpoint fixtures | Normal candidate preparation uses on-demand deep updates; all14 filled positions have complete management coverage |
| Completed4h obstacle | `setup_map.py`, `setup_features.py`; exact UTC grouping, duplicate/gap/partial, prefix invariance, open-of15m timing, long/short nearest-barrier rejection | Actual plans carry4h provenance and map readiness; native geometry consumes the registered nearest objective |
| EMA gates | `setup_features.py`, `setup_screen.py`; sign/NaN invariance, independent swing readiness, no defended-location/confirmation abstention | Three continuation admissions/fills; all three log an old-EMA veto |
| Breakout reset | `setup_features.py`; shallow-inside long/short reset, new event IDs, boundary equality, outside wick retest | Real PEPE paired trace invalidates the old event before the old pipeline's admission |
| Event export | `setup_export.py`; WATCH stays geometry-null, later event owns its plan, schema validation | Actual run003 read-only export generated and validated after reconciliation |
| Genuine Profile routing | `setup_profile.py` → normal preparation/shortlist/scanner → native plan; valid, missing, late, stale, wrong-pair, approximate and multiple-session fixtures | Normal-runner fixture produces a rotation plan consumed by native `row_plan`; historical sample was assembled later, so no historical rotation claim |

The [focused tests](../../../tests/test_setup_fixes.py),
[runbook](../../../docs/operations/pr11-fixes.md),
[protocol](../../../research/setup/candidate-protocol.json) and
[freeze](freeze.json) describe the executable path. Other affected files are
the setup policy, shared causal pivot implementation, namespace/data/prepare/
seal/verify/native/report wrappers, export and advisory playbook documents.
Existing causal-pivot batch behavior remains supported and tested. No frozen
control is rebuilt by the candidate's normal path.

The pinned regression pass ran94 tests:93 passed, with the one already-documented
parent registration error and no unexpected errors/failures. The final affected
setup suite passes39/39, including16 new focused cases. Original structure
regressions pass5/5. These suites overlap; their counts are not additive.
See [verification summary](verification-summary.json), [broad log](verification-logs/verification-pass.txt),
[final setup log](verification-logs/release-setup-tests.txt) and unchanged
[parent proof](../run-001/parent-regression-policy.txt). The broad report's parent-evidence field mistakenly names run002; the preserved parent log is in run001. The exact legacy error is
`test_policy.ConfigTests.test_baseline_and_native_emergency_settings_do_not_inherit_vwap_overrides`:
`registered v3 source changed; record explicit amendment`.

The first-fill15h hard cap, shorter8h/4h/8h/6h playbook holds, separate five-minute
order clock, native geometry checks, historical-only mode refusal and immutable
seals were verified. A final [seal check](verification-logs/release-seal-verification.txt)
passes. No native replay was repeated to improve results.

The comparison uses the original14 Gate linear perpetuals, September1 to
November3,2026 UTC end-exclusive, August22 source warmup,1000USDT wallet,1×,
max2 positions,25USDT cap and7.5bp native fee per side plus archived source funding.
Native limit-touch fills are simulations. The38bp allowance gates admission and
is not charged a second time. Frozen controls retain their own stop/exit/hold rules.

| Portfolio | Evidence | Routed plans | Fills | Gross price PnL | Fees | Funding | Net USDT | Extra10bp/side net |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Frozen V4 structure | Archived native; ledger independently re-audited | 56 | 45 | +5.014990 | 1.537340 | −0.004379 | +3.473272 | +1.423486 |
| Frozen PR11 setup-v1.1 | Archived native; ledger independently re-audited | 5 | 5 | −1.187000 | 0.169678 | +0.004949 | −1.351729 | −1.577966 |
| Corrected setup-v1.2 | One new native replay | 14 | 14 | +0.217300 | 0.468311 | +0.004057 | **−0.246954** | **−0.871369** |

Extra friction is a turnover ledger sensitivity, not another replay or observed
slippage. The new candidate has4 wins/10 losses, profit factor0.889, average hold
187.5min and native maximum drawdown1.186101USDT. Its10 breakout fills net
−0.337645, three continuation fills net−0.632637 and one reversal nets+0.723327.
No historical rotation fills occur. Full metrics, order reconciliation, native
provenance and checks are in [comparison.json](comparison.json) and
[native evidence](native/setup-fixed-touch-750).

| Opportunity/work measure | Frozen PR11 rules | Corrected full-universe offline audit | Corrected candidate |
|---|---:|---:|---:|
| Raw pair-time checks | 84,672 | 84,672 | 84,672 |
| Eligible with required closed-bar data | 72,741 | 72,741 | 72,741 |
| Distinct setup IDs | 4,080 | 4,091 | 3,679 |
| Geometry-qualified opportunities before native | 17 | 16 | 14 |
| Qualified under corrected rules: selected / missed | Different rule set | 16 reference | 14 / 2 |
| Old selector applied to corrected reference | — | 3 selected / 13 missed | Same cutoffs and3-per-lane budget |
| Deep pair updates | Full-history precomputation; not freshly timed | 74,880 | 55,517 |

The old17 qualified opportunities and new16 audit opportunities use different
rules. They are not an isolated selection comparison. Likewise setup IDs changed
with breakout event identity and lifecycle start rules. V4's56 routed plans use
its frozen policy; they are not counted as setup-v1.2-qualified opportunities.

The turnover gate itself is unchanged:74,867 turnover-eligible checks minus2,126
required-data failures equals the old72,741 combined denominator.9,805 checks
fail liquidity/warmup. The candidate logs6,901 distinct market observations,
3,679 arms,1,269 expiries,1,661 invalidations,735 geometry rejections and14 READY
plans.315 developing breakouts close back inside. Geometry rejects include522
insufficient first-obstacle rewards,109 invalid stop distances,79 missing
objectives and25 objectives beyond6ATR. No farther target is used as a fallback.

The candidate uses53,826 unique shortlisted pair-times across98,421 lane slots,
avoiding44,595 duplicate pair updates. It retains1,599 active-setup updates and95
management updates outside the shortlist. The actual filled-position audit finds
no missing updates or hard-hold violations. New lifecycle recognition never runs
on historical feature warmup.

Continuation specifically has902 arms,209 completed confirmations,206 geometry
rejections,29,987 shortlisted pair-times and3 READY/admitted/filled plans. The
old EMA telemetry would veto516 arms and all3 READY plans. These are evidence
counters, not a second native EMA ablation.

Deep calls fall25.86% relative to the explicit full-universe audit. **A walltime
improvement is not demonstrated:** candidate execution took133.74s, including
old-selector bookkeeping, versus89.01s for the audit. Deep-provider time was
51.41s versus16.86s. The audit benefits from continuous state and warmer caches;
candidate reactivation incurs checkpoint work. These are not equivalent latency
benchmarks. Candidate sequential state hits are50,780; checkpoint hits4,737;
warmup reads18,948 rows. Shared checkpoint transport reads14 files/98,112 rows/
79,366,967 canonical bytes with4,755 file-cache hits. Cheap input loading reads
28 files/122,640 rows/3,787,304 bytes in22.95s. Provider requests and new market
downloads are both zero. These measurements describe offline archived compute,
not actual network/API savings. See [compute evidence](compute-work.json).

The [synthetic50-pair fixture](fixture-50-pair.json) checks50 pairs: one illiquid,
49 eligible, nine lane slots, three unique shortlisted pairs and exactly three
deep calls;46 eligible nonshortlisted pairs incur no deep work. Six duplicate
lane slots share those same calls. Separate fixtures prove WATCH retention,
management after eligibility loss and late-shortlist feature warmup without a
retroactive trade.

The traced accepted opportunity is **ETH/USDT:USDT breakout short**, at
October14,2026 13:00UTC. Prior-day estimated turnover is5,690,308,524.58USDT and
seven-day average4,623,202,667.58USDT, both above10M. It ranks as a developing
break,0.269645ATR from the2478.17 hourly lower boundary. That prior20-complete-hour
range reference was known at12:00UTC; the reliable4h map was also known at12:00.
Its setup ID is:

`ETH/USDT:USDT:breakout:short:PRIOR20_COMPLETE_1H_RANGE:2026-10-14 12:00:00+00:00:2478.17:BREAK_AT:2026-10-14T13:00:00+00:00`

The later13:15UTC completed trigger establishes two-close acceptance and a
defended retest. Decision `ETH/USDT:USDT:c3aaf2c1a982dba699c3e763` freezes
2464.4 entry reference,2491.033531 structural stop and2407.77 first objective.
That prior-day low was known at00:00UTC; a confirmed4h low at the same price was
known October13 12:00UTC. They identify one obstacle, not independent confluence
credit. SignalATR is11.217653; stop distance1.080731%; after-cost RR1.312988.
The open thesis requires two completed adverse boundary closes. Entry expires
at13:20UTC; preferred max hold is8h and absolute first-fill cap15h.

Native risk passes with0.01ETH,24.644USDT notional,0.359983USDT modeled loss and
2.498859USDT available risk budget. Leverage remains1×; risk checks include legal
lots, capacity, collateral and stop/liquidation clearance. Current public Gate
tiers are used, not claimed as historical tiers. The simulated fill is13:15UTC;
full objective exit is20:45UTC after450min: gross+0.566300, fees0.036541,
funding+0.000534, net+0.530293USDT. See [the complete trace](traced-opportunities.json).
The trace is the first serialized pair/time plan, selected without using returns.
The frozen report labels it chronological incorrectly; the explicit
[metadata erratum](trace-selection-erratum.json) preserves that completed artifact
and corrects the selection description without changing any decision or result.

The rejected paired case is **PEPE/USDT:USDT breakout short** on September6.
At14:30UTC it arms below3.576e−6, a boundary known at13:00UTC. At14:45UTC the
close3.577e−6 is strictly inside, so the timestamped event becomes INVALIDATED
with `BREAKOUT_CLOSE_BACK_INSIDE`. The old pipeline subsequently admitted the
same unresolved boundary event at15:15UTC, reference3.567e−6, stop3.610460e−6,
target3.437e−6. The corrected pipeline has no READY plan at that cutoff. A new
break would need its own independent sequence. This explains a mechanical
difference; it does not isolate a PnL contribution. All five old plans have
[paired same-cutoff evidence](paired-frozen-opportunities.json).

[Preservation proof](preservation.json) verifies all3,015 existing evidence files
against the starting Git tree with zero changes, all53 pre-replay source hashes,
the original88,360,503-byte backup SHA256 and unchanged frozen-policy/session4/
production configurations. The shared causal pivot file deliberately gains
incremental support; frozen controls retain their own staged source hashes and
ZIPs. No holdout data were inspected. PR11 remains open and unmerged.

The new private bundle is `PR11-Fixes-Private-Backup.tar.gz`,94,817,941 bytes,
SHA256 `eb880f741fff4dc982121414b4585db952d949f3a6c7dd840fd99a3c40b549c2`.
Its actual [restore](new-backup-restore.json) verifies689 files and hydration
copies zero, recognizes642 identical files plus47 losslessly compressed states,
and overwrites zero. The archive writer now materializes hardlinked cache bytes
as regular files so the strict restore accepts its output. The original private
backup is retained. See the runbook for restore, regeneration and exact-replay
commands. The image is
`freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7`,
Freqtrade2026.10 / CCXT4.5.90.

Deliberate implementation choices are the hash-verified prior-close pivot
checkpoint, conservative management-data reservations before fills are known,
and archived-control ledger reuse. Several preparation attempts were interrupted
for compute/storage fixes before any new native outcome; registered settings and
final source hashes were sealed before the single replay. No parameters, period
or playbook were selected by new returns. These choices preserve the requested
causality and bounded work without refetching frozen controls.

Mechanics pass the requested fixtures and the matched replay completed. The
bundled return change does not identify the contribution of an individual fix.
The sample is sparse and development-reused; current-survivor membership,
unknown historical spreads/status/specifications, modeled queue/limit fills,
coarse intrabar ordering and hourly mark-open funding valuation remain limits.
Profile historical economics, authentic historical signed Order Flow and live
agent decision quality remain untested. Keep V4 as a research control, reject
candidate promotion, and leave November17–December1 sealed. Live, testnet and
persistent paper activation remain disabled; OpenBot exports are read-only.
