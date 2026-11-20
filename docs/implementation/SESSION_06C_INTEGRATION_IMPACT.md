# Phase B bounded integration impact

Owner approved Phase B after pushed checkpoint A `8a7e61b` and both successful
CI runs, retaining source/definition/quota gates. The owner confirmed that the
existing native application agent answers using its configured model.

Inspected native role: **Trading Lab Market Researcher**, provider `opencode`,
model `opencode/deepseek-v4.1-flash-free`. The existing Chart-Vision Analyst,
Independent Risk Reviewer, Director and other profiles remain unchanged. No
separate native Deep Analyst profile was found; do not invent a consumer.

Allowed changes, recorded before native installation or further integration:

| Component | Smallest change and purpose |
|---|---|
| `researcher/agent_review.py` | Bounded precomputed evidence request; strict source-citation reply validation; explicit native invocation audit separate from JSON validity |
| `researcher/native_app.py` (Phase C) | Narrow opt-in read-only collector for this exact owner-submitted task; verifies current native records and imports without manual audit delay; no agent invocation |
| `.agents/skills/market-research-review/SKILL.md` | Versioned research-only task for the existing agent; preserve older packet behavior |
| Existing Researcher's skill discovery directories | Install only this scoped new skill, with identical bytes in the existing discovery mirrors; no registry/model/access edit |
| Existing Researcher's research workspace | One bounded request file; no histories, account data or credentials |
| `researcher/discovery.py`, `researcher/__main__.py` and `researcher/handoff.py` | Optional file exchange at the ordinary scan boundary, deterministic fallback and unchanged default behavior; file delivery is never called a model invocation |
| Focused tests and Session 6C docs/evidence | Validator, caching/failure and actual native response audit; sanitized receipts only |

The native application is the supported invocation surface confirmed by the
owner. Codex's Windows UI bridge fails before executing JavaScript on this WSL
path. Standalone provider diagnostic failure is not evidence that the native
agent is broken. A prepared native-app task is used instead; no provider-session
protocol, replacement agent, model switch or API-key setup is introduced.

The native profile's existing access setting is unchanged. Task instructions
allow evidence/skill reads only; they are not represented as host isolation.
Actual native tool calls must be audited. The Python exchange adapter has no
network/process/trading operation and cannot dispatch a model-requested tool.
Validated advice cannot override deterministic admission or source gates.

Preserve all existing specialist skills and old Gate/trade-plan packet handlers,
all other profiles, provider configuration, Freqtrade, trading DB/config/orders,
execution and `main`. No mutable callback from the optional downstream export.
