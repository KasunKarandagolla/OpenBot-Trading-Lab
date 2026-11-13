# OpenBot external-first Market Researcher — Session 1

**Environment:** CODEX_CLOUD. **State:** Session 1 scaffold and bounded proof sprint
implemented; provider qualification **PARTIAL / BLOCKED**. **Session 2: NO-GO**
until the narrower qualification repairs below pass. No Local exception used.

## Verified branch and source authority

- Repository: `KasunKarandagolla/OpenBot-Trading-Lab`.
- Single integration branch: `feature/external-first-market-researcher`, draft
  [PR #24](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/pull/24) to main.
- Starting fetched remote SHA: `694dfdfa9d7700d7ced0a79f4502423b38ff9681`.
- Default main: `2343053ce68f6fff4525c5b67771ea445deb3779`; unchanged.
- Latest relevant unmerged implementation: PR #23 at
  `2f9ebc7b86a99c4519278ced2287a449ed4b2822`; not silently imported. All 24 PRs
  inspected were open/unmerged. [Repo truth/reuse inventory](REPO_TRUTH.md).
- Initial checkout clean. Switched to the supplied branch; fast-forward only.
  No reset/rebase/force push/main mutation. No existing AGENTS instructions were
  overwritten. Branch protection is not configured upstream; no rules bypassed.

All three authoritative files were read completely before implementation. Their
original bytes are preserved; the runtime validates the first two hashes.

| Reference | Git blob | SHA-256 |
|---|---|---|
| [Blueprint](OpenBot_Final_External_First_Market_Discovery_Blueprint.md) | `5a73d9fcbed66b29e3c0151b99b5b0d5e8966fdd` | `cf7a58fd9ed5f5d1010673406c26a405c8112b907216a47f88a9ebee1bd3d45c` |
| [Implementation plan](OpenBot_Cloud_First_GitHub_Synced_Implementation_Plan.md) | `fdccc3890bb9842653495d98dd81adc55df1802b` | `245591eea0f92cd185c51db3420043031c11c1d941f91ecdb31fd64a34e0c232` |
| [Session 1 prompt](CODEX_SESSION_01_PROMPT.md) | Recorded in starting commit | `4043051af7c1cec13314a08cf6e798cd269360158b5f4f366069eece2b09421b` |

## Implemented increment

- Standard-library Python 3.11+ `researcher` package, frozen typed instrument,
  capability, evidence and batch contracts; typed minimal report skeleton.
- Strict Decimal parsing, bar-open/end/known-by/received chronology, exact native
  symbol preservation, missing-value reasons, fidelity/scope and resource fields.
  Earliest provider availability remains null when unknown.
- Real runtime Streamable HTTP MCP initialize/notification/tools-list/call,
  JSON/SSE parsing, session reuse without logged session IDs. Five read tools
  allowlisted; chart/alert/publishing/trading/admin tools rejected. Unqualified
  screens/formulas require an explicit probe and registered expressions.
- One versioned `researcher/config/discovery_specs.json`: **F1–F9 and all 31
  blueprint method rows**, SMC/ICT grouping, roles, observable definitions,
  caveats and honest status. All detectors/packs/formulas disabled; Keepssy is
  DEFINITION_PENDING. No fake detector, compiler, ranking or scheduler added.
- `config validate`, recorded `provider status`, safe `scan smoke`; four optional
  small probe profiles. New report files only in ignored work/, no overwrite or
  traversal/symlink output. Keys are unnecessary and never loaded/sent.
- Concise AGENTS guidance, runbook, source/reuse inventory, bounded fixtures,
  evidence receipts/hashes and an offline CI workflow. Existing paper controls,
  frozen strategies, configs and trading databases were not changed or opened.

The normal smoke makes one targeted provider call after the MCP handshake and
returns no shortlist. No core or specialist evaluation is certified. No native
Deep Analyst service, original agent installation/injection or deployed Freqtrade
integration was verified or activated. Source ideas were reused; no conflicting
historical engine or skill funnel was copied into the feature branch.

## Actual provider qualification

Machine times below are UTC, 13 November 2026. Requests are credential-free.
Full requests/bytes/timing/hash receipts are in the [evidence index](../../evidence/external-first/session1/README.md).

| Operation | Actual scope and result | Capability status |
|---|---|---|
| Binance official exchangeInfo | `https://fapi.binance.com/fapi/v1/exchangeInfo`: **HTTP 451**, 224 bytes. Route stopped; no alternate hostname/location or signed route attempted. Current inventory, listing age, crypto classification, multiplier and tick/lot metadata unverified. | BLOCKED |
| Basis initialization / tools/list | Runtime MCP protocol `2025-03-26`, server `basis` 1.0.0, 43 tools observed; read schemas, variables, formula signatures and orderflow schema inspected. | LIVE_TESTED_NARROW |
| Basis market_candles + width | BTCUSDT, ETHUSDT, SOLUSDT, FILUSDT, 1000PEPEUSDT × 15M/1H: 10 requested symbol/timeframe operations, 10 returned; corresponding 10 remote width calculations executed. Every exact exchange eligibility/multiplier remains UNVERIFIED. | LIVE_TESTED_NARROW; TARGETED_ONLY |
| Finite explicit footer | BTCUSDT + ETHUSDT, 1H, 300-bar load, minimum vendor universe=20: 2 requested / 2 scalar-evaluated / 2 requested returned / 0 missing-failed, **18 fillers excluded**; provider total 20 evaluated. First/repeat executed. Not a tail cohort. | LIVE_TESTED_NARROW, broad capability UNVERIFIED |
| Sparse-column poison | Add `quantile(close[1],1000,0.2)` under `logic:any`: HTTP 200 + `isError=true`, all 20 vendor instruments unevaluable. Requested 2: zero valid / 2 faulted, no negative-setup conclusion. Separate finite recovery succeeds. | LIVE_TESTED_NARROW failure isolation |
| BTC sampled formulas | 65 requested bars, 64 reported closed, 20-point reduced tails; lag, prior extrema, width, median, q=.5 quantile, ATR recurrence, comparison, bar-delta identity and no-event behavior checked. No native pivot entries from current catalogue query; arbitrary historical as_of not exposed/proven. | PARTIAL semantics, not discovery-qualified |
| Genuine independent quiet tail | **0 partitions sent**: current eligible inventory/rank/age source blocked. No actual eligible 50-member cohort can honestly be selected here; no provider top board substituted. Young-contract coverage unknown. | BLOCKED_CURRENT_INVENTORY |
| True VP / footprint / derivatives | Schemas/docs only; no actual flow/history/units/source reconciliation. No optional adapter/key purchased or enabled. | UNVERIFIED |

Normal observation cutoff: 1H bar open **04:00**, source window end **05:00**;
last final smoke received **05:40:40.123268**. LoadedAt is a conservative known-by
time, not claimed earliest publication. Sample 15M/1H clocks are separately
retained. Source contract is provider-reported Binance futures; official
quote/settle/type/multiplier verification is not inferred from its symbol.

Price unit is reported USDT per native contract price unit. Base/quote/taker
volume units are **not independently reconciled**. Bar delta is not footprint;
OHLC value is not true profile; OI does not identify new longs; raw return is not
beta residual. Four-decimal screener rounding cannot support tick-exact levels.
Formula response informational links incorrectly said spot while data objects
said futures; links are ignored, discrepancy retained.

## Numerics, rights, quotas and performance

- **167/167 arithmetic comparisons pass**, over the same provider's bounded BTC
  tails. Width max absolute error `1.6152573441763e-16`; prior extrema, lag,
  3-value median/q=.5 comparisons exact at reported precision. ATR recurrence
  error ≤`6.357142857143e-13`; initial seed not independently tested. Delta
  identity residual ≤`1.8189894035458565e-12` in source base-volume scale.
- This is **independent arithmetic, not independent source data**. Exchange
  authenticity, young/quiet/multiplier oracle cohorts, full ATR seed/warm-up,
  quantile interpolation/ties/general baseline, chronological multi-event
  value_when/pivots and arbitrary historical replay remain unqualified.
- No-event functions returned `defined=0`, omitted tails; never coerced to 0.
  No fake F2/F4/F5 historical sequence or family accuracy claimed.
- Basis MCP page and terms accessed successfully; terms permit lawful research
  and prohibit bypass/abusive automation. Public documentation: 1,000 keyless
  calls/day, optional free key 10,000/day, unknown exact per-minute limit.
  Actual charged quota units absent. No key or paid entitlement used.
- Instrumented final runtime samples + footer + smoke: **33 HTTP requests,
  251,961 response bytes, sum of request durations 25,104 ms**, request p50
  696 ms / nearest-rank p95 1,671 ms. These include three handshakes, are a small
  measured subset of session traffic, and prove no SLA or sustainable cadence.
  Original finite first/repeat: 2,561/1,858 ms; actual server cache temperature
  unknown. No live 429 observed; backoff/denial tested offline.
- All source/fixture hashes are in `evidence/external-first/session1/SHA256SUMS.json`.
  Small public schema/market-fact extracts only; no bulk history, session headers,
  credentials, operational DBs or user data committed.

## Verification and stop/go

Executed from this Cloud checkout:

```bash
python -m unittest discover -s tests -v
python -m researcher config validate
python -m researcher provider status
python -m researcher.qualify samples --output work/runtime-samples-001
python -m researcher.qualify footer --output work/runtime-footer-001
python -m researcher scan smoke --output work/runtime-smoke-release.json
```

Offline suite: **43 passed / 0 failed / 0 skipped**. Includes actual-provider
shape/error fixtures, 167 arithmetic comparisons, wrong contract/venue, clocks,
future bars, missing/truncated/duplicate rows, tool-level errors, denied routes,
quota budget/Retry-After, read-only allowlist, secret/session redaction, output
boundary and complete registry preservation. No inherited implementation suite
exists on the approved documentation base; unmerged native engine tests were
not falsely claimed executed. Live probes are excluded from CI.

Repaired during the session: initial local tracking/refspec setup; initial probe
scratch-directory creation; output traversal caught by tests; a synthetic 15M
test's inconsistent receive/load clock. Final recorded test output is clean.
No unhandled failure is presented as a passed acceptance check.

Session 1's documented-failure path is satisfied: working pushed scaffold,
successful permitted remote observations, precise blocked gates and reproducible
qualification follow-up. G1/G2 production feasibility and all later detector,
nomination/context fairness, watch-resumption and deployment gates are **not**
passed. The fixed advisory/non-veto policy is preserved; real family nomination
invariance tests await actual detectors. No Session 2 implementation began.

Git publication: final pushed SHA and observed CI/check-run status are provided
in the session's exact GitHub handoff; a commit cannot contain its own hash.
CI was not claimed passed before its run was observed. Keep PR #24 draft; no merge.

## Next dependency-ready task — narrower qualification repair

1. Obtain a **lawful, current, provenance-bound official eligible inventory and
   ticker snapshot** with classification, age, status, settlement, tick/lot and
   exact multiplier metadata where supplied. Do not evade the Cloud 451 or use
   Local merely to change IP/location. No user credentials are currently needed.
2. Independently select and freeze actual quiet-tail/medium/young/multiplier
   strata; run an explicit 50-name screen and a smaller footer, audit recognized,
   returned, evaluated, filler, missing and faulted IDs. Production qualification
   requires the blueprint's second independent tail partition too.
3. Reconcile a tiny timestamp-aligned BTC/ETH/several-alt oracle from an
   independently permitted source, including volume units, closed 15M/1H,
   ATR seed/warm-up, no-event and sparse-column semantics. Keep methods disabled
   when proof is absent. Qualify quotas/cadence before any scheduling.
4. Only then decide whether Session 2's full-universe external adapter work is
   dependency-ready. If a specific Cloud-only operation is demonstrably blocked
   while a compliant Local operation exists, hand off **only that operation**
   from the exact verified remote SHA. No parallel implementation track.
