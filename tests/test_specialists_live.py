"""Registration/authorization tests; no model inference claimed by unit tests."""
import hashlib,sys,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.specialists.live import LiveSpecialists
from igris.specialists.registry import CATALOG
from igris.guardian.policy import Denied
from igris.adapters.contracts import ContractError
class LiveSpecialistContracts(unittest.TestCase):
 def test_fifteen_reviewed_choices_and_no_tool_rights(self):
  live=LiveSpecialists();self.assertEqual(len(live.choices()),15)
  for item in live.choices():
   self.assertEqual(item['tools'],[]);args=live.arguments(item['role'],'Review only supplied evidence.')
   self.assertEqual(live.normalize(args),args)
   with self.assertRaises(Denied):live.normalize(dict(args,definition_sha256='0'*64))
   with self.assertRaises(ContractError):live.normalize(dict(args,task='execute_shell'))
 def test_disabled_and_fake_lease_denied(self):
  live=LiveSpecialists()
  with self.assertRaises(Denied):live.scope(threading.Event())
  live.enabled=True
  with self.assertRaises(Denied):live.execute({},threading.Event(),{})
 def test_unknown_malformed_and_oversized_context(self):
  live=LiveSpecialists()
  for raw in (None,[],{}, {'role':'shell'}):
   with self.assertRaises(ContractError):live.normalize(raw)
  for text in ('','x'*5000):
   with self.assertRaises((ValueError,ContractError)):live.arguments('frontend',text)
 def test_specialist_permission_is_separate_from_read_permission(self):
  from igris.guardian.policy import Policy,Permission
  with self.assertRaises(Denied):Policy('owner',frozenset({Permission.READ})).require('specialists.reason')
  Policy('owner',frozenset({Permission.SPECIALIST})).require('specialists.reason')
