# 05 — Analytical Weapons: Adopt, Qualify, Explain

## Decision philosophy

Do **not** build a custom indicator stack. Start with built-in Freqtrade/TA-Lib functions, then add a library only if (a) a selected hypothesis needs it, (b) its calculations agree with independent test vectors, (c) its decision-time availability is proven, and (d) the result improves research quality after realistic costs.

## Candidate register (NOT installed or qualification-passed yet)

| Weapon | Suggested software | Inputs/outputs | Trust/failure boundary | Phase |
|---|---|---|---|---|
| Standard trend/momentum | Freqtrade + TA-Lib | OHLCV → EMA, ATR, ADX/RSI, etc. | Closed candles; correct warm-up and shifted timeframes | Baseline |
| VWAP | Pinned Freqtrade-compatible library or audited small standard formula | price/volume per closed candle → weighted average | VWAP anchor/session/timezone and typical-price choice must be frozen; candle-based approx, not tick VWAP | Candidate 1 |
| SMC / ICT | `smartmoneyconcepts` | validated OHLC DataFrame → FVG, swing, BOS/CHOCH, OB | Swing confirmation can require later bars; preserve *known_at*; no use of retrospectively repainted label | Optional research |
| Volume profile | `py-market-profile` or another verified alternative | historical OHLCV → approximate price distribution, POC/VA | Library methodology may assign candle volume to one price; **not** a true trade-by-price profile | Optional context |
| True order flow / delta | Freqtrade experimental orderflow or approved third-party feed | real trade prints with buyer-maker fields → buy/sell volume and delta | Cannot infer from candle colors; tick/volume provenance, latency, storage and licences | Not initial MVP |
| Funding/open interest | Freqtrade supported futures series, exchange APIs subject to rights | funding, mark, OI with event/measurement clocks | Different units, frequencies, historical revisions and timestamp ambiguity | Context if verified |
| Quant analysis | Pandas/NumPy, optional QuantStats | tagged trade ledger → equity, drawdown, turnover, costs | Independent trades, calendar clustering and fee model must be specified | Evaluation |

**Reference links and status:** see [15-SOURCES-AND-PROVENANCE.md](15-SOURCES-AND-PROVENANCE.md). Project research identified candidates; a qualified dependency list comes from Session 1 actual installation and tests, not this table.

## How OpenBot uses a weapon

1. Researcher requests a *specific feature report* (e.g. latest session VWAP for three approved markets).
2. A trusted deterministic process computes the feature from an explicit source, timeframe, anchor and as-of clock.
3. The result includes numeric value, units, quality, timeframe, available_at, source/version and missing fields.
4. OpenBot **reads the result and explains it**. It does not recompute the feature from a screenshot or invent a price.
5. A frozen Freqtrade strategy independently decides if the feature meets its signal conditions.

## Causal safety for each family

- **EMA/ATR/RSI:** proper warm-up; bar must be closed and current as of decision; no full-sample normalization.
- **VWAP:** never use future session volume; specify start-of-session; reset exactly at anchor; compare only with known data.
- **SMC swing:** if a pivot needs three candles to the right, label the pivot as *tradable/known only after the third right candle*, not at the pivot timestamp. Test append-future-candles invariance.
- **FVG/order block:** detection versus invalidation are different event times; do not treat a zone updated next week as known yesterday.
- **Profile:** OHLCV approximation cannot prove real order placement or bid/ask liquidity at the POC; check rounding, bin sizes, time windows and source fidelity.
- **Order flow:** trade IDs, aggressor mapping, duplicates/gaps, sample watermark and source receipts; a 30-second trade aggregation is not reconstructable from five-minute bars.
- **OI/funding:** distinguish exchange published time, local observed time, settlement time and measurement time; don't use hindsight.

## Acceptance vectors (small exact examples)

| Test | Expected behavior |
|---|---|
| VWAP constant price 100, volumes positive | VWAP exactly 100 |
| VWAP unequal volumes at prices 100 and 110 | Weighted result, e.g. volumes 1 and 3 produce 107.5 under *chosen price input* |
| Append tomorrow's candles | Historical decision outputs unchanged |
| Swap data source from trade prints to candles | Fidelity label changes; true delta unavailable |
| ATR input contains NaN/zero period | Explicit UNAVAILABLE; never fabricated zero-risk stop |
| SMC high marked with lookahead | Signal eligible only after confirmation timestamp |
| Vary profile bin width | Output sensitivity measured and reported |

## Licensing and maintenance

Pin Python package and commit/release, inspect license, tests, update recency, issue backlog and usage constraints. TA-Lib installation may be easier through the pinned Freqtrade image. Third-party packages do **not** inherit Freqtrade's quality guarantees. If installation costs more than the feature is worth, omit the feature instead of expanding infrastructure.

## Strategy versus weapon

VWAP, FVG, order block and volume delta are **analytical tools**, not a profitable trading system. Every *active* strategy needs an explicit trigger, invalidation, stop, target/exit, size/cost policy and testable performance; the agent cannot promote a collection of indicators into a trade by narrative confidence.