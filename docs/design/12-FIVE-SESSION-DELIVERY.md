# 12 — Five-Session Maximum: Deliverables, Stop Gates and Budget Discipline

## Non-negotiable planning rule

We have **at most five Codex sessions left by conversation accounting**, not five sessions that must be consumed. OpenBot/model usage may have separate limits. Sessions are authorized *one at a time*. No Codex or OpenBot sessions were spent writing this document pack.

## Gate-first schedule

| Session | Objective | Deliverable you can open/run | Pass criterion | Stop/hold condition |
|---|---|---|---|---|
| **1: Tool qualification** | Install/pin Freqtrade/FreqUI; run synthetic strategy/indicator and isolated OpenBot report read | Runnable local lab, short demo recording/log, compatibility report, zero-key sandbox test | Start/stop, UI, synthetic backtest, read-only analysis and isolation demonstrated | Paid dependency, agent reaches admin/config, tool incompatibility → BLOCK, don't spend session 2 |
| **2: Mechanism & lawful data** | Freeze one simple baseline and economic test contract; source/license clearance | One strategy card, cost model, permitted-source manifest, backtest or explicit DATA_BLOCKED report | Exact rule/code hash, testable dataset and complete signal ledger; no lookahead | No lawful data or implausible geometry → HOLD, no further engine build |
| **3: Independent economics** | Chronological evaluation, stress and baseline controls | One transparent GO/NO-GO/INSUFFICIENT report, full reproduction commands | Evidence supports *continued paper evaluation*, not profit guarantee | Uneconomic/underpowered → stop sessions 4–5 |
| **4: Agent workflow** | Director + Researcher + Reviewer over read-only exports, no privileged actions | Scheduled explainable report and incident alerts from actual paper/synthetic ledger | Agents produce cited reports; cannot mutate trader | Agent sandbox/host permission failure → manual reporting only, pause automation |
| **5: Paper MVP** | Deploy approved fixed strategy in Freqtrade dry-run, FreqUI and owner manual | Startup/stop/backup/restore demo, incident drills, no-key dry-run monitoring | End-to-end reproducible simulated lifecycle, modest local resource use | No valid economics/data/rights or broken state recovery → defer; do not claim success |

Sessions 2/3 may remain blocked for data/legal reasons. In that case **do not consume sessions 4/5 pretending the strategy is validated**. A synthetic-only lab may be demonstrated, but must be advertised as such.

## Session format for Codex (one template)

```text
BASELINE: exact repo/commit + documented target environment.
SCOPE: the one row above, no extra frameworks or 'nice-to-have' features.
INPUT: this design pack, relevant upstream versioned docs, owner decisions.
BOUNDARIES: no exchange keys/orders, no unapproved historical downloads,
            no strategy tuning on reserved outcomes, no auto-merge.
IMPLEMENT: adopt/configure existing tool first; minimal wrapper only.
VERIFY: run named acceptance tests, list exact environment, version/commands,
        preserve all failures, source rights, resource and time measurements.
OUTPUT: committed reproducible code/config, evidence, operator steps, PR,
        PASS/FAIL/BLOCKED and single next action.
STOP: after this gate. Never self-authorize following session.
```

## Project-manager controls

- No architecture redesign or stack replacement after Session 1 without a documented failed acceptance and owner signoff.
- No simultaneous strategy zoo. One benchmark + one challenger maximum at each research decision point.
- No paid infrastructure, key creation, historical download or plan upgrade without specific owner approval.
- No unearned '95% complete'. Only mark a session PASS when its demo/evidence exists.
- Do not run all five sessions if gate 2/3 fails; stopping preserves budget and is correct management.
- Every change contains rollback instructions, test commands, known issues and next owner decision.

## Meaning of success

**Engineering success:** a beginner can operate a reliable **paper** research application without coding. **Economic success:** a qualified strategy survives adequate independent cost-aware evidence. The second is not guaranteed by the first or by session count.

## What not to outsource to Codex

The owner must choose budget, intended use/licensing, acceptable data rights and live-money policy. Code models must not make irrevocable commercial or trading-risk decisions on the owner's behalf.