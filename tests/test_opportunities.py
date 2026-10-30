import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.opportunities import Evidence, Opportunity, evaluate


class OpportunityTests(unittest.TestCase):
    def sample(self, **changes):
        data = dict(focus='maintenance', requirements='Monitor a sample site', feasible_score=4,
                    competition_score=3, effort_hours=6, expense_paise=0,
                    possible_revenue_paise=300000, risks=('No customer commitment',))
        return Opportunity(**(data | changes))

    def test_sample_evidence_not_real_demand(self):
        e = Evidence('docs/business/sample-opportunity.md', 'Synthetic monitoring inquiry', 'sample')
        result = evaluate(self.sample(demand_evidence=(e,)))
        self.assertFalse(result['market_demand_verified'])
        self.assertTrue(result['estimated_only'])
        self.assertEqual(result['estimated_margin_paise'], 300000)
        self.assertEqual(result['evidence_origins'], ('sample',))

    def test_missing_evidence_losses_and_invalid_estimates(self):
        result = evaluate(self.sample(expense_paise=400000))
        self.assertEqual(result['research_status'], 'needs_market_research')
        self.assertEqual(result['estimated_margin_paise'], -100000)
        self.assertTrue(result['spending_required'])
        for bad in (-1, True, 3.2):
            with self.assertRaises(ValueError): self.sample(effort_hours=bad)
        with self.assertRaises(ValueError): self.sample(feasible_score=6)
