# OpenBot Trading Lab — M32 Wyckoff and M33 CRT+TBS
## Formal Design 1+ method expansion and shadow-implementation contract

**Amendment ID:** METHOD-AMEND-2026-11-23-M32-M33
**Status:** Owner-requested experimental methodology expansion. Detailed design approved for planning; market-source qualification and live admission NOT approved.
**Primary architecture:** OPENBOT_DESIGN1_PLUS_AMENDED_BLUEPRINT_2026-11-23.md
**Full 1,100-line analytical source specification:** references/ANALYTICAL_METHOD_EXPANSION_PROPOSAL_2026-11-14.md — sections A–O, including explicit formulas, state machines, source capability matrices, method-role maps, test vectors and exact v1.0 blueprint insertions.
**Baseline preserved:** F1–F9 and M01–M31; M12 CRT and M05/F4 wick-sweep remain intact.

This file is the governing integration and promotion policy for the full method reference. Read the full linked 14 November proposal before editing methodology modules; this summary is NOT a substitute. Where the proposal contains numerical trials or author interpretations, preserve their experimental status. Its unapproved content does not silently become an empirically validated algorithm.

---

## 1. What the owner wants from these additions

M32 — Wyckoff: the Researcher should reason about an evolving, causally confirmed trading-range lifecycle with rival accumulation/distribution/continuation explanations, *not* a new bullish or bearish indicator flag. Observe multiple chronologically separate tests, potential selling/buying climaxes, AR/ST and later spring/UTAD/SOS/SOW/LPS/LPSY possibilities and compare effort-versus-result episodes. Avoid assuming institutional intent, guaranteed phase sequence or profitable target based on the shape of a range.

M33 — CRT + TBS: the Researcher should distinguish a preselected completed higher-timeframe candle reference, a later lower-timeframe **completed body close outside** its range, a **separate subsequent failure/reclaim**, and a still-later possible structural response. Do not call a wick-only sweep or same-bar inside close a body-close TBS. Different CRT/TBS authors and alternative variants must be versioned separately; the selected version is an engineering trial, not asserted author-canonical strategy rules.

Both can independently NOMINATE early research questions if they add unique information; their shared OHLC events do not earn independent confirmation votes merely because they have extra method labels.

---

## 2. Shared scope and non-negotiable evidence

- Exact Binance USDⓈ-M USDT-quoted and settled crypto perpetual identity; preserve multiplier, tick, units, venue and provider scope.
- Data must contain completed candles, unambiguous UTC interval, first known-at time, available-at, source arrival, source formula hash, provider qualification and explicit missingness.
- Historical ranges or references must be known *before* the event they are used to interpret. Never choose the successful parent candle or Wyckoff accumulation boundary retrospectively.
- Price OHLCV is not genuine footprint; base/quote volume and taker statistics must not be called true price-bin aggression. Funding/OI/liquidations do not reveal one-sided institutional intention.
- Preserve one shared event root for the same observable wick, break, reclaim or volume episode. Method family rivalry is valuable; counting repeated names as independent evidence is not.
- Use external-first broad 1H/15M price/structure precursors; expensive 4H/1H/5M chronology only for selected candidates, with tested source rights and bounded API budgets.
- Method output has separate definition status, detection status, source capability, times/known-at, qualification, opportunity stage and economic room. Never silently downgrade a missing method to numeric false or certify it from a proxy.

---

## 3. M32 Wyckoff state and quantitative trial definitions

### 3.1 Range creation

A range R has pre-known low L, high U, origin, timestamp of first knowability, confirmed distinct touch episodes, volatility reference, range lifecycle and exact source IDs. The baseline method M03/M16 may provide an independently qualified preknown range, otherwise construct from separated upper and lower tests and actual bidirectional rotations. Do not infer an established trading range from a single pivot, a candle retrospectively selected at the extreme or non-separate repeated candle touches.

Trial edge buffer: b = max(2*tick, alpha*ATR_ref), alpha from {0.10, 0.20, 0.30}, with preknown ATR_ref>0. These are parameter exploration values, not production-optimal thresholds. For completed bar t where R was already known:

- Spring geometric candidate: low_t < L - b and close_t > L + b.
- UT/UTAD geometric candidate: high_t > U + b and close_t < U - b.
- Later accepted breakout: independently qualified later closed bars or source-backed tested hold/retest sequence outside the relevant boundary.
- Potential opposite structural response must occur on later actually available bars; an instantaneous phase-certification is prohibited.

Historical confirmed-range start, separated test counts, chosen ATR seed, min retreat/duration, tie conventions and episode normalization must be versioned. If missing, give RANGE_CANDIDATE or UNKNOWN.

### 3.2 Episode effort/result comparison

For separately confirmed comparable episodes e1,e2:
- progress_e = abs(close_end-close_start)/ATR_ref.
- efficiency_e = abs(close_end-close_start)/sum(abs(delta close) within the episode), with denominator policy.
- effort_e = quote_volume_sum / number_of_closed_bars, or other explicitly qualified normalized source units.
- A relative effort increase alongside relative progress deterioration can NOMINATE tension/investigation. Trial effort threshold set {1.2, 1.5, 2.0}, trial relative progress {0.5,0.75}. **Not** confirmation of absorption, not a trading signal.

Compare matched source, native contract, comparable durations/volatility, complete bars, quote/base units, event separation and event-root identities. Otherwise EFFORT_RESULT_UNKNOWN.

### 3.3 Conceptual/chronological vocabulary

- Early trend slowdown: PRELIMINARY_STOPPING_CANDIDATE; do not state terminal support/supply yet.
- SC/BC: climax *candidate* at event; AR and ST become separately knowable *later*. Avoid retroactive confidence.
- AR/ST: actual reaction and subsequent test episodes, not generic current flags.
- Spring/UTAD: preknown range-bound excursion/reclaim; correlate to F4/F6/F2 competing narratives.
- SOS/SOW and LPS/LPSY: later independently observable acceptance/response and controlled retest, not retrofitted arbitrary trend waves.
- Reaccumulation/redistribution: rival hypotheses when trend context and a new coherent range exist.
- A trading range need not pass through every modern schematic phase. Model can output ACCUMULATION_CANDIDATE, DISTRIBUTION_CANDIDATE, ROTATION, BREAKOUT_CONTINUATION, REACCUMULATION, REDISTRIBUTION or UNKNOWN with citations and falsifiers.

### 3.4 Transition and invalidation

NO_VALID_RANGE -> RANGE_CANDIDATE -> ESTABLISHED_BALANCE -> APPROACH -> {SWEEP, OUTSIDE_HOLD, ROTATION} -> {LATER_RETEST, RESPONSE, FAILED_RECLAIM} -> {EARLY, DEVELOPING, WATCH, READY, LATE, INVALIDATED, UNKNOWN}.

These are observational states; "phase A–E" remains a separately annotated *interpretation*. Acceptance opposite the presumed reversal invalidates the **reversal hypothesis**, not the existence of the source range history. A setup is LATE if actual room was consumed even when a retrospective schematic looks attractive. The research horizon <=15 hours limits potential forward opportunity, not permitted historical reference age: multiweek balance can be relevant to an imminent 15M decision.

### 3.5 Rival and question contracts

Candidate M32 asks:
- Was the range actually known by the cited cutoff?
- Are the prior test episodes independent in time?
- Are price progress and executed quote-volume units comparable?
- Is this valid F2 accepted breakout, F4 failed break, F6 rotation, F1 reaccumulation or F9 postshock instead?
- Which new observation would falsify the supposed phase before the next meaningful structural obstacle?
- Does the case have source-qualified room and spread/economics for a Deep Analyst handoff?

AI must be able to keep multiple rivals and a NULL/no-opportunity interpretation; remote source unavailability is not a bullish or bearish vote.

---

## 4. M33 CRT+TBS state and body-break trial definitions

### 4.1 Separate variants

- M12 existing CRT: preselected 1H/4H candle, edge excursion and possible reclaim. Preserve existing implementation and rules.
- M05/F4 wick sweep: high/low pierces a preknown boundary but returns inside on the SAME completed candle. It may be a meaningful price-only observation; never label as the strict M33 body-close pattern.
- M33 body-close-failure v0: a preselected fully completed HTF candle, a LATER 5M closed body outside, a DISTINCT later 5M inside close, no separately qualified accepted outside break before reclaim.
- Alternative internal pivot TBS, CRT expansion or different source-author variant: separate future definition, not automatically v0.

### 4.2 Parent selection and chronology

Example trial parent R: 4H candle previously completed and available, overlapping a previously confirmed 1H decision region, with width 0.6–2.5 times preceding qualified ATR4H. Pin ex-ante selection policy, parent ID, upper U, lower L, midpoint, source and known-at. One to three candidate completed parents of 12–24h historical relevance are a TRIAL grid, not assumed canonical. Future parent highs/lows cannot be used. Do not backselect the most successful reference after observing the supposed failure.

For every 5M bar b:
- Require closed(b) and source.available_at <= the decision cutoff.
- Parent known_at <= b.open_at for first outside test.
- Reclaim bar r.open_at >= break bar t.close_at.
- A 15M scalar cannot prove this 5M event order.

Trial buffers:
- b_out = max(2*tick, alpha*ATR_ref), alpha from {0.05,0.10,0.20}.
- b_in = max(tick, beta*ATR_ref), beta from {0,0.05,0.10}.

Bearish body failure: close_t > U+b_out, then separate later close_r < U-b_in, after no qualified accepted outside hold between t and r and before expiry. Bullish: close_t < L-b_out followed by separate later close_r > L+b_in. Trial reclaim delay {1,2,3,6,12} *closed 5M bars*. A subsequent separately closed opposing internal structural break/displacement may promote RESPONSE_CONFIRMED, but is not required to label the observed two-stage reclaim geometry.

### 4.3 State and rival tree

- PARENT_FROZEN: completed 4H parent selected before excursion.
- NEAR_EDGE: developing 1H/15M boundary approach; early watch, NOT exact TBS.
- BODY_OUTSIDE: 5M close beyond frozen parent boundary; an accepted F2 breakout remains a legitimate rival.
- FAILURE_WATCH: outside action appears unable to extend under a versioned observation window, but reclaim incomplete.
- RECLAIMED: separate later 5M close inside and no accepted outside sequence; operational body failure observable.
- RESPONSE_CONFIRMED: independent later opposing BOS/MSS/displacement/defended retest observed.
- ACCEPTED_OUTSIDE: breakout/hold evidence supports F2 and contradicts premature reversal.
- RECLAIM_FAILED: rebreak/hold can support F5 continuation.
- EXPIRED, LATE, INVALIDATED, UNKNOWN, SOURCE_GAP: objective statuses; no forced reversal.
- First opposing obstacle = nearest actually preknown internal swing/value/parent midpoint/opposite edge, not an automatic profit target.

### 4.4 Source feasibility and admission limits

Wide scan: reuse existing qualified 1H/15M core proximity/pressure; optional source-qualified 4H frozen reference metadata. A wide 1H/15M precursor may independently nominate only an M33-related *question*, not exact verified M33 body failure.

Targeted: fetch a bounded selected-contract 4H/5M event-tail (prefer external computation when oracle-qualified), otherwise controlled read-only native Binance history from an authorized reachable host. No all-universe 5M download or historical local warehouse.

If 5M completeness, parent confirmation time, quote basis, source rights or alignment is missing, return M33_NEAR_EDGE_PROXY or UNKNOWN; never BODY_TBS_CONFIRMED.

---

## 5. Shared schema and family mapping

Extend the existing event/ledger schema minimally with optional stable:
- method_id, variant_id, definition_source_id, definition_status, observed event_root_id and same-event dependency IDs.
- preknown parent_reference_id (M33) / R_id (M32), event timestamps (known_at, available_at), evidence source IDs.
- support/contradiction/unknown ID sets, rival family/method hypotheses and next discriminator question.
- method-specific lifecycle state, first opposing obstacle/room state, scope/coverage and rank eligibility.

Families remain:
- F1 trend pullback or reaccumulation; F2 accepted breakout; F3 compression and expansion; F4 sweep/reversal; F5 failed reversal and continuation; F6 balance/auction; F7 value/VWAP reversion; F8 cross-market residual/relative strength; F9 shock stabilization.

M32 and M33 map to applicable **multiple** families. One source event can support several rival interpretations but only one observational evidence dependency root. The model's chosen alternative family can replace a provisional primary family only if separately qualified with its own evidence/temporal/room constraints. Never downgrade source-qualified hard gates just to make reclassification pass.

---

## 6. LLM interpretation under Design 1+

DISCOVERY AI can independently spot early Wyckoff/CRT-related possibilities in transmitted eligible broad evidence, including quiet and opposite-BTC cases. It must name supported alternative families and the exact missing stage/clock fact; it may choose bounded source-qualified investigation questions, not invent network calls.

SHORTLIST AI assesses actual investigated history, contradictions, room, source capability and unresolved rivals, and can select HANDOFF, WATCH, DECLINE or UNKNOWN. No model can certify a missing 5M reclaim, institutional volume absorption, a guaranteed Wyckoff phase or profitable edge.

Method changes add to evidence and interpretation; they must not introduce a second AI orchestration layer, a new agent, an unrestricted query tool or a new hardcoded market opinion engine.

---

## 7. Required oracle matrix and source feasibility

### Wyckoff positives and negatives
- Preknown established range, separated tests, later spring and independent response => M32 candidate with event order, F4/F6 rivals.
- Same price pattern with only one isolated pivot => no preknown range; NO positive M32.
- Before later AR/ST known => label SC/BC only as climax candidate; do not repaint prior events.
- Distribution/UTAD candidate vs accepted upside breakout => record both, then correctly invalidate the former when source-qualified accepted hold arrives.
- Incomparable quote vs base volume, missing baseline volume, missing bars => effort/result UNKNOWN.
- Multiple nested ranges, equal highs/lows, long holding before a decision => retain roots, causal times and uncertainty.
- Late/past first obstacle => not READY merely because full Wyckoff phase story now seems convincing.
- Append-future regression: outputs already known at T unchanged when future bars appended.

### CRT+TBS positives and negatives
- Completed 4H parent, later 5M close outside, separate later 5M reclaim inside => M33 observed body failure.
- Mirror both directions; independent later opposing response required only for stronger stage.
- Wick-only pierce with same-bar inside close => M05/M12, NOT M33.
- Parent known only after outside test => future-leakage rejection.
- Missing or partial 5M data => SOURCE_GAP / UNKNOWN, never exact body confirmation.
- Accepted outside after body close before any reclaim => F2 rival; reject premature M33 reversal.
- Reclaim then later accepted outside => F5 continuation candidate with original event lineage.
- Same 5M bar counted as both break and reclaim => chronology rejection.
- Same observed excursion can belong to M05/M12/F4 or M33 only when each method predicate actually qualifies; do not double-score independent votes.
- BTC/ETH context never vetoes valid alternative coin structure.

### Integration and resource tests
- Valid source-denominator report per method/timeframe/source/contract.
- Remote provider eligibility/access 403/451 remains truthful, no circumvention.
- No invented price-bin volume, footprint, stop-location/actor-intent data.
- Relative method novelty in matched-budget comparisons: time-to-nomination, extra admissible cases, useful discrimination, cost, false positives and missed no-opportunity cases.
- One coherent actual Researcher AI turn can interpret new method evidence only when native AI boundary has itself been proven.
- No trading orders, no automatic entry/SL/TP, no implied future return.

---

## 8. Implementation and promotion boundaries

**Minimum in one Codex Cloud session, if infrastructure priority permits:**
1. Publish this file + full preserved analytic proposal, anchor M32/M33 in method registry using stable IDs, no renumbering.
2. Implement only the minimal shared event/interpretation extension and selected positive/negative temporal oracles where code's current structure permits small isolated change.
3. Keep new methods SHADOW, annotate watches/questions and source capability; do not promote them to production source-qualified full-market independent methods.
4. Wire evidence IDs, clocks and rivals to existing AI stage schemas when safe and tested.
5. Preserve original files, source rights, code history and independent provider receipt checks.

**Defer or explicitly mark blocked:** source-qualified 5M exact body dataset, full Wyckoff OHLCV/event-tail history on all eligible contracts, empirical after-cost edge, distinct author variant approval, live source integration if unavailable/unauthorized.

**Gate progression:** TRIAL_SPEC -> CODE_IMPLEMENTED_SHADOW -> OFFLINE_ORACLE_VERIFIED -> SOURCE_QUALIFIED_PER_METHOD_CONTRACT_TF -> OWNER_APPROVED_ADMISSION -> PROSPECTIVE_UTILITY. Never promote automatically.

**Hard dependency order:** native AI communication first; market methodology additions must not distract from proving the core reasoner can operate. If the Cloud session is constrained, preserve fully detailed published specifications and a bounded test scaffold rather than a half-implemented "live" M32/M33.

---

## 9. Future review and versioning rule

Every future Codex Local/Cloud review and development must read this **complete document plus the full 14 November source proposal** when methods are in scope; cite the applicable method sections in the Context Acceptance Receipt. Report actual current code, tests, source/coverage and which statuses remain design-only. Do not re-run a source-unavailable method under a different name.

New methodology variants are append-only and explicit. No silent change to M12/M05/F1–F9, and no introduction of multiple independent signals from one set of source candles.
