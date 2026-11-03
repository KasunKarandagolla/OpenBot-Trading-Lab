# Additional Session 3: integrated native policy, management and account risk

**Working implementation; economic qualification blocked.** Stacked on PR #7 at
`913eec38213052f979e67fd532febac809cbcabd`; nothing is merged or activated.

[Practical owner report](owner-report.md) · [Runbook and rollback](../../docs/operations/policy-session3.md) · [Session 4 contract](../../docs/operations/policy-session4-handoff.md) · [Selected reference](../../research/policy/release.json)

The final corrected run is **policy-session3-002**. Run001 and
`retained-before-precision/` are retained engineering evidence, not final controls.
The original preregistered managed reader and preliminary release reader are also
retained; consumers use only **openbot-release/**.

| Full chronological portfolio | Trades | Win rate | Native net USDT | +10 bp/side friction |
|---|---:|---:|---:|---:|
| TrendPullbackBaselineV1 | 453 | 30.02% | -12.41602122 | -33.32364095 |
| IntelligenceRegimeV2 | 8 | 50.00% | +0.58494245 | +0.20730497 |
| PolicyFixedV3 | 68 | 29.41% | +0.19192444 | -2.94951754 |
| PolicyManagedV3 | 68 | 29.41% | -0.35922343 | -3.50051591 |
| PolicyRetraceV3 | 68 | 19.12% | -1.40713072 | -4.56111766 |
| PolicyObjectiveV3 | 68 | 29.41% | +0.12197694 | -3.01939504 |

Native net includes conservative fees and actual source funding; the friction
column additionally charges10 bp/side on actual turnover. Portfolios are alternatives.
The fixed reference is an integration candidate, not a profitable strategy approval.

| Evidence | What it establishes |
|---|---|
| [Protocol](../../research/policy/protocol.json), [registration](policy-session3-002/registration.json), [amendments](policy-session3-002/source-amendments/) | One coherent hypothesis, three targeted ablations, explicit engineering repairs and post-development selection |
| [Opportunity ledger](policy-session3-002/opportunity-ledger.json), [continuation diagnosis](policy-session3-002/continuation-diagnosis.json) |995 new raw setups;78 fixed admissions versus 9 old router admissions; same38 bp net-cost gate; no zero-signal continuation claim |
| [Economic report](policy-session3-002/economic-report.json), [native results](policy-session3-002/native-results/), [trade ledgers](policy-session3-002/trade-ledgers/) |26 final portfolios,1,166 modeled records, long/short and recipe distributions, exits, costs, excursions and zero-trade periods |
| [Reconciliation](policy-session3-002/reconciliation-acceptance.json), [source funding](policy-session3-002/source-funding-audit.json), [chronology](policy-session3-002/funding-chronology.json) |Independent Decimal order accounting and real source-event bounds; no event before actual fill |
| [Native leverage invariance](policy-session3-002/leverage-native-invariance.json), [90 contract scenarios](policy-session3-002/leverage-scenarios.json) |Identical native68-trade orders/net at 1x/10x/20x after precision repair; constant notional/risk with different margin |
| [Paired comparison](policy-session3-002/paired-policy-comparison.json), [complete casebook](policy-session3-002/casebook.json) |Harmful management/retracement/target changes and the old October winner/loser exclusions remain visible |
| [Calendar/exposure uncertainty](policy-session3-002/calendar-exposure-and-uncertainty.json) |Zero days, seven-day blocks, partial-quantity exposure integral and filled holding time; no independent-edge claim |
| [176 tests](tests-final.txt), [native lifecycle fixtures](policy-session3-002/lifecycle-tests.txt), [stopped startup](policy-session3-002/native-dryrun-smoke.json) |174 pass, two unavailable old private-source checks skipped; restart/partial/pending/funding fixtures; zero observed paper orders |
| [Native diagnostics](policy-session3-002/diagnostics/) |Eight qualifying lookahead signals with no detected bias; rounded recursive results and limited cells remain qualified |
| [Preservation](policy-session3-002/preservation.json), [source identity differences](policy-session3-002/parent-source-comparison.json), [strategy freezes](policy-session3-002/strategy-freezes/) |All882 parent evidence files and original strategy freezes remain intact; private backups absent, only 5/20 reacquired slices byte-identical |
| [Final read-only reader](policy-session3-002/openbot-release/), [handoff](../../docs/operations/policy-session4-handoff.md) |Bounded schema-v1 ordinary JSON, coherent selected reference, contradictions, current-only genuine flow/news, native outcomes and stable IDs |

No real/testnet/demo exchange order, exchange credential, persistent paper service,
new backtester/dashboard, agent-order bridge or automatic merge was used. Future
November 17–December 1 holdout is untouched. Three additional sessions completed;
two remain.
