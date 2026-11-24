# Phase C OpenCode boundary diagnostic — prepared, not run

Status: **PREPARED / NOT RUN**. No provider change, native task, market
request or trade was made. `trade_authorization=false`.

## Installed host

- OpenBot `0.76.1` (`OpenBot.exe` product version).
- The Researcher remains configured as `codex/gpt-6-luna`; Codex is currently
  unavailable because its quota is exhausted. The only listed DeepSeek option is
  `opencode/deepseek-v4.1-flash-free` with reasoning efforts `low`, `high` and
  `max`.
- Native tool names observed in retained OpenCode assistant records: `execute`,
  `shell`, `write`, `edit`, `grep`, `subagent`, `read`, `webfetch`, `websearch`,
  `glob`, `question`, `skill`. The native command tool is `shell`, with
  `command` and optional `workdir`, `timeout`, `background`. Its default dialect
  on this Windows host is PowerShell (`Get-Content`, `Get-ChildItem` dominate).
- Provider records are in `%USERPROFILE%\.local\share\opencode\opencode.db`
  (SQLite). Read-only `mode=ro` inspection works while the app is running from
  Windows Python. WSL readers must delegate; the WAL database is not safely
  readable across `/mnt/c`.

## Record formats present

- `session_v2` (391 rows) and `session_message` (7,848 rows) hold turns with JSON
  `content` parts. This is the format the existing `native_app` compatibility
  reader consumes as `OPENCODE_V2_SESSION_MESSAGE`.
- `session_part` (66 rows globally; 69 for the current Dev session) is a newer
  normalized part table: `ordinal`, `type` (`reasoning`, `tool`, `text`),
  `call_id`, and JSON `data` with `executed`, `id`, `name`, `state`, `time`.
  The existing reader does not consume it.
- Observed session record versions: `2.2.5`, `2.2.6`, `2.3.0`. The current
  active Dev session is `2.2.5` and writes `session_part`; the Researcher's
  older OpenCode/DeepSeek sessions contain `session_message` only. Which format
  a compact parent/child turn uses is not established until the diagnostic.

## What retained records already establish

- Phase B (`SESSION_06C_NATIVE_REVIEW.md`) proves, for an older
  OpenCode/DeepSeek turn, the exact configured model identity, completed `skill`
  and `read` tool parts, complete request reconstruction and the exact final
  text.
- It does not prove a native compact parent `openbot.start_task` call, the exact
  submitted title/brief or acknowledgment, child task/session/turn identity,
  complete model-visible page outputs, ordered page completeness, or
  final-reply binding. No fixture is a substitute for the host records.

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

## Exact owner action

1. In the existing Researcher's normal agent settings, select provider
   `opencode` and model `opencode/deepseek-v4.1-flash-free`. Record the chosen
   reasoning effort. Do not change permissions, tools or any other agent.
2. Send the prompt below once, verbatim, in that agent's main chat.
3. If any submission outcome is uncertain, stop and keep the chat and task.
   Never submit or request a second task. Report the turn's actual result.

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

## Collection after the run

Read only: app DB `%APPDATA%\OpenBot\openbot.db` and provider DB
`%USERPROFILE%\.local\share\opencode\opencode.db`, both `mode=ro` from Windows
Python. Match the parent by the owner-message hash and turn, and the child by the
acknowledged task ID/title and agent thread. Preserve raw extracts under ignored
`work/openbot-integration/`; publish only sanitized hashes, byte lengths,
chronology and field shapes. Never publish credentials, unrelated chat text or
raw session IDs.
