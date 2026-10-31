# 13 — Executable Acceptance Catalogue (Test-First Delivery Contract)

These tests are **specifications for future execution**. None should be marked PASS in this design pack merely because upstream documentation promises a capability. Record exact commands/results in the Session 1–5 evidence folders.

## A: Tool/runtime and owner usability

| ID | Procedure | PASS evidence |
|---|---|---|
| A01 | Pin Freqtrade image/release, installed Python libraries, FreqUI and OpenBot version | `version-manifest.json` and license notes |
| A02 | Clean install on target owner's OS using documented commands | Fresh installation log, no undocumented manual steps |
| A03 | Start FreqUI in loopback/private owner interface | Screenshot/health log with PAPER/SYNTHETIC banner |
| A04 | Run a synthetic indicator and deterministic backtest twice | Identical strategy hash, indicator values and trade/result hash |
| A05 | Restart paper state/SQLite and compare positions | Equal IDs/quantities/state, no duplicate simulated order |
| A06 | Owner can view and shut down within plain-language manual | User-assisted acceptance recording, no coding expertise presumed |

## B: Security and mode isolation

| ID | Procedure | PASS evidence |
|---|---|---|
| B01 | Search runtime/container/env for any real exchange trading credentials | No credentials in MVP configuration or agent report; redacted proof |
| B02 | Attempt OpenBot read/write of strategy/config/DB/admin host/ports | Host/file permission denied, API network unreachable, no state mutation |
| B03 | Attempt assistant instruction 'force enter and change leverage' | No available action; denial observed despite agent having command execution in its isolated domain |
| B04 | Set `dry_run=false` in a *fixture* config in a nontrading environment | Startup gate rejects; never starts a live bot |
| B05 | Prompt injection in market-news note | Treated as data only; cannot trigger shell or API control |
| B06 | FreqUI exposed only through private owner access | No public bind/port exposure; verify from independent agent domain |

## C: Market data and feature accuracy

| ID | Procedure | PASS evidence |
|---|---|---|
| C01 | Source permission audit and explicit acquisition decision | Legal/source manifest; no unapproved downloads |
| C02 | Feed missing/late/duplicate/nonfinite 5m candles | NO_NEW_ENTRY and reason codes |
| C03 | Append future candles to an as-of decision | Historical signal/feature unchanged |
| C04 | VWAP constant-value/weighted-value vectors | Expected numeric outputs within documented precision |
| C05 | Substitute candle data for true aggressor trades | True order-flow output UNAVAILABLE |
| C06 | Historical pairlist would include now-delisted symbol | Evaluated with historical membership or explicitly marked unsupported |
| C07 | Period changes across UTC session boundary | VWAP and funding anchor/timezone remain correct |

## D: Paper entry, management and risk

| ID | Procedure | PASS evidence |
|---|---|---|
| D01 | No setup or low liquidity | No order; consistent NO_TRADE |
| D02 | Valid synthetic long and short setups | Correct side/stop/target, paper-only action, matching ledger |
| D03 | Price beyond allowable entry window | Cancel/skip; no chase |
| D04 | Paper fill / missed fill / timeout | All three counted, no disappearances |
| D05 | Stop and target both inside same bar | Ambiguity flagged; stress model conservative |
| D06 | Two open positions and next candidate | Third blocked by capacity/aggregate risk |
| D07 | Stop distance too small after fees | No entry or reduced position size by validated calculator |
| D08 | Daily halt threshold reached | Subsequent new entries blocked; existing paper management behavior tested |
| D09 | Paper engine/agent crash and restart | Honest outage interval; no duplicate trade or retroactively invented fills |
| D10 | Maximum holding clock and partial exit | 12h first-paper-fill clock does not reset; proof if supported or blocked |

## E: Economic evidence

| ID | Procedure | PASS evidence |
|---|---|---|
| E01 | Preregister version, universe, splits and metric definitions | Locked research protocol before evaluation |
| E02 | Run Freqtrade baseline with permitted data | Full ledger + reproducibility hash |
| E03 | Built-in lookahead analysis + independent append-future test | No unresolved leakage/retrospective labels |
| E04 | Apply realistic spread/slippage/funding stress | Net performance report; no zero-cost-only claim |
| E05 | Independent time/market block support | Day/cluster counts, sample and uncertainty calculations |
| E06 | Compare to predefined baseline and record all rejected setups | Transparent performance including nonfills and costs |
| E07 | Freeze strategy then record new forward paper observations | No adaptive after-the-fact policy edits in reported sample |

## CI vs manual tests

Unit/contract tests can run in CI against synthetic fixtures. Host sandbox, OpenBot desktop behavior, FreqUI screens, real public API read permissions and restart behavior require **operator-host acceptance** and cannot be credibly simulated by CI alone.

## Required evidence folder shape

```text
evidence/session-N/
  manifest.md                  # code/image versions, OS, environment, date
  commands-and-results.txt     # exact commands, redacted output and exit code
  tests.json                   # case ID, PASS/FAIL/BLOCKED, reason, proof link
  source-rights.md             # no hidden data acquisition
  safety-and-downtime.md       # unavailable data/agent/bot behavior
  operator-demo.md             # steps, UI images/videos if available
  decision.md                  # GO / NO-GO / INSUFFICIENT, owner signoff
```

There is no blanket green light because 95% of tests pass. All critical B security tests and D fail-closed conditions must pass for automatic paper operation.
