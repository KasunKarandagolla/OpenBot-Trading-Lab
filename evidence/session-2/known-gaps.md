# Known gaps and enforcement boundary

CODE IMPLEMENTED / TESTED: two real IStrategy classes, causal technical features, symmetric signal truth tables, native after-fill fixed stops/custom ROI, holding exit requests, conservative fixed sizing and admission caps, no-chase expiry/timeout and frozen research/config allowlist. Both remain research-only in guard; baseline paper selection is unchanged.

TESTED within model limits: <=25 USDT,1x, max 2/one-symbol/noDCA, fee-inclusive intended risk<=2.5USDT/trade/5aggregate using3% emergency-stop reserve+0.35% costs. This is intended loss under allowances. Actual losses through gaps, downtime, higher funding or adverse stop execution are not bounded by it.

NOT ENFORCED: full 1% UTC mark-to-market account-loss daily halt. The implementation only halts new entries at <=-10 USDT closed realized UTC-day profit; it filters future close dates in backtesting and fails closed if state is unavailable. It does not liquidate current positions or include unrealized P&L. No full risk-qualified extended paper policy is claimed.

OWNER-HOST VERIFICATION REQUIRED: restart with pending/partially filled orders, SQLite backup/restore with positions, browser rendering, source/jurisdiction eligibility, long-running operation and outage recovery. New callbacks were tested through native simulations and deterministic fixtures, not a persistent challenger paper process. No challenger was activated. Paper stops require a running engine.

No OpenBot installed, MCP/admin bridge, automatic promotion, paid feed, exchange keys, private endpoints, real/testnet orders, main modification or merge. The environment's configured demo credential names were never forwarded to the runner. Future report-reader isolation is not implemented in this session.
