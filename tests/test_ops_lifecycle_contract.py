"""Shape/permission tests with synthetic monitor metadata; live lifecycle tests separate."""
import sys,threading,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.ops_lifecycle import OpsIntegration
from igris.integrations.ops_runtime import RealOpsMonitor
from igris.guardian.policy import Denied,Permission,Policy
from igris.adapters.contracts import ContractError
class OpsLifecycleContracts(unittest.TestCase):
 def adapter(self,mode='manual'):
  monitor=object.__new__(RealOpsMonitor);monitor.config={'container_id':'a'*64};monitor.enabled=False
  with patch('igris.integrations.ops_lifecycle.RealOpsMonitor',return_value=monitor):return OpsIntegration('synthetic',mode=mode)
 def test_manual_default_no_start_or_worker(self):
  adapter=self.adapter();self.assertEqual(adapter.mode,'manual');self.assertIsNone(adapter.process);self.assertIsNone(adapter.proxy)
  with self.assertRaises(Denied):adapter.start()
  with self.assertRaises(Denied):adapter.execute(adapter.arguments('start'),threading.Event(),None)
 def test_forbidden_target_mode_arguments_and_repairs(self):
  adapter=self.adapter()
  for raw in ({'action':'repair','container_id':'a'*64,'mode':'manual'},{'action':'start','container_id':'b'*64,'mode':'manual'},{'action':'start','container_id':'a'*64,'mode':'monitoring'},{'action':'start','container_id':'a'*64,'mode':'manual','shell':'injection'}):
   with self.assertRaises((Denied,ContractError)):adapter.normalize(raw)
  with self.assertRaises(Denied):self.adapter('on_demand').arguments('start')
 def test_read_permission_and_exact_lease_required(self):
  with self.assertRaises(Denied):Policy('owner').require('ops.lifecycle')
  Policy('owner',frozenset({Permission.READ})).require('ops.lifecycle')
  self.assertEqual(self.adapter().shutdown()['monitored_application_stopped'],False)
