"""Ops registration contracts; actual Docker execution is in the live script."""
import sys,unittest,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.integrations.ops_runtime import RealOpsMonitor
from igris.guardian.policy import Denied
from igris.adapters.contracts import ContractError,AdapterUnavailable
class OpsRuntimeContracts(unittest.TestCase):
    def monitor(self):
        monitor=object.__new__(RealOpsMonitor);monitor.enabled=False;monitor.config={'container_id':'a'*64};return monitor
    def test_default_disabled(self):
        with self.assertRaises(AdapterUnavailable):self.monitor().scope(threading.Event())
    def test_exact_target_schema(self):
        monitor=self.monitor()
        self.assertEqual(monitor.normalize({'container_id':'a'*64}),{'container_id':'a'*64})
        for raw in ({},{'container_id':'b'*64},{'container_id':'a'*64,'restart':True},[],None):
            with self.subTest(raw=raw),self.assertRaises(ContractError):monitor.normalize(raw)
    def test_cannot_execute_without_guardian_lease(self):
        monitor=self.monitor();monitor.enabled=True
        for permit in (None,{},object()):
            with self.assertRaises(Denied):monitor.execute({'container_id':'a'*64},threading.Event(),permit)
