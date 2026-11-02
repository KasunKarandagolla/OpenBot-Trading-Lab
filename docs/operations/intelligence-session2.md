# Intelligent opportunity research: Session 2

This extends the existing `lab-foundation.sh` command, native Freqtrade pairlists,
causal recipes, funding accounting and OpenBot reader. Research variants cannot
pass the persistent paper guard. No exchange keys, orders or subscription are used.

## Setup and one complete run

Use Docker Engine and Compose v2, Git and Python 3. Check out
`codex/additional-2-opportunity-intelligence`, then run from the repository:

```bash
docker compose -f deploy/freqtrade/compose.yaml pull
./scripts/lab-foundation.sh run intelligence-owner-001
```

Always choose a new `intelligence-` run ID. The prefix selects the explicit V2
protocol and `evidence/additional-2/` tree; other IDs retain the Session 1 route.
The wrapper creates and removes its own disposable pinned native container. It
mounts the public CA bundle, preserves the configured proxy and verifies TLS.
Do not install credentials or start a UI/paper service for this workflow.

Actions can be resumed individually:

```bash
./scripts/lab-foundation.sh validate intelligence-owner-001
./scripts/lab-foundation.sh backtest intelligence-owner-001
```

The full action order is `register doctor preflight scan acquire assess flow
schedule backtest events report compare export intelligence-lookahead`. Completed
sources/results are preserved; failed attempts retain their own logs. Source
changes require an explicit hash-chained amendment and the original failure/code
must remain reviewable. An amendment must never silently change a hypothesis
after inspecting its outcomes.

## Decisions and cost assumptions

The existing native VolumePairList/SpreadFilter and metadata rules perform the
broad screen. Cheap closed 15m context on at most 20 shortlist markets identifies
signed continuation activity and actual prior-boundary failure candidates. Only
five markets receive hourly, causal structure and profile analysis. The top three
receive a bounded current genuine executed-trade observation. This is a current
membership observation, separate from the predeclared historical population.

The historical signed schedule uses three contracts per recipe/side lane, with
at most five distinct contracts in this five-market sample. Continuation ranks
require the corresponding completed-hour EMA direction and use side times
BTC-relative four-hour return plus the inherited capped activity term. Reversal
ranks exist only after the frozen candle failed-boundary signal. Their ranking
uses signed reclaim distance in ATR units, never absolute opposing momentum.

WATCH means confirmation, boundary quality or opposing trend needs resolution.
REJECT means selection, conflict or economic geometry fails. RESEARCH_CANDIDATE
means a defined analytical setup, subject to its expiry. Every current record
retains `execution_status=NO_TRADE`; the read-only file confers no order authority.

All V2 plans and price rechecks use **0.0038**: 0.0015 round-trip modeled fees,
0.002 friction and 0.0003 adverse funding allowance. Native economic results charge
actual source funding and the common 0.00075/side scenario. The allowances are
admission buffers, not additional deductions from native net. Additional turnover
cost stresses are reported separately. Frozen parents retain their old 0.0035
geometry; the dedicated cost-control arm makes the change visible.

All variants keep 1x, initial notional <=25 USDT, max two positions, frozen signal
invalidation, eight/four-hour recipe holds, five-minute signal/limit expiry and
bounded price deviation. The entry experiment changes only the limit to a 0.1ATR
retracement. Native OHLCV range fills are modeled fills; historical queue/depth
and original receipt clocks remain unknown. A 15m-only range fill cannot prove
that an intra-candle fill preceded the configured five-minute expiry. Sub-bar
fill/expiry qualification requires a separately registered finer-data experiment.

Profile/structure targets are alternatives to fixed 2R. A cramped objective
creates an explicit breakthrough-risk caution and retains 2R unless its modeled
net reward/risk meets 1.25. The separate nearest-objective arm always truncates
and rejects insufficient room. These alternatives test the cost of obstacle
vetoes rather than treating a closer target as automatically superior.

## Flow and profile fidelity

The existing Gate signed-trade normalizer checks contract identity, event clocks,
internal trades and base-asset contract multipliers. Current REST prints are
cross-checked against CCXT's aggressor side and amount. Bounded REST pages never
establish full window continuity. The public WebSocket capture separately records
subscription, disconnections, duplicate IDs, arrival ordering, receipt cutoffs
and a public server-clock check. No connection observation proves exchange packet
losslessness. Unsupported, missing or partial coverage leaves confirmation UNKNOWN.

Native Freqtrade footprint aggregation supplies aggressive buy/sell volume and
delta. V2 records a resetting observed-window CVD, price/delta divergence and
pressure around candidate boundaries known before the observation. A possible
failed-aggression pattern requires actual trades beyond the boundary and a return
inside; delta alone cannot prove absorption. These short observations cannot
establish historical profitability or confirm an expired candle setup.

Profile V2 preserves empty price bins on a contiguous log-price grid and computes
POC, contiguous value area, occupied high/low-volume nodes and base-unit totals.
Historical profiles use **OHLCV_PROXY**, assigning prior candle base volume to its
typical price. Current executed-trade profiles use **OBSERVED_TRADES**, with their
limited coverage preserved. Neither observes passive resting liquidity. Existing
profile functions and old evidence remain intact.

## Evidence and reader import

Under `evidence/additional-2/RUN_ID/`:

| File | Review question |
|---|---|
| `registration.json`, `source-amendments/` | What was frozen before native outcomes? |
| `scan.json`, `deep-shortlist.json`, `opportunities.json` | Why these markets, sides and statuses? |
| `orderflow.json` | Are units, clocks, coverage and profile fidelity qualified? |
| `data-manifest.json`, `parent-source-identity.json` | Are sources continuous and byte-identical to the parent cohort? |
| `signed-schedule.json`, `intelligent-opportunities.json` | Which candidate was selected or rejected, and why? |
| `native-results/`, `native-provenance/`, `trade-ledgers/` | What did native Freqtrade model, fill and charge? |
| `economic-report.json`, `source-funding-audit.json` | Do independent fills/fees/funding reconcile? |
| `comparison.json`, `intelligence-casebook.json` | Did a filter discard control winners or merely reduce coverage? |
| `event-briefing.json` | What current official/publisher context exists, with source clocks? |
| `openbot/` | Bounded sanitized schema-v1 reader snapshot and manifest |

Import only `openbot/` as ordinary read-only JSON into the existing OpenBot roles.
The V2 fields extend the existing schema-v1 interface: suitability, structure,
qualified flow/profile evidence, full plans, strongest contradictory evidence,
event IDs and UNKNOWN states. Historical records never inherit current headlines.
News provides context and event risk, never an automatic direction. The existing
Market Researcher contradiction checkpoint remains intact.

Raw sources and native ZIP archives stay outside Git. Preserve the private source
vault and its checksum off the ephemeral workspace. Restore with the existing
`scripts/foundation_restore.py`, which refuses traversal and overwrites, then run
`validate`. Earlier evidence and private source files must never be replaced by a
new download unless an exact original hash matches an absent restoration target.

## Stop and rollback

The research command cleans up its own temporary container and starts no persistent
service. If this specific runner was interrupted, remove only that runner:

```bash
docker ps --filter name=openbot-foundation-intelligence-owner-001
docker rm -f openbot-foundation-intelligence-owner-001
# Preserve private source vaults and any unrelated owner state first.
git switch --detach b912c821d2d0f2ede0bd491e3f13d13d5f65f607
```

No existing PR is merged. The reserved November 17–December 1 parent holdout is
unobserved and untouched. October is inspected development; all economic changes
remain unqualified for persistent paper or profitability claims.
