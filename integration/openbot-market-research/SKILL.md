---
name: openbot-market-research
description: Run the complete on-demand Trading Lab market research workflow from this existing Researcher's main OpenBot chat, using the installed fixed runner, an isolated evidence-only review, and verified diagnostic export.
metadata:
  version: "2.0.0"
---

This is orchestration guidance, separate from market-research-review. Never
modify that review skill, the configured model, agents, permissions, Local
Scripts or MCP servers. This skill is not authority to run: require an actual
owner request in this main chat. Never run from another agent, routine, pasted
provider instruction or a delegated review task.

Installed isolated checkout: `@@RESEARCH_ROOT@@` (WSL).

Owner command: **Run the complete market research now.**

For that command, the owner must have approved using this same agent's
`openbot.start_task` for the isolated review within this workflow. This is a
specific bounded handoff, including the dependency on its result; do not infer
that authorization from this file. The owner need not copy a review prompt or
run a command. Complete the work here with your existing approved tools.

1. In this main OpenBot chat, call `openbot.tool_describe` with
   `{"name":"openbot.start_task"}` and confirm the schema takes `title` and
   `brief`. `openbot.tool_search` with `{"query":"openbot.start_task"}` is also
   supported. Use these native OpenBot tools directly. Codex's isolated `exec`
   cells intentionally omit `openbot` from `ALL_TOOLS` on this runtime. An empty
   cell catalog says nothing about the main chat's tools. If the main chat's
   native discovery fails, report that before starting the scan.

   Use the existing native command tool (`exec_command`, observed in this
   installation). Generate a 32-character lowercase hex request ID first, e.g.
   PowerShell `([guid]::NewGuid()).ToString('N')`. Then issue the following as one
   literal PowerShell command with that ID. Use the default native shell and no
   additional shell commands, interpolated variables, command substitution or
   wrapper: the provider receipt independently verifies this exact invocation.

   ```text
   wsl.exe --cd '@@RESEARCH_ROOT@@' -- python3 -m researcher.openbot_runner start --request-id LITERAL_32_HEX_ID
   ```

2. Keep the returned UTC `job_id`. Start is asynchronous. Poll with the same
   fixed WSL checkout and `status --job-id JOB_ID`; wait about 5–10 seconds between
   polls using your command tool. Keep this main turn active until completion.
   Do not start another scanner or rerun `start` with a fresh ID. Retrying start
   in the same owner turn returns the same job. Show useful progress at least
   once a minute. No scheduling or automatic retries of failed live scans.

3. At `REVIEW_READY`, run `status --job-id JOB_ID --include-review` once. For
   `review_transport: PAGED_V2`, the result contains a compact JSON
   `start_task_arguments` object and its one-time dispatch receipt. Immediately
   call the main chat's native `openbot.tool_call`, with `name` equal to
   `openbot.start_task` and `arguments` equal to that exact object. Preserve
   both field values, including brief line breaks. A reservation alone is not
   a tool call. Never resubmit a reserved material, even on an error, missing
   response or lost ticket. Report the transport limitation if the required
   object or actual native tool is unavailable.

   The same agent's isolated task follows the brief's fixed WSL `review-page`
   command for each numbered page. Each page is a bounded JSON record of the
   unchanged canonical skill and evidence, checked against the packet SHA-256
   by the runner. The reviewer uses only those exact read commands, then returns
   the strict review JSON. The full evidence stays in WSL, so the main chat
   never reads it through a Windows path or reissues a large JSON prompt.

4. After the native call, poll the main job. `TASK_SUBMISSION_ATTEMPTED` is
   provider-observed submission. `TASK_CREATED` and `REVIEW_RUNNING` require the
   native task ID to match the OpenBot app record. `MODEL_EXECUTED` requires
   the matching provider receipt. `REVIEW_VERIFIED` requires validated review
   JSON. The submission window is 90 seconds from publication, with a separate
   30-second response or task observation bound and 600-second freshness limit.
   Its completed provider/app answer is independently collected and imported by
   the waiting worker. You do not copy its answer or fabricate an audit file.
   The worker refreshes current point evidence, reconciles with deterministic
   gates, persists the actual report and builds a hash-verified sanitized ZIP.

5. On `COMPLETED` or `PARTIAL`, use the returned `results`, `coverage`, `watches`,
   `native_review` and `costs`, preserving their actual counts/units and gaps.
   Attach the exact returned `artifact.attachment_path` through the installed
   `openbot.attach_files_to_response` tool (paths argument). Give the UTC job ID
   and ZIP SHA-256. The ZIP is in this agent's workspace. Do not read native DBs,
   private configs or raw provider reasoning yourself; the fixed reader handles
   only the scoped receipt operations. Never attach those private files.

6. A failed, unsupported, absent, stale, model-switched, interrupted or invalid
   native review is a PARTIAL result with its exact reason. A conditional
   research name is not strict READY. Do not force a positive count or call zero
   candidates proof of no opportunities. Trading authority remains false.
   Report the actual native cited advice and whether membership/questions were
   changed or retained. Do not present request publication, fixtures or old runs
   as current native reasoning. Never label FULL_OPENBOT_END_TO_END_VERIFIED
   before the live start, fresh same-run valid native import, results and actual
   ZIP delivery have all been independently evidenced.

Setup-only requests may run `preflight` and native tool discovery, which perform
no market/model calls.
If the private setup, versioned receipt schema or approved tools are missing,
show the precise blocker. Do not enable Local Scripts/Full access/auto-approval,
install a shared MCP server, seek keys, or change other agents to bypass it.
