# Session 1 operation and qualification

Use Python 3.11 or newer. No dependency installation, Docker, trading keys or
optional API keys are needed. Run from the repository root:

```bash
python -m researcher config validate
python -m researcher provider status
python -m researcher scan smoke --output work/smoke-001.json
python -m unittest discover -s tests -v
```

Choose a new output filename each time; writes are exclusive, under ignored
`work/`, and reject parent traversal/symlinks. The smoke uses four HTTP requests:
initialize, initialized notification, tools/list, one three-bar BTC 1H request.
The observation validates exact requested spelling, provider-reported venue and
market, OHLC, bar-open + timeframe = source cutoff, and received/load times.
It preserves unknown exchange identity, earliest publication time and coverage.
It returns no nominees, no entry/SL/TP, and no trading authorization.

`provider status` is explicitly recorded capability/config status, not a live
connectivity claim. The smoke reports actual access and failures. Exit 0 means
the narrow observation completed, not that broad provider qualification passed.
Exit 2 means config/output rejection or a blocked/unqualified smoke. A failed
provider emits a machine-readable empty report instead of pretending no setup
exists. A recorded report is historical evidence once its cutoff ages.

## Reproduce small provider probes

These are explicit qualification operations, separate from normal use. Each uses
one runtime MCP session, a maximum 40-request budget, no retries and fixed public
endpoints. Raw objects stay in a new ignored directory. Do not schedule them.

```bash
python -m researcher.qualify schema --output work/schema-001
python -m researcher.qualify footer --output work/footer-001
python -m researcher.qualify formulas --output work/formulas-001
python -m researcher.qualify samples --output work/samples-001
```

The footer profile requests BTC/ETH with the minimum vendor universe size of 20,
isolates the oversized-quantile failure, and retries only the separate finite
pack. It records 18 vendor fillers separately from 2 requested names. It is not
a quiet-tail test. A deliberate tool-level failure is retained as `FAILED` in
the summary; a process completing this experiment does not certify the formulas.

The formulas profile requests only a 65-bar BTC 1H handle and the manifest's
registered expressions. It stores reduced tails, not a local market history.
The samples profile checks BTC, ETH, SOL, FIL and `1000PEPEUSDT` on 15M/1H with
17 requested bars and one remote normalized-width calculation each. These are
representative spellings, **not independently eligible, young or quiet samples**.
The runtime's non-probe path refuses unqualified formula/screens entirely.

No formula is enabled for discovery. `CORE_1H`, `CORE_15M` and all method packs
remain disabled. Tool availability, successful syntax and arithmetic consistency
do not prove causal family detectors or source correctness.

## Keys, rights and errors

Current enabled public operations require no credentials. `.env.example` only
documents an optional future `OPENBOT_BASIS_TOKEN` name. The runtime does not load
`.env`, read secret files or send environment keys. It exposes key presence only.
No setup prompt is needed. Future single-interface key management is
`python -m researcher setup-keys basis`, **not implemented** until the supported
free-key authentication header/flow is qualified; it should use hidden input and
an atomic, ignored `.env` update, never source edits. Other provider onboarding
remains deferred. Do not put credentials in a command line or Git.

Basis's current public MCP page documents no-account research/agent access,
1,000 keyless calls/day, optional free-key 10,000/day, and per-minute limiting
without an exact number. Terms last reviewed 2026-10-22 permit lawful research
analysis and prohibit bypass, abusive automation and source-rights violations.
No paid tools, publishing, charts, alerts or account mutations are called.
Small public tool-schema/error/market-fact extracts and the bounded 20-point BTC
arithmetic fixture are retained for reproducibility; no bulk history or service
redistribution is provided. Sources, hashes and access limitations are recorded
in the [evidence index](../../evidence/external-first/session1/README.md).

Actual charged quota units and sustainable cadence are unknown. HTTP 429 stops
the route and records Retry-After rather than sleeping/retrying; re-invocation
must respect that interval. 403/451 stops the route with no host/location change.
No alternate Binance hostname, VPN, signed endpoint, scraping or geographic
workaround is part of this work. Bounded 429/denial tests use offline fixtures.

## Next qualification gate

Binance exchangeInfo returned HTTP 451 from Cloud. It cannot establish a current
eligible inventory, tick/lot rules, listing ages, crypto classification or
independently sampled quiet tail. A fresh, lawfully acquired and provenance-bound
official inventory/ticker snapshot is the narrow missing input. A compliant
deployment/operator may supply one only where already permitted; Local is not
authorized as an IP/location workaround. No Local exception was used here.

Then predeclare independently sampled eligible tail/age/multiplier strata, test
one exact 50-member partition and a smaller footer for Session 1 qualification
(the blueprint's production gate needs two tail partitions), and reconcile
small BTC/ETH/alt reference samples against the same source windows. Keep the
seed, dates, source rights, raw hashes and every missing/faulted ID. If this cannot
be done lawfully, retain partial coverage and identify a qualified external
alternative for the exact missing function. Do not begin Session 2 or replace
this gate with mass local klines.
