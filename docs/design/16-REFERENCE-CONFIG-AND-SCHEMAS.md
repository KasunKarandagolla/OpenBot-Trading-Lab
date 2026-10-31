# 16 — Safe Illustrative Configurations, Data Schemas and Handoff

**WARNING:** Examples are **design templates, not installed or tested executable configs**. Session 1 must generate a valid config using the pinned installed Freqtrade version, then verify every setting. Do not paste a config into a real trading environment without dry-run and no-key checks. Everything below is for synthetic/paper research.

## Illustrative Freqtrade policy values (JSON fragment, not a complete config)

```json
{
  "dry_run": true,
  "dry_run_wallet": 1000,
  "trading_mode": "futures",
  "margin_mode": "isolated",
  "max_open_trades": 2,
  "stake_currency": "USDT",
  "exchange": {
    "name": "binance",
    "key": "",
    "secret": "",
    "pair_whitelist": ["BTC/USDT:USDT", "ETH/USDT:USDT"],
    "pair_blacklist": []
  },
  "api_server": {"enabled": false},
  "force_entry_enable": false
}
```

- Values are **illustrative** and incomplete: e.g. stake amount, actual risk sizing, ROI, stop-loss, unfilled timeout, pairlist handlers, database path, exchange mode availability, server configuration and strategy class are not supplied. Do not deploy as-is.
- For FreqUI owner access, use a **separate verified localhost-only** server configuration with authenticated credentials kept outside the agent environment. `api_server.enabled=false` above is the safe initial synthetic/CLI default, not a UI-enabled end-state.
- In Session 1, run `freqtrade --version`, `freqtrade create-userdir --userdir user_data`, `freqtrade new-config --config user_data/config.json` under the actual pinned installation, review generated settings and run a credential-free synthetic probe. These commands do **not** constitute permission to invoke `download-data` or enable real trading.
- `trading_mode=futures` and `isolated` require exact version, venue support and test validation; if unauthenticated testing isn't available, demonstrate an offline synthetic mode and record futures as BLOCKED rather than secretly using spot performance as futures evidence.

## Example strategy pseudocode (NOT a runnable strategy)

```python
class FrozenTrendBaseline:
    def calculate_context(self, closed_ohlcv):
        # Pinned TA-Lib indicators; validate warm-up and available_at.
        return deterministic_features(closed_ohlcv)

    def decide(self, snapshot, frozen_params):
        if not snapshot.data_rights_ok or not snapshot.is_fresh:
            return NoTrade("DATA_UNAVAILABLE")
        if not all_required_inputs_ready(snapshot):
            return NoTrade("INPUTS_MISSING")
        if not frozen_entry_predicate(snapshot, frozen_params):
            return NoTrade("NO_SIGNAL")
        return ProposedPaperEntry(
            side=frozen_side(snapshot),
            entry_bounds=frozen_bounds(snapshot, frozen_params),
            stop=frozen_stop(snapshot, frozen_params),
            target_policy=frozen_exit_policy(snapshot, frozen_params),
        )
```

The actual Freqtrade strategy uses `IStrategy`, `populate_indicators`, `populate_entry_trend`, `populate_exit_trend` and carefully chosen callbacks, **not** the hypothetical methods above. Code must be aligned with the pinned library rather than generated from pseudocode alone.

## Paper snapshot export — example JSON schema-like shape

```json
{
  "schema_version": "trading-lab.snapshot.v0-proposed",
  "environment": "SYNTHETIC",
  "snapshot_utc": "2026-10-31T10:00:00Z",
  "engine": {"name": "Freqtrade", "version": "PIN_AT_INSTALL", "mode": "dry_run", "healthy": true},
  "strategy": {"id": "trend_baseline", "sha256": "PIN_AT_STRATEGY_FREEZE", "economic_status": "UNQUALIFIED"},
  "data": {"source": "synthetic_fixture", "source_rights": "SIMULATED", "fidelity": "SYNTHETIC", "freshness_seconds": 0},
  "scan": {"scanned": 20, "eligible": 2, "rejected": 18},
  "paper_positions": [],
  "alerts": [],
  "disallowed_operations": ["exchange_order", "forceenter", "switch_live", "edit_strategy"],
  "report_sha256": "CALCULATE_ON_EXPORT"
}
```

`healthy`, `eligible`, `freshness` and `positions` must originate from actual observed engine state in production of this report—not from invented text. The `disallowed_operations` list is descriptive only; security enforcement must exist in the host/permissions. Never include passwords or API tokens.

## Example OpenBot read-only tool request

```json
{
  "tool": "get_latest_scan",
  "arguments": {"limit": 10},
  "expected_output": "sanitized, versioned JSON report from approved exporter",
  "permission": "READ_ONLY",
  "implementation_status": "PROPOSED_NOT_BUILT"
}
```

This example is **not** claimed as an actual OpenBot MCP function signature. Session 1 must discover and verify its supported integration protocol with the installed OpenBot release. A local file export via a sandbox-separated directory may be sufficient.

## Command examples for future controlled verification

Official Freqtrade commands to evaluate under pinned installation (do not run downloads until approved):

```bash
freqtrade --version
freqtrade create-userdir --userdir user_data
freqtrade new-config --config user_data/config.json
# Using only an approved local historical dataset:
freqtrade backtesting --config user_data/config.json --strategy QualifiedResearchStrategy
# Leakage probe, only if approved data and strategy fixtures exist:
freqtrade lookahead-analysis --config user_data/config.json --strategy QualifiedResearchStrategy
```

Not included deliberately: commands to create Binance keys, invoke `forceenter`, switch off dry-run, start real trading or fetch Binance Vision archives. Using the above strategy name before its actual creation will fail; these are reference command structures, not a claimed runnable demo.

## Session 1 handoff minimum

Deliver: OS/environment inventory, exact installed releases and licensing results, validated no-key config, successful synthetic deterministic signal and FreqUI report, read-only OpenBot snapshot invocation, proof that agent cannot reach paper-state admin/mutable files, exact resource/storage measurements and owner-facing startup instructions. Anything less is **INCOMPLETE**, not a reason to spend another session automatically.
