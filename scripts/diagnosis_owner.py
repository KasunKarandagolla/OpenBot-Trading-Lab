"""Build the beginner-readable A–J report from sealed native evidence."""
import re
from diagnosis_common import *

def run():
    e=read(OUT/'economic-report.json');summary=read(OUT/'diagnosis-summary.json');deep=read(OUT/'deep-summary.json');tests=read(OUT/'regression.json')
    bundle=read(OUT/'private-input-bundle.json');v4=e['portfolios'][e['official']['development']['v4']]
    def metric(cohort,variant):return e['portfolios'][e['official'][cohort][variant]]
    def n(value):return f'{value:+.6f}'
    table=['| Development policy | Plans | Fills | Net USDT | Net / original V4 plan¹ | Net / common raw opportunity² | Extra10bp/side |','|---|---:|---:|---:|---:|---:|---:|']
    order=['v4','pr12','passive','conditional-entry','passive-30m','structural','thesis-compatible','ema-eligibility-only','rank-only','ema-both','rank-qualified-only','continuation-only']
    for name in order:
        x=metric('development',name);selected='Separate cohort' if name=='pr12' else n(x['matched_net_per_original_v4_plan'])
        raw='Separate cohort' if name=='pr12' else n(x['net_per_common_raw_union_opportunity'])
        table.append(f"| {name} | {x['own_selected_plans']} | {x['fills']} | {n(x['net'])} | {selected} | {raw} | {n(x['additional_friction_ledger']['10'])} |")
    cases=['| Entry opportunity (UTC) | V4 exit UTC / price | Structural exit UTC / price | Net difference USDT |','|---|---|---|---:|']
    for x in read(OUT/'structural-changes.json'):
        a=x['v4']['trade'];b=x['structural']['trade'];cases.append(f"| {x['pair']} {a['open_date']} | {a['close_date']} / {a['close_rate']:g} | {b['close_date']} / {b['close_rate']:g} | {n(x['delta'])} |")
    robustness=['| Policy | Development net | Aug5–22 fills / net | Nov3–4 fills / net |','|---|---:|---:|---:|']
    for name in ('v4','passive','conditional-entry','passive-30m','structural','thesis-compatible','ema-eligibility-only','rank-only','ema-both','rank-qualified-only','continuation-only'):
        a=metric('earlier',name);b=metric('later',name);robustness.append(f"| {name} | {n(metric('development',name)['net'])} | {a['fills']} / {n(a['net'])} | {b['fills']} / {n(b['net'])} |")
    quality=['| Policy | Win rate | PF | Average / median trade | Profitable / losing / flat weeks | Worst loss streak | Native drawdown USDT |','|---|---:|---:|---:|---:|---:|---:|']
    for name in ('v4','passive','conditional-entry','passive-30m','structural','thesis-compatible','rank-only','rank-qualified-only','continuation-only'):
        x=metric('development',name);quality.append(f"| {name} | {x['win_rate']:.1%} | {x['profit_factor']:.3f} | {n(x['average_trade'])} / {n(x['median_trade'])} | {x['profitable_weeks']} / {x['losing_weeks']} / {x['flat_weeks']} | {x['worst_losing_streak']} | {x['native_drawdown']:.6f} |")
    fidelity=['| Fixed Oct5–Nov3 cohort | Main15m fills / net | Genuine5m detail fills / net |','|---|---:|---:|']
    for name,x in e['fidelity'].items():
        a=e['portfolios'][x['main_15m']];b=e['portfolios'][x['detail_5m']];fidelity.append(f"| {name} | {a['fills']} / {n(a['net'])} | {b['fills']} / {n(b['net'])} |")
    ranks=['| Mechanism | Confidence | Evidence and practical implication |','|---|---|---|',
        '| Passive orders sacrifice access to some valuable moves | CAUSAL_MATCHED_DIFFERENCE | Shared36 gain +0.787935; nine absent V4 fills contributed +3.003323. Price quality and fill opportunity must be assessed together. |',
        '| Structural-only replacement can delay protection | CAUSAL_MATCHED_DIFFERENCE / OBSERVED_MECHANISM | Six matched outcome changes; buffered boundary beyond stop in32/40 continuation fills. Geometric incompatibility is proven; true structural failure is not established for every loss. |',
        '| EMA eligibility and ranking have separate economic effects | CAUSAL_MATCHED_DIFFERENCE | Controlled factorial isolates the rules. Relaxed eligibility reduces development PnL; extra fills do not establish quality. |',
        '| Target and shortlist gates have little joint support | OBSERVED_MECHANISM | All56 selected plans fail nearest-objective geometry; three of four raw geometry passes lose ranking and one fails liquidity. |',
        '| Five-minute entry economics are unavailable | INSUFFICIENT_EVIDENCE | Only two early response plans pass geometry before shortlist; neither trades. |',
        '| Costs and rare winners dominate the small apparent edge | OBSERVED_MECHANISM | V4 becomes negative at extra20bp/side; removing three largest winners yields −1.094632. These are sensitivity diagnostics. |',
        '| Exact cause of many individual losses | INSUFFICIENT_EVIDENCE | Overlapping feature distributions and incomplete microstructure do not identify a unique cause. Preserve UNDETERMINED labels. |']
    text=f'''# OpenBot: deep trading failure diagnosis and targeted corrections

Date: 2026-11-04 UTC. Research branch: `codex/deep-failure-diagnosis`. Parent PR13: `ade410ec625be51f8dbcb7194b98965d8286daf7`, still open, draft and unmerged when checked. This report answers the owner's A–J questions. All figures are USDT unless stated otherwise.

**Decision: no variant is ready for promotion or activation.** We isolated several concrete weaknesses and implemented three bounded correction hypotheses. None established reliable, consistent after-cost opportunity selection. This does not establish that EMA/VWAP, market structure, passive execution or 5-minute timing are useless.

The modeled account is1,000USDT,1× leverage, at most two positions and25USDT entry notional per position. The primary fee is7.5bp per side with source-recorded funding. The38bp admission allowance affects qualification/sizing; it is not debited again as an exchange fee. Results are small partly because exposure is deliberately small. A small drawdown here is not evidence of low strategy risk at a larger size.

## A. Why did the methods lose money or fail to trade?

**V4:** the inspected development portfolio was profitable, but its edge is unproven.45 fills produced+3.473272,15 wins and30 losses. Continuation contributed+4.094245 on40 fills; five reversals lost−0.620973. Twelve ROI exits contributed+9.479725, while21 `stop_loss` exits lost−5.687903 and two `trailing_stop_loss` labels lost−0.455086. The latter label can describe the fixed geometric stop tightened from the emergency stop; it does not establish a moving trailing strategy. Six fast pullback-thesis exits lost−0.470409 in aggregate. Per-trade and per-asset details remain in the ledger.

V4's largest winner is+1.779460. Removing it leaves+1.693812; removing the largest three leaves−1.094632. These are arithmetic tail-dependence diagnostics, not new native portfolios. The descriptive seven-day block interval for total PnL is approximately[−1.573,+8.772]. It spans zero and is based on inspected, dependent observations. The earlier August portfolio loses. We cannot distinguish a persistent continuation advantage from favorable episodes with this evidence.

**Passive entry:** price improved on all36 shared fills, and their modeled exit prices did not change. The exact shared-PnL attribution is+0.798300 from entry prices,0 from exit prices,−0.009200 from the quantity interaction,−0.001165 from fees and0 from funding, totaling+0.787935. One order quantity changes because of lot rounding. However, nine V4 fills are absent and their original combined net was+3.003323. Those nine include both winners and losers. The portfolio loses access to enough valuable moves to overwhelm the shared-fill gain.

**Structural thesis exit:** replacing V4's fast warning with a buffered frozen-reference close changes six matched outcomes and reduces net by−0.805202. Five exits occur later; the sixth uses a different native exit price/reason in the same candle. The frozen VWAP reference was added by the structural challenger; it was not an originally registered defended V4 setup zone. For32 of40 continuation fills, its required adverse-close boundary lies beyond the original protective stop. That rule cannot provide earlier protection in those cases.

**Relaxed EMA/context:** the original PR13 portfolio has37 shared fills,24 additional fills and eight displaced V4 fills. Only four additional fills win; their combined net is−3.592819. The eight displaced V4 fills contribute+0.611406. The change therefore admits a weak additional sample while losing some original value. The controlled eligibility-versus-ranking tests below identify separate rule effects; these results do not prove EMA alignment is always necessary.

**Integrated strategy:** it admits zero orders because the selected signals and target gate do not agree. All56 V4-selected plans fail the first-obstacle reward check. Across196 raw strict candidates,187 fail first-obstacle reward, three lack an objective, two have an objective beyond6ATR and four pass geometry. Among those four, DOGE Oct14 ranks fourth and two ZEC reversals rank11th/ninth; LTC Sep7 is liquidity-ineligible and has no rank. It is inaccurate to attribute all four exclusions solely to ranking.

**5-minute entry variants:**307 location candidates become235 registered opportunities;72 fail initial stop/objective geometry. The early-response arm then has34 defended-zone failures,183 trigger-geometry rejections, ten protected-extreme failures, five extended triggers, one missing/expired response and two geometry-qualified responses. Both qualified responses fail the frozen shortlist. The15m-response arm has40 defense failures,124 trigger-geometry rejections,27 protected-extreme breaches, six extensions and38 missing responses, leaving zero. These are sequential funnel counts; some telemetry keys report the same stage twice and must not be summed twice. The early and passive trigger arms share the two qualifications. HYPE Oct17 ranks fifth; UNI Oct13 has no place in the strict directional pool. Their full-universe price paths are retained solely as diagnostics, with no invented fills or cash PnL. Two observations cannot establish the economics of a new entry policy.

Ranked mechanisms, with the strongest directly tested explanations first:

{chr(10).join(ranks)}

## B. Were entry prices wrong?

Some filled entries were measurably less favorable than the passive alternatives, as the36 matched comparisons establish. Waiting is not free: all nine missed V4 cases have a favorable first15m close, but that does not mean all finish profitable. Five have a later reference touch within the inspected hour and four do not. Only two have genuine5m source coverage: HYPE Oct16 first touches at18:40 after18:05 expiry; PEPE Oct20 has no retest within an hour. Older5m event clocks cannot be reconstructed honestly.

We tested one predeclared immediate/passive choice: continuation uses the immediate reference only if the already completed signal body is at least0.8ATR in the trade direction and15m relative volume is at least1.2; otherwise it uses the original0.15ATR passive offset. Reversals retain their original immediate rule. No depth sweep or fitted classifier was used. The42-fill result,+1.953465, improves on unconditional passive but trails V4. It nearly loses all profit under extra10bp/side and loses in August. Its expansion condition does not identify a validated high-value subset.

Separately, extending unconditional passive expiry to30minutes fills38 and makes+1.661944. It recovers two of the nine missed V4 fills; the seven still absent contributed+2.650224 in V4. This does not establish that30minutes is the right expiry. Five initial expiry experiments mistakenly retained the native five-minute timeout; those invalid implementation trials are preserved and explicitly excluded as evidence for30-minute expiry. A source-hashed addendum changes only the newly created native configuration and observes native order removal. Corrected runs actually remove remaining full-development unfilled orders at30minutes.

Original five-minute orders in the main15m engine are removed on a15m event step and may be filled using the full preceding candle range. A native `Order.status` may remain `open` after the engine removes an unfilled trade. The lifecycle addendum records the actual native removal clock; neither field provides exchange queue or exact within-candle touch time.

{chr(10).join(fidelity)}

These use the same completed15m decisions on a fixed October cohort;5m is execution detail, not a new signal. Finer detail removes two fills from original passive and conditional entry. No missing September5m prices were interpolated. The corrected30-minute fill count is unchanged, with a small exit-price difference.

## C. Were protective stops wrong?

The evidence does not justify widening them. Original stops derive from the signal/pullback extreme plus the original buffer, under the original risk and legal-size checks. New entry policies keep those frozen prices; size/rounding and actual risk may still change with the fill price. The structural challenger reveals a mismatch between its added failure reference and the protective geometry, not proof that the protective stop itself was wrong.

All held paths and subsequent stop/target touches are retained. MAE/MFE before the exit candle describe a different interval from native bookkeeping extrema; including the exit candle can include prices after the position closed. Post-exit bounces are hindsight, not accessible profit or evidence that a stop should have been moved. We did not run stop-only optimization or a target/stop sweep. Whether an individual stop represents ordinary pullback or genuine structural failure remains UNDETERMINED unless a separate causal observation supports the classification.

## D. Were take-profit targets irrational?

Neither fixed3R nor the nearest swing is universally correct. The fixed3R target sometimes requires crossing recorded intermediate levels; the obstacle audit gives each level's source, timeframe, availability, active/consumed status, prior crossings and later interaction. Of56 nearest levels,41 are local15m,13 parent/session and two consumed swings. A descriptive relevance rule marks consumed levels, and local levels without a prior opposing reaction of at least one signalATR, as lower relevance. It downgrades nine nearest levels;47 still meet that descriptive criterion. It therefore does not justify ignoring all local barriers. Reaction size is known before entry, but its relevance rule remains unvalidated and diagnostic only.

Continuation needs space toward meaningful opposing parent structure; a weak internal swing may be traversable. Sweep reversal must distinguish a local correction toward internal/VWAP/midrange objectives from a full reversal of the parent trend. Breakout needs a preknown objective beyond an accepted range and an exit if acceptance fails. PR12 already supplies those causal interfaces, but its14-fill portfolio loses−0.246954; it does not isolate a universal target failure. Genuine profile rotation would require authentic frozen executed-volume POC/VAH/VAL; that evidence is NOT_TESTED. An OHLCV proxy cannot supply it.

No target gate was removed to manufacture trades. No new target or runner economics are claimed. A distant target, a later touch and a realistic net payoff are three separate questions. Exact attainability after spread, queue and competing orders remains unknown.

## E. Did the bot choose the wrong opportunities?

The original ranking sometimes gives slots to liquid, directionally ranked markets without an active qualifying signal. That mechanical exclusion is observable, but granting the unused candidates access is not automatically an economic improvement. Ranking only currently qualified signals increases selected plans from56 to162 and fills from45 to129, but loses−0.866186 and increases modeled drawdown to6.805452. Its August gain reverses the development result; there is no stable superiority.

The controlled two-by-two experiment removes only the three raw EMA predicates in the eligibility arm and only the hourly EMA pool veto in the ranking arm. All other original structure predicates, including the existing FVG alternative, are retained. Adding the three predicates back reproduces the frozen real-source continuation signals across all14 markets. Strict eligibility/strict rank is V4; relaxed eligibility alone makes+1.663262; relaxed ranking alone+3.411028; both together−0.730953. Eligibility's effect at strict ranking is{n(e['ema_factorial']['eligibility_effect_at_strict_rank'])}; ranking's effect at strict eligibility is{n(e['ema_factorial']['rank_effect_at_strict_eligibility'])}; the portfolio interaction is{n(e['ema_factorial']['interaction'])}. Capacity and different admitted trades make this an interaction, not a per-trade additive law. PR13's added hourly-structure condition is disclosed separately; its economic portfolio happens to match the controlled both-relaxed arm here.

Winner/loser distributions overlap. As-of4h parent alignment occurs in14/15 winners and23/30 losers; hourly alignment in14/15 and26/30. Median signal extension is1.489ATR for winners versus1.522 for losers; median relative volume1.323 versus1.355. ADX is31.756 versus29.646. These are descriptive associations, not deployable filters. Fixed-direction ADX discrimination changes from AUC0.417 in September to0.653 in October/November; relative-volume discrimination changes from0.560 to0.389. We did not fit a winning subset. Independent discriminatory ability is NOT ESTABLISHED.

V4's56 selected plans become46 submitted orders,45 fills and one unfilled order. Three fail native legal/minimum size checks; six encounter an existing same-pair position; one hits maximum positions. The observer found no cooldown rejection in that control run. These are execution exclusions, not predicted losing trades.

## F. Did management cut winners or hold losers?

Both can occur; the matched evidence does not support replacing every fast warning with structural-only waiting. In the six changed cases, five PnL differences are adverse and one favorable:

{chr(10).join(cases)}

PEPE Oct23 is the same-clock case: removing the custom exit exposes the geometric stop later in native same-candle processing. SOL is the favorable delay. WLD, the September PEPE and XRP hit protective stops after the original fast warning; DOGE reaches the structural failure exit after surrendering an earlier gain. Full causal feature timelines, rather than future pivots, identify what was available at each close. Nine timestamped actual-candle charts include all six changes, a large winner, a protective loss and a missed passive winner. Their future regions are shaded; charts are not profit simulations.

The compatibility guard restores the original fast rule whenever the challenger's buffered boundary cannot be reached before the original stop by more than one native tick. It recovers+0.432537 versus structural-only, reaching+3.100606, but remains−0.372665 behind V4. DOGE remains the one changed outcome versus V4. This repairs a logical incompatibility without validating the surviving structural exit or redefining true failure.

## G. What did we correct and test?

Exactly three correction hypotheses were registered before new native results: H1 entry access (conditional choice and separate expiry ablation), H2 selection authority (eligibility/ranking factorial and qualified-pool diagnostic), and H3 thesis/stop compatibility. The continuation-only arm was explicitly selected after prior playbook results and is a diagnostic, not an independent discovery. There was no threshold search, second round of tuning or profit-selected parameter sweep.

{chr(10).join(table)}

¹ Matched PnL divided by the same56 original V4-selected plans; new unmatched trades are excluded from that numerator. PR12 is a different setup registry. ² Total portfolio PnL divided by the same317 unique strict/EMA-relaxed raw opportunity IDs, before liquidity/ranking/execution. The original strict registry contains196. This broader fixed denominator permits eligibility comparisons; it is not an estimate that every raw signal has a tradable position. Own accepted-plan expectancy and unmatched PnL are also recorded in `economic-report.json`. Extra-cost columns are turnover-based sensitivities, not native reruns unless stated below.

Working improvements are the immutable stop-compatibility decision, isolated EMA/rank controls, correct native expiry configuration, actual terminal-order observation, canonical opportunity IDs and complete nonfill attribution. They improve research correctness. Their economic results include regressions and do not justify promotion.

## H. Did consistency improve?

**No consistent improvement is established.**

{chr(10).join(quality)}

Weeks are UTC calendar buckets with PnL assigned at exit, including partial edge weeks and flat buckets. A different accepted set can populate weeks in which V4 has no fills. Full monthly, weekly, side, playbook, asset, realized-R, average winner/loser, holding-time, fee, funding and turnover distributions are machine-readable. V4 average winner is{v4['average_winner']:.6f} and average loser{v4['average_loser']:.6f}. Its independent order ledger totals gross{n(v4['gross'])}, fees{v4['fees']:.6f} and signed funding{n(v4['funding'])}. Funding uses the actual source event and preceding hourly mark OPEN, not an unavailable exact settlement mark.

V4 net with additional5/10/20bp per side is+2.448379/+1.423486/−0.626301. Native extra10bp replays confirm+1.423486 for V4,+0.031837 conditional entry,−6.743090 qualified ranking and+1.051192 thesis compatibility. A one-tick entry trade-through requirement yields43/+2.891918,40/+1.933376,121/−1.616426 and43/+2.519253 respectively. It is a conservative touch sensitivity, not a model of real queue depth. The30-minute passive ledger becomes−0.083502 at extra10bp; it was not given an additional native high-fee replay. Admission costs are not double-charged.

V4's principal positive assets are NEAR+1.472089,WLD+1.455469,ZEC+1.410023; several others lose. No single market removal makes its total negative, but three large trade removals do. Markets and trade outcomes are correlated; the many alternative ledgers are not independent observations. The block intervals remain wide. Changing costs, periods or selection does not establish repeatability.

{chr(10).join(robustness)}

All window ends are exclusive. August5–22 is a distinct17-day period but was inspected by the broader project before this session; it is not independent validation. November3–4 is a newly frozen one-day extension with only one to three fills per policy. It is too short for a consistency claim. The earlier June probe was refused by Gate's10,000-candle retention restriction. Existing current-survivor membership remains a bias; no historical delisted universe or historical contract-spec recovery is claimed. **Independent validation: NOT COMPLETED.** The future November17–December1 holdout was not accessed.

## I. What remains unknown, and how was execution checked?

Unknowns include historical spreads, queue priority and depth, exact within-candle sequencing, some original5m paths, genuine signed delta/CVD/aggressor flow, authentic executed-volume profiles and absorption, historical contract specifications, delisted-market membership and untested market regimes. Real flow and profile economics remain UNKNOWN/NOT_TESTED. Their existing interfaces are preserved. We did not replace them with candle-direction labels or invented institutional orders.

Many individual losing trades remain UNDETERMINED. As-of parent context and feature differences are descriptive unless the original plan actually consumed them. Post-entry paths, touch/acceptance history and chart selections never become admission labels. Missing data are not zero-price paths, and a missed order is not a losing fill.

The evidence contains57 native result records and1,542 independently reconciled trade records, including overlapping alternatives and repeated controls. This is not1,542 independent opportunities. Four frozen controls reproduce their complete archived native trade objects exactly; terminal observation leaves V4/passive objects unchanged. Every new filled trade conserves quantity and reconciles order-notional gross PnL, both-side fees and real-source funding to native net within1.1e−7USDT. Submitted orders pass native ticks/lots/minima and25USDT checks. Complete source/feature/plan/execution seals, native argv/config/archive hashes, command logs and source validation are retained. There are112 new real source series with no futures/mark candle gaps. Historical metadata is explicitly a current public snapshot.

The regression suite ran{tests['run']} distinct checks: **{tests['passed']} passed, two inherited registration errors, one optional authentic-tape skip, zero assertion failures and zero unexpected errors**. It covers causal clocks/pivots/FVG/prefixes, target availability, expiry, native stop-before-TP handling, fixed stops, risk/capacity, funding, research-only refusal, recovery and archive safety. Controlled synthetic mechanics tests establish behavior, not market profit. Same-candle stop/target collisions are retained in ledgers and handled by native ordering; no favorable custom ordering is substituted.

The policy-registration failure has three stale expected hashes: `research/session3/causal_structure.py`, `scripts/guard.py`, `scripts/session3_common.py`. The old paper-freeze failure also reaches the changed causal-structure file. Their actual bytes already existed at PR13 HEAD; prior commit history and expected/actual hashes are recorded. These old guards correctly fail closed. We did not rewrite a registration, freeze or review to make tests green. The new research namespace has its own seals. Repairing historical activation authority is outside this backtest task.

All3,609 pre-existing tracked files, including3,331 evidence files, remain byte-identical. No real/testnet order, persistent paper activation, paid data, additional job, merge, leverage increase, DCA or stop widening occurred. The disposable backtest worker was removed after the runs.

## J. Recommendation for each method

| Method / specific configuration | Status | Reason |
|---|---|---|
| Frozen V4 | PRESERVE_FOR_RESEARCH | Reproducible positive development control; August loss and tail/cost dependence prevent promotion. |
| V4 continuation-only | PROMISING_RESEARCH_ONLY | Positive development diagnostic; selected after seeing playbook results and loses in August. |
| Frozen PR12 structural playbooks | PRESERVE_FOR_RESEARCH | Useful causal interfaces;14 losing development fills do not establish reliable economics. |
| Unconditional0.15ATR passive / five-minute expiry | REJECT_SPECIFIC_RULE | Shared pricing gains are outweighed by missed opportunities; finer execution worsens results. |
| Conditional entry and30-minute passive | NEEDS_MORE_EVIDENCE | Working isolated variants; neither beats V4 consistently or demonstrates robust opportunity value. |
| Structural-only replacement of fast warning | REJECT_SPECIFIC_RULE | Geometric incompatibility and matched deterioration; do not generalize to all structural exits. |
| Thesis compatibility safeguard | PRESERVE_FOR_RESEARCH | Logical repair, partial recovery; still behind V4 and unvalidated. |
| Unconditional EMA relaxation / current qualified-only promotion policy | REJECT_SPECIFIC_RULE | Fails preregistered development improvement criteria; mixed period results are retained. |
| Relaxed ranking alone | NEEDS_MORE_EVIDENCE | Fewer fills and slightly lower base net, somewhat better cost sensitivity; no independent superiority. |
| Integrated first-obstacle policy | NEEDS_MORE_EVIDENCE | Zero joint support; obstacle relevance and executable objectives unresolved. |
| Genuine5m response entries | NEEDS_MORE_EVIDENCE | Two pre-shortlist qualifications and zero portfolio fills are insufficient economic evidence. |
| EMA/VWAP, SMC/ICT structure and liquidity concepts generally | NEEDS_MORE_EVIDENCE | Rejecting individual rules does not reject entire methodologies. |
| Authentic Order Flow / Volume Profile | NEEDS_MORE_EVIDENCE | Historical economics UNKNOWN/NOT_TESTED; preserve interfaces. |

**One next action:** freeze V4, continuation-only and the compatibility safeguard without further tuning, then evaluate the already reserved November17–December1 cohort only after those dates have completed, under the same fees, exposure and genuine5m detail where available. Keep this a historical evaluation; do not start a trading process. That short holdout can falsify current claims, but cannot by itself establish a durable edge.

## Evidence, restore and review

Start with [the evidence index](../README.md), [the full economic report](economic-report.json), [canonical opportunity forensics](opportunity-forensics.json), [six structural changes](structural-changes.json), [the chart index](chart-index.json), and [the restore/replay/rollback runbook](../../../docs/operations/deep-failure-diagnosis.md). Files use UTC; original opportunity IDs join full native portfolios and diagnostics.

The incremental private bundle has{bundle['files']} files,{bundle['bytes']:,} compressed bytes; SHA256 `{bundle['sha256']}`. Full restore and existing-file hydration both verified all files with zero overwrites. Restore the unchanged PR13 private-input bundle first; its SHA256 is `{bundle['prerequisite']['sha256']}`. Both bundles are owner downloads, not exchange credentials. Raw data, feature caches and native SQLite/ZIP/config exports are in these private bundles; reviewable code, ledgers, provenance, charts and reports are in this stacked PR. Exact source/protocol hashes are in the final seal, and pinned image/runtime versions are in each native provenance record.
'''
    text=text.replace('paid data, additional job,','paid data, additional paid job,')
    # Readable prose measurements; protect code spans, identifiers, and links.
    def spacing(match):
        s=match.group(0)
        s=re.sub(r'(?<=[a-z])(?<!\bpr)(?=\d)',' ',s)
        s=re.sub(r'(?<=[A-Za-z])(?=[+−]\d)',' ',s)
        s=re.sub(r'(?<=[a-z])\.(?=\d)','. ',s)
        s=re.sub(r'(?<=[a-z])(?=ATR\b)',' ',s)
        s=re.sub(r'(?<=\d)(?=(?:minutes|minute|files|fills|checks|records|days)\b)',' ',s)
        s=re.sub(r'(?<=\d)(?=(?:USDT|ATR|bp)\b)',' ',s)
        s=re.sub(r'(?<=\d),(?=[A-Za-z])',', ',s)
        s=re.sub(r'(?<=[A-Za-z]),(?=[+−\d])',', ',s)
        s=re.sub(r'(?<=:\*\*)(?=\d)',' ',s)
        s=re.sub(r'([+−-]\d+\.\d+),(?=\d)',r'\1, ',s)
        s=re.sub(r';(?=\d)','; ',s)
        s=s.replace('approximately[','approximately [')
        s=re.sub(r'\b(Aug|Sep|Oct|Nov|August|September|October|November)(?=\d)',r'\1 ',s)
        return s
    text=''.join(part if part.startswith('`') else re.sub(r'[^`]+',spacing,part) for part in re.split(r'(`[^`]*`)',text))
    (OUT/'owner-report.md').write_text(text)
    print('Wrote owner report',len(text.split()),'words',flush=True)

if __name__=='__main__':run()
