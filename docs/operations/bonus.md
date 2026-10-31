# Bonus research operations

Research-only branch: `codex/bonus-opportunity-recipes`, stacked on verified Session3 `48f34bcd51d080204c3e4bf90ec4b014a3319dd5`. The original entrypoints and all 329 prior tracked files are unchanged. None of these commands starts paper trading, a web server, private exchange access or orders.

Use Linux/WSL, Git, Python3, Docker and Compose. The image is pinned to official Freqtrade 2026.10 digest `sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7`; installed CCXT is 4.5.90. No package installation is needed. The Compose service mounts the host CA bundle read-only. In the managed Cloud environment, the existing local `user_data/runtime/cloud.json` contains public-network proxy/CA settings, never exchange keys; it is excluded from Git.

## Inspect recorded evidence without raw data

```bash
git switch codex/bonus-opportunity-recipes
git rev-parse HEAD
docker compose -f deploy/freqtrade/compose.bonus.yaml pull
./scripts/lab-bonus.sh reconcile
```

Read `evidence/bonus/acceptance.md`, `economic-results.json`, `economic-report.md`, `source-funding-audit.json`, `management-comparison.json` and `independent-reconciliation.json`. Decimal reconciliation needs recorded native orders and ledgers, not raw candles, downloads or strategy execution.

## Full isolated reproduction

```bash
./scripts/bonus-reproduce.sh owner-rerun-001
```

Use a new ID each time. This archives the current committed source into `work/bonus-reproductions/<id>/`, removes only archived copies of bonus generated outputs in that new directory, and keeps all original evidence. Retained raw source bytes and the safe public-network overlay are copied when available. Otherwise bounded public acquisition runs. It executes:

```text
acquire → restore-prior-raw → schedule → run → economics → reconcile → funding-audit → test
```

The reproduction outputs are under that checkout's `evidence/bonus/`. Raw data stay local under `user_data/data/bonus/`; every source file is hash-verified. `restore-prior-raw` copies only absent files whose bytes match earlier recorded manifests, enabling the unchanged regressions. It refuses an existing mismatched raw file. Exchange retention and retrospective feed revisions can prevent exact reacquisition later; retain the original raw files locally.

The owner delivery includes `bonus-local-reproduction-sources.tar.gz` (hash in `evidence/bonus/local-source-bundle.json`). Restore it into this repository with:

```bash
tar -xzf bonus-local-reproduction-sources.tar.gz -C /path/to/OpenBot-Trading-Lab
./scripts/lab-bonus.sh reconcile
./scripts/lab-bonus.sh funding-audit
```

The source-event funding audit and recorded-order reconciliation require no exchange calls. A full fresh native run still loads public instrument and margin-tier metadata. During the actual isolated rerun, eight policies/154 trade records matched field-for-field; repeated Gate HTTP503 responses blocked the final two. The failed attempts are retained. Native CLI failure cannot be treated as a completed run. Keep its log under a new failure filename before retrying that incomplete policy with `run`; do not alter completed artifacts or risk settings. Docker VFS also exhausted local startup space once; removing only the own idle disposable research worker resolved that resource limit.

The primary registered cohort is July 26–October 30 for acquisition, August 5–October 30 for evaluation, UTC and end-exclusive. It is already-inspected DEVELOPMENT, with a five-survivor historical roster. It is not historical full-exchange membership or an independent holdout.

## Bounded public observations and current scanner

```bash
./scripts/lab-bonus.sh scan
./scripts/lab-bonus.sh capture --observation-id owner-btc-001 --symbol BTC/USDT:USDT
./scripts/lab-bonus.sh replay --observation-id owner-btc-001
./scripts/lab-bonus.sh capture --observation-id owner-sol-001 --symbol SOL/USDT:USDT
./scripts/lab-bonus.sh replay --observation-id owner-sol-001
```

Captures last 95 seconds, use one eligible Gate USDT linear perpetual, and refuse reused IDs. Gate signed contracts are converted to base/quote amounts. Ten quote-price ticks form the native footprint scale for new observations; earlier BTC captures retain their recorded scale for exact replay. Only received trades at or before the decision cutoff enter a window. The public WebSocket requests `X-Gate-Size-Decimal: 1` so fractional contract sizes are preserved. Internal nonmatching trades are excluded. Connection completeness does not prove venue losslessness. A real closed-candle shadow assessment is included; manufactured plumbing plans are explicitly labelled and never counted as actual setups or profits. Strict OF confirmation returns UNKNOWN for partial coverage. Historical order-flow profitability remains unmeasured.

The existing native scanner screens broadly, caps its shortlist at 20, and deeper current analysis at 5. Missing ticker source clocks reject live entry. A scanner refresh preserves its original command log; use an isolated new reproduction checkout for a second scan.

The separately registered prospective interval is November 9 05:30 through November 16 05:30 Asia/Colombo (November 9–16 00:00UTC). It does not reuse the earlier November 1–8 reserved cohort. Observations before it are development mechanics demonstrations. Collection is owner-invoked and bounded; no scheduler, daemon or paper deployment is installed.

## Additional checks with retained sources

```bash
./scripts/lab-bonus.sh restore-prior-raw
docker compose -f deploy/freqtrade/compose.yaml --profile tools --profile ui --profile paper config --format json > user_data/runtime/compose-safety.json
./scripts/lab-bonus.sh test
./scripts/lab-bonus.sh risk
./scripts/lab-bonus.sh funding-audit
./scripts/lab-bonus.sh native-replay
./scripts/lab-bonus.sh lookahead
```

Primary replay/lookahead/risk outputs are retained already. Native replay and lookahead refuse overwrites; run them in a new isolated reproduction checkout. Risk scenarios are illustrative on current public tiers and a historical plan; they do not backdate current tiers or approve an operational risk ceiling.

The October 1–30 UTC detail experiment uses the same data directory with separate5m files and native result destinations:

```bash
# In a new checkout without detail files/results:
./scripts/lab-bonus.sh detail
./scripts/lab-bonus.sh detail-run
```

Do not redownload over retained files. The full production of primary evidence required ten main native variants, four detail runs, one native replay and the native lookahead diagnostic. Their result JSON, console logs and provenance hashes are committed under `evidence/bonus/`.

## Known operational blockers

M1 has a pinned native funding defect at exact-clock partial/funding boundaries in two recorded trades. Preserve its research results; fix and revalidate the native lifecycle/accounting before persistent operation. Candle fills do not validate real queue priority, incomplete exchange fills, outages, native database restart recovery or owner-host uptime.

The native admission callback adds fresh completed-candle unrealized PnL and reserves open/pending exposure. Its daily reference is realized-balance based, not a fully reconstructed midnight mark-to-market account baseline. The separate leverage evaluator tests full inputs, missing tiers, pending/correlated exposure and1/10/20x algebra. Neither establishes owner-approved leveraged operation.

The three SKILL.md packages are instructions and static contract cases for existing OpenBot roles. They are not tested model integrations or a security boundary. Host/API/credential isolation and reliable source clocks remain prerequisites for any future role automation.

There is no bonus trade/paper command. The unchanged operational guard refuses these new adjustment strategies. Do not bypass it. Owner review and explicit separate authorization are required for merges, persistent paper, exchange credentials, paid services or any financial execution.
