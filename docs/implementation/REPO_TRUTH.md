# Repository truth and reuse — Session 1

Fetched all 25 upstream branches before editing. GitHub repository ID
`1440694312`, owner `KasunKarandagolla`, public, default branch `main`; authenticated
repository metadata reported push/admin permission. The initial working tree was
clean on environment branch `work`, at documentation commit
`2343053ce68f6fff4525c5b67771ea445deb3779`.

| Reference | Verified head | Reality |
|---|---|---|
| `main` | `2343053ce68f6fff4525c5b67771ea445deb3779` | Original design pack, no deployed researcher |
| `feature/external-first-market-researcher` at start | `694dfdfa9d7700d7ced0a79f4502423b38ff9681` | Three authoritative documents, draft PR #24 to main |
| PR #23 / `codex/openbot-s3-full-intelligence-native-playbooks` | `2f9ebc7b86a99c4519278ced2287a449ed4b2822` | Latest relevant historical implementation; unmerged draft |
| PR #22 / historical replay binding | `6225d925851e3373002d7b5a06a6949d80cbda12` | Unmerged draft; source-bound historical watchlist |
| PR #20 / skills v2 | `a44d58d26a4c46cb892ca16568f34eef34b24ad8` | Unmerged draft; older live/chart contracts |
| PR #18 / native workflow | `d133b3bf91ab51765d9446e4e82f0bc38c0bae94` | Unmerged draft; public research, fail-closed Demo boundary |
| PR #12 / causal fixes | `e2739dcbb6e48016a13a314f3a21507ed181cb60` | Unmerged; historical local calculation fixes |
| PR #11 / setup playbooks | `f0ef4453144869ca013ad156fdd46c81b767af2c` | Unmerged; native historical recipe research |

All PRs #1–#24 were open, none merged at inspection. PRs #18–#24 were drafts.
The complete PR/head/base snapshot and inspected source blob IDs are in
[`upstream-inventory.json`](../../evidence/external-first/session1/upstream-inventory.json).
Feature branch protection was **false**, and repository rulesets were empty;
no protection or workflow was bypassed. This work adds a least-privilege offline
CI workflow but does not claim GitHub enforces protected-branch policy.

The feature reference and PR #23 share ancestor `2343053…`; the implementation
stack is not an ancestor of the supplied reference branch. The approved base
remains the owner's supplied `694dfdf…`. No different approved implementation
base was established, no older stack was imported, and no history reconciliation
or rewrite was performed. There is one integration branch and one active writer.
Local remote configuration was extended to fetch this feature branch, because
the generated environment initially fetched only `main`.

## Actual reusable code and limits

Paths below were inspected at PR #23's exact head, not presumed merged or deployed.

| Source | Reusable concept / actual limitation | Session 1 decision |
|---|---|---|
| `scripts/trading_lab/public.py`, `PublicFeed`, `validate_bars` | Bounded allowlisted reads, Decimal OHLC checks, closed-bar clocks. Its capture scans 24–40 top-volume names and locally fetches their history. Transport explicitly lacks proxy support. | Adopt checks conceptually; do not import that discovery engine or transport into Cloud |
| `research/session3/causal_structure.py`, `structure`, `closed_merge` | Confirmed-pivot known-at times, gap reset, closed informative joins. Strict tie convention differs from blueprint's declared swing variant. Requires pandas/numpy/local frames. | Pinned reuse candidate for later bounded oracle work; no detector imported |
| `scripts/trading_lab/watchlist.py` | SQLite schemas 1–3, immutable events and source bindings. Only four family labels, historical source/case binding, rejects arbitrary live bars. | Preserve as later migration/reference candidate; do not pretend it is this workstream's live ledger |
| `scripts/trading_lab/panel.py`, `playbooks.py` | Source-pinned historical scanner and native playbook research | No broad external equivalent; retain unmerged, no economic promotion |
| `scripts/trading_lab/workflow.py`, `Inbox.handle` | Actual `openbot.shared.request.v2` file inbox: SCAN, CHART, GATE, READINESS, TTL/hash/schema checks. GATE cannot accept signed account state. | Source contract inspected; no bridge activated |
| `scripts/trading_lab/risk.py`, `validate_market_plan` | Existing proposal gate accepts structured entry/stop/quantity plans; output always `order_authorized=false` | Separate downstream interface, never researcher output |
| `scripts/openbot_demo_readonly.py`, `credentials`, `get`; `scripts/guard.py`, `validate` | Demo credentials/signing blocked; guard requires dry-run, denies exchange credentials and unsafe overrides | Boundaries preserved; no frozen files/configs/DBs touched |
| `integrations/openbot/skills/v3/agents/*/skills/*/SKILL.md` | 27 owner-specific assignments: Lead 9, Director 6, Researcher 6, Vision 1, Risk 5. Screening skill retains old volume gates, 24–40/3–6 budgets and recipe funnel. | Preserve expertise as versioned references; do not copy conflicting gates or install/inject skills |

No `AGENTS.md` existed in the checked repository or relevant implementation tree.
No deployed OpenBot environment, running Deep Analyst service, installed skills,
native message/attachment receipts or Freqtrade administration interface was
available in this Cloud checkout. The older workflow involves Lead, Researcher,
Vision, Risk and Director; there is no verified separate service named Deep
Analyst to connect here. Session 1's sanitized JSON is an unconnected, read-only
handoff skeleton. No claim of native five-agent or deployment acceptance is made.

New runtime files are the smallest missing public MCP/contract/config increment.
No old source files were mechanically copied. This avoids installing a second
historical engine while preserving exact provenance for future selective reuse.
