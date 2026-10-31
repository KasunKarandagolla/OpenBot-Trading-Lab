# 14 — Architectural Decision Register and Owner Decisions

## Status: draft, not implementation approval

| ID | Proposal | Why | Status | Trigger to revisit |
|---|---|---|---|---|
| ADR-001 | OpenBot = research Director, not an order-execution owner | Keeps LLM non-determinism off critical order path | PROPOSED | Isolation/licence fails |
| ADR-002 | Freqtrade + FreqUI = one paper and evaluation engine | Dry-run, backtest, pairlists, UI, SQLite and risk hooks already exist | PROPOSED | Session 1 actual test fails materially |
| ADR-003 | No live trading or keys in 5-session MVP | Avoid financial loss, owner complexity and security debt | PROPOSED NONNEGOTIABLE FOR MVP | Separate future live project |
| ADR-004 | Agent may read only separately exported reports | OpenBot's current broad process privileges cannot be fixed by prompts | PROPOSED SECURITY GATE | Agent sandbox must pass B01–B06 |
| ADR-005 | Single active frozen paper strategy | Attribution, operator comprehension, reproducible economics | PROPOSED | Demonstrated need to scale |
| ADR-006 | Initial baseline then one VWAP challenger | Avoid untestable conflated strategy ensemble | PROPOSED | Predeclared research evidence selects stronger hypothesis |
| ADR-007 | Built-in pairlists before custom CCXT scanning | Reduce code/session cost | PROPOSED | Built-in fails eligibility/timing acceptance |
| ADR-008 | No true order-flow module until sourced and economically justified | Data, storage, methodology/fee costs exceed initial scope | DEFERRED | Candidate needs & validates extra information |
| ADR-009 | Local first; VPS only after evidence gate | Avoid recurring cost | PROPOSED | Paper operator downtime unacceptable and budget approved |
| ADR-010 | Native Freqtrade features before plugins/custom indicators | Reuse-first project vision | PROPOSED | Versioned comparison shows failure |
| ADR-011 | Default no unapproved historical dataset downloads | Source/licence/holdout protection | REQUIRED | Owner authorizes named lawful source and exact window |
| ADR-012 | Preserve old AstraBot unchanged, do not auto-merge #34–#36 | Avoid integrating unqualified complex research into minimal MVP | PROPOSED | Independent needed component proves fit and reviewed |
| ADR-013 | 5 sessions **maximum**, one owner authorization per session | Budget protection and verified output | PROPOSED | New owner budget/ROI decision |

## Open questions requiring exact owner or tool evidence

| Question | Why it matters | Default until resolved | Responsible |
|---|---|---|---|
| What OS/CPU/RAM/disk/privilege environment? | Docker, security isolation, FreqUI/OpenBot compatibility | No implementation assumption; Session 1 environment inventory | Owner + Codex |
| Is OpenBot intended for monetized/live/proprietary use? | Current noncommercial license | Noncommercial research only pending rights resolution | Owner / rights holder |
| Which legal historical dataset and periods? | Backtesting, funding and false positives | **No download**; synthetic only | Owner + research/rights review |
| Does the chosen location/venue permit desired futures use? | Venue availability and compliance | Paper-only data probe; no accounts | Owner |
| How is an independent OpenBot sandbox achieved on owner host? | Preview can run arbitrary programs/files | No network agent bridge; manual report exchange | Session 1 |
| What is the maximum optional cost for models/hosting/data? | Total cost not equal to Codex session count | $0 new spending until expressly authorized | Owner |
| Do legacy 0.25%, 0.5%, 2x, 12h values apply to *paper*? | Risk specification and test vectors | Conservative proposal, not a proven engine capability | Owner + Session 1/2 |
| Which trend/VWAP entry formula? | We must freeze before outcome testing | No active economic strategy; only synthetic test | Session 2 |
| What sample/power and after-cost success threshold? | Avoid moving goalposts | INSUFFICIENT until preregistered | Session 2/3 |
| What is Freqtrade's exact current installed API, schema and version? | No API guesswork | Pin/review in Session 1 | Codex |
| How does dynamic shortlist reach the strategy without trading surprises? | Runtime pairlists can change exposure universe | Start static fixture then test supported handlers | Session 1/2 |
| Should Director run scheduled when owner's PC sleeps? | Continuous operation costs a host | Local scheduled-only; no 24/7 promise | Owner |
| How are strategies reviewed and activated? | Owner cannot inspect code deeply | One-page versioned human-readable card + acceptance evidence | Project lead |

## Conflict with legacy governance (intentional pivot)

The earlier AstraBot charter expected all ten analysis families, an independent exchange writer, human approval for every new exposure, a complex event ledger and separate position supervisor. **Those do not silently carry over** into a five-session Freqtrade MVP. What *does* carry over: no unearned profitability claims, reproducible source clocks, safety protections, respect for owner authorization and no accidental live orders.

**Paper-mode exception:** one owner-approved **strategy version** may autonomously simulate individual trades, since simulation has no real exposure. That exception does not change the old live authorization rule or authorize future real exposure.

## Project manager's STOP decision tree

- **Session 1 isolation fails?** Stop agent automation; test static Freqtrade alone or choose a legal/secure alternative.
- **No lawful economically representative data?** Stop at an honest functional lab; do not call strategy validated.
- **Base strategy fails after costs?** Reject. Only test a clearly preregistered independent challenger if the budget/evidence justify it; do not commission a strategy zoo.
- **Unseen test insufficient?** Declare INSUFFICIENT and preserve budget; do not invent confidence.
- **All gates pass?** Owner may authorize *next* paper-only session; never automatic live trading.

## Required owner signoffs before Session 1

A one-line decision can approve only: **“Approve isolated, synthetic, credential-free OpenBot+Freqtrade Session 1 on my specified host; no paid services, archive download, key creation, live or testnet trading.”** This does not approve the rest of the roadmap.
