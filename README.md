# OpenBot Trading Lab

A real-market crypto futures research and paper-trading foundation using official **Freqtrade 2026.10** and FreqUI. The current milestone is **Additional Session 1 of 5**. Engineering works; **economic qualification remains blocked**. No strategy is approved by this research for persistent paper operation.

[Executed milestone and limitations](evidence/additional-1/README.md) · [Beginner runbook](docs/operations/foundation.md) · [Session 2 handoff](docs/operations/foundation-session2-handoff.md) · [Original design](docs/design/README.md) · [Prior sessions](docs/operations/prior-sessions-readme.md)

## Run one complete research cycle

Install Git, Python 3 and Docker with Compose v2. On Windows use Docker Desktop with WSL2. Owner OS/browser verification remains outstanding.

```bash
git clone https://github.com/KasunKarandagolla/OpenBot-Trading-Lab.git
cd OpenBot-Trading-Lab
git checkout codex/additional-1-unified-research
docker compose -f deploy/freqtrade/compose.yaml pull
./scripts/lab-foundation.sh run owner-research-001
```

Use a new run ID. This command performs environment validation, Binance/Gate public-access checks, native VolumePairList/SpreadFilter screening, bounded current assessments, preserved-source acquisition/reuse, causal opportunity planning, six native research portfolios, a source-aware event briefing, independent cost/funding reports, sanitized OpenBot export, lookahead diagnostics, authenticated FreqUI smoke and a disposable stopped-state dry-run startup. Its temporary container is removed on exit. It creates no real/testnet orders and starts no persistent paper service.

**Data:** Gate linear USDT perpetuals, BTC/ETH/SOL/XRP/DOGE. Source interval September 21 through November 1, 2026 UTC, end exclusive; evaluation October 1 through November 1 UTC with 240 hourly warm-up bars. These are predeclared current survivors and inspected development, not historical exchange membership or an unseen holdout. The source sample is about 0.92 MB in 20 files. An identical preserved cohort is copied and verified before considering a new download. Existing datasets and completed runs are never overwritten.

**Venue:** Binance USDT-M is preferred for eventual operations, but its public endpoint returned HTTP 451 here. Gate is the working research fallback. Prices, funding, metadata and performance never cross venues. This workflow uses native `dry_run=true`, not demo/testnet accounts.

## Read the result

Open `evidence/additional-1/<RUN_ID>/economic-report.json`, `casebook.json` and `openbot/research-snapshot.json`. Actual full native results and trade CSVs are beside them. Current WATCH/REJECT/NO_TRADE records are separate from historical RESEARCH_CANDIDATE plans. News coverage is partial; unknown never means no risk.

| Fixed October portfolio | Trades | Native net USDT |
|---|---:|---:|
| Existing baseline |162|-6.38710333|
| Existing VWAP continuation |9|-0.44946448|
| Existing liquidity sweep |24|-0.72529188|
| Original router control |1|-0.11694800|
| Audited frozen-invalidation M0 |1|+0.50352528|
| Research partial-exit M1 with event-once funding |1|+0.42626324|

These are separate portfolios, not additive returns. All use 0.075%/side as a conservative scenario, actual Gate funding/mark sources, 1x, at most 25 USDT per initial position, at most two positions and a 1,000 USDT wallet. Current public generic taker metadata was 0.05%; historical account tiers remain unknown. Additional cost stresses do not refill trades. One positive trade cannot establish an edge.

A separate native replay on recovered **byte-identical old sources** reproduced the audit's nine-trade M1 control, including three partial exits and two funding violations. Event-once funding removed both violations with unchanged entry keys. This qualifies the stated research lifecycle assumption, **not persistent partial-fill/restart behavior**.

## Preserve sources and keep OpenBot isolated

Copy the private bundles under `user_data/data/source-vault/` off the workspace. Raw sources/native ZIPs are intentionally excluded from Git; a manifest cannot restore data after a rolling public endpoint expires. Exact private restoration commands are in the runbook. Source-use scope remains the prior bounded personal/noncommercial Gate research decision; commercial redistribution is not cleared.

Give the parallel OpenBot team only the two ordinary files under `openbot/`, copied into a separate read-only environment. The versioned schema and evidence IDs support the existing Market Researcher, Independent Risk Reviewer and Director. Do not expose the lab root, strategies/configuration, SQLite, Docker socket or authenticated Freqtrade administration. No agent execution bridge or TradingAgents framework is installed.

The existing operational guard still rejects the research router and M1 classes. Account midnight MTM, pending/partial-fill recovery, host isolation and prospective economics remain prerequisites for later persistent paper qualification.

## Stop and rollback

```bash
# Existing owner-host services, if any:
./scripts/lab.sh paper-down
./scripts/lab.sh ui-down
# Research wrapper normally removes its disposable container automatically.
docker ps --filter name=openbot-foundation-
# Preserve private sources, SQLite and credentials before changing checkout.
git switch --detach 29c07b80e8d3b15fb60f097a84eee30d730ffa40
```

Stopping an existing paper engine pauses its position management; it does not guarantee closure. No merge, paid service, future session, live trading, deposit or exchange key is authorized by these instructions.
