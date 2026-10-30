from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.specialists.registry import profile, recommend
from igris.specialists.contracts import contract_fixture, validate_output
from igris.adapters.contracts import ContractError


class DevelopmentSpecialistTests(unittest.TestCase):
    def test_each_development_role_contract(self):
        for role in ('frontend','backend','mobile','ai_engineer','devops'):
            with self.subTest(role=role):
                spec = profile(role)
                self.assertEqual(recommend(spec.task), (role,))
                self.assertEqual(spec.permissions, ())
                result = contract_fixture(spec, 'a'*32, spec.task, 'Supplied synthetic requirements.')
                self.assertEqual(result['origin'], 'simulated')
                self.assertFalse(result['executed_actions'])
                with self.assertRaises(ContractError): contract_fixture(spec, 'a'*32, 'deploy', 'request')
    def test_unknown_roles_and_injected_authority_rejected(self):
        with self.assertRaises(ContractError): profile('../../plugin')
        spec=profile('frontend')
        raw={'role':'frontend','mission_id':'a'*32,'task':spec.task,'summary':'data',
             'recommendations':['data'],'limitations':['fixture'],'commands':['shell']}
        with self.assertRaises(ContractError): validate_output(spec,'a'*32,raw)
