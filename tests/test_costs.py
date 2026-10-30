import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from igris.costs import CostEstimate, CostGuardian
from igris.guardian.policy import Denied


class CostTests(unittest.TestCase):
    def test_zero_budget_denies_positive_unknown_and_paid_intro_offers(self):
        gate = CostGuardian()
        for estimate in (CostEstimate('api', 1), CostEstimate('cloud', None), CostEstimate('infrastructure', 0, paid_service=True)):
            with self.assertRaises(Denied): gate.check(estimate)
        self.assertFalse(gate.check(CostEstimate('resource', 0, quantity=1024, unit='bytes'))['service_activated'])
        report = gate.report()
        self.assertEqual(report['authorized_budget_paise'], 0)
        self.assertEqual(report['rejected_requests'], 3)
        self.assertEqual(report['unknown_estimates'], 1)
        self.assertIsNone(report['actual_spend_paise'])

    def test_invalid_amount_currency_and_budget_override(self):
        for value in (-1, True, 0.5):
            with self.assertRaises(ValueError): CostEstimate('api', value)
        with self.assertRaises(ValueError): CostEstimate('cloud', 0, currency='USD')
        with self.assertRaises(AttributeError): CostGuardian().authorized_budget_paise = 100
