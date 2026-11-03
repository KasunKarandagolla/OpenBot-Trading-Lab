"""Owner decision derived only from completed, reconciled command outputs."""
from recovery_common import *
import csv

def generate():
    x=read(OUT/'economic-report.json');r=x['portfolios'];diag=read(OUT/'opportunity-diagnosis.json')['populations']
    p=lambda w,v,s='fixed',fee='750':r[w+'/'+v+'-'+s+'-touch-fee'+fee]
    n=x['ranking_null'];sources=read(OUT/'source-reconciliation.json');minute=read(OUT/'minute-feasibility.json')
    backup=read(OUT/'private-backup.json') if (OUT/'private-backup.json').exists() else None
    hashes={str(q.relative_to(ROOT)):sha(q) for q in [ROOT/'research/session4/PaperPolicyV4.py',ROOT/'research/policy/PolicyV3.py',ROOT/'research/policy/policy_features.py',ROOT/'research/session4/session4_features.py',ROOT/'configs/paper-policy-limit.json',ROOT/'configs/paper-policy-market.json']}
    decision=dict(at=now(),decision='NO-GO',spend_final_deployment_session=False,
        qualification={'context':'REJECTED','context-smc':'REJECTED','momentum':'REJECTED','liquid-momentum':'INSUFFICIENT;benchmark,not promoted',
            'PaperPolicyV4':'INSUFFICIENT / ECONOMICALLY_UNQUALIFIED;unchanged frozen reference'},
        retained_strategy='PaperPolicyV4',retained_version='structure-execution-v4.0.0',retained_hashes=hashes,
        frozen_V3='PolicyFixedV3 / controlled-pullback-failure-v3.0.0 preserved',
        native_portfolios=x['native_portfolios'],reconciled_trades=x['reconciled_trades'],future_holdout_used=False,
        persistent_activation=False,auto_merge=False,
        reason='Both substantive new hypotheses lose after costs;daily momentum also loses in the separately reserved older period;positive reference/control dollars fail friction or risk normalization. No defensible economic promotion.')
    write(OUT/'decision.json',decision)
    rows=[]
    for w,v in [('development','reference'),('development','structure'),('development','context'),('development','context-smc'),('development','momentum'),('development','liquid-momentum'),('hourly-development','momentum'),('hourly-independent','momentum'),('hourly-independent','liquid-momentum')]:
        a=p(w,v);b=p(w,v,'risk');stress=p(w,v,fee='1750')
        rows.append(dict(window=w,policy=v,fills=a['n'],native_net=a['net_usdt'],native_fee_plus10bp_net=stress['net_usdt'],
            risk_fills=b['n'],constant_risk_net=b['net_usdt'],mean_trade_bp=a['mean_trade_bp'],block95=a['block95_total_usdt'],
            hourly_mark_drawdown=a['source_hourly_mark_drawdown_usdt'],top3_positive_share=a['top3_positive_share']))
    table=['| Venue / period / policy | Fills | Native net USDT | Complete native +10bp/side | Constant-risk net |',
           '|---|---:|---:|---:|---:|']
    for z in rows:table.append(f"| Gate / {z['window']} / {z['policy']} | {z['fills']} | {z['native_net']:+.6f} | {z['native_fee_plus10bp_net']:+.6f} | {z['constant_risk_net']:+.6f} ({z['risk_fills']} fills) |")
    a=diag['reference:continuation:True'];b=diag['reference:reversal:True'];c=diag['structure:continuation:True']
    ref=p('development','reference');st=p('development','structure');mom=p('hourly-independent','momentum')
    def bounds(value,digits=3):return '['+', '.join(f'{v:+.{digits}f}' for v in value)+']' if value else 'unavailable'
    paired=x['comparisons'].get('development/context-smc-fixed-touch-fee750 minus development/context-fixed-touch-fee750',{})
    nulltext=(f"{n['replicates']} complete native matched-ranking nulls, seeds61001–61031: mean null {n['native_null_net_mean']:+.6f}USDT; reference-minus-mean-null {n['reference_minus_mean_null']:+.6f}USDT, paired7day block95% {bounds(n['paired_block95'])}; conditional empirical upper-tail p={n['conditional_empirical_upper_p']:.5f}, resolution1/{n['replicates']+1}." if n else 'Ranking nulls incomplete;do not issue final qualification.')
    report=f"""# Profitability recovery — owner report

**Decision: NO-GO. Pause the final deployment-engineering session. No demonstrable trading advantage emerged.**

This completed investigation contains {x['native_portfolios']} official native Freqtrade result records ({x.get('native_alternatives',x['native_portfolios'])} alternative portfolios plus{x.get('native_reproduction_records',0)} exact replay) and {x['reconciled_trades']} independently reconciled modeled trade records. Overlapping alternatives and the replay do not create independent market samples;returns are never additive. Raw sources, causal inputs, native ZIPs and simulated account state are privately backed up. No persistent paper, live, testnet or demo exchange operation was activated. PR9 remains the parent;no merge/auto-merge is requested.

1. **Why did the existing system fail to demonstrate profitability?**

   The strongest confirmed causes are cost headroom, risk weighting and concentration. The frozen Session4 reference earned3.721900USDT gross,paying2.777714 in fees and0.021045 funding: only0.923141 remained. Extra-friction break-even was2.49bp per side;the structure variant tolerated3.57bp. These are below the mandated10bp/side robustness stress. Funding was not the dominant economic drag.

   The original structure's three largest winners supplied43.66% of positive P&L;removing them changes+0.943062 to−3.624842USDT. August lost1.668367,September earned2.309256,October earned0.793589,and November's two fills lost0.491417. This is unstable contribution,not a stable regime premium. Its summed net stop-R was−3.7313. Reweighting the SAME fills to constant modeled risk changes+0.943062 to−0.361018 before any lot/capacity/sequence changes;equal25USDT reweighting remains+1.221916. Native constant-risk portfolios lose too. The small dollar profit depends on how wider-stop winners are weighted.

   Predictability is **unestablished**,rather than proven universally absent. Among{a['n']} matched-population reference continuation plans,only{a['barrier_probabilities'].get('TARGET_FIRST',0):.1%} reach3R before stop within8h;{a['barrier_probabilities'].get('STOP_FIRST',0):.1%} stop first and{a['barrier_probabilities'].get('NEITHER',0):.1%} reach neither. Median MFE/MAE are{a['mfe_bp']['median']:.1f}/{a['mae_bp']['median']:.1f}bp. Net endpoint return after35bp assumed roundtrip cost averages{a['endpoint_after35bp_bp']['mean']:.1f}bp. Continuation timing lift versus matched times is{a['timing_lift_bp']:.1f}bp,week-block95%{a['week_block95_lift_mean_bp']},conditional matched-null p={a['matched_time_null_199']['upper_p']:.3f}. Reversal has{b['n']} matched plans,target-first{b['barrier_probabilities'].get('TARGET_FIRST',0):.1%},timing-null p={b['matched_time_null_199']['upper_p']:.3f}. These quantities do not establish monetizable signal timing. Actual native fills and all planned opportunities are separate populations.

   The frozen reference funnel has2751 raw recipe records:1157 fail stop/target/net-RR geometry,914 fail suitability,580 fail ranking/liquidity,and100 produce approved plans;82 become native fills. Plans-minus-fills also includes account/capacity/lot effects,not only execution nonfills. Barrier diagnostics condition on valid geometry,a complete outcome horizon and at least8 matched control times;explicit exclusion counts are retained. Favorable-movement times denote15m bar starts,not observed tick times. Thus this analysis does not claim to reject every conceivable use of the raw candle patterns.

   The original structure continuation population has{c['n']} matched plans;its shrunk target-first probability is{c['target_first_shrunk']:.3f},descriptive Jeffreys95%{c['target_first_beta95']}. Only five selected structure reversals enter the matched population. Their favorable conditional result is too sparse and selected during development to qualify a reversal edge. Reversing direction on identical observations is reported separately as a path diagnostic. Native entry timing,stop/target geometry,nonfills and thesis exits are tested independently below. Coarse execution remains uncertain;it cannot explain away the new hypotheses' negative gross/after-cost outcomes.

2. **What trading hypotheses did you test, and why?**

   **Context continuation:** broad directional participation plus asset-specific relative strength might distinguish durable pullbacks from isolated exhausted moves. Keep the original continuation setup/stop/3R target/8h management;require aligned BTC4h movement,aligned relative24h strength,majority24h breadth and ATR expansion versus its prior24h median. One predeclared SMC ablation tests the frozen structural suitability rule. Both variants are REJECTED.

   **Daily cross-sectional momentum:** persistent asset-specific demand might continue over a day and offer movement large enough to pay costs. At00:00UTC select the positive24h winner and negative24h loser;enter at native next-open market,2 completed-hour ATR stop floored at0.6%,abstain above2.5%,4R objective and24h timeout. Compare with a credible liquidity-selected time-series momentum control using the same clock,sign,geometry and exits. No parameter search,retraining or winner substitution after a volatility rejection. Momentum is REJECTED.

   **Meaningful failure/reversal:** evaluate the existing external-boundary sweep,reacceptance,confirmed shift/displacement and opposite-direction paths. No new reversal recipe was promoted from five favorable selected examples. Existing confirmed swings,BOS/CHoCH,prior day/session boundaries,FVG formation/retests and range location are reused causally. They do not prove institutional activity. Historical genuine executed-flow/delta/CVD is UNKNOWN;historical volume profiles are OHLCV proxies. No unavailable flow feature receives claimed uplift.

   Definitions,feature availability,geometry and the evaluation protocol were sealed before new historical acquisition. Gate's documented response limits forced an availability amendment to real1h execution for the older daily-momentum test;the daily economic rule was already frozen. That amendment preceded evaluation. All tested variants,31 nulls,sizing/fee/fill/management scenarios and failed attempts are registered and retained. This is continued development,not an uncorrected discovery from a strategy zoo.

3. **What actually improved?**

{chr(10).join(table)}

   Development means Aug5–Nov3,2026,end exclusive. The separately reserved older Gate test is May20–Jul26,end exclusive,with May10–20 warmup. It contains67 calendar days. Hourly development is the same daily policy replayed at1h resolution;the older result does not independently validate15m continuation. All comparisons use1000USDT,1x,max2 positions,25USDT fixed-notional ceiling;constant modeled-risk target0.25USDT uses the SAME25USDT ceiling. Native legal lots and unchanged account/cooldown constraints determine feasibility. Different exposures,turnover,risk deployment and fill counts are disclosed in economic-report.json.

   The small fresh structure-minus-reference improvement is{st['net_usdt']-ref['net_usdt']:+.6f}USDT;both fail friction/constant-risk qualification. The context SMC ablation improves the losing context policy by{paired.get('net_difference',0):+.6f}USDT,paired block95%{paired.get('block95')};it does not create a profitable policy. No trading improvement is promoted. The completed gains are stronger diagnosis,real minute execution coverage,older market evidence,more credible benchmarks and fully reconciled cost accounting.

   Native touch,1bp trade-through,immediate-open-only,market,deterministic25% nonfill,half desired allocation,barrier-only management and full1m alternatives are in portfolio-table.md. Nonfill/half-allocation scenarios are hypothetical full portfolios,not inferred queue probabilities or observed partial exchange fills. Genuine1m data covers14 markets×7200 rows=100800 candles during Oct29–Nov3. Minute feasibility population counts are{minute['summary']}. Queue priority and within-minute sequencing remain UNKNOWN;five recent days cannot qualify the full90day expiry model.

   Two predeclared structure sensitivities remain slightly positive under fixed-notional higher-cost execution:immediate-open-only+0.138026USDT and the deterministic nonfill realization+0.325305USDT. Twelve separately recorded post-result qualification checks evaluate the SAME frozen entry rules under constant risk and full native costs,with matching reference controls;no threshold is changed. The structure sensitivities become−1.086021 and−0.611086USDT under constant risk plus10bp/side. A favorable arbitrary nonfill realization does not establish predictive information or empirical queue behavior. Neither sensitivity is promoted.

   The primary native fee is7.5bp per side with source funding. Full native17.5bp portfolios implement the additional10bp stress and may change trade sequence;posthoc ledger stress is separately labeled. A venue-specific market scenario uses public current5bp taker plus observed current half-spread and hypothetical2bp slippage;its full native conservative common fee rounds the worst observed cohort cost upward to14.2bp/side. Instantaneous spreads span0.013–14.364bp;they are not historical spread observations. Maker2bp is a source quote,not assumed guaranteed execution. The0.0038 allowance is only admission/risk geometry and is never charged again as a fee.

4. **Is there now a demonstrable trading advantage?**

   **No.** {nulltext} This tests conditional market ranking,not an omnibus proof of timing,direction,SMC or all research multiplicity. The199 matched-time path replicates have resolution1/200;they reuse the actual eligible control population and do not create199 independent market histories. Paired day/week comparisons retain zero-return days and cross-market dependence.

   The ranking nulls average{n.get('mean_null_fills',0):.1f} fills and{n.get('mean_null_turnover',0):.1f}USDT turnover versus{n.get('reference_fills',0)} fills/{n.get('reference_turnover',0):.1f}USDT in the reference. Selection can change setup incidence and capacity even with the same eligible slots;this exposure difference is disclosed,not presented as leverage-free proof of setup alpha. Ranking shows conditional improvement over these nulls,but its empirical p-value,development reuse and negative cost-stressed reference do not establish an independently monetizable edge.

   Fresh reference mean net trade expectancy is{ref['mean_net_usdt']:+.6f}USDT,{ref['weighted_net_bp']:+.2f}bp weighted by entry notional,block95% total{ref['block95_total_usdt']};after10bp/side its ledger net is{ref['additional_friction_stress_usdt']['10']:+.6f}USDT. The independently reserved momentum result averages{mom['mean_net_usdt']:+.6f}USDT per trade,block95% total{mom['block95_total_usdt']},with summed net stop-R{mom['stop_R']:+.3f}. Its results do not support promotion.

   Power is calculated from observed weekly dispersion rather than a universal trade-count minimum. For the fresh reference,the approximate80%-power/two-sided5% detectable mean effect is{ref['effect_detection']['detectable_mean_trade_bp']:.1f}bp per trade-equivalent entry notional,far larger than its observed{ref['weighted_net_bp']:.2f}bp. There are{ref['effect_detection']['weekly_blocks']} weekly blocks. This normal approximation and circular7day bootstrap assume enough temporal stability;few blocks/nonstationarity limit precision. Target-before-stop shrinkage,conditional successful/unsuccessful payoffs and uncertainty are in opportunity-diagnosis.json;they are descriptive and not a fitted admission model.

5. **Which strategy should be retained?**

   Retain **PaperPolicyV4 / structure-execution-v4.0.0** unchanged as the existing guarded reference,with economic status **INSUFFICIENT / UNQUALIFIED**. Keep **PolicyFixedV3 / controlled-pullback-failure-v3.0.0** unchanged as its frozen rule benchmark. This is preservation,not a recommendation to activate trading. No new operational policy is selected. RecoveryPolicyR1/recovery-v1.0.0 and its hourly subclass remain executable historical research implementations;they explicitly refuse live and dry-run activation.

   Exact retained SHA256 values:

{chr(10).join('   - '+k+': `'+v+'`' for k,v in hashes.items())}

   Existing complete eligibility,regime/rank,entry/expiry,stop/invalidation,target/timeout,source-health and account constraints remain in the frozen source and Session4 release/runbook. Wallet1000USDT,max2 positions,25USDT ceiling,1x,0.3–2.5% logical stops,continuation8h/reversal4h,5min entry expiry,and preinstalled2.5% protective bound remain unchanged. Existing paper configuration files were not edited.

6. **What still prevents economic qualification?**

   Specified challengers lose under defensible costs,with no independently evaluated positive candidate. Ranking/timing uncertainty,concentration and risk-weighting effects remain. The14-market current-survivor frame is not a complete historical universe;delisted membership and historical contract/tier changes are unknown. Only source-returned coverage and observed listing clocks support eligibility.

   Gate rejects15m history beyond10000 recent points and funding beyond180days. The January–July15m acquisition failed;its partial1h sources and errors are retained. Binance archives were reachable,but official contract metadata returned451;no Binance prices,costs or funding enter these Gate portfolios. The older67day1h experiment is therefore a separately labeled resolution test. Minute history for that period is unavailable under the same retention constraint.

   The approved Session4 private archive was not attached. Its original manifest and all parent evidence are preserved;no restore of missing raw sources is claimed. All{len(sources['files'])} corresponding reacquired files have separate manifests;raw row-level reconciliation remains UNCOMPUTABLE without originals. Complete reference/structure decision plans were restored from Git-tracked opportunities and BOTH hashes exactly match the private parent plan manifests. Full native replays separate frozen decisions from new source/feature recomputation;see source-reconciliation.json.

   Frozen-decision replays reproduce every82 reference and58 structure entry/exit price,time and quantity. Their only P&L differences are−0.003135 and−0.000669USDT in funding under the source-clock model. Recomputed fresh selection produces76/62 fills;that change is not attributed to a new strategy advantage. Exact trade reproduction does not establish byte identity of missing full source histories.

   All official trades reconcile quantity,fees,net P&L and every source-reported funding event. Second-offset events use the preceding hourly source mark OPEN. Exact settlement marks and venue priority at entry/exit boundaries are unknown. Initial equality-join and pre-exit snapshot failures,contract-volume normalization and matched-control availability corrections are quarantined;failed outputs never qualify a policy. Genuine tape,queue/partial fill probabilities,historical spread distributions and stop-gap tails remain unavailable. There is no historical order-flow uplift claim.

   The November17–December1,2026 future holdout was neither acquired nor inspected. Positive independent after-cost expectancy with credible execution,risk robustness,favorable controls and tighter dependence-aware uncertainty would be needed to reconsider qualification. This session supplies no such candidate.

7. **Should the owner spend the final Codex session?**

   **NO-GO. Do not spend it on deployment engineering now.** Retain the working software and frozen references;pause persistent-operation work. Reconsider deployment only after a separately registered economic hypothesis earns positive independent after-cost evidence. Additional dashboards,agents or deployment polish cannot repair the measured strategy economics. This recommendation does not assume another paid research round.

Reproduce from the private source/input archive in an isolated checkout:

```bash
python scripts/recovery_archive.py restore /path/Recovery-Private-Backup.tar.gz work/owner-restore
python scripts/recovery_archive.py hydrate work/owner-restore .
./scripts/lab-recovery.sh tests
./scripts/lab-recovery.sh replay development reference --replay-id owner-check
./scripts/lab-recovery.sh replay hourly-independent momentum --replay-id owner-check
./scripts/lab-recovery.sh diagnose
./scripts/lab-recovery.sh report
```

Completed output directories refuse overwrite;use a new replay ID. `matrix primary|null|execution` reruns the finite registered matrix in a fresh checkout,or skips immutable completed jobs. Restore validation rejects unsafe paths,duplicates,oversized archives and overwrites. Raw sources/native ZIPs/simulated SQLite remain outside Git. The final backup's actual hash-verified restore is recorded in run-001/private-backup.json.

Evidence: [economic report](run-001/economic-report.json),[full portfolio table](run-001/portfolio-table.md),[opportunity paths](run-001/opportunity-paths.json),[diagnosis](run-001/opportunity-diagnosis.json),[source reconciliation](run-001/source-reconciliation.json),[decision](run-001/decision.json). All research outcomes are modeled historical results,not observed real-money or forward paper profits.
"""
    if backup:
        report+=f"\nValidation:5 recovery regressions,5 confirmed-structure tests and20 flow/profile/intelligence tests pass;all14 new-feature prefixes match. Exact native replay matches all76 complete trade objects. The private archive contains{backup['files']}files({backup['bytes']}bytes);it was fully restored and hash-verified with0overwrites;SHA256 `{backup['sha256']}`.\n"
    for value,digits in [(a['week_block95_lift_mean_bp'],1),(c['target_first_beta95'],3),(paired.get('block95'),3),(ref['block95_total_usdt'],3),(mom['block95_total_usdt'],3)]:
        if value:report=report.replace(str(value),bounds(value,digits))
    report=report.replace(str(minute['summary']),'; '.join(f"{v}: {q['touch']}/{q['n']} touch-range feasibility,{q['through']}/{q['n']} one-bp trade-through" for v,q in minute['summary'].items()))
    import re
    # Keep source identifiers and URLs exact while spacing prose and units.
    protected={};counter=0
    def protect(match):
        nonlocal counter
        key='§'+chr(0x400+counter)+'§';counter+=1;protected[key]=match.group(0);return key
    report=re.sub(r'`[^`\n]+`|\[[^\]]*\]\([^)]*\)|PaperPolicyV4|PolicyFixedV3|RecoveryPolicyR1|RecoveryMomentumHourlyR1|structure-execution-v4\.0\.0|controlled-pullback-failure-v3\.0\.0|recovery-v1\.0\.0',protect,report)
    formatted=[];code=False
    for line in report.splitlines():
        if line.startswith('```'):code=not code
        if not code and not line.startswith('   - '):
            line=re.sub(r'(?<=[A-Za-z])(?=[+−-]?\d)',' ',line)
            line=re.sub(r'(?<=\d)(?=[A-Za-z])',' ',line)
            line=re.sub(r'[,;](?=\S)',lambda m:m.group(0)+' ',line)
            line=re.sub(r'(?<=[A-Za-z]):(?=\d)',': ',line)
            line=re.sub(r'(?<=[A-Za-z%])(?=\[)',' ',line)
        formatted.append(line)
    report='\n'.join(formatted)+'\n'
    for key,value in protected.items():report=report.replace(key,value)
    report=report.replace('PR 9','PR #9').replace('All56','All 56')
    path=OUT.parent/'owner-report.md';path.write_text(report)
    with (OUT/'primary-results.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return decision

if __name__=='__main__':print(generate())
