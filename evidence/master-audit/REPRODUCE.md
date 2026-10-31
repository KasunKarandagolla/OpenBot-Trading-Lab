# Reproduction and evidence boundaries

Use Linux/WSL, Git, Python3, Docker + Compose, and host pandas/matplotlib for figures. Native research runs in official Freqtrade 2026.10 / CCXT 4.5.90, pinned image:

`freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7`

From the committed audit branch:

```bash
bash scripts/master-reproduce.sh owner-audit-001
```

This creates an independent checkout and output tree under ignored `work/master-reproductions/`. It removes generated outputs only in that new checkout, retaining experiment registrations and every old session artifact. Retained exact source files are copied if present; otherwise public native acquisition runs. Source mismatch, unavailable metadata or changed archive retention fails explicitly. No new quote/trade history is fabricated to obtain a match.

Order: predeclared source preflight → bounded book probe → source acquisition/identity → source preservation and test-source restoration → source-candle review → native funding fixture → ten native development policies → Decimal/source-funding comparisons → full tests → figures. Each collector refuses reused output IDs. The initial audit's failed attempts are retained; a new host need not reproduce a routing failure before the corrected probe succeeds. `master_run_ablations.py --resume` retries only incomplete policies, preserving failed logs/directories and refusing completed unregistered output.

Individual host commands are `python3 scripts/master_preflight.py NEW_ID`, `python3 scripts/master_preservation.py`, `python3 scripts/master_restore_test_sources.py` and `python3 scripts/master_charts.py`. Native commands are `scripts/master_native.py acquire`, `scripts/master_verify_sources.py`, `scripts/master_review.py`, `scripts/master_funding_probe.py`, `scripts/master_run_ablations.py`, `scripts/master_compare.py`, and `-m unittest discover -s tests -v`. Run each in the pinned image with repository mounted at `/lab`, working directory `/lab`, the host CA bundle mounted read-only, `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` set to that bundle, and the inherited supported proxy. Do not inject exchange credentials or disable TLS verification. Examples are implemented in the reproduction script.

The optional `scripts/master_current.py` is a bounded, read-only deep analysis of the five recorded shortlisted instruments using existing parent/context components. It emits NO_TRADE for execution because simultaneous quote/account risk approval is absent. It neither starts paper trading nor creates orders. It records computed observations; a full immutable raw current-candle replay is not qualified.

Generated source-candle arrays for plotting are ignored local `work/master-chart-data.json`; the repo retains 28 figures and the numerical casebook. Raw Gate feathers, downloaded ZIPs and native result archives remain local. Public evidence contains hashes, request outcomes, comparison JSON, logs, strategy code and reports. Hash identity proves the original research sources, not entitlement to redistribute them.

Original-source checks preserve all 519 base files and validate all 165 old artifact hashes. `preservation-source.json` lists file hashes. `source-identity.json` lists the 20 source matches. `independent-review.json` includes all 82 rejected signals and all 10 plans. `comparisons.json` includes all ten portfolios, 304 internally reconciled records and source-event bounds; never sum these separate portfolios. Bootstrap seed 4101 / 10,000 draws is descriptive only.

Mechanical config/report and source-review failures are retained alongside their corrected results. The original two native acquisition failures were routing/metadata issues; source availability is established by the corrected successful attempt. The original `book-001` timeout was collector routing; `book-002` is the corrected sequenced observation.

The 17 November–1 December UTC holdout is future and unobserved. No scheduler, extra session, paid resource, merge, paper deployment or live/testnet order is authorized by these commands. Full historical universe, executable queue fills, a repaired M1 lifecycle and operational account MTM remain outside the passed scope.
