---
name: openbot-market-research
description: Run the on-demand Market Researcher with the existing OpenBot agent and verify the research artifact.
metadata:
  version: "5.0.0"
---

Installed isolated checkout: `@@RESEARCH_ROOT@@` in WSL.

Only an actual owner request in this agent's main chat authorizes a run.
**Run the complete market research now.** authorizes the ordinary workflow
once the owner has approved the two bounded native tasks through the existing
agent. An exact commit-bound archived smoke prompt authorizes archived replay
only. Keep the existing provider, model, agent, permissions and trading controls.

1. In the current main-chat turn use native `openbot.tool_describe` with
   `{"names":["openbot.start_task","openbot.attach_files_to_response"]}`.
   Check that the tools accept `title` and `brief`, and `paths`, respectively.
   Discovery must occur in the same turn that runs the step 2 start command.
   Repeat it after any host continuation, owner steer or retry; discovery in an
   earlier setup turn does not authorize this run. These tools are available
   in the main chat. An isolated Codex exec catalog does not expose them.
   Report missing tool discovery before running.
2. Generate one lowercase hexadecimal request ID of length 32. Use the native
   command tool with the default shell and this exact literal PowerShell
   command. Substitute the literal ID. The provider verifies this invocation.

   ```text
   wsl.exe --cd '@@RESEARCH_ROOT@@' -- python3 -m researcher.openbot_runner start --request-id LITERAL_32_HEX_ID
   ```

3. The start response includes `status_command`. Copy it verbatim for
   every poll, with no change to the checkout path. Wait 5–10 seconds between
   polls and share progress at least once per minute. For new AI-core tasks,
   ordinary status issues one `OPENBOT_COMPACT_DISPATCH_V1` object at
   `REVIEW_READY`. Require `submission_permitted: true`, complete
   `start_task_arguments`, and `end_frame: END_OPENBOT_COMPACT_DISPATCH_V1`.
   Submit those exact arguments once through native `openbot.tool_call` to
   `openbot.start_task`. Preserve the brief newline and do not reconstruct a
   command or path. If the object is clipped or submission is uncertain, stop
   and report it; never submit or request the task again. Subsequent status
   polls do not authorize another task. The child uses the bounded evidence
   commands in its brief. Historical jobs retain their original instructions.
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
