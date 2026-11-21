# Windows native receipt recovery

| Release reference | Value |
|---|---|
| Tested baseline | `27addd0a0ea3d39799aad7f8ac0ba602c103fe42` |
| Implementation verified here | `7282cf92ea7f185d38f87396f1ccfe3c51ec960e` |
| Historical job | `20261121T155516Z-817636a12ff84a4797555d0d2887de42` |
| Delivery | `feature/external-first-market-researcher`, draft PR #24 |

## Windows storage

The owner observed an ordinary 272-character Windows path fail with
`NATIVE_STORAGE_UNAVAILABLE / OS MISSING_FILE` while the extended form opened
the same file. The code discarded the `\\?\` prefix during path translation
and used the resulting ordinary Windows path for metadata and byte reads.

The reader now checks traversal and directory scope using the ordinary path.
It checks each component for a symlink or redirecting reparse point before
accessing the next component. That metadata check itself uses the extended API
path because a long component can also be a symlink. The checked I/O path is
then used for metadata and content. Ordinary drive paths, already extended
drive paths and WSL drive paths resolve to the same logical location. The
extended prefix stays out of the canonical WSL evidence commands and hashes.

The change affects `native_identity.py`, `native_handoff.py`, `native_app.py`,
`native_host.py`, `native_codex.py` and `native_runtime.py`. The existing SQLite
read-only URI and query-only mode, canonical material and argument verification,
parent binding, one-shot dispatch and 90/30/600-second limits are retained.

## Historical model identity

The original private request, state, Windows databases and rollout for this job
were unavailable in Cloud. That leaves the reported `NATIVE_MODEL_SWITCHED`
comparison unresolved on the actual job. The reader still requires exact model,
provider and adapter values. It now emits allowlisted diagnostic labels for
the failing comparison.

| Diagnostic | Comparison |
|---|---|
| `CONFIGURED_MODEL`, `CONFIGURED_PROVIDER`, `CONFIGURED_ADAPTER` | Current Researcher configuration versus the captured parent identity |
| `APP_PARENT_MODEL`, `APP_PARENT_PROVIDER` | OpenBot parent provider-session row versus the captured parent |
| `CODEX_PARENT_THREAD_MODEL` | Codex state `threads.model` versus the already matched app parent model |
| `ROLLOUT_TURN_CONTEXT_MODEL` | Exact attested turn's `turn_context.payload.model` versus its expected model |
| `APP_CHILD_MODEL`, `APP_CHILD_PROVIDER`, `CODEX_CHILD_THREAD_MODEL`, `ROLLOUT_SETTINGS_MODEL` | Child session, Codex state or rollout setting versus the required identity |

If the captured sources agree and the configured model differs, the owner
must decide whether to retain the current configuration for a separately
authorized future run or restore the original through the usual application
controls. If the historical sources disagree, inspect the exact schema and
model values locally before considering a compatibility change. Case, whitespace,
prefix and missing-value differences remain grounds for rejection.

## Offline verification

- The independent 272-character fixture failed on the exact baseline at
  `native_handoff.read_object().stat()` for drive, extended-drive and WSL forms.
  The corrected path read the same bytes for all three forms.
- The bridge fixture rebuilt ten canonical pages and checked the packet, saved
  arguments and reservation. It rejected tampered request and argument files.
  Short files, missing long files, path escapes, alternate streams and links
  at the file and ancestor were exercised in isolated files.
- Model fixtures distinguished configuration, app parent session, Codex parent
  thread and parent rollout model mismatches. Alias, missing and different
  models were rejected. Restoring exact fixture metadata restored receipt validation.
- The frozen full offline suite passed `527` tests in `521.379` seconds.
  Configuration validation, syntax checks, protected path comparisons and
  `git diff --check` passed. The Windows filesystem behavior was simulated in
  Cloud. The historical readback logic also passed against a ten-page simulated
  receipt. The original job still requires a readback on the owner host.

[Regression tests](../../tests/test_native_windows_paths.py) · [Draft PR and CI](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/pull/24/checks)

## Bounded owner-host readback

Use the same approved WSL checkout and existing Windows Python. Confirm the
remote is `KasunKarandagolla/OpenBot-Trading-Lab`, keep the original job files
and private audit configuration in place, and fast-forward to the tested code.

```bash
test "$(git branch --show-current)" = feature/external-first-market-researcher &&
test -z "$(git status --porcelain)" &&
git fetch --no-tags origin refs/heads/feature/external-first-market-researcher &&
git merge-base --is-ancestor 7282cf92ea7f185d38f87396f1ccfe3c51ec960e FETCH_HEAD &&
git merge --ff-only 7282cf92ea7f185d38f87396f1ccfe3c51ec960e &&
test "$(git rev-parse HEAD)" = 7282cf92ea7f185d38f87396f1ccfe3c51ec960e
```

Keep the existing checkout directory, which is part of the exact packet
commands. Select the one recorded 64-hex material for the original ten-page
reservation in this job's `review` directory. Match it to the original
dispatch ticket if multiple materials exist.

Save the following as `work/native-receipt-check.py` in that checkout. It prints
hashes, counts and comparison labels. It reads one material and the exact
parent/child evidence using the original recorded freshness interval. It
never calls the runner's start, wait, page-serving or advice-import paths.

```python
import json
import os
import re
import sqlite3
import sys
from datetime import timedelta

checkout, material = sys.argv[1:]
sys.path.insert(0, checkout)

from researcher.agent_review import _material
from researcher.contracts import ContractError, digest, encode, utc
from researcher.native_app import failure, observe_handoff
from researcher.native_codex import turn_records
from researcher.native_handoff import FRESH_SECONDS, SHA256, load_dispatch, read_object
from researcher.native_identity import configured_identity, load_private, path_key, read_db, ref, under_work
from researcher.native_runtime import collect
from researcher.openbot_runner import _read
from researcher.settings import ROOT

JOB = "20261121T155516Z-817636a12ff84a4797555d0d2887de42"


def report(stage, **values):
    print(json.dumps({"stage": stage, **values}, sort_keys=True), flush=True)


def main():
    if os.name != "nt" or path_key(checkout) != path_key(ROOT) or not re.fullmatch(SHA256, material):
        raise ContractError("NATIVE_HANDOFF_UNATTESTED")
    base = ROOT / "work/openbot-integration"
    job = base / "jobs" / JOB
    review = under_work(job / "review")
    path = under_work(review / (material + ".request.json"))
    state = _read(job / "state.json")
    request = read_object(path)
    captured = request["native_identity"]
    if (state["job_id"] != JOB or state["native_identity"] != captured
            or request["material_sha256"] != material
            or digest(encode(_material(request)).encode()) != material):
        raise ContractError("NATIVE_REVIEW_REQUEST_HASH")
    cutoff = utc(request["as_of_utc"]) + timedelta(seconds=FRESH_SECONDS, microseconds=-1)
    as_of = cutoff.isoformat()
    _, fingerprint, pages, ticket = load_dispatch(review, request, as_of=as_of)
    rebuilt = "".join(json.loads(page)["text"] for page in pages)
    if len(pages) != 10 or digest(rebuilt.encode()) != fingerprint:
        raise ContractError("NATIVE_READ_INCOMPLETE")
    report("WINDOWS_SAVED_PACKET", request_hash=digest(path.read_bytes()),
           arguments_hash=ticket["arguments_sha256"], packet_hash=fingerprint, pages=len(pages))

    config = load_private(base / "native-audit-local.json")
    current = configured_identity(config)
    expected = captured["model"]

    def compare(model):
        if model == expected:
            return "EXACT"
        if model is None:
            return "MISSING"
        if not isinstance(model, str):
            return "DIFFERENT_TYPE"
        if model.strip().casefold() == expected.strip().casefold():
            return "CASE_OR_WHITESPACE_DIFFERENCE"
        backend = captured["provider_backend"]
        if model == backend + "/" + expected or expected == backend + "/" + model:
            return "PROVIDER_PREFIX_DIFFERENCE"
        return "DIFFERENT_MODEL_VALUE"

    report("CONFIGURED_RESEARCHER", model=compare(current["model"]),
           agent=current["agent_id"] == captured["agent_id"],
           provider=current["provider"] == captured["provider"],
           adapter=current["adapter"] == captured["adapter"])
    with read_db(config["openbot_db"]) as db:
        db.create_function("receipt_ref", 1, ref, deterministic=True)
        parents = db.execute("""
            SELECT p.provider,p.model,p.external_session_id,t.turn_id,t.started_at,t.completed_at
            FROM projection_threads h JOIN projection_turns t ON t.thread_id=h.thread_id
            JOIN projection_provider_sessions p ON p.id=t.provider_session_id AND p.thread_id=h.thread_id
            WHERE h.agent_id=? AND receipt_ref(h.thread_id)=? AND receipt_ref(t.turn_id)=?
              AND receipt_ref(p.id)=? AND receipt_ref(p.external_session_id)=? LIMIT 2
        """, (captured["agent_id"], captured["thread_ref"], captured["turn_ref"],
              captured["session_ref"], captured["external_session_ref"])).fetchall()
    if len(parents) != 1:
        raise ContractError("NATIVE_SESSION_MISMATCH")
    provider, model, session, turn, start, end = parents[0]
    if start != captured["parent_started_at_utc"]:
        raise ContractError("NATIVE_SESSION_MISMATCH")
    report("APP_PARENT_SESSION", model=compare(model), provider=provider == captured["provider"])
    with read_db(config["provider_db"]) as db:
        row = db.execute("SELECT model,model_provider,cwd FROM threads WHERE id=?", (session,)).fetchone()
    if row is None:
        raise ContractError("NATIVE_SESSION_MISMATCH")
    report("CODEX_PARENT_THREAD", model=compare(row[0]), backend=row[1] == captured["provider_backend"],
           workspace=path_key(row[2]) == path_key(config["agent_workspace"]))
    contexts = {compare(item["payload"].get("model")) for item in
                turn_records(config, session, turn, config["agent_workspace"],
                             start=utc(start)-timedelta(seconds=1),
                             end=min(cutoff, utc(end)) if end else cutoff,
                             backend=captured["provider_backend"]) if item["type"] == "turn_context"}
    report("PARENT_ROLLOUT_MODEL", comparisons=sorted(contexts) or ["MISSING_CONTEXT"])
    parent = observe_handoff(config, identity=captured, directory=review, material=material, as_of=as_of)
    report("PARENT_RECEIPT", submission=parent["submission_state"], task_matched=parent["task_created"])
    if parent["submission_attempts"] != 1 or parent["submission_state"] != "ACKNOWLEDGED" or not parent["task_created"]:
        return 2
    found = collect(request, config, as_of=as_of, directory=review)
    if found is None:
        report("HISTORICAL_RECEIPT", status="NO_COMPLETED_RECEIPT_IN_WINDOW")
        return 2
    _, audit = found
    verified = (audit["native_invocation_verified"] is True and audit["verified_evidence_pages"] == 10
                and audit["reply_validation_status"] == "VALIDATED")
    report("HISTORICAL_RECEIPT", verified=verified, pages=audit["verified_evidence_pages"],
           reply_validation=audit["reply_validation_status"])
    return 0 if verified else 2


try:
    raise SystemExit(main())
except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, RecursionError) as error:
    report("HISTORICAL_RECEIPT_CHECK_FAILED", fault=failure(error, "HISTORICAL_READ"))
    raise SystemExit(2) from None
```

From the WSL checkout, set `RECEIPT_MATERIAL` to the selected material and use
the already configured Windows interpreter. This is a single bounded readback.

```bash
receipt_python=$(python3 -c 'from researcher.native_identity import load_private,local_path; print(local_path(load_private("work/openbot-integration/native-audit-local.json")["native_python"]))')
timeout 90s "$receipt_python" -X utf8 "$(wslpath -w "$PWD/work/native-receipt-check.py")" \
  "$(wslpath -w "$PWD")" "$RECEIPT_MATERIAL"
```

Require `WINDOWS_SAVED_PACKET` for storage and exact matches across all recorded
identity layers for receipt verification. Require `PARENT_RECEIPT` with the
matched acknowledgment and `HISTORICAL_RECEIPT` with `verified=true` and ten
pages to establish the original receipt. A late or missing child final remains
unverified within the original window. Retain the sanitized failing stage for
any further diagnosis.

Before another live acceptance, the owner host must demonstrate the saved
packet readback, resolve any actual identity discrepancy, and verify exact
parent and child evidence. A new controlled run requires separate authorization
and the existing agent/model, installed skill hashes and read-only preflight.
This historical check grants zero trade authority and produces no current advice.
