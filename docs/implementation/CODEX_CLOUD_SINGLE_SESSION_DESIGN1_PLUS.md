# Codex Cloud — One-session implementation brief
## Design 1+ AI reasoning orchestration and M32/M33 shadow expansion

**Status:** Owner-requested implementation plan; repository documents published, code migration not yet implemented or native accepted.
**Branch:** feature/external-first-market-researcher; PR #24 remains draft.
**Canonical new blueprint:** OPENBOT_DESIGN1_PLUS_AMENDED_BLUEPRINT_2026-11-23.md
**Method companion:** M32_M33_WYCKOFF_CRT_TBS_SPEC_2026-11-23.md
**Full methodology reference:** references/ANALYTICAL_METHOD_EXPANSION_PROPOSAL_2026-11-14.md
**Original authority:** OpenBot_Final_External_First_Market_Discovery_Blueprint.md and AI_CORE_DECISION.md.
**One session goal:** Ship the smallest robust, testable Design 1+ implementation *if the actual installed tool contract supports the required parent-turn data-submission mechanism*, plus safe M32/M33 research-only SHADOW capability when engineering budget permits. Never claim live acceptance from Cloud.

---

## STEP 0 — mandatory contextual understanding BEFORE ANY CODE EDIT

1. Fetch the correct GitHub branch and verify actual HEAD and clean checkout. Do not assume main includes the feature branch. Never force push or merge PR #24.
2. Read in full (not merely filenames, excerpts or this summary):
   - root AGENTS.md;
   - docs/implementation/README.md;
   - docs/implementation/OpenBot_Final_External_First_Market_Discovery_Blueprint.md;
   - docs/implementation/AI_CORE_DECISION.md;
   - docs/implementation/OPENBOT_DESIGN1_PLUS_AMENDED_BLUEPRINT_2026-11-23.md;
   - docs/implementation/M32_M33_WYCKOFF_CRT_TBS_SPEC_2026-11-23.md;
   - docs/implementation/references/ANALYTICAL_METHOD_EXPANSION_PROPOSAL_2026-11-14.md;
   - current docs/implementation/PROGRESS.md relevant current entries and dispatch recovery;
   - installed skill source and applicable current session/native test docs;
   - all relevant implementation code and tests, including runner, native_handoff, native identity, native_codex, native_app, native_runtime, ai_core, discover/screening, method registry/config.
3. Before implementation write a concise **Context Acceptance Receipt**: exact commit, consulted document SHAs/paths, precedence, source statuses, current module map, supported vs unproven contracts, estimated narrow code changes, and preserved invariants.
4. Understand owner intent: genuine AI discovery and final comparison; external-first numeric evidence; no formula-by-LLM or subjective data invention; existing agent only; no new mandatory messaging controller; future method extensibility without source/engine rewrite.

Do not permit editing application code if Step 0 is incomplete.

---

## STEP 1 — capability and forensic gates: no speculative transport

A. Read-only repository and installed/native interface contract inventory. Identify whether the existing OpenBot main-chat command tool can:
- read a fixed-path/hash-checked evidence page within observable limits;
- transmit *model-authored* structured response bytes safely to a deterministic Python validator;
- preserve dynamically submitted JSON via documented tool arguments, stdin or an owner-approved constrained file route without constructing long shell-quoted commands;
- expose sufficient provider turn/tool/output records to independently validate actual model, page reads, response and no forbidden actions;
- maintain one or two stages in one main turn or support a safe separately authorized continuation;
- enforce actual owner authorization and provider/model identity.

Do not assume standard input is supported; OpenBot tooling must establish its schema. Inspect upstream source and pinned installed-version evidence if available. Cloud documentation alone is NOT installed proof.

B. Read-only incident III investigation only if original host/parent event records are available; classify first proof/end-marker mismatch using canonical encoding, SHA, length, first offset and timestamps. Do not claim root byte from the error code alone.

C. Select exactly ONE minimum supported new transport path. If the indispensable submit/attest boundary is unsupported or cannot be demonstrated by isolated tests, **stop the core integration work** and report a short explicit blocker and recommended smallest owner-side probe. Do not replace it by another large untested relay or alter Local Scripts permissions. Never invent an acceptance receipt.

---

## STEP 2 — narrow Design 1+ implementation, iff Step 1 permits

Implement the smallest coherent path using existing Python modules and existing agent/skills:

1. Add versioned new protocol ID for new jobs. Leave historical native child records and replay intact; never reinterpret old job as this protocol.
2. Parent starts/reads a job using stable installed command root. No parent-generated 32-hex job ID or reconstructed WSL path. Start/status/page/finish are idempotent/read-only where appropriate.
3. Immutable qualified evidence with hash, page count, citations, exact source scope and known_at/available_at; model sees bounded pages and gets a very small repeatable status. No base64 echo, no z_end_frame authorization ritual, no parent-controlled publication-to-grant deadline, no pre-consumption one-shot reserve.
4. Authenticated owner-bound run state with one active provider/model snapshot, one accepted stage result per stage, same-content retry idempotency, conflicting-content rejection, prompt-tool allowlist, no trading authority.
5. Real AI DISCOVERY invocation from original broad qualified evidence BEFORE costly targeted history; preserve complete nomination/omission ledger and model's ability to ask counter-hypothesis/source questions.
6. Accepted DISCOVERY directs permitted deterministic inquiry with actual source/contract/interval/type, bounded research budget and UNKNOWN for unavailable source.
7. Separate real AI SHORTLIST decision on qualified investigated facts, citations and objective economic/room/clock gates; legitimate zero shortlisted; model may choose a better-supported rival family where independently qualified.
8. Independent read-only provider-turn attester (initial Codex only) proving actual expected model/session, page outputs, submitted reply and no forbidden actions. Do not treat a model-supplied hash or fixture-shaped JSON as provider receipt.
9. Safe checkpoint/partial states, independent artifact ZIP and separately verified attachment/delivery. No new standalone event bus/Local Scripts controller.
10. Adapt existing SKILL.md in-place preserving installed skill identity/revision history. Do not silently assume a repo file update installs a new skill on the owner's host.

Use existing reusable types and validators. Remove code in *new path* that only exists to make LLM echo control bytes; keep legacy read-only replay if tests require it. Do not overengineer a new complete state service. If test results do not prove the new transport, mark CODE_IMPLEMENTED/OFFLINE_VERIFIED, not NATIVE_BOUNDARY_VERIFIED.

---

## STEP 3 — rigorous tests against actual risks

Minimum offline tests:
- fixed path/root, idempotent start/page/finish and no stale reconstructed commands;
- exactly one accepted stage, duplicate accepted same bytes, conflicting second rejected;
- malformed submit JSON, absent/invalid citation, wrong material id, unsupported alternate family;
- full bounded page receipt, clipped model-facing output, missing/late page, unexpected tool action;
- actual clock isolation: old archived material remains archived; live closed-bar freshness still gated;
- workspace/session/agent/model identity mismatch and unsupported provider format fail;
- proof that both accepted stages are real provider-turn dependent, not mock-verified;
- existing AI Discovery vs final Shortlist ordering and question-driven investigation;
- source undercoverage, quiet-tail, no BTC veto, zero-valid-candidate reporting and no trading;
- historical original native child replay still works under its old protocol;
- one synthetic STOP/partial/recovery path plus preservation of source and artifact.

Cloud can only test local mocks/serialized transports. Record this boundary explicitly. The first real owner-side native certification MUST be a tiny no-market, no-trade authorized model turn, not a complete archived/live smoke. Do not ask for repeated 180-second retries without first locating exact failure boundary.

---

## STEP 4 — M32/M33 Wyckoff & CRT+TBS, in priority order

Only after the core path is stable under offline tests, implement the highest-value parts of the in-depth companion and source reference:
1. Read the **full** 14 November proposal sections D/E/F/G/H/I/J/K/L/M/N/O before translating formulas.
2. Register M32 WYCKOFF-TR-LIFECYCLE-v0 and M33 CRT-TBS-BODY-FAIL-v0 as SHADOW/TRIAL, retaining M01–M31 and the existing M12 CRT / M05 sweep IDs and behavior.
3. Reuse existing preknown references and immutable causal event roots. Add a minimal optional version/variant/source-qualified interpretation schema only if not already represented.
4. Implement source-aware, closed-bar, non-repainting selected-symbol predicates and state transitions (M32 separated range tests, spring/UTAD, effort/result UNKNOWN handling; M33 prior completed 4H parent, separate later closed 5M outside/reclaim, no post-hoc parent).
5. Reuse external-first nomination and targeted verification; do not implement a second whole-market scanner or local 5M candle warehouse.
6. Add rival/F1–F9 and shared-event/double-count controls; the AI should compare formation and uncertainty, not automatically rank patterns as profitable.
7. At minimum implement a deterministic synthetic temporal oracle matrix for each method, positive/negative/missing/source-limited/append-future, plus a baseline old-method regression.
8. Keep all new outputs in SHADOW or QUESTION_ONLY, never falsely announce source-qualified full-universe detection. Gate first-class admission behind independent host/provider source tests and a later owner decision.
9. A method may have weeks-old HTF context but must show a fresh decision relevant to the <=15-hour future research horizon. No executable entry/SL/TP, no investment-profit claim.

If the session cannot safely complete both transport and methods, prioritize the AI boundary and publish the precise remaining M32/M33 gates and test source. Do not ship partial method flags as live-qualified.

---

## STEP 5 — commit, CI, acceptance handoff and release truth

- Run targeted regressions, full unit suite where feasible and researcher config validation; do not suppress failing tests or call skipped tests passed.
- Keep original blueprint and archived implementation plan byte-identical.
- Commit and push to feature/external-first-market-researcher only; no force push, no merge main, no new PR. Verify remote HEAD and CI.
- Update PROGRESS.md with scope, model/market calls (Cloud expected zero), actual tests, independent failure classification, source status, M32/M33 shadow status, true blocked items and the **single smallest owner-host native acceptance action**.
- Provide module-by-module change inventory, exact SHA, explicit nonimplemented requirements, measurable remaining integration risk and whether the current installed Researcher skill still needs approved revision registration.
- Never claim task completed if the native owner-host gate remains open.

**Red flags requiring STOP and owner decision:** unproven stdin or untrusted file-message route; unverified installed OpenBot task API; new privileges or model/provider/key changes; invented native execution receipt; attempt to bypass Binance 451; long encoded confirmation ceremony recreated; unbounded source requests; mandatory unapproved Live Scripts controller; fake source-qualified Wyckoff/CRT/TBS; model hard-coded back into optional formatter role.

**Success definition:** one clean implementation branch with concise auditable code, real offline tests and a tiny deterministic owner-host certification instruction. If the native boundary is not proven, do NOT call it released. One Codex Cloud session may do all code work but cannot magically perform a native request on the owner's absent Windows/OpenBot host.
