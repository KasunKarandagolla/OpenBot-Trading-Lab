# Profitability recovery

**NO-GO for deployment.** Read the [seven-question owner report](owner-report.md)
and the machine-readable [decision](run-001/decision.json).

There are 113 alternative native Freqtrade portfolios plus one exact replay,
and 7,882 independently reconciled trade records. Alternatives and correlated
markets do not create independent samples; portfolio returns are not additive.
Both new economic hypotheses lose. The small positive execution sensitivities
fail the combined constant-risk and adverse-cost check. Existing strategies and
operational configurations remain unchanged.

- [Primary results](run-001/primary-results.csv) and [all portfolios](run-001/portfolio-table.md)
- [Economics, paired uncertainty and 31 ranking nulls](run-001/economic-report.json)
- [Trade-path / conditional expectancy diagnosis](run-001/opportunity-diagnosis.json)
- [Opportunity rows](run-001/opportunity-paths.json) and [sizing attribution](run-001/ledger-diagnosis.json)
- [Genuine minute feasibility](run-001/minute-feasibility.json)
- [Sources and exact parent decision replay](run-001/source-reconciliation.json)
- [Original local seal](run-001/freeze.json), [availability amendment](run-001/hourly-freeze.json), [final provenance](run-001/source-provenance.json)
- [Backup and actual restore verification](run-001/private-backup.json)
- [Frozen parent integrity](run-001/frozen-integrity.json) and [exact native replay](run-001/replay-verification.json)

The development sample is Gate Aug 5–Nov 3, 2026, end exclusive. The separately
reserved older hourly test is May 20–Jul 26, with ten days of warmup. Gate's
15-minute retention and funding limits block the initially requested longer
15-minute history. The hourly result is a separate resolution experiment.
Historical universe completeness, second-level settlement marks, queue priority
and genuine historical order flow remain unknown. The future Nov 17–Dec 1
holdout was not acquired or inspected.

Native result/state/provenance/ledger records are under `run-001/native`.
The finite primary, null, execution and qualification matrices retain commands,
return codes and logs. Quarantined engineering attempts are separate and never
enter official statistics. Raw candles, immutable feature/plan inputs, native
ZIPs and simulated SQLite are private; restore them using the verified archive
before running the commands in the owner report. Closed SQLite files were
losslessly compacted to fit the workspace; the archive restores their original
paths and bytes.

No persistent paper worker, external order, merge or auto-merge was used.
