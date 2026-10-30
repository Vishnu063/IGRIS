from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.adapters.contracts import AdapterUnavailable, ContractError
from igris.adapters.hermes import MockHermesAdapter, PlannerRequest, parse_mock_plan, select_hermes


class HermesTests(unittest.TestCase):
    def test_mock_contract_has_explicit_simulated_origin(self):
        request = PlannerRequest('a' * 32, 'inspect approved fixture')
        result = select_hermes('mock').plan(request)
        self.assertEqual(result.route, 'inspect_fixture')
        self.assertEqual(result.origin, 'simulated')
        self.assertEqual(select_hermes('mock').connectivity, 'simulated_only')

    def test_live_is_unavailable_with_no_silent_mock_fallback(self):
        for mode in ('disabled', 'real'):
            adapter = select_hermes(mode)
            self.assertEqual(adapter.connectivity, 'not_connected')
            with self.assertRaises(AdapterUnavailable):
                adapter.plan(PlannerRequest('b' * 32, 'request'))

    def test_malformed_and_authority_bearing_output_rejected(self):
        for raw in (None, [], {'route': 'shell', 'summary': 'execute command'},
                    {'route': 'inspect_fixture', 'summary': 'data', 'permissions': ['admin']},
                    {'route': 'inspect_fixture', 'summary': 'data', 'origin': 'real'},
                    {'route': 'inspect_fixture', 'summary': 'x' * 8193}):
            with self.subTest(raw_type=type(raw).__name__), self.assertRaises(ContractError):
                parse_mock_plan(raw)

    def test_bad_request_and_sensitive_text(self):
        for mission, text in (('../x', 'text'), ('a' * 32, ''), ('a' * 32, 'x' * 8193)):
            with self.assertRaises(ContractError):
                PlannerRequest(mission, text)
        request = PlannerRequest('a' * 32, 'password: synthetic fixture')
        self.assertEqual(request.prompt, '[REDACTED]')
        plan = MockHermesAdapter({'route': 'summarize', 'summary': 'token: synthetic fixture'}).plan(request)
        self.assertEqual(plan.summary, '[REDACTED]')
        with self.assertRaises(ContractError):
            MockHermesAdapter().plan({'prompt': 'untyped'})
