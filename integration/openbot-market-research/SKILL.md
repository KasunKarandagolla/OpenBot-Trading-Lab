---
name: openbot-market-research
description: Run the on-demand Market Researcher with the existing OpenBot agent and verify the research artifact.
metadata:
  version: "3.0.0"
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

3. Poll the returned job using the same fixed command prefix and
   `status --job-id JOB_ID`. Wait about 5–10 seconds between polls and share
   progress at least once per minute. At each `REVIEW_READY`, issue one
   `status --job-id JOB_ID --include-review` with `max_output_tokens:30000`.
   When it returns a complete `start_task_arguments`, call native
   `openbot.tool_call` with `name: openbot.start_task` and that exact
   `arguments` object. Preserve every byte of both field values. If the
   result is truncated, continue polling for the diagnostic artifact.
   A reservation does not count as a submission. Never resubmit a reserved
   packet. For `INLINE_AI_CORE_V1` the child receives the whole packet in its
   brief and uses no tools. Continue to poll for the final reasoning task and
   the terminal job. Historical paged jobs retain their original instructions.
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
