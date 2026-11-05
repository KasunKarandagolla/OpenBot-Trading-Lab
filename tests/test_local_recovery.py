"""Regression checks for five-minute confirmation and archival provenance."""

import gzip
import json
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from local_recovery_charts import source_panels
from local_recovery_convert import load
from local_recovery_data import WORK, monthly_url, protocol
from local_recovery_scan import FIVE, cheap_frame, entry_features, examine


class RecoveryTiming(unittest.TestCase):
    def setUp(self):
        self.at = pd.Timestamp("2026-08-01T00:15Z")
        self.end = self.at + pd.Timedelta(days=2)
        self.gates = protocol()["gates"]

    def candidate(self):
        return dict(opportunity_id="regression", symbol="BTCUSDT", armed_at=self.at.isoformat(),
                    side="long", playbook="continuation", sign=1, boundary=100.0, atr15=1.0,
                    extreme=99.6, objective_candidates=[dict(price=105.0, source="1h_swing",
                    known_at=(self.at - pd.Timedelta(hours=1)).isoformat())])

    def bars(self):
        dates = pd.date_range(end=self.at + 6 * FIVE, freq=FIVE, periods=65)
        frame = pd.DataFrame(dict(date=dates - FIVE, open=100.0, high=100.2,
                                  low=99.8, close=100.1, volume=10.0))
        trigger = dates == self.at + FIVE
        frame.loc[trigger, ["high", "close", "volume"]] = [100.8, 100.7, 15.0]
        return entry_features(frame)

    def test_cannot_arm_and_trigger_on_same_bar(self):
        candidate = self.candidate()
        examine(candidate, self.bars(), self.gates, self.end)
        plan = candidate["plan"]
        self.assertEqual(pd.Timestamp(plan["decision_at"]), self.at + FIVE)
        self.assertEqual(pd.Timestamp(plan["expires_at"]), self.at + 2 * FIVE)
        self.assertLess(plan["stop"], plan["entry"])
        self.assertLess(plan["entry"], plan["target"])

    def test_prefix_equivalence_and_no_future_fill_price(self):
        bars = self.bars()
        full = self.candidate()
        examine(full, bars, self.gates, self.end)
        truncated = self.candidate()
        examine(truncated, bars.loc[:self.at + FIVE], self.gates, self.end)
        self.assertEqual(truncated, full)

    def test_missing_execution_candle_invalidates(self):
        candidate = self.candidate()
        examine(candidate, self.bars().drop(self.at + FIVE), self.gates, self.end)
        self.assertEqual(candidate["events"][-1]["reason"], "MISSING_5M_CANDLE")
        self.assertNotIn("plan", candidate)

    def test_no_trigger_expires_and_partition_purges(self):
        candidate = self.candidate()
        bars = self.bars()
        quiet = bars.copy()
        quiet.loc[:, "rvol"] = .5
        examine(candidate, quiet, self.gates, self.end)
        self.assertEqual(candidate["status"], "EXPIRED")
        candidate = self.candidate()
        examine(candidate, bars, self.gates, self.at + pd.Timedelta(hours=15))
        self.assertEqual(candidate["events"][-1]["reason"], "PARTITION_EXIT_PURGE")

    def test_monthly_url_has_source_identity(self):
        self.assertTrue(monthly_url("klines", "BTCUSDT", "5m", "2026-08").endswith(
            "/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-2026-08.zip"))
        with self.assertRaises(ValueError):
            monthly_url("klines", "../BTCUSDT", "5m", "2026-08")


@unittest.skipUnless((WORK / "development/scan-freeze.json").exists(), "real research run is absent")
class RealInputTiming(unittest.TestCase):
    def test_real_hour_and_parent_prefix(self):
        cutoff = pd.Timestamp("2026-08-07T13:15:00Z")
        hours = load("FILUSDT", "1h", sidecar=True).rename(columns={"base_volume": "volume"})
        quarters = load("FILUSDT", "15m")
        full = cheap_frame(hours, quarters)
        partial = cheap_frame(hours.loc[hours.date + pd.Timedelta(hours=1) <= cutoff],
                              quarters.loc[quarters.date + pd.Timedelta(minutes=15) <= cutoff])
        full = full.loc[full["at"] <= cutoff].reset_index(drop=True)
        pd.testing.assert_frame_equal(full, partial, check_dtype=False)
        self.assertTrue((partial.hourly_at.dropna() <= partial.date[partial.hourly_at.notna()]).all())
        self.assertTrue((partial.known4h.dropna() <= partial.date[partial.known4h.notna()]).all())

    def test_chart_adequacy_and_hidden_forward_cutoff(self):
        cutoff = pd.Timestamp("2026-08-07T13:15:00Z")
        _, panels, _, participation = source_panels("FILUSDT", cutoff)
        self.assertTrue(all(x["missing_bars"] == 0 for x in panels.values()))
        self.assertTrue(all(pd.Timestamp(x["last_available_at"]) <= cutoff for x in panels.values()))
        self.assertEqual(participation.date.iloc[-1] + FIVE, cutoff)
        _, insufficient, _, _ = source_panels("FILUSDT", pd.Timestamp("2026-05-02T00:00Z"))
        self.assertGreater(insufficient["4h"]["missing_bars"], 0)

    def test_registry_is_causal_for_every_proposal(self):
        with gzip.open(WORK / "development/opportunities.json.gz", "rt") as handle:
            candidates = json.load(handle)
        plans = [c for c in candidates if "plan" in c]
        self.assertGreater(len(plans), 0)
        for candidate in plans:
            plan = candidate["plan"]
            trigger = next(e for e in candidate["events"] if e["state"] == "TRIGGERED")
            decision = pd.Timestamp(plan["decision_at"])
            self.assertLess(pd.Timestamp(candidate["armed_at"]), decision)
            self.assertEqual(pd.Timestamp(trigger["trigger_bar_open"]) + FIVE, decision)
            self.assertLessEqual(pd.Timestamp(candidate["boundary_known_at"]), pd.Timestamp(candidate["armed_at"]))
            self.assertLessEqual(pd.Timestamp(plan["objective"]["known_at"]), pd.Timestamp(candidate["armed_at"]))


if __name__ == "__main__":
    unittest.main()
