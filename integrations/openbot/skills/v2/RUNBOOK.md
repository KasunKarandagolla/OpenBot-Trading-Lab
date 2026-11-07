# Research skills v2 — owner runbook

This checkout runs public Binance research, local PNG requests and a fail-closed numerical gate. It does not install skills or enable orders. Use this checkout, not a different OpenBot audit checkout. PR #18 baseline is `d133b3bf91ab51765d9446e4e82f0bc38c0bae94`; PR #19 skill source is `6f1a378269d962e019498369099bf1a5039c70a4`.

## 1. Check and start a fresh research session

From the checkout directory, with Python 3.12:

```bash
python3 -m venv .venv
.venv/bin/pip install -r integrations/openbot/skills/v2/requirements.txt
export PYTHONPATH="$PWD/scripts:$PWD/tests"
export MPLCONFIGDIR=/tmp/openbot-research-mpl
.venv/bin/python -m trading_lab.skills check
.venv/bin/python -m trading_lab.skills bootstrap --agent chart-vision-analyst
```

`check` must report PASS, 27 assignments, 9 unique IDs, 55 skill files. The five owner names are in `contract.json`. Give the original agent its own `BOOTSTRAP.md`, skill copies and exact checkout path in a shadow research task. Merely writing these files does not prove an original agent loaded them.

## 2. Fetch public data and build charts

Choose a new run directory each time:

```bash
.venv/bin/python -m trading_lab.workflow capture ../research-run/raw --universe 24 --shortlist 4
.venv/bin/python -m trading_lab.workflow build ../research-run/raw ../research-run/packets
```

Read `index.json` and copy its actual candidate directory into `PACKET`. Ranking is attention, not a trade. If clock/network checks fail, retain that attempt and use a new run name. Do not widen freshness rules. After three minutes, the snapshot is historical; refresh before considering a current proposal. Building/reasoning time consumes this window.

```bash
.venv/bin/python -m trading_lab.skills quality "$PACKET"
.venv/bin/python -m trading_lab.skills request "$PACKET" --run-id research-run --request-id vision-question --timeframe 5m --visible-candles 120 --overlays confirmed_swings --purpose 'Which known level would falsify this hypothesis?' --output ../chart-request.json
.venv/bin/python -m trading_lab.skills chart "$PACKET" ../chart-request.json ../chart-revisions
.venv/bin/python -m trading_lab.workflow gate "$PACKET"
.venv/bin/python -m trading_lab.workflow readiness
```

Expected no-proposal gate: `SKIPPED_NO_PROPOSAL`; readiness: `BLOCKED / EXECUTION_BLOCKED_CREDENTIAL_BOUNDARY`. Both commands exit 0 because these are valid fail-closed results. Request errors exit 1. Inspect actual PNG pixels; a pathname is not an image receipt. `skills chart` accepts the entire generated bridge envelope; lower-level `workflow chart` accepts only its `payload.chart`. Consecutive revisions use the same inner ID, revisions 1–4, different outer request IDs. Defaults consume four of the twelve candidate images. Uncaptured 1m must fail `CHART_FEED_NOT_CAPTURED`.

For an entirely isolated file-bridge demonstration:

```bash
.venv/bin/python -m trading_lab.acceptance ../research-run ../new-shadow-test
```

This creates a shadow `OpenBot/Shared` inside the chosen new directory and exercises the actual Inbox implementation. Its receipts are **not native OpenBot messages**. It creates two operator revisions, GATE and READINESS, checks deduplication and rejects uncaptured 1m. It never claims native Risk or pixel delivery.

## 3. Native OpenBot acceptance is still pending

The installed OpenBot CLI documents `list`, `run`, `status` and `new-chat`, but its Local scripts URL/token markers were absent. No native task was sent and no settings were changed. After separately authorizing the needed original profiles' Local scripts access, use that CLI's supported `run`/`status` on the five original roles, pointing to this exact Windows-accessible checkout. Do not change model, identity or permissions merely to pass a test. Use native attachment transfer for PNGs and retain actual message/session/attachment IDs. Missing Risk means `AGENT_NOT_VERIFIED / NO ACTION`.

No credentials or account JSON go into Shared. Signing needs a separately approved isolated execution project. A numerical PASS never authorizes an order.

## 4. Reproduce the real casebook and tests

The evidence folder contains the frozen registration, twelve source-backed decision inputs and later evaluator results. Native paired N/N+V trials are zero. Prior development-data exposure means this is not a pristine holdout. Six systematic cutoffs are retained as abstentions. Range-only, exhaustion and true native agent behavior are not established by this subset.

With an existing verified PR #17 historical data directory:

```bash
.venv/bin/python -m trading_lab.casebook register "$HISTORY" ../new-cases
.venv/bin/python -m trading_lab.casebook export "$HISTORY" ../new-cases
.venv/bin/python -m trading_lab.casebook evaluate "$HISTORY" ../new-cases
```

The exporter excludes later bars. The separate evaluator checks seals and complete contiguous future windows, compares converted rows to official-checksum ZIP CSVs, and uses explicit hypothetical fills/costs. These commands do not create OS isolation or prove exchange queue fills. No decision is rewritten after outcomes.

```bash
export OPENBOT_REAL_PACKET="$PACKET"
.venv/bin/python -m unittest test_openbot_current test_binance_research_data test_local_recovery test_trading_lab_workflow test_skill_integration -v
```

For the inherited real-data timing tests, mount/link the preserved data at `user_data/data/local_recovery` read-only. Without it those three inherited tests skip. Without `OPENBOT_REAL_PACKET`, the new real-source integration tests skip. Report skips; never call fixtures a live demonstration. Exact session stdout/counts/exit codes are in `evidence/skills-v2/20261107/RESULTS.md` and accompanying logs.

## 5. Optional installation and rollback — not performed

Installed activation is `PENDING_OWNER_APPROVAL`. The default workflow needs no installation. The installer has only been exercised on scratch roots; Windows-native junction/power-loss behavior is not proven. It performs a journaled transaction over 27 directories, not one OS-atomic operation across all roots. Stop agent writes before a separately approved install/rollback.

Prepare a **private** JSON map of the five owner names to their verified effective skill roots. Never commit it. On the same filesystem, outside those roots:

```bash
.venv/bin/python -m trading_lab.skill_install prepare PRIVATE_ROOTS.json PRIVATE_TRANSACTION_DIR
# Only after separate owner authorization and review of the exact prepared hashes:
.venv/bin/python -m trading_lab.skill_install apply PRIVATE_TRANSACTION_DIR --owner-authorized
.venv/bin/python -m trading_lab.skill_install rollback PRIVATE_TRANSACTION_DIR --owner-authorized
```

Prepare backs up every exact original and stages new files; apply rechecks all hashes, exact ownership and root identities before touching any target. Drift or symlinks fail closed. A failed rename rolls back. An interrupted APPLYING transaction can be rolled back with the same rollback command. Rollback refuses to overwrite later owner changes. Generic skills, provider mirrors, profiles, queues, models and conversations are outside the mutation set. Provider-mirror activation would need its own owner review; this tool does not update it silently. Live SQLite preservation, if separately needed, uses Windows-native SQLite online backup and scratch integrity/count checks, never a naked live DB copy.

## 6. Stop / review

No persistent worker was activated. Stop any manually started foreground worker with Ctrl+C or its `control/STOP` file. Keep original artifacts; remove only newly created shadow directories if desired. Review the draft PR; do not merge, sign or trade as part of this session.
