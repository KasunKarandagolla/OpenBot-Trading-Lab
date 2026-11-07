# Compatibility and adversarial Codex self-review

This is an independent Codex subagent pass within the same engineering session. It is not human validation, original OpenBot agent application, native image transfer or trading intelligence evidence. No installed profile, app database, credentials, private messages or sixth profile was accessed or changed. Later real outcome data were not read.

## Checks actually run

The focused command used the isolated Python runtime, `PYTHONPATH=scripts`, an authentic sealed XRP packet supplied through `OPENBOT_REAL_PACKET`, and:

```text
python -m unittest discover -s tests -p test_skill_integration.py -v
Ran 19 tests in 199.237s
OK
exit 0; failures 0; skips 0
```

The tests covered exact 27-assignment ownership, five bootstrap cards, current request/schema bounds, expired/future requests, WATCH rejection, absent Risk, proxy/gapped flow, no-pixel candidate refusal, real chart rendering/replay, wrong venue/symbol/cutoff/uncaptured 1m, re-sealed future-bar mutation, actual inbox account injection rejection, swing prefix equivalence, scratch installer opt-in/preconditions/failure recovery/rollback and post-prepare root symlink refusal. Installer testing used temporary shadow roots only.

Inspection compared the actual `charts.py`, `workflow.py`, `risk.py`, current `order-intent.schema.json`, v2 request/assessment schemas, `skills.py` and `casebook.py`. The v2 order decisions now match the public gate's MARKET/LIMIT/CONDITIONAL vocabulary; *_ENTRY remains its internal legacy translation. A numerical gate result still grants no order authority, and the unsigned inbox excludes account state.

## A1 — P1: image receipt hashes were not bound to the sealed packet/source

**Reproduced failure:** The original `scripts/trading_lab/skills.py:224` loop compared assessment image fields only against a mutable local renderer receipt. In a temporary copy of the real XRP `default-5m-r1` revision, setting both receipt and assessment image `source_sha256` to 64 zeroes and `packet_sha256` to 64 ones still returned PASS. The top-level assessment retained the real packet hash; the PNG and request were unchanged. The baseline and corrupted cases both passed in the same command, exit 0.

**Fix verified:** Current `skills.py` compares receipt packet hash against the actual packet seal and source hash against the captured source selected by the request timeframe. A matching alteration in receipt and assessment now returns `IMAGE_PACKET_OR_SOURCE_BINDING`. No original chart files were modified.

**Residual limit:** Local metadata validation cannot authenticate a native sender or establish that a model actually received image pixels. The validator explicitly returns native/pixel delivery independently verified = false; keep that limitation.

## A2 — P2: a seen image unlocked visual claims about an unrelated image

**Reproduced failure:** With one correctly declared seen XRP image, a VISIBLE observation using `evidence_id=nonexistent-image-r1` returned PASS. The initial global `pixels` boolean did not bind individual observations to their image evidence.

**Fix verified:** Current validator rejects the same observation with `VISUAL_CLAIM_IMAGE_NOT_SEEN`. It also rejects synchronized forgery of `last_available_ms` in receipt and assessment with `IMAGE_BAR_WINDOW_MISMATCH`. The authentic baseline continues to PASS. A single latest-source retest command exercised all four corruptions, exit 0:

```text
baseline PASS
source REJECTED IMAGE_PACKET_OR_SOURCE_BINDING
packet REJECTED IMAGE_PACKET_OR_SOURCE_BINDING
window REJECTED IMAGE_BAR_WINDOW_MISMATCH
unbound-visible REJECTED VISUAL_CLAIM_IMAGE_NOT_SEEN
```

## A3 — P1 for claimed path economics: evaluator accepted an interior missing bar

**Reproduced failure:** `scripts/trading_lab/casebook.py:150` checked only that the future path was nonempty and its first open equaled the cutoff. It did not require a contiguous completed five-minute grid or the full declared hold window before computing exit/P&L.

An explicitly **synthetic negative control**, not a market demonstration, patched `load_frame` to return two bars at opens 0 and 600000 with availability 300000 and 900000, omitting the intervening open 300000. Entry 100, stop 99, target 102, long, fifteen-minute hold. The archive verifier was patched only to isolate the chronology check. `evaluate` accepted the gap and returned:

```text
{"negative_control":"SYNTHETIC_NOT_MARKET_EVIDENCE",
 "missing_future_bar_accepted":true,"outcome":"TIME_EXIT",
 "net":-0.05003750000000142}
exit 0
```

A missing bar could contain the first stop or target, so neither the exit nor modeled economics is determined.

**Fix verified:** The parent added `validate_outcome_window` and invokes it before all path metrics. It requires the exact five-minute row count, first open, last availability, contiguous opens and availability = open + five minutes. The new focused `ContractTests.test_outcome_gaps_cannot_produce_path_metrics` passed (one test, 0.962s, exit 0). Repeating the same synthetic evaluator reproduction now raises `OUTCOME_WINDOW_INCOMPLETE_OR_GAPPED`; no outcome file is created, command exit 0.

**Additional source hardening checked:** `verify_archives` now compares selected converted OHLCV/taker fields and clocks against actual CSV rows in the checksum-verified ZIP, rather than trusting a source-hash column alone. An isolated explicitly synthetic ZIP control accepted its matching row and rejected a changed converted close with `CASE_ARCHIVE_ROW_VALUE`, exit 0. An initial attempt to mutate an integer Pandas column with a float failed in the test harness; the corrected integer-value negative ran successfully. This is a source-validation negative, not genuine Binance economic evidence.

## Acceptance scope

Contract/negative tests establish functioning fail-closed code paths under the tested inputs. The newly bound image/source/window checks are improved source validation, not proof of analysis quality. Native five-agent requests, actual native attachments, independent original Risk participation, N versus N+V performance and forward economics remain unestablished by this pass. The separate evaluator is a hypothetical candle-touch model, not exchange fill evidence; the casebook explicitly labels its development-data and no-OS-isolation limitations.
