# 15 — Sources, Verification Levels and Design Provenance

**Source review date:** 2026-10-31. URLs point to upstream projects/documentation, not to installed versions. Exact tags/commits, capabilities and licenses must be frozen and tested during Session 1. Official documentation can change after this date.

## Checked primary public sources

| Source | Relevant verified documentation claim | Link |
|---|---|---|
| Freqtrade home | Backtesting, dry-run, market selection, SQL trade history, web UI | https://www.freqtrade.io/en/stable/ |
| Freqtrade plugins | Pairlist handlers: VolumePairList, SpreadFilter, VolatilityFilter, AgeFilter, etc. | https://www.freqtrade.io/en/stable/plugins/ |
| Freqtrade backtesting | No-slippage requested-price fill assumptions; intra-candle ordering; optional detail timeframe | https://www.freqtrade.io/en/stable/backtesting/ |
| Freqtrade callbacks | `confirm_trade_entry`, `custom_entry_price`, `custom_stoploss`, `custom_exit`, timeout, adjustment caveats | https://docs.freqtrade.io/en/latest/strategy-callbacks/ |
| Freqtrade download | Historical-download CLI, futures/mark/funding/OI types, default Feather | https://www.freqtrade.io/en/stable/data-download/ |
| Freqtrade REST API | Auth, localhost by default, read/write endpoints including `forceenter` | https://www.freqtrade.io/en/stable/rest-api/ |
| Freqtrade lookahead | Built-in leakage probe and its assumptions/limitations | https://www.freqtrade.io/en/stable/lookahead-analysis/ |
| Freqtrade config/install | Dry-run supports empty keys; install/dry run configuration | https://www.freqtrade.io/en/stable/configuration/ and https://www.freqtrade.io/en/stable/installation/ |
| OpenBot README | Agent coordination, development-preview **danger-full-access**, current license | https://github.com/nightly-labs/openbot |
| OpenBot privacy | Agent shell/files/network/browser access; not a host permission boundary | https://github.com/nightly-labs/openbot/blob/main/PRIVACY.md |
| Binance Vision dataset terms (v1.0, 2026-08-26) | By default CC BY-NC-SA noncommercial; written commercial use agreement separately | https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md |
| Freqtrade GitHub | Repository and GPL-3.0 designation from GitHub metadata | https://github.com/freqtrade/freqtrade |
| Jesse GitHub | MIT codebase metadata; alternative if research/paper licence fit changes | https://github.com/jesse-ai/jesse |
| SMC candidate | Open-source SMC library; direct function/timing tests still required | https://github.com/joshyattridge/smart-money-concepts |
| Volume-profile candidate | Candidate implementation for approximate profiles, methodology must be checked | https://github.com/bfolkens/py-market-profile |
| Hummingbot MCP candidate | Repository was archived at review | https://github.com/hummingbot/mcp |

## User-supplied research basis

The owner supplied a detailed 32-candidate research summary with ranking **OpenBot + Freqtrade/FreqUI first**, Jesse alternative, Hummingbot and NautilusTrader, plus findings concerning OpenBot permissions/licence, Freqtrade backtest limitations, historical archive rights, SMC repainting and inaccurate close-assigned profile inputs. A second pasted report recommended Jesse but asserted paper mode was free; this design does **not** adopt that unsupported claim. The detailed library research was pasted by the owner in the conversation; the external report's library-link content itself has **not** been reproduced inside this pack as an independently accessible source. Avoid treating its internal probes as tests run by this assistant.

## Existing project files used as historical input

- `01-PROJECT-CHARTER.md`: reuse-first, data/approval/risk principles and original scope; the new pivot supersedes its large architectural ambitions for MVP.
- `02-SYSTEM-ARCHITECTURE.md`: as-of clock, typed source evidence, independent order protection, brief agent summaries; used only as lessons/constraints, not as a mandate to reproduce its modules.
- `08-CHATGPT-PROJECT-INSTRUCTIONS.md`: owner-focused implementation discipline and budget/session governance.
- `OWNER_OPENBOT_ACCEPTANCE_REPORT(3).md`: earlier AstraBot synthetic C06 fake-owner/agent acceptance on owner host; **not** a live trading demonstration or an OpenBot→Freqtrade compatibility test.
- `FULL_PANEL_DESIGN_FREEZE.md`, `EVENT_YIELD_CENSUS_PROTOCOL.md`: original Phase 6 M4 research freezes; informative history, **not** automatically the new trend/VWAP strategy specification.

## Accuracy policy

- **Official-doc verified:** documented upstream behavior, not a successful owner-host installation.
- **Owner-reported:** data from pasted reports, not independently rerun here.
- **Proposed engineering:** tool binding, retention, schemas, agent messages, risk settings and session plan awaiting tests.
- **Not verified:** any profitable market strategy, session-1 working environment, license authorization for commercial trading, exact live fill quality, owner-host isolation or hosted third-party order-flow accuracy.

## External access record

This documentation task accessed public documentation to check current semantics; it did **not** download market data, run backtests, install trading applications, connect to an exchange or consume a Codex/OpenBot session.
