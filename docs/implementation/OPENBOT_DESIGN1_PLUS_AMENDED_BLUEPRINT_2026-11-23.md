# OPENBOT TRADING LAB
# Design 1+ — AI-Led Market Researcher and Minimal Deterministic Orchestration
## Authoritative additive architecture amendment

**Architecture ID:** AMEND-2026-11-23-DESIGN1-PLUS  
**Decision date:** 23 November 2026  
**Status:** OWNER-SELECTED ARCHITECTURAL DIRECTION; IMPLEMENTATION AND NATIVE ACCEPTANCE NOT YET VERIFIED  
**Frozen implementation baseline:** feature/external-first-market-researcher at 79f14742d9f08e62ab7eb365dfd0b8dc5c6944dc; draft PR #24  
**Scope:** Market Researcher, read-only opportunity discovery, bounded investigation, AI-led shortlisting, and independently verifiable handoff  
**Method companion:** M32_M33_WYCKOFF_CRT_TBS_SPEC_2026-11-23.md  
**Implementation-session contract:** CODEX_CLOUD_SINGLE_SESSION_DESIGN1_PLUS.md  
**No trading authorization. No live order placement.**

> Executive decision: Keep the existing OpenBot Trading Lab Market Researcher as the **real analytical intelligence** for mandatory DISCOVERY and SHORTLIST stages. Use the existing Python researcher and runner to supply immutable, source-qualified observations, enforce safe computation, store checkpoints, validate evidence and observe actual model executions. Remove the fragile model-mediated Base64 confirmation / timed reservation / routine child-task page relay from the new workflow. Prefer a minimal parent pull-and-submit interface, subject to one genuine native proof before committing the migration. Do not create a separate Local Scripts messaging controller or a new AI agent by default. Preserve a compact native child-task alternative only as a documented fallback, not a simultaneous second production orchestration path.

---

## A. Reading this amendment, precedence, and what is not being claimed

### A1. Normative sources

1. Human authorization, read-only security and explicit research-only scope take precedence over every technical suggestion.
2. The original **OpenBot_Final_External_First_Market_Discovery_Blueprint.md** remains authoritative for exchange instrument eligibility, external-first source strategy, F1–F9, M01–M31, causal evidence semantics, context, economic caution, no-trading scope, source capability status and Deep Analysis boundaries. Its original bytes and SHA-256 must not be modified.
3. The owner-approved **AI_CORE_DECISION.md**, 23 November 2026, supersedes the original blueprint's optional model pass **for this owner's current AI-core workflow**. It requires genuinely model-reasoned discovery **before** selective investigation and a genuinely model-reasoned final comparison **after** investigation.
4. **This document** amends the orchestration, evidence handoff, model/decision authority, replay, failure recovery, native verification and development sequence. The owner has selected this architecture direction. The exact OpenBot command/transport implementation is still CONDITIONAL on real installed-host evidence.
5. **M32_M33_WYCKOFF_CRT_TBS_SPEC_2026-11-23.md** provides detailed, **trial-only** Wyckoff and CRT+TBS definitions. It does not silently declare the earlier M32/M33 analytical proposal approved as proven market signal logic. Implementation into a research-only SHADOW registry is within the requested development scope; independent source qualification and owner acceptance remain required before method promotion.
6. The original implementation plan and historic runbooks remain audit records, not permission to repeat obsolete native acceptance recipes. Later audited owner decisions must be additive and versioned, never silently rewrite history.

### A2. Mandatory certainty labels

Every implementation report must distinguish:

- DESIGN_APPROVED: owner-selected intended behavior, not proof that the app supports it.
- CODE_IMPLEMENTED: code and unit/integration fixtures exist, not proof of native app operation.
- OFFLINE_VERIFIED: deterministic fixture, archived data and regression tests pass.
- NATIVE_BOUNDARY_VERIFIED: installed OpenBot executed one real, independently attested model turn with exact evidence and parsed response.
- TWO_STAGE_ARCHIVED_VERIFIED: DISCOVERY and SHORTLIST have separate authentic receipts and evidence-linked decisions on retained historical inputs.
- LIVE_SOURCE_QUALIFIED: method, source, contract and timeframe coverage have actually passed live host/oracle gates.
- PROSPECTIVE_UTILITY_VERIFIED: matched-budget forward evaluation supports incremental research usefulness.
- ECONOMIC_EDGE_UNPROVEN: default; detection and reasoning are not profitable trade evidence.

Do not promote one label into another.

### A3. Not within this amendment

No discretionary live trading; no trading keys, approvals, orders, leverage, automated execution, stop/TP placement or position management; no paid market/LLM subscriptions or direct model billing API; no new mandatory scheduler; no compulsory all-universe local 5M candle warehouse; no source-access bypass after 403/451; no rewriting unrelated Freqtrade paper-lab modules; no deployment, model/provider change, or permissions expansion without explicit owner grant. Preserve the existing Researcher identity and workspace. The first native proof uses the Researcher's actually configured, supported provider/model without changing it; no provider or model is hardcoded.

---

## B. Mission and practical user experience

### B1. User's actual vision

The Researcher should behave as a technically grounded market analyst, not an indicator voter or canned strategy machine:

1. Broadly observe the eligible Binance USDⓈ-M crypto USDT-settled perpetual universe through lawful and qualified sources; distinguish inventory, scalar snapshot, structural, specialist and targeted coverage.
2. Identify **developing** and early important structures, not simply 24-hour top returns or already-mature moves.
3. Understand 4H/1H context, 15M evolving decisions and selective 5M evidence; historical daily/weekly reference levels may be older than a proposed <=15-hour research opportunity.
4. Recognize multiple plausible professional interpretations (F1–F9, M01–M31 and later source-qualified new methods); preserve rival and no-trade hypotheses.
5. Let AI select high-value questions and request discriminating evidence through a bounded, permitted, **deterministic query executor**.
6. Let AI compare source-qualified investigated opportunities and select **zero to five** handoffs in reasoned order, including zero when nothing merits deeper attention.
7. Maintain EARLY, DEVELOPING, WATCH/APPROACHING, READY, LATE, INVALIDATED, NEAR_MISS, SOURCE_GAP and NOT_REVIEWED_BUDGET records; do not present an omitted symbol as rejected for poor quality.
8. Pass a traceable research dossier to a separate Deep Analysis capability, which is free to reject it. Market Researcher does not itself choose executable entries, stop losses or targets.

### B2. Hypothetical behavioral walkthrough

- Source data: SOLUSDT approaches a **pre-known** prior high; a completed candle moves above and closes back below. Room, spreads, exact reference age and evidence coverage are separately assessed.
- DISCOVERY AI: "F4 failed-break/sweep reversal is plausible; F2 accepted breakout and F6 rotation remain rivals; first verify closed-bar continuation/reclaim and whether the historical high was pre-known." Cite source evidence IDs. It can nominate a candidate even if the deterministic top-return rank was unimpressive.
- Runner: validates instrument, family/method, citations and available data; uses only approved history/measurement queries; records unavailable specialist flow as UNKNOWN, never false or positive.
- SHORTLIST AI: reviews the completed evidence and may choose WATCH, HANDOFF, DECLINE or UNKNOWN with explicit contradictions, remaining-room and earliest first-obstacle assessment. A valid rival may replace the earlier provisional primary family if that family independently passes formation/economic/temporal gates.
- Deterministic reconciler: enforces source honesty, freshness, exposure/deduplication and feasibility. Output remains research-only.

Nothing about the above example asserts SOL is currently near a high or that a strategy has edge.

---

## C. Existing design and observed failure lessons

### C1. Prior implementation: CODE_IMPLEMENTED at baseline, not native accepted

Existing Python modules include:
- researcher/openbot_runner.py — job start/status, worker, review reservation, state and report.
- researcher/native_handoff.py — canonical child title/brief, Base64URL proof, receipt pages and deadlines.
- researcher/native_app.py, native_codex.py, native_runtime.py, native_identity.py — native child and provider record observation.
- researcher/ai_core.py — two AI stages, reply validation, questions and final reconciliation.
- researcher/discovery.py, screening.py, source adapters, methods and ledger — market-data and structure work, with partial qualification.
- integration/openbot-market-research/SKILL.md — installed Researcher command instructions.
- Original baseline methods, source gates and docs are retained.

### C2. Incident register — do not erase causal uncertainty

| Incident | Code / job | Established immediate issue | Exact unresolved element |
|---|---|---|---|
| I | 20261123T084728Z-df41c5be1afc410796a1097cce9326d7 | Large parent-facing task JSON clipped after premature ticket creation; no usable new AI task | Real clipping layer in host tooling |
| II | 20261123T102245Z-5c1c1d4fc00c4c219bd8c63ff600f491 | Wrong WSL path, ~60.985-second gap, READY preview requested after publication deadline; no task | Cause of scheduling gap |
| III | 20261123T112418Z-863928dae53f4f53b185c4d5850b6c66 | First reserve confirmation returned NATIVE_PARENT_ARGUMENT_MISMATCH, later NATIVE_DISPATCH_WINDOW_CLOSED, zero task/model requests | First differing value/byte, whether proof, end marker, encoding, runner reconstruction, or tool transport |

Current code confirms the validator has multiple branches producing the same mismatch error. **Do not claim a specific altered character or blame the model without the original first parent command.** Keep this incident available for bounded read-only host forensics. Historic provider-record reports include a separate 21 November native child execution; do not say all OpenBot native tasks have always failed.

### C3. Root architectural issue and test deficit

The previous relay required the parent model to copy encoded arguments, reproduce paths, coordinate narrowly timed one-time confirmation, submit a matching child task, then rely on multiple child model-issued page reads. The design relied on the model behaving as an exact text-transport and timing controller. Simulated Python confirmation tests did not exercise the actual parent tool/model boundary. This is an **architecture and qualification problem**, not evidence that F1–F9 or market methodology is analytically defective.

**Hard rule:** No more "many green offline tests = native integration complete" conclusions.

---

## D. Design 1+ responsibilities: clear authority without a rigid analytical mind

### D1. AI Researcher — genuine but bounded decision authority

The same existing OpenBot Researcher performs both model turns/stages when the installed host supports the lifecycle:

- DISCOVERY: interpret supplied broad observations and contextual cards, nominate hypotheses including non-top-ranked eligible rows, state family/method/direction/stage, identify rivals and NULL, cite support/contradiction, choose permitted discriminating question(s) and time-to-decision.
- SHORTLIST: compare investigated source-backed structural cards, family rivalry, method uncertainty, source gaps, friction/room, reference validity, age, sector correlation and shared exposure. Decide HANDOFF/WATCH/DECLINE/UNKNOWN and order up to five admissible opportunities.
- A stage may legitimately yield zero. No LLM invented measurements, unsupported footprint/absorption/volume profile or institutional-intent assertions.
- The AI may reclassify a candidate's most appropriate family where the *alternative* already qualifies under its independent evidence requirements. Audit the existing ai_core.validate primary_family equality before a change: do not relax any hard gate or auto-accept every reinterpretation.
- Model-generated citations are validated against actually transmitted evidence IDs; unsupported citations/figures fail.
- The assistant may explain and challenge conflicting interpretations; do not hardcode "all sweeps mean reversal", "BTC bear vetoes bullish alts", "Wyckoff schematic implies manipulation" or "CRT means automatic short".

### D2. Python / deterministic infrastructure

Retain one existing researcher/runner implementation as the state owner. It owns:
- Stable job ID, source cutoff, approved provider/model snapshot, owner-turn authorization, stage ordering and transition receipts.
- Exact eligible exchange instrument identity, qualified providers, formula mathematics, numerical measurements, cold/closed bar and known-at/available-at/received-at chronology.
- Source coverage denominators, missingness and provenance for each method/timeframe/contract.
- Evidence materialization, immutable manifest and hash-checked page retrieval.
- Approved question allowlist, constrained targeted query execution, cost/latency/remote quota budget, targeted history cap and fact reuse.
- Stage validation, atomically accepted once-only result, idempotent read/status, safe recovery and final archive.
- Hard data/eligibility/room/friction/security gates. The model's selected opinion is not a forged data point.
- Read-only provider-turn attestation and final artifact delivery verification.

**No new standalone Local Scripts controller, no background agent swarm, no duplicate research engine and no implicit permissions escalation are required.**

### D3. Six technical planes, one minimal implementation

1. Human authorization and immutable run identity.
2. External-first source evidence and capability map.
3. Bound AI interpretation for discovery and final selection.
4. Minimal deterministic state/controller already located in Python runner.
5. Independent actual provider-turn evidence and model receipt reader.
6. Audit/research output and separately observed attachment.

Do not add distributed queues, event buses, services, new provider gateways, or human copy/paste steps unless a narrow native finding proves necessity and the owner authorizes it.

---

### D4. Provider- and model-flexible Researcher — owner clarification (mandatory)

**Architecture requirement: The Researcher's runtime provider and model are configurable choices, NEVER hardcoded implementation constants.** Design 1+ uses the **existing OpenBot Researcher agent and its current configured provider/model** at the beginning of each run. A concrete earlier run happened to use \`codex / openai / gpt-6-luna\`; that is an observed historical configuration, **not a permanent restriction, desired default, or model selection rule**.

1. **Dynamic per-run selection:** The owner may choose a different model or provider in OpenBot's supported agent settings *between runs*, without editing the researcher architecture, method definitions, scripts, prompts, or source-code constants. The controller reads the installed provider, provider account/backend (where applicable), selected exact model identifier, agent/session context and available attestation format at run start. Do **not** pass a hardcoded provider/model into the runner or force the agent back to Codex.
2. **Immutable identity inside a run:** Freeze the actual \`provider\`, \`model\`, backend/account as exposed, session/turn identity and supported adapter revision in the run manifest. Verify every stage's real recorded identity against that snapshot. A mid-run provider/model change, automatic fallback, unsupported recorder revision or wrong session must not silently produce a verified research result. A later run may use a different provider/model.
3. **Provider-neutral research core:** External-first source adapters, contract/time/source evidence, method registry, causal structures, two-stage decision schemas, citations, query planner, shortlist gates, watch states, output and security do not know or branch on a particular LLM vendor/model name.
4. **Minimal pluggable native attestation:** Isolate provider-specific turn, tool-call and response formats behind a tiny \`ProviderAttester\`/registry interface owned by the current \`native_*\` modules. At minimum define an explicit interface for \`probe_capability(config, installed_host)\`, \`identify_real_turn(expected_run)\`, \`verify_observed_evidence_reads(material)\`, and \`verify_reply_bytes_and_model(stage)\`. Prefer thin verified adapters; no new generic LLM gateway, direct paid API or separate orchestration service. Keep already implemented Codex receipt logic as one reusable adapter; evaluate OpenCode support separately from its actual installed records and official capabilities, not the presence of its name in a registry.
5. **Capability before use:** A model/provider can be *selected* in the UI without yet having a certified evidence/receipt adapter. In that case, report \`PROVIDER_ATTESTATION_UNSUPPORTED\` or a specific \`NATIVE_INTERFACE_UNQUALIFIED\` result before declaring an AI stage complete. The user should receive a clear compatibility status and smallest necessary adapter gap—not a forced switch back to Codex, invented model receipt, silent unverified execution, or claim that all providers already work.
6. **No hardcoded model text in skill/prompt:** Agent instructions describe the Researcher's analytical role, schemas and runtime discovery; they do not demand \`gpt-6-luna\` or any other fixed identifier. Provider-specific prompt/tool quirks belong only in tested adapter configuration. Model capabilities (tool IO, context, output format, token budgets) may change per selected model, so negotiate measured limits and fail clearly if unsupported.
7. **New supported provider onboarding:** Add only a small implementation-specific parser/attester with independent positive/negative native tests, preserving the existing agent and all data/evidence logic. Do **not** duplicate the research engine for each provider. New adapters may ship later if real host records are not accessible during the one Cloud session; never mask unsupported status.
8. **Provider portability acceptance:** At minimum verify (a) same selected provider/model recorded on DISCOVERY and SHORTLIST, (b) model's real input/source-page reads and generated response, (c) validity of evidence/citations and no unauthorized tools, (d) correct historical readback after user switches model between runs, and (e) incompatible/unknown provider fails closed. When available, check genuine Codex and genuine OpenCode turns independently with matching model identity, not simulated equivalent fixtures.

**Separation of concerns:** Provider/model flexibility is an **operating and adapter requirement**, not a reason to rebuild the Market Researcher, replace its identity, relax source truth or build a multi-provider abstract platform before proving one real native stage. Existing Codex-specific source is a known baseline limitation to progressively remove from orchestration assumptions, not a design choice to hardcode the Researcher's future provider.

### D5. Refactor in place — explicit prohibition on from-scratch redevelopment

**Mandatory instruction to developers:** Inspect and reuse existing \`researcher/\` modules, source adapters, evidence ledger, query planner, \`ai_core.py\`, state/receipt readers, skills, method config and tests. Map each design contract to an existing implementation BEFORE writing new code. Favor minimal in-place changes, versioned adapters and deletion of unnecessary *new-path* relay ceremonies while preserving historical replay.

- Create a **Reuse/Change Matrix**: existing file/function, what already works, evidence of tests, exact requested delta, smallest implementation step, regression and rollback. Mark unchanged modules explicitly. State why any new module is indispensable.
- **Never** create a second market scanner, a second AI reasoning engine, a parallel persistent research database, a new agent, or a general new provider-control service just because the architecture is amended.
- Keep F1–F9/M01–M31 semantics, approved two-stage \`AIResearch\`, default read-only scope, historical snapshots and native failure artifacts. Integrate M32/M33 as additive SHADOW methods in existing code.
- Keep a single versioned new-path transport rather than competing simultaneous parent/child/Local Scripts implementations. Preserve old records for read-only audit.
- One Cloud session should prioritize a verifiable working delta over quantity of rewritten code. Do not restart from initial scaffolding or reinterpret documentation publication as an instruction to rebuild the repository.
- Report \`REUSED_UNCHANGED\`, \`REFINED_IN_PLACE\`, \`ADDED_MINIMAL\`, \`DEFERRED_UNVERIFIED\` per subsystem with real tests and evidence. If an underlying capability is missing, stop at a sharply bounded gap, not wholesale reengineering.

---

## E. Candidate minimal pull-and-submit interface (requires native qualification)

### E1. Preferred minimal command shape

A fixed, previously installed command stem in the existing skill (no model-reconstructed root/path), with only bounded integers where possible:

| Operation | Behavior | Side effects / idempotency |
|---|---|---|
| start | Find/create existing owner's single active run; report tiny stage status and evidence count | No model-made request ID; idempotent for same authorized turn |
| page N | Read precomputed page N and its integrity metadata for the current stage | Read-only, deterministic, replayable |
| submit | Accept AI-authored stage JSON through an **actual installed supported channel**; validate, hash, checkpoint; no raw proof echoed | Exactly one accepted stage value; identical retry same receipt, conflicting second body rejected |
| await/status | Observe investigation readiness; capped wait that does not cause the LLM to race a publication timer | Read-only; safe repeated calls |
| finish | Return final artifact metadata, immutable job state and delivery instruction | Idempotent |
| attach | Existing supported OpenBot attachment tool; separate final visibility check | No "delivered" claim until observed |

**The above is a design contract, not proof that OpenBot currently supports STDIN submission.** The first consultation proposes stdin, but the actual shell/provider interface may not pass dynamic model-authored stdin reliably. Gate 1 must inspect the installed tool schema and demonstrate this exact path. If unsupported, choose the **smallest verified supported native submission surface**, e.g. a strictly scoped file/structured tool call with independently captured actual payload, subject to owner approval and security restrictions. Avoid free-form shell interpolation of model JSON and avoid recreating encoded confirmation tokens. Do not implement multiple hypothetical submit transports in parallel.

### E2. Desired human experience and stages

~~~mermaid
flowchart TD
  O[One owner-authorized read-only run] --> P[Existing Researcher main turn]
  P --> R[Python runner: start and frozen context]
  R --> S[Remote-first qualified observations]
  S --> E[Immutable DISCOVERY evidence manifest]
  E -->|small read-only page commands| P
  P --> D[Real AI DISCOVERY reply with citations and rivals]
  D --> V[Independent provider-turn and content validation]
  V --> Q[Selected bounded investigations, missingness and costs]
  Q --> F[Immutable SHORTLIST manifest]
  F -->|small read-only pages| P
  P --> H[Real AI SHORTLIST comparison]
  H --> X[Independent verification + hard gate reconciliation]
  X --> A[Report, watches, 0 to 5 research handoffs]
  A --> U[Owner-visible attachment and delivery observation]
~~~

A complete turn may or may not support both active stages. Verify lifecycle and context ceilings first. Do not automatically resume in a new main turn, impersonate the owner, activate Local Scripts, or broaden task permissions. If same-turn completion cannot be proven, stop at a checkpoint and propose the smallest separately authorized continuation.

### E3. Data-plane vs control-plane rule

- Model may receive *stable small* stage labels/page indices and write **its own** evidence-grounded interpretation.
- Model must NOT echo a 1–2 KB proof, manually reconstruct the filesystem root, copy an entire task argument object, manage a grant-expiry countdown or be responsible for exact delivery of unbounded text.
- A SHA-256 digest proves bytes, not person/owner identity; an echo of a digest is not a security authorization.
- The runner and independent observer prove what the model genuinely received and said from provider records, including tool-visible outputs where the supported provider exposes them.
- Source evidence can be paged, but no model turn may declare complete receipt until all required pages are independently observed.

### E4. Security and trust contract

- Owner's **actual main-chat user turn** is the only run authorization; agent-generated text is not a new owner request. Bind run to approved agent, provider/model snapshot, workspace, checkout, read-only permissions and scope.
- Record original owner-turn reference and effective grant; avoid claiming OpenBot supplies an authentication API unless independently demonstrated.
- No implicit automatic approval requests; no self-change of provider/model, agent skills, credentials or Local Scripts permissions.
- Model input may contain malicious vendor text; delimit untrusted source content as data; strict allowlist of queries and cited evidence.
- Freeze model/provider identity per run; between runs the owner may select another OpenBot-supported provider/model without changing architecture or methodology code. Verify receipt/tool evidence through the matching qualified attestation adapter. The current inspected code has Codex/OpenAI-specific limitations, which must not be enshrined as architecture defaults. An unsupported selected provider reports an explicit compatibility gap without silent fallback.
- Do not write private OpenBot database, provider rollout or session files. Read-only scoped inspection only when owner-authorized and version-verified.
- Validate payload size, filename/path confinement, role permissions, allowlisted commands, replay resistance and no trading authority.
- No claim of cryptographic owner authentication based on a local SHA-256 without a trusted identity source.

---

## F. Data contracts, exact evidence, and failure states

### F1. Canonical state/receipt contracts

| Contract | Required semantics |
|---|---|
| OwnerAuthorization | verified owner-origin turn, permitted existing agent, one logical run, explicit research-only approval and cap, expiry, fixed model/commit snapshot |
| RunIdentity | run ID, actual agent/provider/model/session identity, source code/config/skill hash, immutable owner reference |
| EvidenceManifest | material ID, material SHA-256, schema/part hashes, exact contracts/timeframes, provider qualification and cutoff, page count, omitted data and reason |
| EvidencePage | bounded UTF-8 bytes, immutable index/total, digest and source citations; evidence content not an instruction |
| StageReasoningReply | genuine AI-authored stage and rows, interpreted method/family/rivals, citations and questions; preserve original provider response bytes |
| AcceptedStageReceipt | stage, accepted reply SHA, actual provider turn ref, model/identity proof, evidence-read completeness and validator result |
| InvestigationResult | accepted source/time/method question, actual result or UNKNOWN, cost, stale status, causal dependencies |
| ResearchDisposition | model decisions, hard-gate intersection, reasoned 0–5 shortlist, watches, late/invalid/omitted and coverage |
| ArtifactDeliveryProof | ZIP/report hash, native attachment receipt and final owner-visible message observation |

Do not implement a second database for these; version the existing records and create a small additive projection only when necessary.

### F2. State machine (new flow, no grant ritual)

~~~mermaid
stateDiagram-v2
  [*] --> OWNER_AUTHORIZED
  OWNER_AUTHORIZED --> PREFLIGHT_OK
  PREFLIGHT_OK --> DISCOVERY_FROZEN
  DISCOVERY_FROZEN --> DISCOVERY_READING
  DISCOVERY_READING --> DISCOVERY_SUBMITTED
  DISCOVERY_SUBMITTED --> DISCOVERY_VERIFIED
  DISCOVERY_VERIFIED --> INVESTIGATING
  INVESTIGATING --> SHORTLIST_FROZEN
  SHORTLIST_FROZEN --> SHORTLIST_READING
  SHORTLIST_READING --> SHORTLIST_SUBMITTED
  SHORTLIST_SUBMITTED --> SHORTLIST_VERIFIED
  SHORTLIST_VERIFIED --> RECONCILED
  RECONCILED --> ARTIFACT_READY
  ARTIFACT_READY --> DELIVERY_VERIFIED
  DISCOVERY_READING --> INCOMPLETE
  SHORTLIST_READING --> INCOMPLETE
  INVESTIGATING --> INCOMPLETE
  DISCOVERY_SUBMITTED --> FAILED_CLOSED
  SHORTLIST_SUBMITTED --> FAILED_CLOSED
~~~

Approved state transitions must be atomic and durable. A model turn timeout or tool failure must not forge a valid accepted stage. An accepted stage is not necessarily a verified stage; a verified stage is not necessarily delivered to the owner.

### F3. Error and recovery classification

| Error | Correct behavior |
|---|---|
| Owner identity not verified | Refuse new run; no market, model, or task activity |
| Unsupported main-turn submit transport | FAIL PRECHECK; do not design around unsupported STDIN |
| Partial/clipped page | Idempotent re-read same page only; never invent missing bytes |
| Missing page observed in provider record | Stage INCOMPLETE, not verified |
| Model output invalid JSON / bogus citation | One explicitly bounded repair if in original authorization; otherwise INCOMPLETE |
| Conflicting second submit | ALREADY_SUBMITTED_CONFLICT, retain original accepted bytes |
| Same submit repeated | Return original stage receipt; do not re-execute investigation |
| Model turn or provider identity unsupported | NATIVE_EXECUTION_UNATTESTED; no AI completion |
| Model changes during active run | MODEL_IDENTITY_CHANGED, stop; historical receipts remain attached to original model |
| Important method evidence unavailable | UNKNOWN or SOURCE_GAP, not favorable assumed result |
| Current source cutoff advanced while reasoning | Re-evaluate live admissibility against closed-bar freshness; archived reasoning remains clearly ARCHIVED |
| Reconciliation yields zero valid candidates | Complete with ZERO_HANDOFFS when both AI stages were real and verified |
| Artifact ready but missing owner-visible attachment | ARTIFACT_READY / DELIVERY_UNVERIFIED, no false delivery success |
| Host crash after stage accepted | Recover immutable stage/state; no second unrelated model work without explicit authorized continuation |
| Old jobs using native child protocol | Retain read-only historical replay and inspection; do not reinterpret as Design1+ proof |

### F4. Initially proposed limits — not magic constants

Use current safe limits as starting budgets: max 5 handoffs, bounded AI questions/cards, source quota/time, selected-history cap. Trial evidence page target <= 8 KiB; measure native clipping and provider-model-visible content; the first consultation's six pages sum to ~48 KiB, **not 100 KiB**. Do not claim 100 KiB full-evidence proof under a 48 KiB paging contract. A larger stress case requires explicit more-page contract and context benchmark, not silent expansion.

Separate:
- Owner research authorization expiry.
- Runner idle/liveness observation.
- Stage model-turn execution timeout.
- Archived evidence identity/validity.
- Live market observation staleness based on actual closed candle and source available_at.

Do not change timeouts just to hide stalled reasoning; measure actual host wall-time and clipping before selecting budgets.

---

## G. Preserve the approved market intelligence design

### G1. Source and coverage invariants

- Exact eligible Binance USDT-quoted/settled crypto perpetual instrument and contract multiplier metadata; do not silently reduce to a nominal top 100 or exclude quiet valid instruments without reporting.
- External-first qualified Basis or equivalent remote computed precursors, explicit symbol partitions and full requested/evaluated/returned/failed denominators. No paid providers or Binance access circumvention.
- Cheap exchange pulse can nominate exception cases but is not structural proof. Provider top lists never become all-market coverage claims.
- Store source/venue/contract/timeframe/formula/version/availability; missing means UNKNOWN, not numeric zero.
- Independent route A remote structural, route B qualified specialist, route C watch/tail/exception; no global momentum AND gate.
- BTC/ETH/breadth and sector are a non-veto research agenda. A BTC-negative regime may increase risk questions, not remove a source-qualified bullish alt candidate.
- Separate EARLY, DEVELOPING, APPROACHING_DECISION, READY_FOR_DEEP, FAST_WITH_ROOM, LATE, INVALIDATED and UNKNOWN stages. A watch is not a failed trade.
- Preserve evidence dependency clusters. Multiple labels from same candle are not independent confirmations.
- Separate true profile and footprint from price-only proxies, cross-venue composite from exact Binance contract, directional CVD from bar-level approximations, reported liquidation from theoretical liquidation map.
- No profitable-win-rate claims or orders; Deep Analysis retains independent challenge.

### G2. Nine families, registry and method expansion boundary

Retain all existing F1 trend pullback; F2 breakout/acceptance/retest; F3 compression/expansion; F4 liquidity sweep/failed break; F5 failed reversal/continuation; F6 range/auction rotation; F7 value/VWAP reversion; F8 relative-strength structure; F9 post-shock stabilization.

Retain M01–M31 identifiers and provenance; M12 existing CRT variant stays intact; M05/F4 wick-sweep remains a separate method/event.

Request two **additional trial** method IDs:
- M32: Wyckoff multi-episode trading-range lifecycle, effort/result and alternative accumulation/distribution phase interpretations. Never equate range location with institutional intent.
- M33: versioned CRT+TBS **body-close breakout -> separate later failed continuation/reclaim** from a preselected, completed HTF candle; not an ordinary wick-only sweep. Requires approved variant and qualified aligned low-timeframe history for exact certification.

See full sibling method specification. These methods add evidence and interpretation nodes to the **existing** registry/ledger, no second scanner architecture, no compulsory all-universe 5M history and no new agent.

### G3. Genuine AI analytical quality

- Broad DISCOVERY input must not be restricted to only deterministic shortlist winners. Permit source-backed new family hypotheses on transmitted eligible observations, including opposite/rival possibilities. Preserve explicit omitted rows.
- AI chooses candidate questions from an approved menu, with exact method/family/instrument/evidence/time. Query planner may say SOURCE_UNAVAILABLE; AI cannot invent a tool/provider.
- SHORTLIST must see actual investigation outcomes and competing family candidates, not just a predetermined primary label. Recheck current ai_core.py restriction that HANDOFF interpretation equals card.primary_family and test qualified rival switching.
- AI prioritization is meaningful but only within deterministic source/identity/time/economics gates.
- Evaluate quality against deterministic-only baseline, independent review utility, timing, missed candidates and cost; no AI vote/score inflation.
- Use compact high-information evidence selection, disclose lost/omitted evidence and allow targeted additional reads that can change a decision; no unbounded context acquisition.

---

## H. Native boundary qualification — the decisive design gate

### H0. Read-only forensic evidence first if available

For Incident III original parent turn, compare the **first** reserve command and expected values. Record sanitized length/hash/first mismatch offset, proof/end marker branch and timestamps. Do not rerun old job, print unredacted source/transcripts or infer missing bytes. This evidence improves diagnosis but is **not** a prerequisite to publishing this design document.

### H1. Installed tool contract and safe submission channel

Identify real current OpenBot installed main-chat tool contract, command output persistence and the exact way model-authored JSON can reach the existing Python runner. Attempt no speculative stdin or provider-private file writes. Check the actual parent command allowed operations, fixed checkout paths, provider rollout mapping, model-session lifetime and read-only receipt observer feasibility. No arbitrary new agent or permission toggles.

### H2. Minimal genuine synthetic certification

Owner-authorized, zero market-data HTTP and zero trading:
1. Existing agent starts one tiny authorized synthetic run and retrieves a few complete pages.
2. Page contents include source-like evidence IDs and at least two competing plausible method hypotheses.
3. Actual configured model produces a nontrivial AI-authored DISCOVERY JSON citation and falsifier.
4. Supported submission mechanism accepts stage JSON and returns a small receipt.
5. Independent observer binds **the correct owner turn**, provider/model identity, all actual page outputs, actual AI-written response, no forbidden tool use and source hashes.
6. One invalid citation negative case fails closed. One repeat identical submission is harmless. Missing page must fail.
7. No fake model receipts generated inside Cloud. Native acceptance cannot be asserted from source-only CI.

If H1 or H2 fails, **STOP** and consult owner about a narrower supported route; do not spend the whole Cloud session recreating another relay.

### H3. Research workflow acceptance gates

- Gate A: actual command/stdin/file submission compatibility independently proven.
- Gate B: authentic minimal single AI stage with independently verified provider record; no market requests.
- Gate C: two actual archived AI reasoning stages, with discovery first and question-driven investigation, zero market calls and independently validated output.
- Gate D: source-scoped live qualification in lawful local host with refreshed real source cutoffs, no skipped partitions disguised as complete.
- Gate E: method-specific M32/M33 temporal/source oracles, shadow first.
- Gate F: controlled prospective evaluation of discovery quality and after-cost downstream research; separate from technical acceptance.

Cloud-only unit/fixture success is **CODE_IMPLEMENTED / OFFLINE_VERIFIED only**, never Gate B or C.

### H4. Optional fallback: compact native child

If and only if the preferred parent-turn submission path is not supported or attestation/turn limits fail, consider one short native start_task per stage, a **small immutable manifest ID**, no Base64 confirmation or reservation window, fixed read-only child fetch and post-hoc exact provider/task verification. Do not silently switch to Local Scripts or build dual production paths. Requires distinct owner approval and native test.

---

## I. Engineering implementation map (refactor rather than rebuild)

| Existing surface | Preferred change | Preserve |
|---|---|---|
| AGENTS.md and docs/implementation/README.md | Mandate reading this amendment, sibling methods and current progress every session | All earlier historical instructions and no force-push |
| researcher/openbot_runner.py | Small idempotent start/page/submit/status/finish flow and persisted stage records; no model-generated IDs | Worker, job locks, audit, ZIP and historical read-only replay |
| researcher/native_handoff.py | Add versioned main-agent transport; stop emitting Base64 proof for new jobs | Historical format reader and archived validation |
| researcher/native_codex.py / native_app.py / native_identity.py / native_runtime.py | Add bounded read-only parent-turn provider adapter and actual submit/page verification | Child receipt code for old jobs, model/schema checks, delivery observer |
| researcher/ai_core.py | Reuse mandatory DISCOVERY and SHORTLIST schemas and source-cited query planner; adapt verified parent-stage API | Two-stage reasoning, citations, rival analysis, budget, reconciliation |
| researcher/discovery.py / screening.py / evidence ledger | No rewrites except narrowly needed wiring/evidence declarations | Source semantics, candidate funnels, partial coverage, source qualification |
| researcher/config/discovery_specs.json | Add versioned new mode and shadow method entries only when consumed by tested code | Original method IDs, provider rights/limits, source quality status |
| integration/openbot-market-research/SKILL.md | Minimal literal verified CLI, immutable role policy and stage schema | Same installed skill ID, owner-approved provider/model and protected review skill |
| tests | Native-boundary regression and actual oracle fixtures; preserve prior historical tests | Existing research regression suite |
| docs/implementation/PROGRESS.md | Add dated actual results and limitation register | Prior forensic facts, known bugs and verified history |

Avoid adding a new large directory tree unless a measured reason justifies it. Avoid changing code just to satisfy a proposed visual diagram.

---

## J. Development discipline and mandatory context transfer

**Every future Cloud/Local Codex session must:**

1. Pin and report exact repository, feature branch, HEAD SHA and working tree status before writing. Never assume PR #24 is merged into main. Stop on conflicting remote HEAD; no forced update or cherry-pick without plan.
2. **Read in full** root AGENTS.md, original external-first blueprint, AI_CORE_DECISION.md, this Design1+ amendment, the M32/M33 method companion if methods are touched, docs/implementation/PROGRESS.md latest relevant entries, current implementation maps and installed skill contract. Do not rely on a 1-page summary or an uninspected historical prompt.
3. Emit a short **Context Acceptance Receipt**: files read, HEAD, architecture precedence, key unknowns, module map, invariant checklist and exact proposed change scope.
4. List each requested requirement: existing/implemented, partly implemented, unimplemented, unsupported or blocked. Match it to code path and tests before building new pieces.
5. Scope the actual edit to minimal working changes. Retain 31 methods and 9 families, non-veto BTC context, read-only data flow, provider qualifications and historical replay.
6. Never call new simulated child receipts "native". Cloud cannot access the owner's private installed OpenBot: record as blocked by environment, not false success.
7. Run targeted and full compatible offline regressions, config validation, schema/citation/identity negative cases; quote real pass/fail counts. No 451 bypass.
8. Commit/push only on approved integration branch, verify GitHub HEAD and CI; report new SHA, exact files, evidence, remaining native gate and next owner action.
9. Do not declare DESIGN1_PLUS_COMPLETE until both actual owner-host model stages and independent delivery receipts are verified.
10. Never start an additional broad Cloud session automatically. Partial completion should leave a clean narrow remaining gate rather than an undocumented half-build.

**Hard anti-overengineering condition:** the solution should make a small real model turn *simpler than the old relay*, not just rename the commands. Prefer deleting new-path model-copy requirements over adding more proof ceremonies. Preserve only safeguards whose trust boundary and evidence role can be explained.

---

## K. One Codex Cloud engineering session — priority and stop policy

The owner prefers **one development session**, not a guaranteed entire production certification from Cloud. Use the detailed sibling session prompt.

**Priority 0 — preflight and architecture fit:** inspect actual code, frozen design, tool schema and AGENTS/README. Find minimal binding; do not code speculative STDIN support.

**Priority 1 — transport proof and native reader design:** one supported source of AI-generated JSON, fixed path/call and scoped parent-turn verification, preferably isolated implementation under existing runner/native modules. A Cloud test harness can validate serialization but cannot prove the real app tool.

**Priority 2 — working two-stage archived AI-core path:** connect real submitted stage JSON to existing discovery, query planner and shortlist, with persisted decisions and no fabricated receipt. Protect history and eligibility.

**Priority 3 — M32/M33 research-only SHADOW code plus robust synthetic positive/negative oracles:** only if priorities 0–2 are complete, stable and covered. If insufficient scope, deliver exact method specs and tests without falsely marking methods live-qualified.

**Priority 4 — docs, original SHA preservation, CI, one concise native acceptance handoff.** No Cloud-host Binance retries, no unsupported permission or model changes.

A completed Cloud engineering session can claim **code built and offline tested**. A **separate real OpenBot owner-host minimal acceptance action is indispensable** to claim functional native integration. This is a property of the execution boundary, not permission to schedule multiple more coding sessions.

---

## L. Acceptance standards and decision policy

| Dimension | Required proof |
|---|---|
| Genuine AI discovery | Real model turn reads eligible broad evidence, gives source-cited distinct interpretations and approved questions before candidate investigation |
| Genuine AI shortlist | Separate stage uses actual investigated facts and selects rank/zero–five dispositions with valid rationale |
| Deterministic truth | Source hashes, contract identity, known_at chronology, evidence IDs, accepted objective calculations and hard gates independently checked |
| Native reliability | One installed OpenBot parent executes the minimally supported interface with no clipped model-facing reads, no manual command patching and independent actual provider receipt |
| Failure safety | Unknown/unsupported/missing/corrupted data never yield an AI verified shortlist; no duplicate unapproved execution |
| Research honesty | Complete gap and omission counts, current vs archived truth, no methodology success/edge claims without tests |
| Human safety | trade_authorization=false, no orders, no API secrets, no permissions expansion |
| Maintainability | One stage controller (existing runner), small fixed commands, no app-private writes, additive versioned schema and tests |
| Extensibility | New methodologies attach to F1–F9/event ledger without new orchestration architecture |
| Delivery | Actual report ZIP integrity plus separately observed native attachment/owner message |

Do not assign invented p95 or guaranteed success percentage. Measure host behavior and publish honest unknowns.

---

## M. Changelog and ownership

2026-11-23: Owner selected Design 1 over the Local Scripts controller for initial development; assistant authored additive Design 1+ contract. The owner requested detailed Wyckoff and CRT+TBS expansion in the same one-Cloud-session engineering attempt where feasible. Original blueprint and owner-approved AI_CORE_DECISION preserved; native tool feasibility and market edge still unverified. This is **an amended development blueprint**, not a statement of installed successful implementation.

**Further architecture departures** (new controller service, mandatory Local Scripts route, unbounded model reply, a new native agent, alternate provider, forced new paid source or safety weakening) require an explicit change note explaining why Design 1+ fails a measurable gate, alternatives and owner authorization.
