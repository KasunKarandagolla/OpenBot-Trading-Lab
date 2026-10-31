# Session3 research operation

Use the Session3 PR branch, Docker/Compose and Python3. The immutable2026.10 image is reused; there is no application build or new dependency. Read evidence/session-3/manifest.md and known-gaps.md. No strategy is economically qualified or authorized for new paper operation.

```bash
python3 scripts/init_runtime.py
docker compose -f deploy/freqtrade/compose.session3.yaml pull
./scripts/lab3.sh --help
./scripts/lab3.sh structure-check
./scripts/lab3.sh test
# Recorded outputs: no source candles, downloads, strategies or admin access needed.
./scripts/lab3.sh economic-compare s3-development-v1
./scripts/lab3.sh validation-report s3-transfer-v1
```

The new Compose file does not publish ports, mount Docker socket, inherit trading keys or start persistent services. It makes code/strategies read-only. Staging copies verified strategy sources into ignored work/session3-strategies; unknown/tampered modules/parameter files reject. The original scripts/lab.sh and guard.py, strategy registry, configs and all prior evidence remain unchanged.

For fresh acquisition only, within lawful Gate public-source eligibility and personal/noncommercial scope:

```bash
./scripts/lab3.sh research-download s3-development-v1
./scripts/lab3.sh research-download s3-transfer-v1
./scripts/lab3.sh research-run s3-development-v1
./scripts/lab3.sh research-run s3-transfer-v1
./scripts/lab3.sh candidate-census s3-development-v1
./scripts/lab3.sh native-replay s3-development-v1
./scripts/lab3.sh opportunity-asof SOL/USDT:USDT 2026-08-25T01:00:00Z
./scripts/lab3.sh opportunity-scan --cohort s3-development-v1 --as-of 2026-08-25T01:00:00Z
./scripts/lab3.sh lookahead s3-development-v1
./scripts/lab3.sh recursive-check s3-development-v1
```

Raw files go to user_data/data/session-3/<id>/gate, never prior paths. Downloads and primary runs refuse existing source/results. With retained raw data, native-replay reruns the challenger without replacing committed primary artifacts. To retry a partial acquisition or run, preserve it and register a new cohort ID; do not remove your only sample. Native lookahead refuses an existing CSV to avoid known Pandas append issues: preserve/move the prior diagnostic before an intentional repeat. Today's surviving shortlist is never historical membership.

For current assessment, reuse the existing scanner into an isolated Session3 output path:

```bash
./scripts/lab3.sh scanner-refresh
./scripts/lab3.sh opportunity-scan
```

Run together: snapshot max age5min; venue ticker max age60sec, future tolerance5sec. Unknown timestamps reject. Max5 candidates. Current receipt time is separate from venue time. In this Cloud run all5 rejected missing venue timestamps; do not force them to pass. Historical reports use Arrow predicate filtering before pandas indicators; asof needs explicit UTC and cannot be future. Outputs are bounded, schema-validated, deterministic except observed current times. Ranking: ACCEPT first, capped relative-volume score min(rvol,5), symbol tie-break; never rank by known profits. Signal is known at candle close and expires5min later. Target is a fee-adjusted native ROI reference with funding uncertainty; not a fill promise.

Future cohorts require no code editing:

```bash
# Example already registered: s3-prospective-v1, evaluation Nov1–Nov8 UTC.
./scripts/lab3.sh prospective-plan
# Only after2026-11-08T00:00:00Z, if source remains lawful/available:
./scripts/lab3.sh research-download s3-prospective-v1
./scripts/lab3.sh research-run s3-prospective-v1
./scripts/lab3.sh economic-compare s3-prospective-v1
# Register another bounded version before outcomes (example ID, not yet executed):
./scripts/lab3.sh cohort-register prospective-week2-v1 20261029 20261108 20261115 \
  BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT --classification PROSPECTIVE_RESERVED
```

Registration runs host Python so reviewed source descriptors can be written while the research container keeps source read-only. It records registration time, cohort hash and strategy/protocol freezes; future end dates cannot be acquired early. Max5 unique linear USDT markets,100 download days,>=240h warmup. Current collector requires observed funding interval matching the declared8h default; other schedules require a separate reviewed cohort definition, not zero-funding fallback. Native pair/mark/funding coverage and continuity block bad samples. New calendar blocks must retain their pre-outcome registration; changing code invalidates prospective registration and requires a new cohort/version. Negative prospective outcomes must not be relabeled development for tuning.

Optional bounded supporting commands:

```bash
./scripts/lab3.sh orderflow-sample
# First call only: separate real5m source window, no overwrites.
./scripts/lab3.sh detail-download
./scripts/lab3.sh execution-sensitivity
```

Orderflow captures one60sec requested window, one public page<=1000prints/2MB. Current documented aggressor-side meaning remains UNKNOWN; no delta used in strategy. Detail compares fixed October1–30 parent/challenger with official5m detail; does not claim queue fills. Raw files/native ZIPs remain local, derived JSON/CSV in evidence/session-3/.

Cloud only: LAB_EXEC_CONTAINER can select an already running disposable official-image runner. Follow the current cloud-runtime skill for proxy/CA setup. Proxy/CA configuration stays ignored under work/ and user_data/runtime; never copy Cloud addresses to owner config or disable TLS. Credentials are never forwarded from the host; CLI/config/mode overrides and FREQTRADE__ are rejected. No API/admin keys needed for any report.

Rollback: there is no Session3 daemon to stop. Preserve source datasets and any pre-existing paper SQLite/private config, then check out f09cb39b6116d103b9efc0f8c37bf6a1d607e7d6. This does not merge PR1/PR2 or alter their branches. Existing paper/UI stop commands remain ./scripts/lab.sh paper-down and ui-down; stopping them pauses simulated management and does not guarantee position closure.
