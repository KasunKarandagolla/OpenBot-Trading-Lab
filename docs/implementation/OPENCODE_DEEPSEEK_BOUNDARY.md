# OpenCode compact native boundary: adapter implemented, acceptance pending

Status: **ADAPTER IMPLEMENTED / OFFLINE VERIFIED / NATIVE ACCEPTANCE NOT
CLAIMED**. The selected existing OpenCode/DeepSeek configuration is not changed.
The compact adapter is pinned to normalized session/part record version 2.4.1;
the legacy message reader retains its observed historical versions. The exact
owner prompts, their runner modes and their supported Code Mode invocation are
defined in `OPENCODE_NATIVE_ACCEPTANCE.md` and its three canonical prompt files.
Do not run acceptance until the owner separately authorizes each stage.

Historical `SESSION_06C_NATIVE_REVIEW.md` records a real older OpenCode model
review with skill and evidence reads. It does not prove the current installed
host's compact parent task call, acknowledged task ID, complete model-visible
page outputs, per-turn identity and final-reply binding. Pinned upstream source
at `a0b754f8baa8fb49fb200ffb3759b17429a962a9` shows ACP raw input/output
handling, but is not proof of installed version, persisted record shape, output
completeness or turn attribution. No local fixture is an actual provider receipt.

## Phase C result (24 November 2026)

The owner performed the one-run diagnostic on the existing Researcher with
`opencode/deepseek-v4.1-flash-free` at effort `high`. Read-only records show one
parent turn, one acknowledged task, one child turn and one final answer. The
parent ran the exact read-only page command (exit `0`, `235`-byte output,
SHA-256 `ea011a591e8bd4d7c1cd64dc8fa25b36c9c74ac8e33d131230b19c8ef414461c`),
discovered both requested schemas inside the turn, and submitted the exact title
and brief once. The child ran exactly the same one `shell` command and returned
the page ID, nonce, marker and `9 × 7 = 63`. No market-data or trading tool
appears in either session.

The format gap is exact: both sessions are OpenCode record version `2.4.1` and
store tool calls only in `session_part` (`type=tool`, `name`, `call_id`,
`state.input`, `state.content`, `state.metadata.exit`). Every assistant
`session_message` row in these turns has `content: []`, so the existing
`OPENCODE_V2_SESSION_MESSAGE` reader sees no tool calls and cannot attest them.
The task call is nested inside the native `execute` Code Mode tool, not a
top-level provider `openbot.start_task` call. This is boundary evidence, not
native acceptance of the runner, paged transport or any market capability.

The next gate is a narrowly scoped `OPENCODE_V2_SESSION_PART` reader and
attester with adversarial offline tests. Do not add OpenCode to
`COMPACT_ADAPTERS` until that reader is reviewed and published. The full
chronology, hashes and failure cases are in
`PHASE_C_OPENCODE_BOUNDARY_DIAGNOSTIC.md`.

## Owner-host action (performed)

The action below was performed once on 2026-11-24. It is retained as the record
of what was authorized; it is not an invitation to repeat it.

In the already authorized existing Researcher main chat, perform **one tiny,
no-market, no-trade diagnostic model turn** with the currently configured
provider/model and the host's actual documented tools. Discover the installed
native task and read-only command tool schemas; create at most one small task
only if those schemas support it, with a fixed non-secret synthetic page and a
short model-authored response. Preserve the installed OpenBot version and
sanitized, read-only app/provider records showing: parent session and turn;
exact submitted task arguments and acknowledged task ID; child session, actual
provider and model; every complete model-visible page/tool output; and the
exact final response and tool actions. Record byte lengths and hashes alongside
retained bytes so truncation and attribution can be checked independently.
Exclude credentials and private conversation content. If any required record is
missing or a tool cannot expose it, stop there and report that exact boundary;
do not retry an uncertain task or change permissions, providers or settings.

This is a diagnostic evidence collection, **not acceptance of the current
runner**. The actual host records must first justify a narrowly scoped OpenCode
attester and safe transport, with adversarial offline tests. Only after that
work is reviewed and published can the following acceptance sequence proceed:
fast-forward the clean existing feature branch to its approved commit; render,
install and verify the existing orchestration skill through the established
owner-approved procedure; run setup preflight; execute one synthetic paged
Discovery task; independently replay its provider and app evidence; then run
a separately observed archived two-stage test. Keep `trade_authorization=false`.
Each step stops on an unsupported schema, identity mismatch, incomplete pages,
forbidden operation, or missing independently attributable receipt. A pass for
one provider/version/model is not qualification of a different one or of live
market sources.
