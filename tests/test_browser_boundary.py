import sys,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.integrations.playwright_runtime import OwnedBrowser
from igris.guardian.policy import Denied
from igris.adapters.contracts import AdapterUnavailable
class BrowserBoundaryTests(unittest.TestCase):
 def test_default_disabled(self):
  with self.assertRaises(AdapterUnavailable):OwnedBrowser().scope(threading.Event())
 def test_no_generic_browser_actions(self):
  adapter=OwnedBrowser()
  for action in ('submit','upload','purchase','evaluate','click','navigate'):
   with self.assertRaises(Denied):adapter.normalize({'site':'owned_acceptance','action':action})
  with self.assertRaises(Denied):adapter.normalize({'site':'../private','action':'inspect_and_screenshot'})
 def test_no_direct_execution(self):
  with self.assertRaises(Denied):OwnedBrowser(enabled=True).execute({'site':'owned_acceptance','action':'inspect_and_screenshot'},threading.Event(),None)
