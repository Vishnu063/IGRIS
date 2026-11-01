"""Typed boundary tests only; live CLI acceptance is a separate script."""
import json,sys,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.integrations.n8n_runtime import RealN8n
from igris.guardian.activities import ExecutionPermit,canonical
from igris.guardian.policy import Denied
from igris.adapters.contracts import AdapterUnavailable,ContractError

class N8nRuntimeTests(unittest.TestCase):
    def test_only_two_bounded_integer_operands(self):
        adapter=RealN8n()
        for raw in ({'left':'$(touch outside)','right':1},{'left':True,'right':1},{'left':1.0,'right':1},
                    {'left':1001,'right':0},{'left':1,'right':2,'workflow':'other'},{'left':1}):
            with self.subTest(raw=raw),self.assertRaises(ContractError):adapter.normalize(raw)
        self.assertNotEqual(adapter.normalize({'left':7,'right':5})['workflow_sha256'],adapter.normalize({'left':7,'right':6})['workflow_sha256'])
    def test_disabled_and_direct_or_forged_invocation_denied(self):
        adapter=RealN8n()
        with self.assertRaises(AdapterUnavailable):adapter.scope(threading.Event())
        with self.assertRaises(Denied):adapter.execute({'left':1,'right':2},threading.Event(),None)
        class ForgedIssuer:
            def _consume_permit(self,*args):raise AssertionError('Untrusted issuer invoked.')
        with self.assertRaises(Denied):ExecutionPermit(ForgedIssuer(),None).consume('n8n.calculate',{})
    def test_typed_telemetry_does_not_disable_string_privacy(self):
        self.assertEqual(json.loads(canonical({'epoch':1793500000}))['epoch'],1793500000)
        for value in ({'text':'+91 9876543210'},{'password':'synthetic-placeholder'}):
            with self.assertRaises(Denied):canonical(value)
