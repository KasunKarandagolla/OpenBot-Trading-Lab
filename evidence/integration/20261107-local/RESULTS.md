# Local integration results — PARTIAL / NO MERGE / DEMO ONLY

This is public-data research plus an unsigned add-on and offline recovery harness.
It is not a completed five-agent or filled Demo-trade demonstration.

| Acceptance | Status | Observed result |
|---|---|---|
| F1 preservation/regression | PASS | All six profile rows and queue rows unchanged; seven original checkout HEAD/ref/status/worktree inventories unchanged. Verified 66,323 files / 6,117,951,972 bytes in the earlier full backup. New Windows-native SQLite backup restored to scratch: integrity OK, all 84 table counts equal, six profiles, 6,535 messages. Six provider backups valid. 115 skill/package files restored to scratch with matching hashes. Of 4,002 current source/skill/settings files, 4,000 unchanged; two volatile app resource/run-marker files changed during normal app runtime. No original profile/skill/access/model/database edits. |
| F2 current public research | PASS | Final capture 2026-11-07 05:06:24.014 UTC; 942 exchange instruments assessed, 24 eligible symbols received 72h context, 42 public HTTPS responses retained. Ranked XRPUSDT, ONEUSDT, BIRBUSDT, LYNUSDT; four sealed 11-member packets. Frozen strategy result NO_OPPORTUNITY for all four; no claim of an agent verdict or profitable edge. Source quote times, UTC availability, raw responses, hashes and rejection ledger retained locally. |
| F3 chart service/native intelligence | PARTIAL | Existing local candle primitives reused; legacy images retained. Sixteen clean 1920x1080 default charts with 4h/120, 1h/150, 15m/144, 5m/72 completed candles. All sixteen UTC grids/hash checks passed. XRP default charts visually inspected at original resolution. Two operator-generated revisions through the actual Shared worker returned different PNG hashes; six displayed swing levels independently checked against raw rows. Native Vision's own requests/pixel receipts/blinded valid-invalid case assessment remain PENDING_OPENBOT_OWNER_RUN. |
| F4 five-agent/gate | PARTIAL | Actual Shared GATE reply SKIPPED_NO_PROPOSAL. No fabricated native agent messages/receipts. Authentic BNB historical contract at 2026-08-23 06:20 UTC: geometry PASS, original net RR 1.6000373310814, archive hash verified, future-bar case rejected. Historical leverage stays 1x; execution metadata/quantity/Demo filters remain UNKNOWN. No complete new account-qualified trade proposal was available. |
| F5 signed Demo/account/order | BLOCKED | Credential boundary not established: same owner OS principal can read the credential file. Credential bytes were not opened. All signing paths in this add-on fail closed. Unsigned Demo public quotes/filters fetched; ordinary/algo/open-algo GET probes returned HTTP 401 / -2014 without a key. This does not prove authenticated route or stop support. Signed account reads 0; orders/settings mutations 0; transaction approval absent. |
| F6 recovery | PASS (OFFLINE ONLY) | Persistent simulated submit intent, ambiguous acknowledgment reconciliation, restart, partial fill, stop rejection/disappearance/mismatch, pending-order exclusion, kill switch, close-only emergency policy, expiry and no duplicate opening calls exercised. Offline recovery ends CLOSED and flat; SIMULATED IDs are not Binance IDs. Real exchange protection/TP/user stream/fees/funding/management remain unverified and unimplemented in the isolated service. |
| F7 publication/evidence | PASS (PUBLICATION; archive reported separately) | Draft PR #18 is open against PR17. Published trees are verified against their local counterparts; remote readback confirmed visibility. A final funding-stressed liquidation correction and adversarial regression are included; final HEAD is reported to the owner. Public source/tests/summaries are secret-scanned; full sanitized evidence remains outside Git. Private backups, databases, skills, conversations and credentials are excluded. |

## Verification

- Unmodified recovered integration, with preserved historical files mounted read-only: **41 tests passed, no skips**.
- Final focused set: **71 tests passed, no skips**, 23.140 seconds, exit 0. Includes 30 new workflow tests.
- Initial fixture-free run skipped three real-data timing cases; rerunning with the existing data resolved all three.
- An initial final-suite Docker mount failed (exit 125) because the ignored mountpoint was absent. Creating the empty mountpoint in the new checkout fixed it; original data stayed read-only.
- WSL owner launcher captured, rendered and staged the final run successfully (exit 0, 129.7 seconds, staged CURRENT_RESEARCH).
- Shared worker processed four operator requests, stopped at its bound and deduplicated on restart. Native Windows verified all 44 packet members and both revision images.
- Windows PowerShell script policy rejected the first launcher attempt. Policy was left unchanged; native Python converted Windows paths and started/stopped the WSL worker successfully (exit 0).
- See [test-results.txt](test-results.txt), [REVIEWS.md](REVIEWS.md), and the [operator runbook](../../../research/openbot_current/WORKFLOW_V2.md).

The test command uses the pinned Freqtrade image, `--network=none --read-only`, a tmpfs,
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=/lab/scripts`, the checkout mounted at `/lab`,
and preserved research data mounted read-only at `/lab/user_data/data/local_recovery`:

```python
import unittest, sys
sys.path.insert(0, 'tests')
suite = unittest.TestLoader().loadTestsFromNames([
    'test_openbot_current', 'test_binance_research_data',
    'test_local_recovery', 'test_trading_lab_workflow'])
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
```

Image: `freqtradeorg/freqtrade@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7`.

## History and remaining work

Remote PR #17 remains at d88a3106886239a929989531faacf7b8d8d9b012, stacked on
91bcedfba3569c08933c03c144caeb96d47a524c. Original unpublished
fb8d0a1d1117324d70de7e3b6e52ff908323b8d8 was found and preserved locally/bundled.
Its implementation is included in the final integrated source. The public branch starts
directly above PR #17 with the final fail-closed reader, omitting the unsafe intermediate
credential-loading/signing version from all new public history. The original commit and
intermediate local replay remain preserved locally; no original branch is rewritten.
A concrete Windows account example is replaced by OWNER. Connected GitHub Git-data
publication may give identical trees different commit IDs; final local/remote tree
identity and ancestry are verified before reporting.

Native five-agent acceptance and an OS-isolated signed service are outstanding. The
current signed-service implementation is an unconditional stub, not a trade executor.
The official modular Binance SDK is documented for a future isolated integration;
no account connection, exchange stop or live-position management is claimed.

Draft review: https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/pull/18 . The final documentation/readback commit may advance the PR head without changing the tested implementation.
