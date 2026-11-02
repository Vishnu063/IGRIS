import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.catalog import default_catalog
from igris.guardian.policy import Denied
class CatalogTests(unittest.TestCase):
 def test_idle_is_lazy_and_platform_accounts_unavailable(self):
  catalog=default_catalog();self.assertEqual(catalog.loaded,{})
  for name in ('naukri','linkedin','github','gmail','browser','ops_pilot','n8n'):
   with self.assertRaises(Denied):catalog.resolve(name)
  self.assertEqual(catalog.loaded,{})
 def test_only_requested_lightweight_adapter_loaded(self):
  catalog=default_catalog();clock=catalog.resolve('clock');self.assertIs(clock,catalog.resolve('clock'));self.assertEqual(set(catalog.loaded),{'clock'});self.assertEqual(clock.health()['status'],'stopped');catalog.shutdown();self.assertEqual(clock.health()['status'],'stopped')
