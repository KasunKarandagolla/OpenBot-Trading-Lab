# Session 4 trading implementation and research

[Owner report](owner-report.md) · [Commands, recovery and Session 5 handoff](../../docs/operations/policy-session4.md) · [Registered protocol](../../research/session4/protocol.json)

`run-001/` contains the actual public acquisition, causal inputs, nineteen native
portfolio records (eighteen alternatives plus one exact economic reproduction),
independent Decimal ledgers, matched null, cost sensitivity, runtime observations
and isolated native order tests. Returns from alternative portfolios must never
be added together.

The challenger is **PaperPolicyV4 / structure-execution-v4.0.0**. The frozen
**PolicyFixedV3 v3.0.0** remains unchanged. Economic status is **UNQUALIFIED**.
No persistent paper service or external exchange order was activated.

Key artifacts:

- `registration.json`, `amendments/`: outcome-before/after boundaries and retained engineering repairs.
- `cohort.json`, `listing-coverage.json`, `data-manifest.json`: twenty current crypto swaps sampled; fourteen complete historical sources evaluated. Historical delisted membership remains unknown.
- `causality.json`, `feature-manifest.json`, `selection-summary.json`, `opportunities.json`: confirmed clocks, prefix checks, complete setup/rejection coverage and sealed replay inputs.
- `native-results/`, `native-provenance/`, `native-states/`, `trade-ledgers/`: official pinned Freqtrade, frozen plans, actual funding events and reconciled order economics.
- `economic-report.json`, `execution-diagnostics.json`, `source-reconciliation.json`: paired uncertainty, friction, R definitions and original-source limitations.
- `runtime/`: real bounded keyless workers, zero observed orders, source-outage entry inhibition and flat SQLite restart. **Fresh-price/order-to-outcome vertical acceptance remains blocked by Gate 503s.**
- `tests/native-order-trace.jsonl`: actual native dry-order creation/fill/cancel and SQLite recovery with controlled books. These are isolated tests, not observed forward fills.
- `prospective/`: bounded Gate book/tape attempts; all remained UNKNOWN during this outage. No historical order-flow uplift is asserted.

The first limit/market JSON producers incorrectly used a startup log line for
`public_data_observed`. That field is **not fresh-price evidence** in those two
initial records. The corrected restart record sets it to false and separately
records the observed source outage. All monitor events consistently show
`SOURCE_UNAVAILABLE` and no ranked slots. Logs and original records are retained.

Original parent evidence, strategy versions and data manifests are unchanged.
Raw sources, immutable feature/plan caches, native ZIPs and simulated SQLite state
are excluded from Git and supplied in the hash-verified owner backup.
