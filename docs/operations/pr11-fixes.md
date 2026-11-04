# PR11 corrections: setup-v1.2 / run-003

This is a separate historical candidate based on PR11 commit
`f0ef4453144869ca013ad156fdd46c81b767af2c`. Completed PR11 evidence, frozen V4
and the original EMA benchmark remain at their original references. No live,
testnet, persistent paper or agent-to-order operation is authorized or enabled.
The November17–December1 holdout remains sealed.

| Area | Candidate behavior |
|---|---|
| Shortlist | Complete-day turnover eligibility, then at most3 new candidates per playbook/side. Rank developing state, nearest relevant ATR-normalized location, activity and stable pair. Only selected pairs, existing setups and potential/open positions receive local pivot/setup work. Deduplicate lanes. |
| 4h map | Four exact, consecutive UTC hourly bars; distinguish duplicates, gaps and partial groups. Two-left/two-right pivots become available after their actual confirmation close. Join obstacles at the15m candle OPEN. Readiness requires a complete pivot window, not a directional pivot or EMA warmup. |
| Continuation | Confirmed1h structure and ADX>=20, existing impulse/touch/confirmation rules. Session VWAP readiness applies only to that branch; a confirmed1h swing works independently. EMA telemetry has no new-path veto. |
| Breakout | Any strictly inside completed close invalidates the developing event. A new qualifying break creates a fresh timestamped ID and must confirm independently. A wick retest can remain valid. Open-position two-close thesis exits stay unchanged. |
| Export | Each event owns its timestamp, ID, state, reason and contemporaneous payload. WATCH geometry is null. A shared setup ID links events and never looks up a later plan. Existing schema remains compatible. |
| Profile | Validate actual tape/receipt input, select the latest eligible completed anchor by pair/venue/window/receipt time, preserve multiple sessions. A late assembly cannot authorize a past decision. Missing or approximate data disables that lane. |

Logical stops remain0.3–2.5% with the0.2ATR buffer. First-objective admission retains
the6ATR horizon,38bp allowance and minimum1.25 after-cost RR. No farther target or
fixed3R admission fallback is added. Five-minute entry expiry is separate from
first-fill holding clocks:8h continuation,4h reversal,8h breakout,6h rotation,
absolute15h maximum. Actual execution remains1x,1000USDT, max2 positions and25USDT
notional cap. Native fees are7.5bp/side plus source funding.

The provider checkpoints the existing causal pivot implementation. On first use
or return after an inactive gap, the candidate restores only the immediately
preceding closed-bar local structure from the sealed PR11 feature cache. It
verifies canonical hashes and requires that structure to be known by the current
bar open. Four prior raw bars restore pivot history; sequential updates then use
the original pivot implementation. No setup lifecycle is imported. Fixtures can
fall back to at most960 prior15m warmup bars without a checkpoint loader. An eligible shortlist
observation begins a new lifecycle; existing armed setups continue when rankings
change. Before native fills exist, preparation conservatively reserves management
data through the possible holding period of every ready plan. The report audits
actual filled-position coverage against this trace. Loss of entry eligibility
does not stop position management.

The matched replay uses the existing sealed14-market Gate cohort, September1
through November3,2026 UTC exclusive, with August22 warmup. No replacement data
download is permitted on this path. Current-survivor membership, historical
market status/spreads and changing contract specifications remain limitations.
The38bp allowance is an admission hurdle and is not debited again in PnL.

## Reproduce from the supplied source archive

The original archive is `Setup-Private-Backup.tar.gz`,88,360,503 bytes, SHA256
`abde1f5b151b4bec77eb166e285abc57b0538dd1a3fe4467f2a324df6d6beb7a`.
Verify it before use. Restoration validates members and hashes and hydration
rejects differing existing files. Use a fresh research checkout at the recorded
implementation commit `5786ec7afccf3c687b673e6aa64af9bbec7b18d1`, before completed
run-003 artifacts were committed. Its decision sources match all53 pre-replay
sealed hashes, so source preparation never needs to overwrite published manifests.

```bash
python scripts/setup_archive.py restore /path/Setup-Private-Backup.tar.gz work/input-restore
python scripts/setup_archive.py hydrate work/input-restore .
SETUP_RUN_ID=run-003 ./scripts/lab-setup.sh verify
SETUP_RUN_ID=run-003 ./scripts/lab-setup.sh candidate --audit
```

`candidate --audit` executes actual preparation, an explicit immutable source/
feature/plan/input seal, one native candidate replay, reconciliation/comparison,
and schema-validated export. `--audit` explicitly adds an offline full-universe
reference using the corrected rules; it is not another native strategy sweep.
There is no parameter grid or return-based selection.

With the delivered run-003 cache backup hydrated into the final checkout, use:

```bash
SETUP_RUN_ID=run-003 ./scripts/lab-setup.sh native setup --replay-id owner-check
SETUP_RUN_ID=run-003 ./scripts/lab-setup.sh report
SETUP_RUN_ID=run-003 ./scripts/lab-setup.sh export
```

The wrapper forwards `SETUP_RUN_ID` into the container. It pins
`freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7`,
binds no network port and removes its disposable worker on exit. Completed seals
and native result directories refuse overwrite. All output is under the explicit
run-003 evidence/cache namespace. Frozen controls are reused from their sealed
native records and their ledgers re-audited; they are not called fresh replays.

## Profile input

Optional `user_data/data/setup/profile-index.json` contains a `references` list
of objects with `trades` and `receipt` paths relative to that data directory.
Paths cannot escape it. Each input goes through `verified_profile()`. Receipt
and tape hashes enter the seal. Selection uses actual availability and expires
the reference after its registered duration. Multiple session entries are kept;
there is no day-only overwrite key. If the index is absent, the existing real
LTC sample is supplied through the same route. Its later receipt time makes it
ineligible for the historical window, so rotation economics remain NOT TESTED.
The normal-runner fixture separately verifies that a genuinely timestamp-valid
reference can produce a rotation plan consumed by the native geometry check.

Screening counters measure logical work and actual offline compute on archived
inputs. They do not measure observed network latency, API charges or savings from
avoided historical downloads. Per-lane duplicates, retained setups, management
reservations, cache hits and warmup work are reported separately. The50-pair
fixture is explicitly synthetic. All signed historical Order Flow stays UNKNOWN
where authentic required data are absent. OpenBot receives manual read-only
exports only; confidence or narrative cannot authorize an order.
