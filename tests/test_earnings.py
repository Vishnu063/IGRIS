import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from igris.earnings import Earnings
from igris.guardian.policy import Denied


class EarningsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'earnings.db'
        self.e = Earnings(self.path, 'owner', initialize=True)

    def test_persistent_lifecycle_partial_payments_and_actual_profit(self):
        deal = self.e.opportunity('owner', 'Synthetic client project', 900000)
        self.assertEqual(self.e.report('owner')['actual_profit_paise'], 0)
        with self.assertRaises(ValueError): self.e.invoice('owner', deal, 100000)
        for target in ('proposal_submitted', 'client_acquired', 'project_completed'):
            self.e.advance('owner', deal, target, evidence_ref='Synthetic lifecycle evidence')
        invoice = self.e.invoice('owner', deal, 100000)
        self.assertEqual(self.e.invoice_status('owner', invoice), 'unpaid')
        self.e.payment('owner', invoice, 40000, reference='sample-one', evidence_ref='Synthetic receipt', confirmed=True)
        self.assertEqual(self.e.invoice_status('owner', invoice), 'partial')
        self.e.payment('owner', invoice, 60000, reference='sample-two', evidence_ref='Synthetic receipt', confirmed=True)
        self.e.expense('owner', 10000, reference='sample-expense', evidence_ref='Synthetic expense receipt', confirmed=True)
        self.assertEqual(self.e.invoice_status('owner', invoice), 'paid')
        report = Earnings(self.path, 'owner').report('owner')
        self.assertEqual(report['actual_profit_paise'], 90000)
        self.assertEqual(report['estimated_revenue_paise'], 900000)
        self.assertEqual(report['proposals_submitted'], 1)
        self.assertFalse(report['bank_verified'])

    def test_replay_invalid_money_and_access_denied(self):
        with self.assertRaises(Denied): self.e.report('intruder')
        for amount in (-1, True, 1.1):
            with self.assertRaises(ValueError): self.e.opportunity('owner', 'Sample', amount)
        with self.assertRaises(ValueError): self.e.expense('owner', 100, reference='sample', evidence_ref='Synthetic')
        self.e.expense('owner', 100, reference='sample', evidence_ref='Synthetic', confirmed=True)
        with self.assertRaises(ValueError): self.e.expense('owner', 100, reference='sample', evidence_ref='Synthetic', confirmed=True)
        self.assertEqual(self.e.report('owner')['actual_profit_paise'], -100)
