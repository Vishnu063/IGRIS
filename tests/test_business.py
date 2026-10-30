import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.business import BusinessController, FOCUS
from igris.controller import MissionController, State


class BusinessTests(unittest.TestCase):
    def test_independent_missions_and_all_focuses(self):
        business = BusinessController()
        technical = MissionController('owner', {'plan': lambda ctx: None})
        task = technical.create('Plan a site', 'plan')
        for focus in FOCUS:
            mission = business.create(focus, 'Research a legitimate opportunity')
            self.assertEqual(mission.category, 'business')
            business.link_technical(mission.id, task.id)
            business.move(mission.id, 'evaluating')
        self.assertEqual(technical.get(task.id).state, State.REQUESTED)

    def test_invalid_transitions_and_sanitization(self):
        b = BusinessController()
        mission = b.create('devops', 'password: synthetic')
        self.assertEqual(mission.objective, '[REDACTED]')
        with self.assertRaises(ValueError): b.move(mission.id, 'closed')
        with self.assertRaises(ValueError): b.create('guaranteed_income', 'anything')
        for state in ('evaluating', 'proposal_draft', 'delivery_planning', 'closed'):
            b.move(mission.id, state)
        with self.assertRaises(ValueError): b.move(mission.id, 'research')
