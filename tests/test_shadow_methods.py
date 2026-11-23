"""Point-in-time synthetic oracles; no live source or economic claims."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from researcher.contracts import ContractError
from researcher.engine_capabilities import analyze_selected, manifest, qualified_route_a
from researcher.numerics import Bar
from researcher.observations import iso_seconds
from researcher.query_planner import ResearchSources
from researcher.settings import load_config
from researcher.shadow_methods import crt_tbs_shadow, wyckoff_shadow
from test_session6a import START, TICK, bars, mirror


class ShadowMethods(unittest.TestCase):
    pattern=[(100,101,99,100),(101,102,100,101),(104,105,103,104),
             (105,106,104,105),(104,105,103,104),(101,102,100,101)]

    def balance(self,tail=()):
        return bars((self.pattern*6)[:32]+list(tail))

    def wy(self,b,at=None):
        at=at or b[-1].end
        return wyckoff_shadow(b,TICK,cutoff=at,as_of=at)

    def five(self,rows,start=START+14400):
        result=[]
        for i,row in enumerate(rows):
            o,h,l,c=map(D,map(str,row));end=iso_seconds(start+(i+1)*300)
            result.append(Bar('TESTUSDT','5m',(start+i*300)*1000,o,h,l,c,D(10),c*10,D(5),c*5,10,
                'SYNTHETIC-5M-SOURCE',end,available_at=end))
        return result

    def parent(self):
        return bars([(100,110,90,100)],tf='4h')[0]

    def tbs(self,children,parent=None,**options):
        parent=parent or self.parent()
        return crt_tbs_shadow(parent,children,selection_known_at=options.pop('selection_known_at',parent.end),
            cutoff=options.pop('cutoff',children[-1].end if children else parent.end),
            as_of=options.pop('as_of',children[-1].end if children else parent.end),
            tick=TICK,atr_ref=D(2),source_complete=options.pop('source_complete',True),**options)

    def test_wyckoff_spring_later_response_retest_and_mirror(self):
        b=self.balance([(100,101,97,100),(100,105,99,104),(104,105,102,103),(103,105,102,104)])
        result=self.wy(b)
        self.assertEqual(result['state'],'LPS_CANDIDATE')
        self.assertEqual([x['kind'] for x in result['events']],
            ['SPRING_GEOMETRY','SOS_CANDIDATE','RETEST_CANDIDATE','LPS_CANDIDATE'])
        self.assertEqual(result['events'][0]['event_root_id'],b[32].id)
        self.assertEqual(self.wy(mirror(b))['state'],'LPSY_CANDIDATE')
        self.assertFalse(result['rank_eligible']);self.assertFalse(result['production_enabled'])
        self.assertFalse(result['trade_authorization'])

    def test_wyckoff_range_missing_volume_and_later_invalidation(self):
        b=self.balance([(100,101,97,100),(99,100,96,97),(97,99,95,96)])
        self.assertEqual(self.wy(b)['state'],'INVALIDATED_REVERSAL')
        zero=[replace(x,base_volume=D(0),quote_volume=D(0),buy_base=D(0),buy_quote=D(0)) for x in b]
        self.assertEqual(self.wy(zero)['effort_result']['state'],'EFFORT_RESULT_UNKNOWN')
        self.assertEqual(self.wy(b[:20])['state'],'UNKNOWN')
        flat=bars([(100,101,99,100)]*40)
        self.assertEqual(self.wy(flat)['state'],'RANGE_CANDIDATE')

    def test_wyckoff_append_future_keeps_the_old_cutoff(self):
        b=self.balance([(100,101,97,100),(100,105,99,104)])
        at=b[-1].end
        longer=self.balance([(100,101,97,100),(100,105,99,104),(104,105,102,103),(103,105,102,104)])
        self.assertEqual(self.wy(b),self.wy(longer,at))
        self.assertEqual(self.wy(b[:33])['state'],'SPRING_CANDIDATE')
        self.assertEqual(self.wy(b[:10]+b[11:])['state'],'SOURCE_GAP')

    def test_body_break_then_separate_reclaim_in_both_directions(self):
        up=self.five([(109,111,108,110.5),(110.3,110.4,109,109.5)])
        r=self.tbs(up)
        self.assertEqual(r['state'],'RECLAIMED')
        self.assertEqual([e['event_root_id'] for e in r['events']],[b.id for b in up])
        down=self.five([(91,92,89,89.5),(89.7,91,89.6,90.5)])
        self.assertEqual(self.tbs(down)['state'],'RECLAIMED')
        self.assertIn('F2_ACCEPTED_BREAKOUT',r['rivals'])
        self.assertFalse(r['source_qualified']);self.assertFalse(r['rank_eligible'])

    def test_wick_only_same_bar_and_late_parent_never_reclaim(self):
        wick=self.five([(109,111,108,109.5)])
        self.assertEqual(self.tbs(wick)['state'],'PARENT_FROZEN')
        event=self.five([(109,111,108,110.5),(110.3,110.4,109,109.5)])
        self.assertNotEqual(self.tbs(event[:1])['state'],'RECLAIMED')
        self.assertEqual(self.tbs(event,selection_known_at=event[0].end)['state'],'PARENT_FROZEN')
        self.assertEqual(self.tbs(event,selection_known_at=iso_seconds(START+1))['state'],'UNKNOWN')

    def test_accepted_break_expiry_missing_and_gap(self):
        b=self.five([(109,111,108,110.5),(110.5,111,110,110.6),(110.6,111,110,110.7)])
        self.assertEqual(self.tbs(b)['state'],'ACCEPTED_OUTSIDE')
        self.assertEqual(self.tbs(b,max_reclaim_bars=1)['state'],'EXPIRED')
        self.assertEqual(self.tbs(b,source_complete=False)['state'],'SOURCE_GAP')
        self.assertEqual(self.tbs([b[0],b[2]])['state'],'SOURCE_GAP')
        self.assertEqual(self.tbs(b[:2],cutoff=b[2].end,as_of=b[2].end)['state'],'SOURCE_GAP')
        self.assertEqual(self.tbs(b[1:])['state'],'SOURCE_GAP')

    def test_close_beyond_opposite_parent_edge_is_not_a_reclaim(self):
        b=self.five([(109,111,108,110.5),(110,111,88,89)])
        self.assertEqual(self.tbs(b)['state'],'BODY_OUTSIDE')

    def test_delayed_break_cannot_precede_a_followup_it_was_not_known_for(self):
        b=self.five([(109,111,108,110.5),(110.3,110.4,109,109.5)])
        b[0]=replace(b[0],available_at=b[1].end,received_at=b[1].end)
        self.assertEqual(self.tbs(b)['reason'],'OUTSIDE_BAR_NOT_AVAILABLE_BEFORE_FOLLOWUP')

    def test_m33_append_future_and_shared_bar_root(self):
        b=self.five([(109,111,108,110.5),(110.3,110.4,109,109.5),(109.5,110,106,107)])
        prior=self.tbs(b[:2])
        self.assertEqual(prior,self.tbs(b,cutoff=b[1].end,as_of=b[1].end))
        self.assertEqual(prior['events'][0]['source_ids'][0],b[0].id)
        self.assertEqual(self.tbs(b)['state'],'RESPONSE_CANDIDATE')

    def test_shadow_registry_and_selected_engine_do_not_enable_admission(self):
        config=load_config();m=manifest(config)
        self.assertEqual(len(m['methods']),31)
        self.assertEqual([x['id'] for x in m['shadow_methods']],['M32','M33'])
        b=self.balance([(100,101,97,100)])
        output=analyze_selected(b,TICK,cutoff=b[-1].end,as_of=b[-1].end)
        self.assertEqual(output['shadow_methods'][0]['state'],'SPRING_CANDIDATE')
        self.assertEqual(output['shadow_methods'][1]['state'],'SOURCE_GAP')
        self.assertEqual(qualified_route_a(output,None,native_symbol='TESTUSDT',timeframe='1h',cutoff=b[-1].end),[])
        self.assertEqual(len(output['methods']),31)

    def test_optional_m33_input_is_offline_only_and_cannot_break_baseline(self):
        b=self.balance([(100,101,97,100)])
        for invalid in ({}, {'parent':'not a bar','children':[],
                            'selection_known_at':b[-1].end,'atr_ref':1}):
            output=analyze_selected(b,TICK,cutoff=b[-1].end,as_of=b[-1].end,inputs={'M33':invalid})
            self.assertEqual(output['shadow_methods'][1]['reason'],'INVALID_OPTIONAL_SHADOW_INPUT')
            self.assertEqual(len(output['methods']),31)
        for mode,allowed in (('SYNTHETIC',True),('AUTHENTIC_REPLAY',True),('LIVE',False)):
            sources=ResearchSources(mode=mode,selected_inputs={('TESTUSDT','1h'):{'M33':{}}})
            self.assertEqual('M33' in sources.inputs_for('TESTUSDT','1h',b[-1].end,b[-1].end),allowed)

