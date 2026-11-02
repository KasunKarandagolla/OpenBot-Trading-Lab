# Additional Session 2: intelligent opportunity discovery and analysis

**Working research implementation delivered; economic promotion remains blocked.**
The existing native Freqtrade scanner now feeds signed continuation selection,
failure-based reversal routing, five-market deep assessments, qualified real
executed-trade observations, profile/structure plans and comparative native
economics. No existing PR was merged, exchange credential used, order placed or
persistent paper service activated.

Stacked on PR #6, `codex/additional-1-unified-research`, verified at exact parent
`b912c821d2d0f2ede0bd491e3f13d13d5f65f607`. This branch is
`codex/additional-2-opportunity-intelligence`. [Setup/rollback](../../docs/operations/intelligence-session2.md)
and [precise Session 3 handoff](../../docs/operations/intelligence-session3-handoff.md).

## Executed functionality

| Requirement | Actual evidence |
|---|---|
| Existing broad native scanner | **586 eligible → 38 native candidates → 17 final shortlist → five deep markets**. Current membership, metadata rejects and liquidity rejects remain explicit. [Final scan](intelligence-003/scan.json), [signed shortlist](intelligence-003/deep-shortlist.json). |
| Signed opportunity selection | Continuation ranks use side-signed BTC-relative return in the corresponding hourly EMA direction. Reversal ranks require an actual closed failed-boundary parent signal and use reclaim distance/ATR. Strong opposing momentum alone creates no reversal rank. [Protocol](../../research/intelligence/protocol.json), [schedule](intelligence-003/signed-schedule.json). |
| Strategy matching and plans | Both frozen recipes, native ADX20/30 overlap, opposing-continuation danger, confirmed boundary/structure alternative, frozen stop, price deviation, limit trigger, expiry and after-cost objectives. **34 common parent opportunities per V2 arm** (ten VWAP, 24 sweep), **306 arm records**. [Complete candidate ledger](intelligence-003/intelligent-opportunities.json). |
| Current deep analysis | Five markets, both recipes/sides, **20 WATCH** records and overall NO_TRADE; lot geometry, source/receipt quote clocks, structure, proxy profile, opposing evidence and uncertainty. [Assessments](intelligence-003/opportunities.json). Absence of a setup is not an opportunity to invent one. |
| Genuine Order Flow | Final observation: **3,000 executed REST trades**, **129 WS prints**, **12 ten-second observed-window attempts** across three shortlisted contracts; no disconnect, duplicate, invalid or out-of-order event recorded. REST remains PARTIAL. Signed contracts convert to verified base units; native Freqtrade footprints, delta, resetting-window CVD, divergence and predefined-boundary pressure are retained. [Final flow](intelligence-003/orderflow.json). |
| Real flow application | Separate earlier corrected capture has **180 WS prints** and actual observed rejection of a pre-observation ZEC boundary, with executed volume beyond it. This is a bounded current shadow observation, not proof of passive absorption or an entry. [Corrected observation](intelligence-001/orderflow.json). Historical genuine flow remains UNKNOWN; no synthetic flow P&L was substituted. |
| Proper profile fidelity | Contiguous price grid retains empty bins; POC, value area and occupied high/low-volume nodes are base-volume distributions. Historical prior-day typical-price profiles are **OHLCV_PROXY**. Current executed-trade distributions are **OBSERVED_TRADES** with their own limited window/coverage. Old profile/flow modules are byte-identical to the parent. |
| Comparable actual sources | Five Gate contracts, September 21–November 1 source interval, October 1–November 1 evaluation, 240-hour warm-up. **All 20 sources match original Session 1 hashes**. [Identity](intelligence-001/parent-source-identity.json). Final run reuses preserved sources without historical redownload. [Reuse](intelligence-003/source-reuse.json). |
| Native portfolios and independent accounting | Fourteen native portfolios, **219 modeled trade records per run**; actual fill/fee/funding ledgers, drawdown, Sharpe/Sortino, per-pair/side and turnover stress. [Economics](intelligence-003/economic-report.json), [paired comparisons](intelligence-003/comparison.json), [all trade ledgers](intelligence-003/trade-ledgers/), [source funding audit](intelligence-003/source-funding-audit.json). |
| Missed valid opportunities | Exact control-fill/candidate joins retain excluded winners and losers. [Full casebook](intelligence-003/intelligence-casebook.json). This measures coverage costs rather than celebrating fewer trades. |
| Native lookahead | Regime and target arms each report **three signals, no detected bias**. Default native lookahead forces market orders; the retracement-entry arm yields **zero signals / insufficient evidence**, despite process exit0. Never call that a passing bias test. [Qualified interpretation](intelligence-003/diagnostic-qualification.json), native text/CSVs beside it. |
| OpenBot and news | **116** bounded schema-v1 compatible read-only records; verified structure, plans, contradictory evidence, flow clocks/CVD/boundary observations and genuine trade-profile levels. Current flow is explicitly later observation, never retroactive setup confirmation. [Reader](intelligence-003/openbot/research-snapshot.json), [manifest](intelligence-003/openbot/manifest.json), [official/publisher briefing](intelligence-003/event-briefing.json). |
| Preservation and tests | **137 tests pass**; all **619 prior artifact hashes** and all original strategy freezes verify. [Full tests](tests-full.txt), [preservation](preservation.json), [acceptance/replay](acceptance.json). |

## Native October outcomes

Every portfolio uses the same five-market chronological data, 1x, initial notional
at most 25 USDT, max two positions, 1,000 USDT wallet and **0.075%/side fees**.
Source funding is actual; historical account fee tier and queue/depth are UNKNOWN.
Portfolios are alternatives and their returns must not be summed.

| Portfolio | Native fills | Native net USDT |
|---|---:|---:|
| Frozen TrendPullbackBaselineV1 |162|−6.38710333|
| Frozen VWAPTrendContinuationV1 |9|−0.44946448|
| Frozen LiquiditySweepReversalV1 |24|−0.72529188|
| Session 1 RouterOnlyV1 |1|−0.11694800|
| Audited Session 1 FoundationRouterM0V1 |1|+0.50352528|
| V2 absolute-selection cost control |1|+0.50352528|
| V2 signed selection |3|−0.23436884|
| V2 signed + regime matching |3|−0.23436884|
| V2 all-market regime control |3|−0.23436884|
| V2 confirmed structure/boundary |1|+0.50352528|
| V2 profile objective with 2R fallback |3|−0.23436884|
| V2 structure/profile objective with 2R fallback |3|−0.23436884|
| V2 automatic nearest-obstacle veto |2|−0.73789412|
| V2 0.1ATR retracement entry |3|−0.12883894|

All V2 admissions and callbacks use **0.0038** = 0.0015 round-trip fees  + 0.002
friction  + 0.0003 adverse funding allowance. Frozen parents retain 0.0035. These are
admission buffers, not extra deductions from native net; additional 1.5/5/10/20 bp
turnover scenarios are separate. The cost-control arm isolates the allowance
change before signed selection. Baseline strategies have their original entry
rules; causal attribution is limited to paired V2 arms on the common 34 parent
opportunities, not the entire baseline-to-router P&L difference.

**What helped:** the structure variant excluded two October 29 ETH/XRP long-sweep
control losses (−0.35070697 and −0.38718715). The entry/geometry variant improved net
by 0.10552990 while retaining three modeled fills. Both observations remain small,
inspected development results; the entry arm is still negative.

**What harmed:** signed selection added those two losing opportunities, worsening
net by 0.73789412 versus the cost-matched control. Automatic nearest-obstacle veto
discarded the sole October 2 XRP short winner (+0.50352528) and kept both losers.

**No observed uplift:** regime matching, removing signed selection, profile targets
and structure/profile fallback targets all retain the same three fills. No new
VWAP plan survives the tested routing/cost geometry, so continuation uplift is
insufficiently evidenced. One positive structured trade does not establish an edge.

All fourteen native trade lists are compared field-for-field between the two
completed runs in [acceptance.json](acceptance.json), including fees, funding,
orders and entry/exit keys. Independent Decimal order accounting and source-event
funding bounds are checked by the unchanged economic reporter.

## Exact commands, retained failures and limits

The ordinary complete command is:

```bash
./scripts/lab-foundation.sh run intelligence-owner-002
```

Actual runs used the pinned official image, the wrapper and its individual actions.
Run001 introduced and retained mechanical corrections. Run003 independently
replayed the final strategy implementation. Its initial command was interrupted
by the source-hash guard when reader-only enrichment landed during execution;
the missing portfolios and remaining actions were explicitly resumed:

```bash
LAB_FOUNDATION_CONTAINER=openbot-intelligence-session2 bash -c 'set -e; for step in backtest events report compare export intelligence-lookahead; do ./scripts/lab-foundation.sh "$step" intelligence-003; done'
docker exec -e FOUNDATION_RUN_ID=intelligence-003 openbot-intelligence-session2 python -m unittest discover -s tests -v
python3 scripts/intelligence_acceptance.py intelligence-003 intelligence-001
```

[Initial003 command](intelligence-003/initial-command.txt), [actual resume output](intelligence-003/resume-command.txt),
[001 initial](intelligence-001/initial-command.txt), [001 resumed outputs](intelligence-001/resume-command.txt),
[source amendments](intelligence-001/source-amendments/), [003 reporting-only amendments](intelligence-003/source-amendments/).

Retained faults: initial tests before Compose/private-source prerequisites;
staging refusal after a declared source amendment; Gate REST seconds mislabeled
`create_time_ms` and CCXT contract amounts; additions initially placed in frozen
bonus files (moved to V2 modules and original bytes restored); source guards when
live code changed (including run 002); and strict JSON refusal of pandas NaN from
blank native diagnostic cells. Original code commits, raw observations, failed
logs and hash-chained corrections remain. No numerical strategy hypothesis,
cohort, evaluation dates or thresholds were retuned after outcomes.

Raw sources/native ZIPs remain outside Git. A private backup includes source
vaults, restored old samples, bounded current observations and native result ZIPs.
[Actual restore smoke](intelligence-003/source-restore-smoke.txt) verifies all 20
restored files without touching originals. The ordinary reader bundle contains
only sanitized JSON/schema and never a DB, auth/config or mutable lab mount.

Remaining limits: inspected survivor history; no independent holdout; historical
flow/news/queue/depth/original receipt clocks UNKNOWN; 15m range fills cannot
resolve intra-candle five-minute expiry; entry lookahead has no qualifying signals;
full account midnight MTM/pending exposure and persistent partial-fill/restart
qualification remain Session 3 work. The inherited November 17–December 1 reserved
holdout is untouched and unobserved. No persistent collection schedule exists.
