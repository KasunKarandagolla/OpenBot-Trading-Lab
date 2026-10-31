# Native leakage diagnostics — TESTED / EXECUTED IN CODEX CLOUD

Final command: `LAB_EXEC_CONTAINER=openbot-s2-runner ./scripts/lab.sh research-lookahead`; exit 0. Pinned Freqtrade 2026.10, callback version 1.0.1, frozen BTC/ETH/SOL cohort July 30–October 30 UTC. Full stdout and native CSVs are retained.

| Strategy | Actual sampled signals | Entry bias | Exit bias | Indicator bias |
|---|---:|---:|---:|---|
| VWAPTrendContinuationV1 | 17 | 0 | 0 | none detected |
| LiquiditySweepReversalV1 | 20 | 0 | 0 | none detected |

VWAP did not reach the target 20 signals. Seventeen is a thin diagnostic sample; absence of detected bias is not universal proof. Sweep sampled 20 rather than all 39 native primary trades. Official diagnostics internally use market orders and larger research wallet settings; custom sizing/admission remains conservative. These diagnostics do not establish realistic limit fills, profitability or independent validation.

Independent tests cover exact closed-hour merge, UTC session reset, shifted range/volume and future-append invariance for both strategies. Native tests establish stop-before-ROI ordering for long and short. There is no retrospectively confirmed pivot package.

A final rerun initially failed after computing the VWAP analysis because native CSV append reloaded blank strings as float under pinned Pandas 3, then rejected a string assignment. Actual failure exit 1 and traceback remain in lookahead-vwap-export-failure.txt. The wrapper now removes only the previous generated local diagnostic CSV before rerunning; native output is copied to evidence on success. No dependency or market-data changes were necessary. The completed fresh-output run above is the final diagnostic.
