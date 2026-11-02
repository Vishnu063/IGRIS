"""Disposable Linux preparation-file checks; never claims Mac or VM execution."""
import importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('mac_package',ROOT/'scripts/mac_package.py');package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
class MacPackageTests(unittest.TestCase):
 def test_roundtrip_preserves_unlisted_user_files(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as folder:
   root=Path(folder)/'preparation';package.install(root);package.check(root);(root/'notes.txt').write_text('Preserve user content.');result=package.uninstall(root)
   self.assertEqual(result['retained'],['notes.txt']);self.assertEqual((root/'notes.txt').read_text(),'Preserve user content.')
 def test_existing_modified_and_vm_state_preserved(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as folder:
   root=Path(folder)/'preparation';package.install(root)
   with self.assertRaises(package.Blocked):package.install(root)
   (root/'lima.yaml').write_text('user modified')
   with self.assertRaises(package.Blocked):package.uninstall(root)
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as folder:
   root=Path(folder)/'preparation';package.install(root);(root/'vm-state').mkdir()
   with self.assertRaises(package.Blocked):package.uninstall(root)
   self.assertTrue((root/'manifest.json').exists())
 def test_no_linux_or_x86_fallback(self):
  with patch.object(package.platform,'system',return_value='Linux'),patch.object(package.platform,'machine',return_value='aarch64'):
   with self.assertRaises(package.Blocked):package.native_gate()
  with patch.object(package.platform,'system',return_value='Darwin'),patch.object(package.platform,'machine',return_value='x86_64'):
   with self.assertRaises(package.Blocked):package.native_gate()
 def test_no_home_mount_or_autostart(self):
  text=(ROOT/'packaging/macos/lima.yaml').read_text();self.assertIn('mounts: []',text);self.assertIn('provision: []',text);self.assertNotIn('guestSocket',text);self.assertIn('hostIP: 127.0.0.1',text)
  assets=json.loads((ROOT/'packaging/macos/assets.json').read_text());self.assertEqual(assets['authorized_spend_inr'],0);self.assertEqual(assets['status'],'PINNED_NOT_EXECUTED')
