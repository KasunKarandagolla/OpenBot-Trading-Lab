---
name: openbot-market-research
description: Run the on-demand Market Researcher with the existing OpenBot agent and verify the research artifact.
metadata:
  version: "4.0.0"
---

Installed isolated checkout: `@@RESEARCH_ROOT@@` in WSL.

Only an actual owner request in this agent's main chat authorizes a run.
**Run the complete market research now.** authorizes the ordinary workflow
once the owner has approved the two bounded native tasks through the existing
agent. An exact commit-bound archived smoke prompt authorizes archived replay
only. Keep the existing provider, model, agent, permissions and trading controls.

1. In the main chat use native `openbot.tool_describe` with
   `{"names":["openbot.start_task","openbot.attach_files_to_response"]}`.
   Check that the tools accept `title` and `brief`, and `paths`, respectively.
   These tools are available in the main chat. An isolated Codex exec catalog
   does not expose them. Report missing tool discovery before running.
2. Generate one lowercase hexadecimal request ID of length 32. Use the native
   command tool with the default shell and this exact literal PowerShell
   command. Substitute the literal ID. The provider verifies this invocation.

   ```text
   wsl.exe --cd '@@RESEARCH_ROOT@@' -- python3 -m researcher.openbot_runner start --request-id LITERAL_32_HEX_ID
   ```

3. Poll the same job with `status --job-id JOB_ID` every 5–10 seconds and
   share progress at least once per minute. For each `REVIEW_READY`, run
   `status --job-id JOB_ID --include-review`. For
   `CONFIRMED_AI_CORE_PAGES_V2`, require the entire JSON frame, including
   `begin_frame`, the whole `start_task_arguments`, `reserve_command_prefix`
   and `z_end_frame`. If it is clipped or incomplete, report it with
   `reserve-review --job-id JOB_ID --material MATERIAL_SHA256` using the same
   fixed WSL prefix and no confirmation flags. A preview can be read again
   before a reservation and within the window. Keep the same job and stage.
   With a complete frame, run the literal `reserve_command_prefix` followed
   by one space and the exact `z_end_frame` value. Wait for
   `submission_permitted: true` and check its `arguments_sha256` against the
   same preview. Then call native `openbot.tool_call` once, with
   `name: openbot.start_task` and the preview's exact `start_task_arguments`.
   Keep the brief's newline. A repeat poll or duplicate reservation does
   not grant permission. Continue polling for the next stage and terminal
   result. The child follows the task's bounded, read-only evidence commands.
   Historical paged jobs use their original one-time dispatch instructions.
4. A task appearing in OpenBot is not model proof. The runner checks the
   acknowledged task ID, configured provider/model, exact app and provider
   input, final output, citations, and tool use. Discovery can direct approved
   targeted measurements. Final decisions must pass source, clock, room and
   economic checks. Return the actual AI stage statuses and review coverage.
   On partial failure report the exact reason. On an empty shortlist describe
   the reviewed scope. Keep `trade_authorization=false`.
5. At a terminal state attach the returned `artifact.attachment_path` with
   `openbot.attach_files_to_response`. Give the job ID and ZIP SHA-256 in
   the final response so the observer can verify delivery independently.
   For archived smoke use the actual archived statuses and zero market
   requests. Keep the main turn active until the artifact is available.

Setup-only requests may run `preflight` and tool discovery. Do not read
private native storage directly, request credentials, install shared tools or
alter agent settings. The scoped reader checks the existing installation.
