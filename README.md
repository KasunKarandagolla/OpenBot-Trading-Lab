Session 5.5: narrow source-qualified causal nominations, public depth/OI and repair work; **PARTIAL**, integration gates still open. See [acceptance matrix](docs/implementation/SESSION_05_5_RUNBOOK.md).

# OpenBot Trading Lab

**Status: Session 2 partial external discovery implementation, on demand and read-only. Full CORE and provider qualification remain incomplete; no trading authority.**

The current workstream follows the [finalized implementation references](docs/implementation/README.md).
Read [PROGRESS.md](docs/implementation/PROGRESS.md) for verified capabilities, blocked
qualification gates, branch history and the next task. The older Freqtrade design
below remains a separate paper-lab reference; its unmerged implementations are
inventoried in [REPO_TRUTH.md](docs/implementation/REPO_TRUTH.md).

Python 3.11+; standard library only. From the repository root:

```bash
python -m researcher config validate
python -m researcher provider status
python -m researcher scan smoke --output work/smoke-001.json
python -m researcher scan now --output work/discovery-001.json
python -m unittest discover -s tests -v
```

The smoke command performs one public targeted Basis observation after the MCP
handshake. It emits an empty research shortlist and explicit unknown exchange
coverage. `provider status` reports recorded capabilities; `scan smoke` checks
actual current access. See the [Session 1 runbook](docs/implementation/SESSION_01_RUNBOOK.md).

`scan now` executes explicit 1H/15M partitions of the finite provider-reported
width observation on the five previously exercised symbols, with exact filler,
missing/failure and budget accounting. It reports `PARTIAL_INVENTORY`, unknown
eligible universe and zero qualified CORE/strategy coverage. See the
[Session 2 runbook](docs/implementation/SESSION_02_RUNBOOK.md) for capability
limits and the provenance-bound official inventory snapshot interface.

A small, reuse-first **OpenBot-directed crypto trading research and paper-trading laboratory**, proposed to use Freqtrade/FreqUI for deterministic strategy testing and simulated position management. **No strategy has been proven profitable.**

## Design pack v1.0

The complete original Markdown design is preserved in **[docs/design/README.md](docs/design/README.md)**. Start with:

- [Start here — beginner guide](docs/design/00-START-HERE.md)
- [Product contract](docs/design/01-PRODUCT-CONTRACT.md)
- [System architecture](docs/design/02-SYSTEM-ARCHITECTURE.md)
- [Data and storage](docs/design/03-MARKET-DATA-AND-STORAGE.md)
- [Strategies and decisions](docs/design/06-STRATEGIES-AND-DECISIONS.md)
- [OpenBot agents and tools](docs/design/08-OPENBOT-AGENTS-AND-TOOLS.md)
- [Economic validation](docs/design/10-ECONOMIC-VALIDATION.md)
- [Security, licensing and risk](docs/design/11-SECURITY-LICENSING-AND-RISK.md)
- [Five-session delivery plan](docs/design/12-FIVE-SESSION-DELIVERY.md)
- [Acceptance tests](docs/design/13-ACCEPTANCE-TESTS.md)
- [Open decisions](docs/design/14-DECISIONS-AND-OPEN-QUESTIONS.md)
- [Document integrity manifest](docs/design/MANIFEST.json)

## Project controls

1. **Design ≠ deployed software; backtest ≠ proven profitability.** No production or paper engine is installed by these documents.
2. Session 2 permits credential-free, bounded on-demand observations and tiny oracle samples under the finalized references. Routine all-market historical downloads remain outside this workstream.
3. OpenBot must remain isolated from trading keys and execution-administration APIs. Research outputs are read-only.
4. Authorize at most one bounded Codex session at a time, with explicit pass/fail gates. Do not spend the remaining five by default.
5. Do not import AstraBot's unfinished branches or implementation architecture automatically.

**Next:** Follow the current partial-coverage handoff in [PROGRESS.md](docs/implementation/PROGRESS.md). Session 3 has not begun.


## External-first Market Researcher (PARTIAL, read-only)

Python 3.11+, standard library; run `python3 -m researcher scan now`. It refreshes
public sources automatically and persists research metadata under ignored `work/`.
No keys, inventory JSON, orders or scheduler are required. Qualified sampled price
precursors are not complete CORE or all-method structural discovery. Read the
[current operator runbook](docs/implementation/SESSION_05_RUNBOOK.md) and
[verified implementation status](docs/implementation/PROGRESS.md) before use.
