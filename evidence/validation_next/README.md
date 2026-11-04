# Fresh market validation

Start with [the owner report](run-001/owner-report.md) and [operator runbook](../../docs/operations/validation-next.md).

**No economic promotion:** 27 corrected native Binance fixture portfolios,579 overlapping reconciled trade records. V4's seven-fill April holdout makes+0.279531USDT but becomes−0.066347 with extra10bp/side fixed-fill friction. Every result remains `PARTIAL_COST_MODEL / INSUFFICIENT_ECONOMIC_VALIDATION`; public CCXT test-fixture metadata is not historical exchangeInfo.

- [Predeclared protocol](../../research/validation_next/protocol.json), [ingestion registration](run-001/ingestion-registration.json), [evaluation freeze](run-001/evaluation-freeze.json), [single opening](run-001/holdout-opened.json).
- [Official archive manifest](run-001/data-manifest.json), [metadata fixture](../../research/validation_next/binance-fixture-markets.json), [contract audit](run-001/trade-contract-audit.json), [compact contracts](run-001/compact-trade-contracts.json).
- [Economics](run-001/portfolio-economics.json), [full comparison](run-001/comparison-table.md), [all opportunities](run-001/opportunity-lifecycle-ledger.json.gz), [cash ledger](run-001/trade-cash-ledger.json.gz), [matched mechanisms](run-001/matched-trade-differences.json.gz).
- [Corrected execution ambiguities](run-001/execution-ambiguities.json), [invalid-run index](run-001/invalid-run-index.json), [technical corrections](run-001/technical-corrections.json), [storage recovery](run-001/holdout-recovery.json), [exact recovery equivalence](run-001/holdout-recovery-equivalence.json).
- [Raw prefix checks](run-001/causal-prefix-checks.json), [11 focused passes](run-001/focused-tests-final.json), [broad regression:136/153 passes,15 errors,two skips](run-001/regression-and-validation.json), [final verification](run-001/final-verification.json).
- [Prior Gate source-seal verification](run-001/frozen-control-verification.json), [old case lineage](run-001/prior-case-lineage.json). All4,210 PR14 files remain byte-identical; no old evidence or safety hash changed.
- [Private input receipt](run-001/private-input-bundle.json), [620-file fresh restore](run-001/restore-check.json), [identical-tree hydration](run-001/hydrate-check.json).

Both funding-clock-invalid and negative runs remain. Initial development console filenames were reused during repair; those overwritten stdout streams are not claimed retained. The invalid native ZIPs/configs/result/orders/states and exact original runner source are preserved. The final corrected logs are in the owner-private input bundle.

Derived Binance Vision data reports carry attribution to **Binance Vision**, CC BY-NC-SA4.0, for personal noncommercial research. Public CCXT fixture copyright/license is supplied beside the fixture. No key, trade, recurring process, deployment or merge is authorized or activated.
