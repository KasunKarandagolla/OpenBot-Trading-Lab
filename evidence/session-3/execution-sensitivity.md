# Executed native finer-candle sensitivity

Predeclared October1–October30 2026 UTC DEVELOPMENT window, BTC/ETH/SOL, copied and hash-verified15m/1h/mark/funding data plus bounded actual5m candles. Separate local detail directory; source manifest retains every hash and request count.

Official `--timeframe-detail 5m` completed against same-window coarse15m runs with identical strategies/risk/costs. Parent10 trades, -0.38629737USDT; advanced1 trade, -0.09962120USDT in both modes. Native DD, fills/admission totals and exit P&L did not change. Field-level comparison below records any timing changes; these must not be confused with queue validation.

```json
{
  "LiquiditySweepReversalV1": {
    "counts": {
      "coarse": 10,
      "fine": 10
    },
    "matching_by_pair_side_open_date": true,
    "changed_field_counts": {
      "open_date": 0,
      "close_date": 5,
      "open_rate": 0,
      "close_rate": 0,
      "exit_reason": 0,
      "profit_abs": 0,
      "trade_duration": 5
    }
  },
  "StructureAwareSweepV1": {
    "counts": {
      "coarse": 1,
      "fine": 1
    },
    "matching_by_pair_side_open_date": true,
    "changed_field_counts": {
      "open_date": 0,
      "close_date": 0,
      "open_rate": 0,
      "close_rate": 0,
      "exit_reason": 0,
      "profit_abs": 0,
      "trade_duration": 0
    }
  }
}
```

Only this small development window was tested. The full86-day window is outside5m10000-bar retention. Finer candles do not reproduce queue priority, partial fills, historical spreads, latency, outages or real fills. Extra5/10/20bp costs remain posthoc turnover sensitivity and do not refill trades. No contemporary spread is treated as measured historical spread. Native full results/CSV/logs are in execution-detail/.
