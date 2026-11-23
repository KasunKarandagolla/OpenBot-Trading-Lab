# AI-core native-only acceptance

Use the existing Windows/WSL Researcher installation and its private
path-only audit configuration. The smoke uses retained Session 5 observations,
runs both production AI stages and makes zero market-data requests. The owner
authorizes it with the commit-bound message below. The Cloud implementation
and CI involve no real OpenBot tasks.

## Prepare the exact published checkout

On the existing WSL checkout, verify a clean tree. Fetch the feature branch
and fast-forward the local branch to the SHA published in PR #24. Confirm the
SHA with `git rev-parse HEAD`. Use the existing registered Researcher workspace,
its Codex provider and the owner-configured model.

Update the existing `openbot-market-research` skill with the checkout's
`integration/openbot-market-research/SKILL.md`, replacing
`@@RESEARCH_ROOT@@` with the absolute WSL checkout path. Use the protected
skill installation procedure in [Native handoff v2](NATIVE_HANDOFF_V2.md), with
the orchestration source hash set to
`1386fa4ec69eb4dffc27ae5713832dea699515f4fdf66cb4456f0057bbbf7530`.
Keep the existing `market-research-review` skill. Its hash in that procedure
still applies. The pinned checkout supplies the staged methodology guide and evidence
through bounded, hash-checked child reads.

## Copy the canonical owner instruction

From the pinned checkout, render the single authorized message:

```bash
sed "s/@@APPROVED_COMMIT@@/$(git rev-parse HEAD)/g" docs/implementation/OPENBOT_AI_CORE_SMOKE_PROMPT.txt
```

Paste the output as one message in the existing Trading Lab Market Researcher's
main OpenBot chat. Allow that turn to finish and attach the ZIP. A partial result
is diagnostic evidence. Use the returned job ID with a local read-only audit
after the main response has been saved:

```bash
python3 -m researcher.openbot_runner replay-native --job-id JOB_ID
```

Acceptance requires two independently verified child receipts for
`DISCOVERY` and `SHORTLIST`, one confirmed reservation per stage, exact native arguments and complete
provider-attested page delivery, accepted citations, `AI_RESEARCH_COMPLETE` in the archive reconciliation, zero market
requests, a verified archive, and `VERIFIED` delivery. An empty qualified
shortlist can pass. The result is archived only.

The preview is repeatable before reservation. Each first grant permits one
call to the native task tool. If the grant result is clipped or uncertain,
continue polling the job and keep the artifact. A duplicate grant response
cannot authorize a submission.

## Rollback

If the smoke fails, retain its job ID, source and artifact. Use the bounded
read-only replay above to capture the first failure. For a runtime rollback,
create a separate clean worktree at
`7fd0865c062889b228b9d0a1a336173f104ee8a1` and reinstall its orchestration skill
with that checkout's path and original hash from Native handoff v2. Keep the
published branch and both job directories intact. Run setup-only preflight
against the intended checkout before authorizing another task.
