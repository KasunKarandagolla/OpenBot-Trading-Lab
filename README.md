# OpenBot Trading Lab

**Status: DESIGN ONLY — awaiting owner review. No trading, installation, historical downloads or financial returns have been authorized.**

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
2. Initial scope: credential-free, offline/synthetic tool qualification. No downloads of historical datasets until data rights and cost are approved.
3. OpenBot must remain isolated from trading keys and execution-administration APIs. Research outputs are read-only.
4. Authorize at most one bounded Codex session at a time, with explicit pass/fail gates. Do not spend the remaining five by default.
5. Do not import AstraBot's unfinished branches or implementation architecture automatically.

**Next:** Review the [owner decisions](docs/design/14-DECISIONS-AND-OPEN-QUESTIONS.md) before granting the first implementation task.
