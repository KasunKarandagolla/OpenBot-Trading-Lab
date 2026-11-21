"""Independent synthetic boundary sequences, shared by both selected reducers."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from researcher.contracts import ContractError, utc
from researcher.family_engine import boundary_family, closed_prefix
from researcher.structures import boundary_events, event
from test_session6a import bars, mirror, ref


REFERENCE_BAR = (98, 99, 97, 98)
RECLAIM = [(100, 102, 98, 99)]
WEAK = (99, '99.1', '98.3', '98.5')
STRONG = ('98.5', '98.6', 95, '95.5')


class F4Recovery(unittest.TestCase):
    def assert_initiative(self, rows, expected_index, side):
        b = bars([REFERENCE_BAR, *rows])
        if side == -1:
            b = mirror(b)
        reference = ref(b, side=side)
        for reducer, event_field in ((boundary_family, 'timeline'), (boundary_events, 'events')):
            with self.subTest(reducer=reducer.__name__, side=side):
                result = (reducer('F4', reference, b, as_of=b[-1].end) if reducer is boundary_family else
                          reducer(reference, b, as_of=b[-1].end))
                initiatives = [item for item in result[event_field] if item['kind'] == 'OPPOSING_INITIATIVE']
                if expected_index is None:
                    self.assertEqual(initiatives, [])
                    continue
                expected = event(reference, b[expected_index + 1], 'OPPOSING_INITIATIVE')
                self.assertEqual([item['id'] for item in initiatives], [expected.id])
                initiative = initiatives[0]
                self.assertEqual(initiative['known_at'], b[expected_index + 1].end)
                self.assertEqual(initiative['available_at'], expected.available_at)
                self.assertEqual(initiative['reference_id'], reference.id)

    def test_weak_progress_then_strong_confirmation_mirrored(self):
        for side in (1, -1):
            self.assert_initiative([*RECLAIM, WEAK, STRONG], 2, side)
            self.assert_initiative([*RECLAIM, (99, '99.1', 95, '95.5')], 1, side)
            self.assert_initiative([*RECLAIM, WEAK], None, side)

    def test_wrong_direction_expiry_and_outside_acceptance(self):
        self.assert_initiative([*RECLAIM, WEAK, (95, 99, '94.9', 98)], None, 1)
        self.assert_initiative([*RECLAIM, (95, 98, '94.9', 98)], None, 1)
        outside = [(100, 102, 100, 101)] * 3
        b = bars([REFERENCE_BAR, *RECLAIM, WEAK, *outside, STRONG])
        r = ref(b)
        outcome = boundary_family('F4', r, b, as_of=b[-1].end)
        self.assertEqual(outcome['timeline'][-1]['kind'], 'LATER_OUTSIDE_ACCEPTANCE')
        self.assertEqual(outcome['stage'], 'INVALIDATED')
        self.assertFalse(outcome['details']['opposing_initiative_verified'])
        b = bars([REFERENCE_BAR, *RECLAIM, WEAK, STRONG])
        r = replace(ref(b), valid_until=b[2].end)
        outcome = boundary_family('F4', r, b, as_of=b[-1].end)
        self.assertEqual(outcome['timeline'][-1]['kind'], 'EXPIRED')
        self.assertFalse(outcome['details']['opposing_initiative_verified'])

    def test_prefix_gap_exact_threshold_and_repeated_confirmation(self):
        # Frozen ATR=2, TR/ATR=1.2, body/range=.5, progress=1.2.
        exact = (99, 99, '96.6', '97.8')
        below = (99, 99, '96.6001', '97.8')
        self.assert_initiative([*RECLAIM, exact, STRONG], 1, 1)
        self.assert_initiative([*RECLAIM, below], None, 1)
        b = bars([REFERENCE_BAR, *RECLAIM, WEAK, STRONG])
        r = ref(b)
        prefix = closed_prefix(b, cutoff=b[2].end, as_of=b[2].end)
        before = boundary_family('F4', r, prefix, as_of=b[2].end)
        after = boundary_family('F4', r, b, as_of=b[-1].end)
        self.assertEqual(before['timeline'], after['timeline'][:-1])
        self.assertEqual(boundary_family('F4',r,b,as_of=b[2].end)['timeline'],before['timeline'])
        with self.assertRaisesRegex(ContractError, 'MISSING_OR_MISALIGNED_BARS'):
            closed_prefix([b[0], b[-1]], cutoff=b[-1].end, as_of=b[-1].end)
        late = (utc(b[-1].end) + timedelta(seconds=1)).isoformat()
        delayed = replace(b[-1], available_at=late, received_at=late)
        with self.assertRaisesRegex(ContractError, 'SOURCE_NOT_AVAILABLE'):
            closed_prefix([*b[:-1], delayed], cutoff=b[-1].end, as_of=b[-1].end)
