"""Causal decision/reliability tests. Synthetic unit bars are never market evidence."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from trading_lab.playbooks import advance,initial_state,plan_for,prepare,VERSION,active_levels
from trading_lab.panel import ArchivePanel,safe_file
from trading_lab.panel_monitor import add,tick
from trading_lab.watchlist import connect,observe
from trading_lab.skills_v3 import check


class PlaybookLogic(unittest.TestCase):
    def setup_case(self,side='long',family='BREAKOUT_RETEST'):
        sign=1 if side=='long' else -1
        return dict(symbol='FILUSDT',side=side,family=family,boundary=100.,armed_at='2026-08-01T00:00:00Z',
                    boundary_known_at='2026-07-31T23:00:00Z',expires_at='2026-08-01T03:00:00Z',atr1h=1.,
                    fresh_opposition=False,obstacles=[dict(price=100+sign*5,known_at='2026-07-31T23:00:00Z',basis='known')],
                    setup_key='unit-test',source_id='unit-only',feature_version=VERSION)

    def bar(self,n,side='long',close=100.2,low=99.95,high=100.4):
        if side=='short':close,low,high=200-close,200-high,200-low
        return dict(at=pd.Timestamp('2026-08-01T00:00Z')+pd.Timedelta(minutes=5*n),close=close,low=low,high=high,rvol=1.3)

    def test_acceptance_requires_two_then_later_retest_both_sides(self):
        for side in ['long','short']:
            s=self.setup_case(side);state=initial_state()
            state,e=advance(s,state,self.bar(1,side));self.assertEqual(e['state'],'WATCH')
            state,e=advance(s,state,self.bar(2,side));self.assertEqual(e['state'],'ACCEPTED')
            state,e=advance(s,state,self.bar(3,side));self.assertEqual(e['state'],'TRIGGER_CANDIDATE')
            plan=plan_for(s,state,self.bar(3,side));self.assertEqual(plan['diagnostics'],'GEOMETRY_PASS_RESEARCH_ONLY')
            self.assertEqual(plan['earliest_order_at'],plan['decision_at'])
            self.assertLessEqual(plan['max_hold_minutes'],900)
            self.assertEqual(plan['native_risk'],'AGENT_NOT_VERIFIED')

    def test_breakout_failure_no_chase_and_immediate_comparator(self):
        s=self.setup_case();state=initial_state()
        state,_=advance(s,state,self.bar(1));state,e=advance(s,state,self.bar(2),variant='immediate')
        self.assertEqual(e['state'],'TRIGGER_CANDIDATE')
        state=initial_state();state,_=advance(s,state,self.bar(1));state,_=advance(s,state,self.bar(2))
        _,e=advance(s,state,self.bar(3,close=99.9));self.assertEqual(e['state'],'INVALIDATED')
        state=initial_state();state,_=advance(s,state,self.bar(1));state,e=advance(s,state,self.bar(2,close=101.5,high=101.8),variant='immediate')
        self.assertNotEqual(e['state'],'TRIGGER_CANDIDATE');self.assertEqual(e['reason'],'TOO_LATE_NO_CHASE')

    def test_sweep_requires_reclaim_then_later_confirmation_both_sides(self):
        for side in ['long','short']:
            s=self.setup_case(side,'SWEEP_RECLAIM');state,e=advance(s,initial_state(),self.bar(1,side,low=99.7))
            self.assertEqual(e['state'],'RECLAIMED')
            state,e=advance(s,state,self.bar(2,side,close=100.5,high=100.6));self.assertEqual(e['state'],'TRIGGER_CANDIDATE')
            plan=plan_for(s,state,self.bar(2,side,close=100.5,high=100.6));self.assertEqual(plan['diagnostics'],'GEOMETRY_PASS_RESEARCH_ONLY')
            self.assertAlmostEqual(abs(plan['stop_anchor']-plan['stop']),.15)

    def test_fresh_opposition_and_acceptance_do_not_become_reversal(self):
        s=self.setup_case(family='SWEEP_RECLAIM');s['fresh_opposition']=True
        state,_=advance(s,initial_state(),self.bar(1,low=99.7),variant='early')
        self.assertNotEqual(state['phase'],'TRIGGER_CANDIDATE')
        state,e=advance(s,state,self.bar(2,close=100.5,high=100.6));self.assertNotEqual(e['state'],'TRIGGER_CANDIDATE')
        state,e=advance(self.setup_case(family='SWEEP_RECLAIM'),initial_state(),self.bar(1,close=99.7,low=99.6))
        self.assertEqual(state['phase'],'WATCH')

    def test_consumed_pivot_does_not_remain_target_wall(self):
        times=pd.date_range('2026-08-01T00:00Z',periods=4,freq='1h')
        f=pd.DataFrame({'struct_known_at':times,'close':[100.,105.,111.,109.],
                        'swing_high':[120.,110.,110.,110.],
                        'swing_high_known_at':[times[0],times[1],times[1],times[1]],
                        'swing_high_pivot_at':[times[0]-pd.Timedelta(hours=3),times[1]-pd.Timedelta(hours=3),times[1]-pd.Timedelta(hours=3),times[1]-pd.Timedelta(hours=3)],
                        'swing_low':[90.,90.,90.,90.],
                        'swing_low_known_at':[times[0]]*4,'swing_low_pivot_at':[times[0]-pd.Timedelta(hours=3)]*4})
        result=active_levels(f)
        self.assertEqual([x['price'] for x in result.iloc[1].active_resistances],[120.,110.])
        self.assertEqual([x['price'] for x in result.iloc[2].active_resistances],[120.])
        # Falling below a consumed high does not silently invent a role-flip target.
        self.assertEqual([x['price'] for x in result.iloc[3].active_resistances],[120.])

    def test_expiry_gap_same_bar_and_obstacle_reject(self):
        s=self.setup_case()
        with self.assertRaisesRegex(ValueError,'FOLLOW_ARMING'):advance(s,initial_state(),self.bar(0))
        state,_=advance(s,initial_state(),self.bar(1))
        with self.assertRaisesRegex(ValueError,'GAPPED'):advance(s,state,self.bar(3))
        state,e=advance(s,initial_state(),self.bar(36));self.assertEqual(e['state'],'EXPIRED')
        s['obstacles'][0]['price']=100.3
        p=plan_for(s,state,self.bar(1));self.assertEqual(p['diagnostics'],'REJECT')
        self.assertIn('NEARBY_OBSTACLE_OR_COST_ECONOMICS',p['reasons'])
        s['atr1h']=20
        p=plan_for(s,state,self.bar(1));self.assertIn('STRUCTURAL_STOP_POLICY_CONFLICT',p['reasons'])


class SkillsAndStorage(unittest.TestCase):
    def test_all_owner_skills_original_members_and_refs(self):
        self.assertEqual(check()['assignments'],27)
        self.assertEqual(check()['original_members'],55)

    def test_symlink_source_and_database_refused(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'real').write_text('x');(root/'link').symlink_to(root/'real')
            with self.assertRaisesRegex(Exception,'SYMLINK'):safe_file(root,'link')
            with self.assertRaisesRegex(Exception,'UNSAFE'):safe_file(root,'../escape')
            (root/'watchlist.sqlite3').symlink_to(root/'real')
            with self.assertRaisesRegex(ValueError,'SYMLINK'):connect(root)

    def test_schema_two_migrates_and_arbitrary_raw_hash_stays_blocked(self):
        with tempfile.TemporaryDirectory() as name:
            db=connect(name)
            db.execute('DROP TRIGGER source_bindings_no_update');db.execute('DROP TRIGGER source_bindings_no_delete')
            db.execute('DROP TABLE source_bindings');db.execute('PRAGMA user_version=2');db.close()
            db=connect(name);self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)
            with self.assertRaisesRegex(ValueError,'UNVERIFIED_RAW_BARS'):observe(db,'x',[], 'a'*64,as_of_ms=1,mode='HISTORICAL')
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');db.close()


class RealPanelCausality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel=ArchivePanel()
        cls.five=cls.panel.frame('FILUSDT','5m');cls.hour=cls.panel.frame('FILUSDT','1h')

    def test_real_prefix_htf_and_pivot_confirmation(self):
        cutoff=pd.Timestamp('2026-08-01T12:00Z')
        # Smaller source prefix for fast exact comparison, retaining warmup and UTC alignment.
        start=pd.Timestamp('2026-07-01T00:00Z')
        f=self.five.loc[(self.five.date>=start)&(self.five.date<cutoff+pd.Timedelta(days=1))]
        h=self.hour.loc[(self.hour.date>=start)&(self.hour.date<cutoff+pd.Timedelta(days=1))]
        full,ctx=prepare(f,h);part,pctx=prepare(f.loc[f.date+pd.Timedelta(minutes=5)<=cutoff],h.loc[h.date+pd.Timedelta(hours=1)<=cutoff])
        pd.testing.assert_frame_equal(full.loc[full['at']<=cutoff].reset_index(drop=True),part)
        pd.testing.assert_frame_equal(ctx.loc[ctx['at']<=cutoff].reset_index(drop=True),pctx)
        pivots=ctx.loc[ctx.swing_high_known_at.notna()]
        self.assertTrue((pivots.swing_high_known_at>=pivots.swing_high_pivot_at+pd.Timedelta(hours=3)).all())
        available=ctx.loc[ctx.at4.notna()]
        self.assertTrue((available.at4<=available['at']).all())

    def test_real_plan_prefix_does_not_use_future_updates(self):
        from trading_lab.playbooks import research_symbol
        start=pd.Timestamp('2026-08-01T00:00Z');cut=start+pd.Timedelta(hours=3)
        five=self.five.loc[self.five.date.between(start-pd.Timedelta(days=35),start+pd.Timedelta(hours=6))]
        hours=self.hour.loc[self.hour.date.between(start-pd.Timedelta(days=35),start+pd.Timedelta(hours=6))]
        d,h=prepare(five,hours)
        side=self.panel.frame('FILUSDT','5m',sidecar=True)
        quote=pd.DataFrame({'at':side.date+pd.Timedelta(minutes=5),'quote24':side.quote_volume.rolling(288).sum()})
        whole=research_symbol('FILUSDT',d,h,quote,start,start+pd.Timedelta(days=7),self.panel.identity)
        prefix=research_symbol('FILUSDT',d.loc[d['at']<=cut],h,quote,start,start+pd.Timedelta(days=7),self.panel.identity)
        self.assertEqual([s for s in whole[0] if pd.Timestamp(s['as_of'])<=cut],prefix[0])
        self.assertEqual([e for e in whole[1] if pd.Timestamp(e['at'])<=cut],prefix[1])
        self.assertEqual([p for p in whole[2] if pd.Timestamp(p['decision_at'])<=cut],prefix[2])

    def test_bound_monitor_restart_duplicate_correction_and_backup(self):
        from trading_lab.playbooks import discover,ms
        start=pd.Timestamp('2026-08-01T00:00Z')
        five=self.five.loc[self.five.date.between(start-pd.Timedelta(days=35),start+pd.Timedelta(days=1))]
        hours=self.hour.loc[self.hour.date.between(start-pd.Timedelta(days=35),start+pd.Timedelta(days=1))]
        d,h=prepare(five,hours);chosen=None
        side=self.panel.frame('FILUSDT','5m',sidecar=True)
        quote=pd.Series(side.quote_volume.rolling(288).sum().to_numpy(),index=side.date+pd.Timedelta(minutes=5))
        for at in pd.date_range(start,periods=24,freq='1h'):
            q=discover('FILUSDT',d,h,at,self.panel.identity,quote_volume_24h=float(quote.loc[at]))
            if q['setups']:chosen=q['setups'][0];break
        self.assertIsNotNone(chosen)
        with tempfile.TemporaryDirectory() as name:
            db=connect(name);sid=add(db,self.panel,chosen);when=ms(chosen['armed_at'])+300000
            tick(db,self.panel,when);before=db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
            tick(db,self.panel,when);self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],before)
            backup=sqlite3.connect(Path(name)/'backup.sqlite3');db.backup(backup);backup.close();db.close()
            db=connect(name);self.assertEqual(db.execute('SELECT COUNT(*) FROM source_bindings').fetchone()[0],1)
            cached=self.panel.cache['monitor-features','FILUSDT'];original=cached.copy(deep=True)
            mask=cached['at'].eq(pd.Timestamp(when,unit='ms',tz='UTC'));cached.loc[mask,'close']*=1.0001
            try:
                with self.assertRaisesRegex(ValueError,'CORRECTED_COMPLETED_BAR'):tick(db,self.panel,when+300000)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],before)
            finally:self.panel.cache['monitor-features','FILUSDT']=original
            self.panel.version='unexpected-source-version'
            try:
                with self.assertRaisesRegex(ValueError,'SOURCE_VERSION_MISMATCH'):tick(db,self.panel,when+300000)
            finally:self.panel.version='binance-archive-panel-v3'
            db.close()

    def test_source_cutoff_future_stale_symbol_and_gap_reject(self):
        for symbol,tf,at in [('FILUSDT','15m',999),('BTCSPOT','5m',1785585600000),('FILUSDT','5m',1900000000000)]:
            with self.assertRaises(Exception):self.panel.completed(symbol,tf,at)
        with self.assertRaisesRegex(ValueError,'GAPPED'):prepare(self.five.iloc[-200:].drop(self.five.index[-100]),self.hour.iloc[-100:])

    def test_wrong_receipt_version_and_hash_tamper_reject(self):
        from trading_lab import panel as module
        bad=copy.deepcopy(self.panel.pins);bad['sources_sha256']='a'*64
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'pins.json';path.write_text(json.dumps(bad))
            with patch.object(module,'PINS',path),self.assertRaisesRegex(Exception,'SOURCE_RECEIPT_VERSION'):ArchivePanel()
        source=self.panel.sources[0]
        from binance_research_data import verify_cached_archive
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'tampered.zip';path.write_bytes(b'bad zip')
            with self.assertRaises(Exception):verify_cached_archive(path,source['official_sha256'])


if __name__=='__main__':unittest.main()
