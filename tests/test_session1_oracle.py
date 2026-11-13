import copy
import json
from pathlib import Path
import unittest
from researcher.contracts import ContractError
from researcher.oracle import check_tail_fixture

FIX = Path(__file__).parent / "fixtures/session1/oracle_btc_1h.json"


class SelectedTailOracle(unittest.TestCase):
    def test_independent_arithmetic_against_actual_remote_tail(self):
        result = check_tail_fixture(json.loads(FIX.read_text()))
        self.assertTrue(result["all_checks_passed"])
        self.assertEqual(result["numeric_comparisons"], 167)
        self.assertEqual(result["independent_source_oracle"], "BLOCKED_BINANCE_HTTP_451")
        self.assertIn("ATR seed", result["does_not_qualify"])

    def test_time_shift_cannot_pass_numeric_comparison(self):
        fixture = json.loads(FIX.read_text())
        fixture["series"]["lag"]["tailTimes"][0] += 3600
        with self.assertRaises(ContractError):
            check_tail_fixture(fixture)

    def test_prior_window_includes_no_current_high(self):
        fixture = json.loads(FIX.read_text())
        fixture["series"]["prior_high"]["tail"][-1] = fixture["series"]["high"]["tail"][-1]
        result = check_tail_fixture(fixture)
        self.assertFalse(result["checks"]["prior_high"]["passed"])

    def test_missingness_cannot_be_replaced_by_false_zero(self):
        fixture = json.loads(FIX.read_text())
        fixture["series"]["no_event_bars"].update(defined=64, tail=[0]*20)
        result = check_tail_fixture(fixture)
        self.assertFalse(result["checks"]["no_event_bars"]["passed"])


if __name__ == "__main__":
    unittest.main()
