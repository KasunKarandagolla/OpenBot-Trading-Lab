Session 5.5: narrow source-qualified causal nominations, public depth/OI and repair work; **PARTIAL**, integration gates still open. See [acceptance matrix](SESSION_05_5_RUNBOOK.md).

# OpenBot Market Researcher — Implementation References

These are the **approved design and implementation references** for the *external-first, read-only* market-discovery workstream. They are design/plan inputs, **not claims that the system has been coded, all providers qualified, or trading performance established**.

1. [`OpenBot_Final_External_First_Market_Discovery_Blueprint.md`](./OpenBot_Final_External_First_Market_Discovery_Blueprint.md) — primary architecture, formulas, nine families, specialist methodologies, source qualification, non-veto BTC/ETH context, on-demand operation, data contracts, validation and safety boundaries.
2. [`OpenBot_Cloud_First_GitHub_Synced_Implementation_Plan.md`](./OpenBot_Cloud_First_GitHub_Synced_Implementation_Plan.md) — six-session Cloud-first plan, GitHub synchronization and acceptance gates. Five substantive Sol sessions and an optional narrow Luna polish session are the target, not a shortcut around tests.
3. [`CODEX_SESSION_01_PROMPT.md`](./CODEX_SESSION_01_PROMPT.md) — ready-to-use first-session instruction; it requires full reading of both references and first verifies actual repository code and remote provider capability.
4. [`SESSION_02_RUNBOOK.md`](./SESSION_02_RUNBOOK.md) — historical R0 partial observation and optional import contract.
5. [`SESSION_05_RUNBOOK.md`](./SESSION_05_RUNBOOK.md) — current on-demand Local command, qualified price precursors, durable watches/gaps and explicit PARTIAL release limits.

## Source integrity

The first two files are published **verbatim** from the owner-provided attachments dated 13 Nov 2026, without altering their content. Initial attachment SHA-256 values:

```text
cf7a58fd9ed5f5d1010673406c26a405c8112b907216a47f88a9ebee1bd3d45c  OpenBot_Final_External_First_Market_Discovery_Blueprint.md
245591eea0f92cd185c51db3420043031c11c1d941f91ecdb31fd64a34e0c232  OpenBot_Cloud_First_GitHub_Synced_Implementation_Plan.md
```

## Operating rule for every future Codex session

- Verify actual repository/branch/upstream SHA; read `AGENTS.md`, these reference files and the latest `docs/implementation/PROGRESS.md` (created/updated during implementation).
- Read all applicable source/skill instructions. Do not presume older PR branches are merged.
- Start from the latest **verified GitHub push** on the approved integration branch; preserve unrelated work; never force-push or silently change `main`.
- Test, commit, push and verify remote SHA every completed increment. Document actual source coverage, missing methods, errors and next tasks.
- Keep the researcher **read-only**, external-first, scope- and timestamp-aware. BTC/ETH context informs questions, **never vetoes independently valid altcoin opportunities**.

If the actual implementation base differs from the branch carrying these docs, reconcile that explicitly and safely before writing application code.
