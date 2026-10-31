"""Boundary tests for research changes; fixtures are never market evidence."""
import copy
import io
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'research'),str(ROOT/'scripts')]
from master_audit.data_checks import validate_book,validate_candles,validate_archive


class SourceBoundaries(unittest.TestCase):
    def book(self):
        return dict(id=10,current=100.,update=99.9,
                    bids=[dict(p='99',s='1')],asks=[dict(p='100',s='2')])

    def updates(self):
        return [dict(U=9,u=11,t=100000,received_ms=100100),dict(U=12,u=15,t=100100,received_ms=100200)]

    def test_bridge_and_contiguous_chain(self):
        result=validate_book(self.book(),99.8,100.2,self.updates())
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['final_id'],15)

    def test_missing_clock_stale_crossed_and_sequence_gap_reject(self):
        for change in [dict(current=None),dict(current=90),dict(bids=[dict(p='101',s='1')])]:
            self.assertEqual(validate_book(self.book()|change,99.8,100.2,self.updates())['status'],'REJECT')
        gap=self.updates();gap[-1]['U']=13
        self.assertIn('SEQUENCE_GAP',validate_book(self.book(),99.8,100.2,gap)['errors'])
        self.assertIn('WEBSOCKET_CONTINUITY_UNVERIFIED',validate_book(self.book(),99.8,100.2)['errors'])

    def test_empty_level_updates_still_advance_id_and_backward_clock_rejects(self):
        updates=[x|dict(a=[],b=[]) for x in self.updates()]
        self.assertEqual(validate_book(self.book(),99.8,100.2,updates)['final_id'],15)
        updates[-1]['t']=99000
        self.assertIn('BACKWARD_EVENT_CLOCK',validate_book(self.book(),99.8,100.2,updates)['errors'])
        updates=self.updates();updates[-1]['received_ms']=110000
        self.assertIn('STALE_OR_FUTURE_UPDATE',validate_book(self.book(),99.8,100.2,updates)['errors'])

    def test_candle_gaps_duplicates_and_bad_prices(self):
        rows=[dict(t=t,o='10',h='12',l='9',c='11',v=1) for t in range(0,1800,900)]
        self.assertEqual(validate_candles(rows,0,1800,900)['status'],'PASS')
        for bad in [rows[:1],rows+rows[:1],[rows[0]|dict(h='8'),rows[1]]]:
            self.assertEqual(validate_candles(bad,0,1800,900)['status'],'BLOCKED')

    def test_archive_checksum_fails_before_zip_parsing(self):
        with self.assertRaisesRegex(ValueError,'CHECKSUM_MISMATCH'):
            validate_archive(b'notzip',b'0'*64,'BTC','2026-10-29','15m')


class NativeExitBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import freqtrade
        except ImportError:
            raise unittest.SkipTest('Pinned native image required')
        sys.path[:0]=[str(ROOT/'research/bonus'),str(ROOT/'research/session3'),
                      str(ROOT/'research/master_audit'),str(ROOT/'user_data/strategies')]

    def test_opposite_adx_is_not_new_invalidation_both_sides(self):
        import pandas as pd
        from types import SimpleNamespace
        from AuditVariantsV1 import AuditStructuralCloseM0V1
        from OpportunityRouterV1 import RouterOnlyV1
        from freqtrade.enums import CandleType
        for short in (False,True):
            now=pd.Timestamp('2026-08-25T01:00Z')
            geometry=dict(stop=101 if short else 99,target=97 if short else 103,max_hold_hours=4)
            trade=SimpleNamespace(is_short=short,open_date_utc=now-pd.Timedelta(minutes=30),get_custom_data=lambda k:geometry)
            frame=pd.DataFrame([dict(date=now-pd.Timedelta(minutes=15),close=100.,
                                     struct_direction_1h='UP' if short else 'DOWN',adx_1h=30.)])
            cfg={'candle_type_def':CandleType.FUTURES}
            old=RouterOnlyV1(cfg);new=AuditStructuralCloseM0V1(cfg)
            old.dp=new.dp=SimpleNamespace(get_analyzed_dataframe=lambda *a:(frame,None))
            self.assertEqual(old.custom_exit('X',trade,now,100.,0.),'closed_hour_thesis_invalidated')
            self.assertIsNone(new.custom_exit('X',trade,now,100.,0.))
            frame['close']=102 if short else 98
            self.assertEqual(new.custom_exit('X',trade,now,100.,0.),'frozen_structure_close_invalidated')
            frame['date']=now  # this bar is not closed at the decision
            self.assertIsNone(new.custom_exit('X',trade,now,100.,0.))

    def test_M1_has_no_native_runner_registration(self):
        import subprocess
        result=subprocess.run([sys.executable,str(ROOT/'scripts/master_native.py'),
                               'backtest','RouterOnlyM1V1'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('disabled M1',result.stderr)

    def test_native_partial_funding_double_count_and_event_once_candidate(self):
        from master_funding_probe import fixture,ResearchFundingBacktest
        from freqtrade.optimize.backtesting import Backtesting
        for short in (False,True):
            original=fixture(Backtesting,short)
            repaired=fixture(ResearchFundingBacktest,short)
            self.assertAlmostEqual(original['native_funding'],2*original['expected_before_exit_priority'])
            self.assertTrue(repaired['reconciles'])
            self.assertAlmostEqual(repaired['order_funding'][-1],0.)

    def test_target_obstacle_gate_both_sides_keeps_old_source_unchanged(self):
        import pandas as pd
        from unittest.mock import patch
        from AuditVariantsV1 import AuditNearestObjectiveM0V1
        from OpportunityRouterV1 import RouterOnlyV1
        from freqtrade.enums import CandleType
        strategy=AuditNearestObjectiveM0V1({'candle_type_def':CandleType.FUTURES})
        for short in (False,True):
            sign=-1 if short else 1
            plan=dict(side='short' if short else 'long',reference=100.,stop=100-sign,
                      target=100+sign*2,risk_fraction=.01,after_cost_rr=1.3)
            row=dict(enter_short=int(short),enter_long=int(not short),bonus_reason='TRADE',
                     bonus_plan=json.dumps(plan),prior_day_low=99.8 if short else 90.,
                     prior_day_high=110. if short else 100.2)
            original=pd.DataFrame([row])
            with patch.object(RouterOnlyV1,'populate_entry_trend',return_value=original.copy(deep=True)):
                result=strategy.populate_entry_trend(pd.DataFrame(),{})
            self.assertEqual(result.enter_long.iloc[0]+result.enter_short.iloc[0],0)
            self.assertEqual(result.bonus_reason.iloc[0],'AUDIT_NEAREST_OBJECTIVE_ROOM')
            self.assertEqual(json.loads(original.bonus_plan.iloc[0]),plan)


if __name__=='__main__':
    unittest.main()
