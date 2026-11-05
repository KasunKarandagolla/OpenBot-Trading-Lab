# Local Binance recovery

The five-minute challenger runs in disposable Freqtrade 2026.10 backtests. Use the isolated Linux checkout and the already-installed image digest in the wrapper. The Git branch contains the workflow, tests, protocol and handoff. Source archives, derived market data, exchange snapshots, analysis packets and native results belong under the ignored local data directory.

## Reproduce

Start from a new checkout with the same PR #16 ancestry. Keep the original run for review. A fresh download of current exchange information changes the scenario. Preserve the captured snapshot and source manifest for an identical-input replay.

```bash
git log -1 --oneline
docker image inspect freqtradeorg/freqtrade@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7
mkdir -p user_data/data/local_recovery
python3 scripts/binance_data.py probe
python3 scripts/local_recovery_data.py inventory
python3 scripts/local_recovery_data.py acquire
curl -fSs --max-time 12 --max-filesize 2097152 \
  https://fapi.binance.com/fapi/v1/exchangeInfo \
  -o user_data/data/local_recovery/current-exchangeinfo.json
scripts/lab-local-recovery.sh convert
scripts/lab-local-recovery.sh freeze
scripts/lab-local-recovery.sh scan development
scripts/lab-local-recovery.sh test
scripts/lab-local-recovery.sh replay development
scripts/lab-local-recovery.sh replay development --mode market
scripts/lab-local-recovery.sh replay development --mode touch
scripts/lab-local-recovery.sh scan validation
scripts/lab-local-recovery.sh replay validation
scripts/lab-local-recovery.sh scan holdout
scripts/lab-local-recovery.sh replay holdout
scripts/lab-local-recovery.sh report
```

The held-out dates were frozen before inspection in this study. Any subsequent experiment should treat these outcomes as seen. The cohort is a 24-symbol convenience panel with eligibility calculated from completed historical data. Current Binance status and filters serve as an explicit execution scenario only. The archive inventory reports directory coverage. Historical contract status, fee tier and spread remain unknown.

The order timestamp is the close of a five-minute candle, which is also the timestamp of the next candle's open. A one-candle limit tests a one-tick trade-through in the primary replay. Touch and market use the same development opportunity IDs. Native protection uses the absolute stop and full first objective. The funding join uses the exact archived event time and the mark candle open in its hour. Trade-through cannot recover order queue priority or intra-candle sequence.

## Generate and verify the visual handoff

Matplotlib was staged in `user_data/data/local_recovery/mpl` with the pinned image's Python. Use Matplotlib 3.10.8 in that local target if it is absent. The container wrapper runs the rendering without networking.

```bash
scripts/lab-local-recovery.sh charts development
packets=user_data/data/local_recovery/development/analysis-packets
for card in "$packets"/*/evidence-card.json; do
  python3 scripts/local_recovery_verify_packet.py "$(dirname "$card")"
done
```

See [manual visual evaluation](../../research/local_recovery/manual-visual-evaluation.md). The source license permits the bounded personal research use here. Review the terms before any redistribution. [Binance Vision Dataset Terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md)

## Roll back

To inspect the prior state, create a separate checkout at `91bcedfba3569c08933c03c144caeb96d47a524c`. Preserve the ignored research directory if exact reproduction matters. There is no running recovery service to stop.
