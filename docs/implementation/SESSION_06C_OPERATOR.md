# On-demand operation with the existing native Researcher

Default deterministic command:

```bash
python3 -m researcher scan now --output work/operator-001.json
python3 -m researcher show results
python3 -m researcher show watches
python3 -m researcher show coverage
```

Use a new output filename; the research ledger persists original reference
knowledge and observed gaps. Read source/eligible/evaluable counts alongside the
0–5 handoffs. Zero handoffs under partial coverage does not prove no opportunity.

## Optional interactive native review

Reuse **Trading Lab Market Researcher** and its configured
`opencode/deepseek-v4.1-flash-free`. No new profile, model, key or permission.
Scoped skill `market-research-review` version `6c-native-review.2` is installed
only in that agent's existing discovery mirrors. Its current hash is
`96830b0189fc13b141513d44d4146637a83f5ad6c10d8c51c954e2c9052250fb`.

The Local setup keeps a JSON configuration below ignored `work/`:
`openbot_db`, `provider_db`, `agent_workspace`, each an absolute local path to the
existing installation. Do not put credentials, personal paths or this local
configuration in Git. This session's prepared file is
`work/session6c/native-audit-local.json`. It contains paths only, no keys/tokens.
On WSL, optional `native_python` names the already installed Windows `python.exe`.
Only the fixed receipt-reader module runs there. This avoids native Windows WAL
locking failures without UI automation, app restarts, new software or a model
change. The scanner and deterministic calculations continue in WSL.

```bash
python3 -m researcher scan now \
  --native-review-dir work/operator-native \
  --native-audit-config work/session6c/native-audit-local.json \
  --native-wait-seconds 600 \
  --output work/operator-native-001.json
```

After source collection, the command writes `<material>.prompt.txt` in the
exchange directory and places the exact bounded request in the existing agent's
research workspace. While the command waits, paste that prompt into a fresh
chat under the **same existing agent** in OpenBot. This starts no replacement
agent and changes no profile. A fresh chat reduces unrelated history/token cost.
The application remains the owner-confirmed invocation surface; the scanner
does not submit a model request or use an undocumented provider protocol.

The collector checks only this task's native turn and provider records using
SQLite `mode=ro` and `query_only`. It verifies the exact model, complete current
skill and request reads, strict whole JSON, source citations and allowed tools.
It never reads account/credential/shared-data tables, preceding chat history or
other agents' conversations, and never writes the native databases. Brief
Windows WAL read failures retry only the read within the explicit wait. There
is no model retry, scheduler, background subscription or API-key setup.

The ordinary scan imports the audit immediately, rechecks admission at its final
completion time, records actual observed native provider attempts and persists
the result. Advice supplies priority/rival/next question; deterministic identity,
source, clock, invalidation, first-obstacle and economics gates still decide
admission. The existing native profile's host access remains unchanged: task
instructions are not represented as host isolation. Audited task tools must be
only the named skill and exact request reads; no tool is dispatched from advice.

Limits: at most4 ordinary cards (12 in explicit contract tests),32 events/card,
98KB card budget/128KB complete request. Oversized nested values stay in the
local source graph and are explicitly hash-referenced, never numeric claims.
Breadth keeps aggregate values and exact denominators; long evidence/missing
lists keep8 examples plus full-list count/hash. All omissions are accounted.
Replies are <=32KB/depth32, with stricter concise skill guidance. No invented
prices, citations, profile/footprint/liquidation/OI direction or trade fields.

The wait is0 by default and can be0–600s. Missing, incomplete, invalid, stale,
wrong-model, unauthorized-tool or unavailable native evidence retains the
deterministic result and cannot block scanner persistence. No response is
silently repaired. Same input fingerprint requires no repeat native submission;
cached accepted advice observes0 new model attempts. A changed closed cutoff or
source changes the evidence fingerprint. Never backdate a late native reply.

## Scope and downstream

The full27/9/31 matrix and source certificates remain authoritative. Actual
native reasoning does not qualify a missing feed or prove live usefulness.
Current production family/method flags stay disabled under the approved source
gates. All current results are research hypotheses, with no executable entry,
stop, target, sizing, account, order, bot or scheduling connection.

`openbot.research-handoff.v1` remains a hashed one-way export. No compatible
separate Deep Analyst input handler was configured in the inspected native
hierarchy. Its optional downstream status is NOT_INTEGRATED; preserve existing
vision/risk/director reasoning and trading behavior. The smallest future change
is a read-only version/hash/freshness-checked input handler in an owner-designated
existing consumer after the relevant source/admission gate passes.
