# Selected component checks

Pinned official image: Freqtrade 2026.10, CCXT 4.5.90, Python 3.14.10. No dependency upgrade or new package installation.

The installed `freqtrade.data.converter.orderflow.trades_to_volumeprofile_with_total_delta_bid_ask` bins side-labelled trades into price levels and sums base amounts. The bonus collector calls that implementation directly; its source hash is in each observation. Gate's [USDT futures WebSocket documentation](https://www.gate.com/docs/developers/futures/ws/#trades-notification) states: “Positive size means taker is buyer，negative seller”. Contract size converts signed contracts into base units. Internal nonmatching insurance/ADL prints are excluded. These are executed aggressor volumes, not resting liquidity or proof of absorption.

The [py-market-profile project](https://github.com/bfolkens/py-market-profile) accepts candle price/volume series and provides POC, value area and nodes. Its candle input cannot recover actual traded volume by price. Adding a dependency would not solve historical fidelity. The bonus uses the existing NumPy/Pandas environment for bounded weighted bins and adjacent-bin value-area expansion, plus the native Freqtrade footprint for real trades. This is a small wrapper/calculation, not a replacement indicator platform. No runtime compatibility claim is made for the uninstalled package.

The historical proxy explicitly puts candle base volume at typical price in a fixed 10bp log grid. Its prior 96 bars exclude the signal candle. True captured profiles use actual observed execution prices/base volume. These cohorts are never pooled as equivalent economic observations.

Session3 causal pivots, BOS/CHoCH, confirmed-hour handling and the original scanner/eligibility exporter are reused unchanged. The prior losing StructureAwareSweepV1 is rerun as an explicit negative control.

Documentation was inspected through the web connector after a direct document request returned HTTP403. The actual public REST and WebSocket feeds were accessible through the configured proxy with TLS verification enabled.
