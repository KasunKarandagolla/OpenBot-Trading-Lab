import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from binance_research_data import DataError
import openbot_current_market as market
import openbot_current_risk as risk
import openbot_demo_readonly as demo


def candle(open_ms):
    return [open_ms, '100', '101', '99', '100', '50', open_ms + 299_999, '5000', 10, '24', '2400', '0']


class MarketTests(unittest.TestCase):
    def test_closed_bar_cutoff_excludes_current_open(self):
        cutoff = 865 * 300_000
        rows = [candle(i * 300_000) for i in range(866)]
        self.assertEqual(len(market.closed_rows(rows, '5m', cutoff)), 865)

    def test_gap_staleness_and_bad_timestamps_fail(self):
        rows = [candle(i * 300_000) for i in range(865)]
        cutoff = 865 * 300_000
        with self.assertRaisesRegex(DataError, 'gap'):
            market.closed_rows(rows[:9] + rows[10:], '5m', cutoff)
        with self.assertRaisesRegex(DataError, 'stale'):
            market.closed_rows(rows, '5m', cutoff + 300_000)
        rows[4][6] += 1
        with self.assertRaisesRegex(DataError, 'clock'):
            market.closed_rows(rows, '5m', cutoff)

    def test_chart_hash_wrong_venue_and_freshness(self):
        with tempfile.TemporaryDirectory() as scratch:
            candidate = 'ETHUSDT-20261106T161054-93184b9fdf'
            packet = Path(scratch) / candidate
            packet.mkdir()
            members = {}
            for name in market.REQUIRED:
                path = packet / name
                path.parent.mkdir(exist_ok=True)
                body = b'\x89PNG\r\n\x1a\n' if name.endswith('.png') else b'{}'
                path.write_bytes(body)
                members[name] = hashlib.sha256(body).hexdigest()
            market.write(packet / 'MANIFEST.json', members)
            chart = packet / 'charts/context.png'
            chart.write_bytes(b'broken')
            with self.assertRaisesRegex(DataError, 'PNG'):
                market.verify(packet)
            chart.write_bytes(b'\x89PNG\r\n\x1a\n')
            record = dict(schema=market.SCHEMA, market_type='wrong-venue', venue='binance',
                          candidate_id=candidate, as_of_ms=1)
            for venue, message in (('wrong-venue', 'market type'), (market.MARKET, 'stale')):
                market.write(packet / 'candidate.json', {**record, 'market_type': venue})
                members['candidate.json'] = market.sha256((packet / 'candidate.json').read_bytes())
                market.write(packet / 'MANIFEST.json', members)
                with self.assertRaisesRegex(DataError, message):
                    market.verify(packet, fresh=True)


class RiskTests(unittest.TestCase):
    def setUp(self):
        lot = {'minQty': '0.001', 'maxQty': '10', 'stepSize': '0.001'}
        self.constraints = {'market_type': market.MARKET, 'symbol': 'ETHUSDT',
                            'public_filters': {'tick_size': '0.01', 'minimum_notional': '5',
                                               'limit': lot, 'market': lot},
                            'public_quote': {'bid': '99.99', 'ask': '100.02', 'quote_time_ms': 990}}
        self.plan = dict(decision='LIMIT_ENTRY', venue='Binance USD-M Demo', symbol='ETHUSDT', side='LONG',
                         entry='100', stop='99', tp1='103', tp2='105', quantity='0.2', leverage=20,
                         expires_at_ms=100_000, packet_sha256='fixture')
        self.demo = dict(verification='AUTHENTICATED_DEMO_WITH_SYMBOL_RULES', symbol='ETHUSDT',
                         demo_filters=self.constraints['public_filters'], observed_at_ms=990, open_positions=0,
                         pending_entry_slots=0, max_leverage=25, fee_per_side='0.0005', slippage_per_side='0.0005',
                         adverse_funding_rate='0.0001', available_usdt='25',
                         margin_model='ISOLATED_ONE_WAY_SINGLE_TIER', maintenance_ratio='0.004',
                         maintenance_deduction_usdt='0')
        self.receipts = {
            role: dict(agent_id=role if role != 'researcher-rebuttal' else 'market-researcher',
                       message_id=role + '-msg', session_id=role + '-session', observed_at='now',
                       packet_sha256='fixture', image_transfer_id='fixture-image')
            for role in risk.ROLES
        }

    def evaluate(self, plan=None, state=None):
        return risk.assess(plan or self.plan, self.constraints, state or self.demo, 1000, self.receipts, 'fixture')

    def test_arithmetic_and_no_order_authority(self):
        result = self.evaluate()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['metrics']['notional_usdt'], '20.0')
        self.assertEqual(result['metrics']['gross_stop_loss_usdt'], '0.2')
        self.assertFalse(result['order_authorized'])

    def test_price_size_leverage_venue_and_expired_conditional(self):
        cases = [
            ({'quantity': '0.26'}, 'POSITION_NOTIONAL_ABOVE_25_USDT'),
            ({'quantity': '0.01'}, 'BELOW_PUBLIC_MINIMUM_NOTIONAL'),
            ({'entry': '100.001'}, 'PRICE_TICK_MISMATCH'),
            ({'quantity': '0.2001'}, 'QUANTITY_FILTER_MISMATCH'),
            ({'leverage': 26}, 'LEVERAGE_OUTSIDE_10_TO_25'),
            ({'venue': 'Binance production'}, 'WRONG_DECISION_OR_VENUE'),
            ({'packet_sha256': 'another-packet'}, 'PROPOSAL_PACKET_HASH_MISMATCH'),
            ({'decision': 'CONDITIONAL_ENTRY', 'expires_at_ms': 1000}, 'EXPIRED_OR_INVALID_TTL'),
            ({'decision': 'CONDITIONAL_ENTRY'}, 'MISSING_CONDITIONAL_TRIGGER_OR_REVALIDATION'),
        ]
        for overrides, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(self.evaluate({**self.plan, **overrides})['reasons'], [reason])

    def test_exposure_and_liquidation(self):
        self.assertEqual(self.evaluate(state={**self.demo, 'open_positions': 1, 'pending_entry_slots': 1})['reasons'],
                         ['PORTFOLIO_SLOT_CAP'])
        result = self.evaluate({**self.plan, 'leverage': 25}, {**self.demo, 'maintenance_ratio': '0.039'})
        self.assertEqual(result['reasons'], ['INSUFFICIENT_LIQUIDATION_BUFFER'])

    def test_missing_and_rejected_specialists(self):
        del self.receipts['chart-vision']
        self.receipts['risk-reviewer']['status'] = 'permission.rejected'
        result = self.evaluate()
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertIn('MISSING_NATIVE_RECEIPT:chart-vision', result['reasons'])
        self.assertIn('PERMISSION_REJECTED:risk-reviewer', result['reasons'])


class DemoTests(unittest.TestCase):
    def test_reject_mutating_path_real_host_and_bad_signing(self):
        with patch.object(demo, 'HTTPSConnection') as transport:
            for target in ('/fapi/v1/order', '/fapi/v1/leverage', 'https://fapi.binance.com/fapi/v3/account',
                           '/fapi/v3/balance?signature=forbidden'):
                with self.assertRaisesRegex(demo.ReadError, 'REJECTED'):
                    demo.get(target, ('dummy', 'dummy'), 123)
            with self.assertRaisesRegex(demo.ReadError, 'REJECTED'):
                demo.get('/fapi/v3/balance')
            transport.assert_not_called()

    def test_only_demo_get_and_never_follow_redirect(self):
        with patch.object(demo, 'HTTPSConnection') as transport:
            conn = transport.return_value
            conn.getresponse.return_value.status = 302
            conn.getresponse.return_value.read.return_value = b'{}'
            with self.assertRaises(demo.ReadError) as raised:
                demo.get(demo.CLOCK)
            self.assertEqual(transport.call_args.args[0], 'demo-fapi.binance.com')
            self.assertEqual(conn.request.call_count, 1)
            self.assertEqual(conn.request.call_args.args[0], 'GET')
            self.assertNotIn('signature', json.dumps(raised.exception.receipt))

    def test_sanitized_projection_drops_provider_fields(self):
        report = demo.summarize([{'asset': 'USDT', 'balance': '5000', 'accountAlias': 'private'}],
                                {'availableBalance': '5000', 'secret': 'unwanted'}, [])
        self.assertNotIn('private', json.dumps(report))
        self.assertNotIn('unwanted', json.dumps(report))
        self.assertEqual(report['assets'][0]['balance'], '5000')


if __name__ == '__main__':
    unittest.main()
