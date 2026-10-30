from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.specialists.registry import profile, recommend
from igris.specialists.contracts import contract_fixture, validate_output
from igris.adapters.contracts import ContractError


class QualitySpecialistTests(unittest.TestCase):
    def test_all_quality_roles_have_scoped_permissionless_outputs(self):
        for role in ('security_privacy','testing','code_reviewer','ui_ux','database'):
            with self.subTest(role=role):
                spec=profile(role)
                self.assertEqual(spec.permissions, ())
                self.assertEqual(spec.mode, 'proposal_only')
                self.assertEqual(recommend(spec.task), (role,))
                output=contract_fixture(spec,'b'*32,spec.task,'Supplied synthetic evidence.')
                self.assertFalse(output['executed_actions'])
                with self.assertRaises(ContractError): contract_fixture(spec,'b'*32,'execute_migration','text')
    def test_invalid_output_correlation_size_and_secrets(self):
        spec=profile('security_privacy')
        base={'role':spec.id,'mission_id':'b'*32,'task':spec.task,'summary':'password: synthetic fixture',
              'recommendations':['Review supplied evidence.'],'limitations':['Not a full audit.']}
        self.assertEqual(validate_output(spec,'b'*32,base)['summary'], '[REDACTED]')
        for key,value in (('role','database'),('mission_id','c'*32),('recommendations',[]),
                          ('summary','x'*1025),('permissions',['admin']),('origin','real')):
            with self.subTest(key=key), self.assertRaises(ContractError):
                validate_output(spec,'b'*32,dict(base,**{key:value}))
