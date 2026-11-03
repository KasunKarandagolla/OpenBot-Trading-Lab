# Session 3 native policy workflow

This release contains an integrated deterministic policy and native lifecycle/risk
mechanics. Economic qualification and persistent paper activation are separate.
No process, exchange order bridge or agent execution permission is installed.
The existing persistent-paper guard continues to reject research policy classes.

## Run one complete bounded evaluation

Use the branch `codex/additional-3-integrated-policy`, Docker with Compose v2,
Python 3 and the existing official pinned Freqtrade 2026.10 image. The wrapper
creates one disposable container, then removes it on exit:

```bash
docker compose -f deploy/freqtrade/compose.yaml pull
./scripts/lab-foundation.sh run policy-owner-001
```

Use a fresh ID. This command performs public native VolumePairList/SpreadFilter
screening, a signed shortlist, five deep assessments, genuine bounded executed
trade observations, read-only news, public historical acquisition, causal plans,
26 native chronological portfolios (including matched10x/20x management scenarios), native lifecycle fixtures, contract-backed
risk scenarios, independent accounting and schema-v1 OpenBot export. It is a
research command; it never starts a persistent paper service.

The historical five-market universe is a predeclared survivor cohort, not a
reconstruction of old exchange membership. Sources cover July 26–November 2;
evaluation is August 5–November 2 UTC, end exclusive. August–October were inspected
in earlier development. November 1 is one newly registered completed day, not a
sufficient independent holdout. The November 17–December 1 reserved period is
unacquired and unobserved. One-minute detail covers October 28–November 2; the
original October 26 request exceeded Gate's rolling 10,000-point endpoint limit.

Gate history rolls out of availability. Keep the private source/native-result
backup outside this workspace. Never silently replace an old dataset or interpret
reacquisition as byte-identical restoration. The manifests record original versus
reacquired source hashes. Only five of twenty original October source slices
matched byte-for-byte; unchanged replay of an old strategy is assessed separately.

## Resume and inspect

An interrupted run retains completed evidence. Resume verifies historical file
hashes, reuses completed snapshots, preserves failed logs and uses separate native
attempt directories. It does not refetch the already completed current scan:

```bash
./scripts/lab-foundation.sh resume policy-owner-001
```

Only one pinned container is needed. On a small Docker VFS host, stop disposable
unused containers before creating another copy of the image. The session's
recovery used the existing disposable runner:

```bash
LAB_FOUNDATION_CONTAINER=openbot-policy-session3 \
  ./scripts/lab-foundation.sh resume policy-session3-002
```

Read `economic-report.json`, `trade-ledgers/`, `source-funding-audit.json`,
`casebook.json`, `opportunity-ledger.json`, `leverage-scenarios.json` and
`native-provenance/` under the run's `evidence/additional-3/` directory. Native ZIPs
and private sources remain under `user_data/`, outside Git. Portfolios are
alternatives; their returns must never be summed. Funding is independently bounded
from real source events and native held quantities.

Native net includes the configured 0.075%/side fee scenario and actual source
funding. Native candle-range fills have no modeled spread or queue. The 38 bp
admission allowance is not subtracted again from P&L. Separate turnover stress
shows additional spread/slippage; 10 bp/side corresponds to the 20 bp round-trip
friction allowance. A positive native net that fails that stress is economically
unqualified.

## What owns positions and risk

Freqtrade owns entry, amount precision, native ROI, protective stops, partial
reductions, pending-order cancellation and final exits. The strategy freezes entry,
stop, target, expiry and decision ID before filling. Native Trade custom data
persists geometry, observed quantities, monotone stops and funding events; a
separate single-writer SQLite checkpoint stores account day/peak/streak state.
No DCA or positive position adjustment is permitted.

Continuation maximum hold is eight hours; reversal is four hours, measured from
first actual fill. A pending entry expires after five minutes. An observed partial
entry is canceled through native timeout so its filled amount crystallizes.
Pending partial exits are canceled/rechecked through native mechanisms; any
replacement can request only the unfilled portion of the original one-third
allocation. Filled quantities and event IDs prevent repeated whole partials.

The account engine distinguishes cash, realized net, unrealized net, equity, posted
margin, free collateral, pending margin, gross notional and intended stop risk.
Pending exits retain conservative exposure until native reconciliation. Native
open partial fills contribute to MTM before they become a terminal order. UTC
baseline/peak state survives restart; a missed exposed-account midnight rollover
inhibits new entries. Protective management continues during an entry halt.

Budget: 0.25% equity/trade, 0.50% aggregate stop risk, two simultaneous positions,
all-five-markets correlation bucket capped at 0.5x equity, gross 1x equity, 1% UTC
MTM loss, 5% peak drawdown and a one-hour cooldown after three losses. Research
comparisons share a 25 USDT initial notional cap; the generic account contract
supports a 250 USDT ceiling with equity-based sizing. Leverage changes posted
margin, not the logical stop or risk budget. Current public contract tiers and a
1% stop/liquidation clearance govern supported 10x/20x scenarios. Historical tiers
and intrahour mark paths remain unknown. Missing tiers reject leveraged entries;
fully collateralized 1x has a separately labeled fallback.

The dry-run funding adapter scopes event-once accounting to the existing native
Exchange instance. It uses native public history and native valuation, never an
order API. Consumed event IDs and monetary state persist on the native Trade.
A funding source gap retains last-known fees and marks accounting UNKNOWN; it
cannot become favorable zero. Unknown accounting inhibits entries while exits
continue. The event-before-same-clock-exit convention is explicit; real venue
priority is not claimed. Controlled fixtures establish restart/partial accounting,
not an observed forward paper fill.

## OpenBot and the next two sessions

Copy only the selected run's `openbot-release/` ordinary JSON files into a separate
read-only OpenBot environment. The original `openbot/` snapshot preserves the
preregistered management candidate. `release.json` identifies the final reference
and makes its post-development selection explicit. Neither snapshot grants
execution permission. Never mount the lab root, SQLite, config, Docker socket or
Freqtrade administration into the agent environment.

[Session 4 contract](policy-session4-handoff.md) defines decision, trade, outcome,
contradiction, source-clock and unknown-state fields. The three existing logical
roles can interpret this evidence. They cannot change stops, place administrative
orders, alter the release or clear missing evidence. News remains read-only and
current flow is never attached to old historical signals.

## Stop and rollback

The wrapper removes its disposable container on normal completion or failure.
To stop a manually reused disposable runner, first ensure no bounded command is
still running, then remove that named container. Preserve private sources and
state before changing checkout. Return to the exact parent without merging:

```bash
git switch --detach 913eec38213052f979e67fd532febac809cbcabd
```

Stopping a future paper engine would pause management, not close positions. Host
isolation, current source/mark readiness and prospective economics still require
separate operational qualification. This session starts no persistent service.

## Restore the delivered private backup

Check the archive SHA256 against `private-backup.json` in the final run, then
verify/extract into an empty staging folder. The helper rejects path traversal,
symlinks, unexpected paths, mismatched digests and overwrites:

```bash
python scripts/policy_restore.py OpenBot-Session3-Private-Backup.tar.gz work/restored-session3
cp -an work/restored-session3/user_data/. user_data/
cp -an work/restored-session3/work/. work/
./scripts/lab-foundation.sh resume policy-session3-002
```

Do not copy the backup into OpenBot. It contains private raw research data, native
ZIPs, immutable strategy/config stages and account checkpoints. The delivered
read-only reader ZIP contains only the two final ordinary JSON files. Restoration
was actually verified for all 447 files, without overwriting a file.
