# 00 — Start Here: AstraBot Comeback in Plain Language

## What we are changing

The original AstraBot accumulated a large research/execution architecture but did not demonstrate a profitable after-cost strategy. The new product is **not** a rewrite of that system. It is a small lab assembled from mature tools, with a clear economic stop gate.

**Team analogy:**

- **OpenBot Director** = researcher/manager; coordinates work and tells the owner what the tools found.
- **Market Researcher agent** = analyst; requests market summaries and evaluates versioned strategy candidates.
- **Risk/Operations Reviewer agent** = inspector; reads paper-trade facts and warns about risk, outages and inconsistent evidence.
- **Freqtrade** = mechanical employee; runs repeatable calculations and an approved paper strategy while OpenBot is offline.
- **FreqUI** = the trading application's existing dashboard.
- **Owner** = chooses goals and authorizes changes; never required to hand-type Python to interpret routine outcomes.

## One complete example (invented numbers; NOT a real trade)

1. At 09:00 the pair filters examine 120 available markets using lightweight exchange summaries and keep eight liquid candidates.
2. At 09:05 the trend playbook evaluates closed candles for those eligible markets. BTC/USDT is considered, but has not yet met the strategy's exact signal.
3. At 09:10 a completed 5-minute candle meets the approved rule. The program checks data freshness, trading costs, risk limits and strategy version.
4. The engine would simulate a long at a fill model; if entry price is too far from the allowable limit or data is stale, it produces **NO_TRADE**.
5. After a simulated fill, Freqtrade follows the versioned stop/target/timeout behavior. OpenBot is not in the real-time exit loop.
6. At 09:15 the Director reads a *sanitized report*, explains the reason and points to the recorded paper trade. FreqUI shows the position.
7. The owner sees gross and net-after-assumed-cost performance. No claim is made about real fills.

## What runs continuously?

**While the computer/host is on:** the Freqtrade process polls supported market data and evaluates the configured strategy; the OpenBot schedule periodically reviews aggregated reports. **If the machine is off, neither runs.** A VPS is an optional future operating cost, not included by default.

## What is stored?

- Approved, bounded historical candles locally for research, in Freqtrade's supported file formats.
- A small persistent SQLite paper-trade database, strategy files and deterministic run reports.
- Short-lived market cache and *minimal* OpenBot summaries. Do not keep every agent chat or every market tick forever.

## What is the 'sniper entry'?

A **selective conditional entry**, not a millisecond arbitrage bot. The strategy waits for a specific closed-candle setup, then checks acceptable price, spread/cost and expiry before a simulated entry. If price runs away, cancel/skip. More accurate fills require better-quality data and validated order semantics; five-minute candles alone cannot guarantee precision.

## How much will this cost?

The recommended tools have free software/research paths, but compute, cloud hosting, AI model usage, market-data licenses and futures access can cost money. **Budget approval precedes any spend.** Jesse's native MCP is attractive but its paper/live functions may be paid; it is a fallback, not the chosen MVP engine.

## The uncomfortable facts

- No current strategy is independently proved profitable.
- The old project shows why strong software does not imply a trading edge.
- We cannot promise 'profitable in five sessions'. We can demand an auditable, runnable tool/strategy/economics demonstration and terminate uneconomic paths early.
- OpenBot should **not** receive private trading keys, admin API tokens or unrestricted access to a live trader. For the MVP, there are **no real trading keys at all**.

## Quick questions and answers

**Will it download the whole market?** No. Lightweight summaries cover a wider universe; deeper candles/history only for a small approved list. Historical downloads are disabled until rights and sources are approved.

**Who chooses a trade?** A frozen Freqtrade strategy produces the signal; a deterministic risk/cost gate admits or rejects it. OpenBot explains and can recommend further research, not invent live orders.

**What if OpenBot crashes?** The paper engine should continue according to its configured strategy; alerts may be delayed. If Freqtrade stops, paper simulation/management stops too—there is no magical background protection.

**Can it become profitable?** Possibly, but only a validated after-cost result and subsequent forward-paper evidence can support that claim. Popularity or complexity of indicators does not prove it.

**What do I approve now?** This design as a *provisional plan*, and at most a single safe tool-installation/qualification session—not real trading.
