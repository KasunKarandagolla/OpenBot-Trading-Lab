# Phase C OpenCode boundary diagnostic — run complete, adapter not implemented

Status: **HOST EVIDENCE OBSERVED / OPENCODE COMPACT ADAPTER NOT IMPLEMENTED /
NATIVE ACCEPTANCE NOT CLAIMED**. One synthetic owner-authorized run completed on
2026-11-24. No market request, trade, production-runner call or second task was
made. `trade_authorization=false`.

## Installed host

- OpenBot `0.76.1` (`OpenBot.exe` product version).
- The diagnostic ran on the existing Researcher configured as
  `opencode/deepseek-v4.1-flash-free`, reasoning effort `high`. Permissions,
  tools, other agents and the protected `market-research-review` skill were not
  changed.
- Native tool names observed in retained OpenCode assistant records: `execute`,
  `shell`, `write`, `edit`, `grep`, `subagent`, `read`, `webfetch`, `websearch`,
  `glob`, `question`, `skill`. The native command tool is `shell`, with
  `command` and optional `workdir`, `timeout`, `background`. Its default dialect
  on this Windows host is PowerShell (`Get-Content`, `Get-ChildItem` dominate).
- Provider records are in `%USERPROFILE%\.local\share\opencode\opencode.db`
  (SQLite). Read-only `mode=ro` inspection works while the app is running from
  Windows Python. WSL readers must delegate; the WAL database is not safely
  readable across `/mnt/c`.

## Record formats observed in this run

- Both the parent and child sessions are session version `2.4.1` and write
  normalized `session_part` rows.
- `session_message` still carries `user`, `assistant`, `idle` and
  `model-switched` rows, but every assistant row in these two turns has
  `content: []`. The tool calls are not in `session_message`.
- `session_part` carries `ordinal`, `type` (`reasoning`, `tool`, `text`),
  `call_id` and JSON `data`. A tool row has `name`, `state.status`,
  `state.input`, `state.content` and `state.metadata.exit` (plus
  `state.metadata.truncated`). The `executed` field is `false` even for a
  completed call, so it is not a completion signal.
- The existing `native_app` reader consumes `session_message` assistant
  `content` and reports `OPENCODE_V2_SESSION_MESSAGE`. It sees zero tool parts
  for these turns and cannot attest them. The compact-adapter registry still
  excludes OpenCode.
- The older `2.2.5`, `2.2.6` and `2.3.0` session records remain historical
  context. They are not this run's format.

## Synthetic evidence page

- Path: `C:\Users\User\OpenBot\Shared\phase-c-opencode-boundary\page.txt`
- Bytes: `233`
- SHA-256: `e529506e6b3cff6881a02616138a50b68eba9e7ec17ed801f2f8f82ed271d798`

```text
OPENBOT PHASE C SYNTHETIC EVIDENCE PAGE v1
Page ID: PC-OC-20261124-A
Nonce: 7f3c1a9e5b2d4c60
Marker: CORAL-LANTERN-42
Check: multiply 9 by 7 and report the product.
Note: Synthetic boundary evidence only. No market data. No trading.
```

The child must compute `9 × 7 = 63`; `63` does not appear on the page.

## Observed run

### Parent turn

- Session version `2.4.1`; model
  `opencode/deepseek-v4.1-flash-free`, variant `high`; idle outcome `succeeded`.
- The turn contains four completed native tool calls, in order:
  1. `shell` — input
     `Get-Content -Raw 'C:\Users\User\OpenBot\Shared\phase-c-opencode-boundary\page.txt'`;
     status `completed`, exit `0`; output `235` bytes, SHA-256
     `ea011a591e8bd4d7c1cd64dc8fa25b36c9c74ac8e33d131230b19c8ef414461c`.
  2. `execute` — a `tools.openbot.tool_call` attempt naming
     `openbot.tool_describe`; status `completed`; output `145` bytes, SHA-256
     `46a1baa549bd893f7d428e800639343ec53ec3f8b66494dcf56003597258244e`.
     The bridge rejected the nested call with the explicit instruction to call
     `tool_describe` directly.
  3. `execute` — direct `tools.openbot.tool_describe` with exactly
     `{"names":["openbot.start_task","openbot.attach_files_to_response"]}`;
     status `completed`; output `2,341` bytes, SHA-256
     `aa370892476f450c33c99e0ed9dc3e8b14831f5481bc07df0bb9000229f7312a`.
     Both schemas were returned with the expected property sets.
  4. `execute` — `tools.openbot.tool_call` naming `openbot.start_task` with the
     exact title and brief; status `completed`; output `487` bytes, SHA-256
     `3f6f33c8f9d2f2087a1e59e71171e9eb820b99d9698b1d81791c7487fba270e6`.
     The result contained exactly one task ID and no retry.
- The final combined report after the task report was `2,584` bytes, SHA-256
  `2ced1eece6ccc3e22fcbf2626250ee4efdfacef3fc5481d5694a78cf6df3ff0f`.
- The earlier interim answer was `2,922` bytes, SHA-256
  `7be9a2e2eb0ab950e3a8f09f20e702323240d8d8e34d599a3110b06fdc15dd36`.

### Child task

- App thread title `OPENBOT-PHASE-C-OC-BOUNDARY-20261124-A`; one completed turn
  from `2026-11-24T14:16:49.610Z` to `2026-11-24T14:17:07.393Z`; provider
  `opencode`; model `opencode/deepseek-v4.1-flash-free`; effort `high`.
- Provider session version `2.4.1`; same model; idle outcome `succeeded`.
- Exactly one tool call: `shell` with the same exact command; status
  `completed`, exit `0`; output `235` bytes, SHA-256
  `ea011a591e8bd4d7c1cd64dc8fa25b36c9c74ac8e33d131230b19c8ef414461c`.
- One reasoning part and two text parts. The final answer is `220` bytes,
  SHA-256 `45d26b165b7bd746e4feebe2a360741c47ba8b617acf0c5e6af328fd1bcafbb5`.
  It reports `PC-OC-20261124-A`, nonce `7f3c1a9e5b2d4c60`, marker
  `CORAL-LANTERN-42` and `9 × 7 = 63`.
- No `write`, `edit`, `read`, browser, web, market-data or trading tool call
  exists in the child session.

### Binding and scope

- The app projection and provider records agree on the task title, provider,
  model, effort, turn window, child final answer and completion.
- The child's shell output is the `233`-byte page plus the trailing CRLF, giving
  `235` bytes; parent and child hashes are identical.
- The only tool names in the parent are `shell` and `execute`; the only child
  tool name is `shell`. No market-data or trading operation appears.
- One task was submitted once. The bridge returned one task ID and the child
  produced one final answer.

## What the host proves

- The installed OpenCode host executed the exact read-only PowerShell command in
  both the parent and the child, and both outputs match the fixed page.
- The model discovered both requested schemas inside the parent turn and
  submitted the exact title and brief once; the bridge acknowledged exactly one
  task.
- The child session, turn, provider, model and final answer are attributable and
  the child performed exactly the one permitted shell read.
- No market-data request, trade or production-runner call occurred in either
  recorded session.

## What it does not prove

- It does not prove a top-level native `openbot.start_task` provider tool call.
  The task call is nested inside the native `execute` Code Mode tool; the
  provider record shows the exact code and result, not a separate provider tool.
- It does not prove that the existing Codex-shaped verifier accepts OpenCode.
  `attest_smoke_discovery` reads Codex `response_item` / `item_completed`
  records and would not parse these `session_part` rows.
- It does not prove paged or compact transport, page ordering, complete
  multi-page delivery, a production review receipt or final-delivery proof.
- It does not prove OS-level child isolation. It proves the recorded child
  session used one shell call and no other tool.
- It is not native acceptance of the current runner or of any market capability.

## Next gate

Implement a narrowly scoped `OPENCODE_V2_SESSION_PART` reader and attester that:

1. binds the parent session, turn and configured model;
2. matches one completed `execute` call whose code invokes
   `tools.openbot.tool_describe` with exactly the required names and whose
   output contains both schemas;
3. matches one completed `execute` call whose code invokes
   `tools.openbot.tool_call` with `openbot.start_task` and the exact title and
   brief, and whose output acknowledges one task;
4. binds the task thread, child session, child turn, model and final answer;
5. verifies the child's one read-only `shell` call and exact output; and
6. fails closed on duplicate tasks, wrong schemas, earlier-turn discovery,
   unexpected tools, truncated output or model mismatch.

Add adversarial offline tests for each failure. Do not add OpenCode to
`COMPACT_ADAPTERS` or claim acceptance until that reader is reviewed and
published. The next real acceptance run must be separately authorized; this
diagnostic is transport evidence only.

## Owner action performed

The owner selected `opencode/deepseek-v4.1-flash-free` on the existing
Researcher, sent the prompt below once, and preserved the turn and task. No
permissions, tools or other agents were changed.

## Prompt

```text
OPENBOT PHASE C OPENCODE BOUNDARY DIAGNOSTIC — ONE RUN ONLY

This is a synthetic boundary diagnostic, not a production research run. Use the current provider/model and this existing agent. Make zero market-data requests and no trades. Do not use the production runner. If any step is uncertain, stop and report it; do not retry.

1. Call openbot.tool_describe with exactly {"names":["openbot.start_task","openbot.attach_files_to_response"]}. Report both returned schemas exactly, including the property names each accepts.

2. State the native command tool available in this chat (expected name: shell) and its input fields. Then use it once, read-only, with exactly:

Get-Content -Raw 'C:\Users\User\OpenBot\Shared\phase-c-opencode-boundary\page.txt'

Report the exact command, exit status and complete output. Do not write, create or modify any file.

3. Create exactly ONE task with openbot.start_task using this exact title and brief:

Title: OPENBOT-PHASE-C-OC-BOUNDARY-20261124-A
Brief:
This is a synthetic boundary diagnostic. Use the read-only shell tool to run exactly:
Get-Content -Raw 'C:\Users\User\OpenBot\Shared\phase-c-opencode-boundary\page.txt'
Read only that file. Do not write, browse, use the web, call the production runner, request market data, or trade. Then reply in at most 80 words with the page ID, the nonce, the marker, and the product the page asks you to compute.

Copy the complete openbot.start_task result verbatim, including any task or thread identifier. If the submission outcome is uncertain, stop; never submit or request a second task.

4. When the task report arrives, report in one message: the discovery output; the parent shell command, exit status and complete output; the exact title and brief submitted; the complete start_task result; the child's complete final answer; and confirmation that no market data or trading occurred. Do not claim native acceptance.
```

## Collection performed

Read only: app DB `%APPDATA%\OpenBot\openbot.db` and provider DB
`%USERPROFILE%\.local\share\opencode\opencode.db`, both `mode=ro` from Windows
Python. The parent was matched by its owner turn and the child by the
acknowledged task title/ID and agent thread. This document publishes only
sanitized hashes, byte lengths, chronology and field shapes; it contains no raw
provider session IDs, credentials or unrelated chat text. No raw extract or
temporary file was written.
