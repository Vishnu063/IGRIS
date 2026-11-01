"""Fail-closed mount-profile contracts; actual NN isolation has live evidence."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.isolated import IsolatedWorker
from igris.adapters.contracts import ContractError
class MemoryIsolationTests(unittest.TestCase):
 def test_original_worker_profile_rejects_writable_state(self):
  with tempfile.TemporaryDirectory() as folder,self.assertRaises(ContractError):
   IsolatedWorker().run('sha256:'+'a'*64,[],[],component='worker-test',state_directory=folder)
 def test_memory_worker_rejects_outside_index_root(self):
  with tempfile.TemporaryDirectory() as folder,self.assertRaises(ContractError):
   IsolatedWorker().run('sha256:'+'a'*64,[],[],component='mem0',mount_profile='mem0-semantic-index',state_directory=folder)
 def test_memory_profile_cannot_be_used_for_other_components(self):
  with self.assertRaises(ContractError):IsolatedWorker().run('sha256:'+'a'*64,[],[],component='n8n',mount_profile='mem0-semantic-index')
