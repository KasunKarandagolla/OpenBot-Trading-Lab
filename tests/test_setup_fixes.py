"""Owner acceptance cases. Synthetic mechanics are separate from economic evidence."""
import sys,json,copy,tempfile,hashlib,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from collections import Counter
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from setup_common import *
from setup_features import features,scan_pair,make_plan,_arm
from setup_map import four_hour_map
from setup_profile import verified_profile,select_profile,load_profiles
from setup_screen import DeepProvider,Workflow,shortlist
from setup_checkpoint import ArchiveCheckpoints
from setup_candidate import execute
from setup_export import export_event
from SetupPolicyV1 import SetupPolicyV1
from test_setup import row,CLOCK,PAIR
from freqtrade.enums import CandleType,RunMode

def opposite(r):
    d=r.copy()
    pairs_=[('high','low'),('previous_high','previous_low'),('pull_high','pull_low'),
        ('prior_day_high','prior_day_low'),('prior_session_high','prior_session_low'),
        ('range_high_1h','range_low_1h'),('swing_high_1h','swing_low_1h'),('prior_swing_high','prior_swing_low')]
    for k in ['open','close','previous_close','prior_vwap','vwap']:
        if k in d:d[k]=200-r[k]
    for a,b in pairs_:d[a]=200-r[b];d[b]=200-r[a]
    d['struct_direction']=d['struct_direction_1h']='DOWN';d['bias4h']=-r.bias4h
    return d

def profile_fixture(end=CLOCK):
    trades=[dict(id=str(i),event_ms=(end-pd.Timedelta(hours=1)).timestamp()*1000+i,received_ms=end.timestamp()*1000,
        price=p,amount=v) for i,(p,v) in enumerate([(99.,9.),(106.,10.),(110.,9.)])]
    receipt=dict(source='SYNTHETIC_CONTRACT_FIXTURE',venue='gate',pair=PAIR,fidelity='EXECUTED_TRADES',coverage='COMPLETE_VERIFIED',
        start=(end-pd.Timedelta(hours=8)).isoformat(),end=end.isoformat(),known_at=end.isoformat(),
        sha256=hashlib.sha256(json.dumps(trades,sort_keys=True,separators=(',',':')).encode()).hexdigest())
    return trades,receipt,verified_profile(trades,receipt,end)

class SetupCorrections(unittest.TestCase):
    def test_common_validity_has_no_hidden_ema_warmup_veto(self):
        n=160;close=100+np.sin(np.arange(n)/4)
        b=pd.DataFrame(dict(date=pd.date_range(CLOCK,periods=n,freq='15min'),open=close,high=close+.4,low=close-.4,close=close,volume=10.))
        h=b.set_index('date').resample('h').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).reset_index()
        f=features(b,h)
        self.assertTrue((f.setup_valid & f.map4h_ready & f.ema50_1h.isna() & f.bias4h.isna()).any())

    def test_4h_nearest_barrier_blocks_both_sides_and_late_level_has_no_effect(self):
        for side,s in [('long',1),('short',-1)]:
            r=row(close=101. if s==1 else 99.,prior_swing_low=93.5,swing_low_1h=93.5)
            a=_arm(PAIR,r,'continuation',side,100.,'fixture',r.date,99.5 if s==1 else 100.5);a['confirmation']='fixture'
            self.assertIsNotNone(make_plan(r,a)[0])
            key='swing_'+('high' if s==1 else 'low')+'_4h';stamp=key.replace('_4h','_known_at_4h')
            r[key]=101.2 if s==1 else 98.8;r[stamp]=r.date-pd.Timedelta(hours=1)
            self.assertEqual(make_plan(r,a)[1],'FIRST_OBSTACLE_INSUFFICIENT_AFTER_COST_REWARD')
            r[stamp]=r.date+pd.Timedelta(seconds=1)
            p,_=make_plan(r,a);self.assertIsNotNone(p);self.assertNotEqual(p['target_origin'],key)
        self.assertTrue(all(x['known_at']<=p['available_at'] for x in p['obstacles']))

    def test_missing_map_blocks_admission_independently_of_pivot_existence(self):
        r=row(close=101.,map4h_ready=False,map4h_reason='GAP_OR_PARTIAL_4H')
        a=_arm(PAIR,r,'continuation','long',100.,'fixture',r.date,99.5);a['confirmation']='fixture'
        self.assertIn('MAP4H_UNAVAILABLE:GAP',make_plan(r,a)[1])
        r['map4h_ready']=True
        self.assertIsNotNone(make_plan(r,a)[0]) # valid map with no4h pivot is allowed

    def test_4h_complete_alignment_confirmation_duplicates_gaps_and_prefix(self):
        hours=[]
        for i,price in enumerate([100,102,110,103,101,104,105]):
            for j in range(4):hours.append(dict(date=CLOCK+pd.Timedelta(hours=4*i+j),open=price,close=price,high=price+1,low=price-1,volume=10.))
        h=pd.DataFrame(hours);full=four_hour_map(h)
        self.assertFalse(full.map4h_ready.iloc[3]);self.assertTrue(full.map4h_ready.iloc[4])
        self.assertEqual(full.swing_high_4h.iloc[4],111.)
        self.assertEqual(full.swing_high_known_at_4h.iloc[4],CLOCK+pd.Timedelta(hours=20))
        self.assertTrue(pd.isna(full.bias4h.iloc[4])) # no EMA warmup veto
        pd.testing.assert_frame_equal(full.iloc[:5].reset_index(drop=True),four_hour_map(h.iloc[:20]).reset_index(drop=True))
        bad=pd.concat([h.iloc[:1],h.iloc[:1],h.iloc[2:]],ignore_index=True)
        self.assertEqual(four_hour_map(bad).input4h_reason.iloc[0],'DUPLICATE_SOURCE_HOUR')
        self.assertFalse(four_hour_map(h.drop(index=5)).map4h_ready.iloc[1])
        self.assertEqual(four_hour_map(h.iloc[:3]).input4h_reason.iloc[0],'GAP_OR_PARTIAL_4H')

    def test_ema_sign_and_nan_telemetry_cannot_veto_structural_swing_continuation(self):
        base=[row(prior_vwap=np.nan,vwap_valid=False,session_bars=1,swing_low_1h=100.),
            row(1,close=101.5,open=100.4,low=100.2,high=101.8,prior_vwap=np.nan,vwap_valid=False,session_bars=2,swing_low_1h=100.)]
        plans=[]
        for bias in [10.,-10.,np.nan]:
            d=pd.DataFrame(base);d['bias4h']=bias;d['ema20_1h']=np.nan;d['ema50_1h']=np.nan
            p=[e['plan'] for e in scan_pair(d,PAIR) if e['plan']]
            self.assertEqual(len(p),1);plans.append(p[0])
        self.assertEqual(plans[0],plans[1]);self.assertEqual(plans[1],plans[2])
        d=pd.DataFrame(base);d['swing_low_1h']=95.
        self.assertFalse([e for e in scan_pair(d,PAIR) if e['plan']])
        self.assertFalse([e for e in scan_pair(pd.DataFrame(base[:1]),PAIR) if e['plan']])

    def test_ema_cross_without_a_defended_location_cannot_enter(self):
        d=pd.DataFrame([row(prior_vwap=97.,ema20_1h=101.,ema50_1h=99.),row(1,close=101.5,low=101.,prior_vwap=97.,ema20_1h=105.,ema50_1h=99.)])
        self.assertFalse([e for e in scan_pair(d,PAIR) if e['plan']])

    def test_shallow_inside_close_consumes_break_and_fresh_event_must_reconfirm(self):
        bars=[row(balance_1h=True,range_high_1h=100.,previous_close=99.5,prior_vwap=97.,low=99.8),
            row(1,balance_1h=True,range_high_1h=100.,close=99.9,open=100.1,low=99.8,prior_vwap=97.),
            row(2,balance_1h=True,range_high_1h=100.,previous_close=99.9,close=100.4,open=100.1,low=99.95,prior_vwap=97.),
            row(3,balance_1h=True,range_high_1h=100.,previous_close=100.4,close=100.8,open=100.5,low=100.1,prior_vwap=97.)]
        for rows in [bars,[opposite(r) for r in bars]]:
            events=[e for e in scan_pair(pd.DataFrame(rows),PAIR) if e['playbook']=='breakout']
            arms=[e for e in events if e['state']=='ARMED'];self.assertEqual(len(arms),2)
            self.assertNotEqual(arms[0]['setup_id'],arms[1]['setup_id'])
            self.assertTrue(any(e['setup_id']==arms[0]['setup_id'] and e['reason']=='BREAKOUT_CLOSE_BACK_INSIDE' for e in events))
            self.assertFalse(any(e['plan'] and e['setup_id']==arms[0]['setup_id'] for e in events))
            self.assertTrue(any(e['plan'] and e['setup_id']==arms[1]['setup_id'] for e in events))

    def test_outside_close_with_wick_retest_remains_valid(self):
        a=row(balance_1h=True,range_high_1h=100.,previous_close=99.5,prior_vwap=97.,low=99.8)
        b=row(1,balance_1h=True,range_high_1h=100.,close=100.8,open=100.3,low=99.9,prior_vwap=97.)
        self.assertTrue([e for e in scan_pair(pd.DataFrame([a,b]),PAIR) if e['playbook']=='breakout' and e['plan']])
        b['close']=100.
        self.assertFalse([e for e in scan_pair(pd.DataFrame([a,b]),PAIR) if e['playbook']=='breakout' and e['plan']])

class RoutingAndExport(unittest.TestCase):
    def test_sealed_prior_close_checkpoint_matches_warmup_and_rejects_future_state(self):
        from causal_structure import structure
        bars=[]
        for i in range(24):
            price=100+np.sin(i/2)
            bars.append(row(i,open=price,close=price,high=price+.5,low=price-.5))
        f=pd.DataFrame(bars);cached=structure(f[['date','open','high','low','close','volume']])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/(slug(PAIR)+'.pkl');cached.to_pickle(path)
            loader=ArchiveCheckpoints(tmp,{PAIR:sha(path)})
            a=DeepProvider({PAIR:f});b=DeepProvider({PAIR:f},checkpoint_loader=loader)
            x=a.get(PAIR,f.iloc[16]);y=b.get(PAIR,f.iloc[16])
            for key in ['struct_direction','swing_high','swing_low','swing_high_known_at','swing_low_known_at','prior_swing_high','prior_swing_low']:
                if pd.isna(x[key]):self.assertTrue(pd.isna(y[key]))
                else:self.assertEqual(x[key],y[key])
            self.assertEqual(b.counts['deep_warmup_rows'],4)
            self.assertEqual(b.counts['deep_checkpoint_hits'],1)
            loader.frames[PAIR].loc[f.date.iloc[15],'struct_known_at']=f.date.iloc[17]
            with self.assertRaisesRegex(ValueError,'future causal checkpoint'):loader(PAIR,f.date.iloc[16])

    def test_first_fill_hold_clock_and_order_expiry_remain_separate(self):
        s=SetupPolicyV1(dict(runmode=RunMode.BACKTEST,dry_run=True,candle_type_def=CandleType.FUTURES));s.dp=Mock()
        s.dp.get_analyzed_dataframe.return_value=(pd.DataFrame(),None)
        g=dict(side='long',recipe='continuation',stop=99.,target=110.,boundary=100.,atr_at_signal=1.,max_hold_hours=24)
        state=dict(first_fill=(CLOCK+pd.Timedelta(hours=2)).timestamp())
        t=Mock();t.is_short=False;t.open_date_utc=CLOCK.to_pydatetime()
        t.get_custom_data.side_effect=lambda k,default=None:g if k=='policy_plan' else state
        self.assertIsNone(s.custom_exit(PAIR,t,CLOCK+pd.Timedelta(hours=15),100.,0))
        self.assertEqual(s.custom_exit(PAIR,t,CLOCK+pd.Timedelta(hours=17),100.,0),'max_hold_15h')
    def test_50_pair_fixture_stops_illiquid_and_nonshortlisted_deep_work(self):
        frames={f'ASSET{i:02d}/USDT:USDT':pd.DataFrame([row(swing_low_1h=100.,prior_vwap=90.,vwap=90.,eligible=i!=0,
            activity=1.,prior_day_quote=2e7 if i else 1e6,prior7_quote=2e7 if i else 1e6)]) for i in range(50)}
        rows={p:f.iloc[0] for p,f in frames.items()};provider=DeepProvider(frames);wf=Workflow(provider)
        wf.tick(rows)
        called={p for p,_ in provider.last.items()};chosen=set(wf.selections[(CLOCK+pd.Timedelta(minutes=15)).isoformat()])
        self.assertEqual(called,chosen);self.assertNotIn('ASSET00/USDT:USDT',called)
        self.assertLess(len(called),50);self.assertEqual(provider.counts['deep_calls'],len(chosen))
        self.assertTrue(wf.counts['deduplicated_lane_slots']>0)
        self.assertFalse(any('rotation:' in lane for lanes in wf.selections.values() for z in lanes.values() for lane in z))
        self.assertTrue(any(x['location_source']=='swing_low_1h' for trace in wf.trace for x in trace['shortlist']))
        write(WORK/'fixture-50-pair.json',dict(classification='SYNTHETIC_LOGICAL_WORK_NOT_NETWORK_COST',pairs=50,counts=dict(wf.counts),deep=dict(provider.counts),trace=wf.trace))

    def test_dropped_watch_can_finish_and_position_updates_survive_ineligibility(self):
        frames={PAIR:pd.DataFrame([row(),row(1,close=101.5,open=100.4,low=100.2,high=101.8),row(2,eligible=False)])}
        provider=DeepProvider(frames);wf=Workflow(provider)
        chosen=({PAIR:{('continuation','long')}},{PAIR:[{'fixture':'FIRST_OBSERVATION'}]},Counter())
        empty=({}, {},Counter())
        with patch('setup_screen.shortlist',side_effect=[chosen,empty,empty]):
            for i in range(3):wf.tick({PAIR:frames[PAIR].iloc[i]},positions=[PAIR] if i==2 else [])
        self.assertEqual(sum(map(len,wf.plans.values())),1)
        self.assertEqual(provider.counts['deep_calls'],3)
        self.assertTrue(wf.trace[1]['retained_setup']);self.assertTrue(wf.trace[2]['position_or_reservation'])

    def test_late_shortlist_warmup_cannot_retroactively_trade(self):
        frames={PAIR:pd.DataFrame([row(),row(1,close=101.5,open=100.4,low=100.2,high=101.8),row(2,close=101.7,low=101.4,high=102.)])}
        provider=DeepProvider(frames);wf=Workflow(provider);empty=({}, {},Counter())
        chosen=({PAIR:{('continuation','long')}},{PAIR:[]},Counter())
        with patch('setup_screen.shortlist',side_effect=[empty,empty,chosen]):
            for i in range(3):wf.tick({PAIR:frames[PAIR].iloc[i]})
        self.assertFalse(wf.plans);self.assertEqual(provider.counts['deep_calls'],1)
        self.assertEqual(provider.counts['deep_warmup_rows'],2)

    def test_watch_export_never_inherits_later_plan(self):
        r=row(3,close=101.);a=_arm(PAIR,r,'continuation','long',100.,'fixture',r.date,99.5);a['confirmation']='fixture'
        g,_=make_plan(r,a);early=dict(pair=PAIR,setup_id='SHARED',at=(CLOCK+pd.Timedelta(minutes=15)).isoformat(),state='ARMED',reason='WAIT',plan=None)
        late=dict(early,at=g['available_at'],state='READY',reason='TRADE',plan=g)
        first=export_event(early);second=export_event(late)
        self.assertIsNone(first['geometry']);self.assertNotEqual(first['decision_id'],g['decision_id']);self.assertNotEqual(first['event_id'],second['event_id'])
        self.assertEqual(second['geometry'],g);self.assertEqual(first['decision_at'],early['at'])
        import jsonschema
        report=dict(schema_version=1,snapshot_id='FIXTURE',generated_at=now(),mode='READ_ONLY_RESEARCH',venue='gate',source_provenance={},candidates=[first,second],event_briefing=dict(schema_version=1,clearance='UNKNOWN',coverage='UNKNOWN',events=[]),orders_created=False,uncertainty=[])
        jsonschema.validate(report,read(ROOT/'research/foundation/openbot.schema.json'))

    def test_validated_profile_changes_normal_runner_plan_and_native_geometry(self):
        trades,receipt,p=profile_fixture();boundary=p['val']
        frames={PAIR:pd.DataFrame([row(balance_1h=True,low=boundary-.2,close=boundary+.6,open=boundary+.3,previous_close=boundary+1.,prior_vwap=97.),
            row(1,balance_1h=True,low=boundary+.4,high=boundary+1.8,close=boundary+1.5,open=boundary+.6,previous_close=boundary+.6,prior_vwap=97.)])}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);write(root/'trades.json',trades);write(root/'receipt.json',receipt);write(root/'index.json',{'references':[{'trades':'trades.json','receipt':'receipt.json'}]})
            profiles,status=load_profiles(root/'index.json',root,CLOCK);self.assertEqual(status['status'],'READY')
            wf,_,_=execute(frames,profiles);missing,_,_=execute(frames,[])
        plans=[g for z in wf.plans.values() for g in z.values() if g['recipe']=='rotation']
        self.assertEqual(len(plans),1);self.assertFalse(missing.plans)
        g=plans[0];self.assertEqual(g['profile_reference']['source_sha256'],p['source_sha256'])
        s=SetupPolicyV1(dict(runmode=RunMode.BACKTEST,dry_run=True,candle_type_def=CandleType.FUTURES));s.dp=Mock()
        df=pd.DataFrame([dict(date=pd.Timestamp(g['available_at'])-pd.Timedelta(minutes=15),enter_long=1,policy_plan=json.dumps(g))])
        s.dp.get_analyzed_dataframe.return_value=(df,None)
        consumed=s.row_plan(PAIR,pd.Timestamp(g['available_at']),'long',g['reference'])
        self.assertEqual(consumed['stop'],g['stop']);self.assertEqual(consumed['target'],g['target'])
        self.assertIsNone(s.row_plan(PAIR,pd.Timestamp(g['expires_at']),'long',g['reference']))

    def test_profile_missing_late_stale_wrong_pair_proxy_and_multiple_sessions(self):
        _,_,p=profile_fixture();cut=CLOCK
        self.assertIsNone(select_profile([],PAIR,cut))
        for modified in [dict(p,known_at=(CLOCK+pd.Timedelta(hours=1)).isoformat()),dict(p,pair='OTHER/USDT:USDT'),dict(p,fidelity='OHLCV_PROXY')]:
            self.assertIsNone(select_profile([modified],PAIR,cut))
        self.assertIsNone(select_profile([p],PAIR,CLOCK+pd.Timedelta(hours=8)))
        _,_,later=profile_fixture(CLOCK+pd.Timedelta(hours=8))
        self.assertEqual(select_profile([p,later],PAIR,CLOCK+pd.Timedelta(hours=9))['anchor_end'],later['anchor_end'])

if __name__=='__main__':unittest.main()
