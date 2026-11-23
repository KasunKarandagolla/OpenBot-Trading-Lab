# Market Researcher AI-core architecture

Owner decision recorded on 23 November 2026. The mandatory AI reasoning in
this amendment supersedes the optional interpretation policy for the owner
OpenBot workflow. Historical blueprint and implementation plan bytes are
preserved. Baseline is feature branch commit
`7fd0865c062889b228b9d0a1a336173f104ee8a1` on draft PR #24.

| Baseline gap | Implementation |
|---|---|
| Native reasoning started after investigation allocation | `scan_market_research` calls `AIResearch.discover` after qualified broad observations and context, before alt history allocation |
| AI could only advise on existing cards | The discovery contract accepts source-cited methodology hypotheses from any transmitted observation, with rivals and time-to-decision |
| Follow-up questions were internally selected | `QueryPlanner.opportunity` verifies the citation, method/family pair, exact contract and closed interval, then executes an approved method calculation with the existing source adapter |
| Final selection inherited deterministic membership | `AIResearch.shortlist` compares supplied reconstructed cards. `reconcile` applies model membership and priority to candidates that still satisfy deterministic gates |
| Model-operated evidence-page reads caused completeness failures | New tasks carry a whole bounded, trim-stable brief. The receipt still binds dispatch, provider input, output, model identity and exact task |
| Optional review failures allowed completed results | Required stages, investigation and freshness gate the shortlist and the runner's completion status |

## Evidence and analytical authority

Support and contradiction refer to exact supplied evidence keys. A broad
precursor is an observation. The model can suggest a different interpretation
of that observation, including a new candidate or opposite direction. Numerical
observations and historical chronology come from deterministic source code.
Unsupported operations and unsupported claims fail validation. A source
signature does not qualify a new detector. Price-only calculations preserve
the limits of the original candle, position, tape, profile and depth sources.

The broad nomination ledger, exact Binance perpetual identity and F1–F9/M01–M31
registry remain in use. Discovery rotates through routes and intervals and
reports bounded packet omissions. Investigations share existing history caps
with protected observation lanes. An equivalent question reuses its validated
fact within the run. The final pass receives investigation outcomes and
source-backed reference, lifecycle, room, time and economic evidence. Comparison
can return zero to five research handoffs in model priority order, with full
offline gate enforcement and same-contract deduplication. Watch, early,
unsupported, omitted and invalidated decisions remain visible. Provider scope
and staged expansion remain separately qualified.

## Runtime and failure handling

`openbot_runner` publishes two independently identified materials using the
owner's existing agent. The scoped Windows reader verifies the parent call and
acknowledgment, matching app projection, exact provider input, authentic
provider turn and usage, reply bytes and absence of child tool operations.
Archived paged materials retain their builder and verifier. Packet omissions
are decided before dispatch. Missing or altered packet bytes fail closed.
After an observed acknowledgment, the inline collector uses the scoped app
projection between parent observations and independently checks the parent
receipt again at import. Reads have bounded timeouts. App records that advance
past an earlier observation timestamp require a newer observation. Invalid
record chronology is rejected.

A missing model, unavailable provider, unsupported backend, bad response,
stale evidence or incomplete investigation preserves evidence without
publishing a completed shortlist. Source and cutoff checks apply again at
finalization. A replay uses archived source clocks plus independent native
dispatch and receipt clocks and is always identified as archived. A verified
analysis with zero qualified handoffs is a valid completed analysis. Final
delivery requires a separately observed attachment and matching final response.

Limits are in `researcher/config/discovery_specs.json`. The new runner allows
at most two child tasks and accepts at most two provider attempts across
them. An independently observed over-budget result fails the stage. The
model cannot call sources, request arbitrary formulas, execute code or change
settings. A later owner run binds the current configured model and verifies
its own receipts. Cross-job stage resume and reuse of a prior model's
decision are outside the implemented slice.

## Qualification and reproducibility

| Requirement | State |
|---|---|
| AI discovery, bounded investigation, final comparison and fail-closed handoff | `IMPLEMENTED_AND_OFFLINE_VERIFIED` |
| Direct transport, model and task binding, archived orchestration, ZIP receipt | `IMPLEMENTED_NOT_NATIVE_VERIFIED` |
| Exact-basis closed precursors and selected offline F1–F9 calculations | `IMPLEMENTED_AND_OFFLINE_VERIFIED`; existing sampled source claims retained |
| True volume profile and nodes, footprint, absorption, exhaustion, specialist depth/positioning/funding, liquidations, sectors and catalysts outside qualified envelopes | `SOURCE_BLOCKED`; M17/M18/M22–M29/M31 dependent on source and scope, with selected price-relative and public point observations still available |
| M14, M15 and proposal-level M32/M33 | `DEFINITION_PENDING` |
| Other native backend or unattestable provider record versions | `INTERFACE_BLOCKED` |
| Whole-market methodology qualification, empirical usefulness, and cross-job stage resume | `NOT_COMPLETED` |

Offline end-to-end fixtures exercise M05 sweep/reclaim against its breakout
rival on both a synthetic market and the retained-source path. The focused
pipeline fixture also exercises M08 gap lifecycle, M16 balance and an
unavailable M22 footprint from the same non-nominated contract. Independent
historical regression fixtures retain causal invalidation, used room,
prior receipt/page compatibility and Windows storage failure cases.

Run the production-path and archived regressions with:

```bash
PYTHONPATH=tests python -m unittest test_ai_core test_workflow_e2e test_workflow_lifecycle_recovery -v
python -m unittest discover -s tests -v
python -m researcher config validate
```

The recorded [fixture trace](../../evidence/external-first/ai-core/fixture-trace.json)
uses simulated native receipts and market responses. The shipped archived source
is the five-contract retained Session 5 fixture. Neither qualifies a current
market or genuine OpenBot execution in Cloud.

[Local acceptance and rollback](AI_CORE_LOCAL_ACCEPTANCE.md)
