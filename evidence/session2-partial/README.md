# Session 2 partial: pinned historical watchlist replay

**PARTIAL / RESEARCH ONLY / NO MERGE.** This is not the requested completed
Session 2. There is no active v3 skill pack, current-market discovery, live watcher,
native five-agent acceptance, new Freqtrade challenger, economic qualification,
or 24/7 operation. Trigger candidates below are observations, not orders or trade plans.

## What changed

The v1 SQLite database migrates to v2 without rewriting existing setup or event rows.
It gains an immutable binding to one of twelve repository-pinned historical casebook
inputs. A matching input digest, case identity, venue, symbol, 5m bar digest, available
prefix and setup cutoff are required before replay. A legacy setup cannot be upgraded
into a pinned setup, because old observations may have come from unverified bars.
The old `observe`/`tick` raw-bar interface fails closed; LIVE remains unavailable.
Existing setup and event records remain immutable. Expiry reconciliation does not
require another bar, and `case-tick` uses only the completed prefix for state decisions.

The repository pin establishes identity with the reviewed casebook export. It is not
an exchange signature, proof of fresh HTTPS capture, or a new validation of the original
archive; the casebook reports that earlier archive checks were performed. A malicious
or altered checkout is not a trust anchor. The setup's hypothesis and levels are still
researcher-supplied and are not proven correct by the source pin. The two-close breakout
acceptance and same-bar excursion/reclaim observations are simple research models, not
full multi-timeframe, financially qualified strategies. Distance to a level uses the
mean range of 24 prior 5m bars solely for a provisional APPROACHING label.

From the checkout root:

```bash
PYTHONPATH=scripts python3 -m unittest discover -s tests -p test_watchlist.py -v
PYTHONPATH=scripts python3 evidence/session2-partial/replay.py
python3 -m trading_lab.watchlist --help  # set PYTHONPATH=scripts as above
```

The replay reads fixed, previously studied casebook inputs B01–B03 and derives
24-bar high/low references at bar 300. It then advances 48 completed bars one at
a time. It creates four separate hypotheses per symbol, totaling 12 across FILUSDT,
XLMUSDT and ARBUSDT. On restart all 12 setup definitions were recovered. The
recorded run includes sweep/reclaim and breakout/retest observations and invalidations;
see `case-replay.json` for timestamps, reasons and SHA-256 pins. This is neither a broad
scan nor an independent holdout. The stop references are experimental boundaries,
not executable risk plans. No fills, fees, P&L or predictive success are calculated.

The Session 1 historical `evidence/watchlist-s1/reproduce.py` uses the now-disabled
unbound raw-bar function and is retained as historical evidence; use the Session 2
replay above. Its prior output remains unchanged.

## Test environment and limitations

The pinned `freqtradeorg/freqtrade` 2026.10 image is present and can run with no
network, a read-only checkout and read-only preserved research data. It does not
include Matplotlib. The full compatibility attempt ran 102 tests: 99 passed, three
real-packet chart tests errored on `ModuleNotFoundError: matplotlib`. No chart tests
were claimed as passing. A subsequent run explicitly excluded those three chart tests
and passed the other 100 tests with real packet and historical fixtures mounted
read-only. Earlier attempts also exposed a test-ordering mistake and a
mount name that violated the packet's sealed candidate identity; both were corrected.
The original installer drift test used the first filesystem glob result, which could
be the unrelated generic skill. It now selects an explicit installed assignment; the
installer's code and protected owner profiles were not changed.

Public Binance and GitHub hostnames did not resolve from the shell in this sandbox.
The GitHub connector verified PR #18–#21 and supplied the exact missing PR #21 blobs;
the reconstructed starting commit and tree matched GitHub. The installed OpenBot CLI
requires its Local scripts URL/token markers; both were absent in its documented
Windows automation directory. Its documented CLI message interface exposes task text,
not an image-attachment option. No separate native OpenBot connector was available.
No agent message, native image, or independent reviewer receipt was obtained; enabling
agent Local scripts or changing identities, permissions and installed skill roots was
outside this work. Native five-agent status remains AGENT_NOT_VERIFIED / NO ACTION.

## Review findings and remaining risks

These were implementation self-reviews, not four independent specialist reviews.

- **Source and persistence:** the inherited raw hash could be arbitrary and the old
  replay accepted it. The raw observation path now fails closed and new replays bind
  immutable setup IDs to pinned case inputs. Regression tests cover wrong symbol/hash,
  unbound setups, repeat processing, migration, restart and SQLite backup integrity.
  This does not implement fresh public REST receipts, corrections or exchange authentication.
- **Chronology:** validating all future bar contents during a historical run could
  leak future data quality into a decision. Prefix validation now stops at the as-of
  boundary; a regression injects a malformed future bar. Input hash verification still
  reads the sealed complete case export as bytes, which is an integrity check rather
  than a claim that these cases were prospective.
- **Risk and market interpretation:** the 5m event models do not establish 4h/1h
  structure, economic feasibility, stop quality, fills, or profit. They cannot feed a
  trade gate. The deterministic risk code and frozen strategies are untouched.
- **Architecture and tests:** there is no incremental live feed, broad screening,
  cache invalidation, reconciliation daemon, feature migration policy or Freqtrade
  challenger. The v2 migration and event transaction are covered, but no concurrent
  multi-process stress, independently conducted review, 24-hour soak or live restart
  test has been completed.

Session 3 needs the complete v3 concept reconciliation and real-case evaluation,
source-verified incremental Binance discovery and monitoring, qualified native
breakout and sweep strategies, native backtests and portfolio economics, agent access,
and independent adversarial reviews. This branch should not be treated as successful
completion of Session 2 or as an operating paper-trading system.
