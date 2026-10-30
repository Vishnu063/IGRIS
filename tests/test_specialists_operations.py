from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.specialists.registry import CATALOG, profile, recommend
from igris.specialists.contracts import contract_fixture
from igris.adapters.contracts import ContractError


class OperationsSpecialistTests(unittest.TestCase):
    def test_exactly_fifteen_distinct_capabilities_individually_testable(self):
        self.assertEqual(len(CATALOG),15)
        self.assertEqual(len({task for _,task in CATALOG.values()}),15)
        for role in CATALOG:
            with self.subTest(role=role):
                spec=profile(role)
                self.assertEqual(spec.id,role)
                self.assertEqual(recommend(spec.task),(role,))
                result=contract_fixture(spec,'c'*32,spec.task,'Synthetic supplied task.')
                self.assertEqual(result['role'],role)
                self.assertEqual(result['origin'],'simulated')
                self.assertFalse(result['executed_actions'])
    def test_operations_profiles_are_inert_and_immutable(self):
        for role in ('research','project_manager','incident_response','voice_ai','minimal_change'):
            spec=profile(role)
            self.assertEqual(spec.permissions,())
            with self.assertRaises(FrozenInstanceError): spec.mode='autonomous'
            with self.assertRaises(ContractError): contract_fixture(spec,'c'*32,'execute','request')
        with self.assertRaises(TypeError): CATALOG['new_agent']=('arbitrary','execute')
