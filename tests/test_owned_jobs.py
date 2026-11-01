"""Ownership guard command-contract fixtures; live cleanup tested separately."""
import subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.owned_jobs import remove_owned
class OwnedJobTests(unittest.TestCase):
 def test_never_removes_by_name_and_requires_exact_label(self):
  calls=[];remaining=[('a'*64)+'\n','','']
  def fixture(args,**kwargs):
   calls.append(args)
   return subprocess.CompletedProcess(args,0,remaining.pop(0) if 'ls' in args else '')
  with patch('igris.owned_jobs.subprocess.run',fixture),patch('igris.owned_jobs.time.sleep'):
   remove_owned(['docker'],{},'igris-fixture-test','b'*32)
  self.assertIn('label=com.igris.owner='+('b'*32),calls[0]);self.assertEqual([args for args in calls if 'rm' in args],[['docker','rm','--force','a'*64]])
 def test_unrelated_name_is_preserved(self):
  with patch('igris.owned_jobs.subprocess.run',return_value=subprocess.CompletedProcess([],0,'')) as call,patch('igris.owned_jobs.time.sleep'):
   remove_owned(['docker'],{},'igris-fixture-test','b'*32)
  self.assertTrue(all('rm' not in args[0][0] for args in call.call_args_list))
 def test_automatic_removal_race_requires_repeated_absence(self):
  results=[('a'*64)+'\n','',''];calls=[]
  def fixture(args,**kwargs):
   calls.append(args);return subprocess.CompletedProcess(args,1 if 'rm' in args else 0,results.pop(0) if 'ls' in args else '')
  with patch('igris.owned_jobs.subprocess.run',fixture),patch('igris.owned_jobs.time.sleep'):
   remove_owned(['docker'],{},'igris-fixture-test','b'*32)
  self.assertEqual(sum('ls' in args for args in calls),3)
 def test_remaining_owned_container_never_reports_cleanup(self):
  def fixture(args,**kwargs):return subprocess.CompletedProcess(args,1 if 'rm' in args else 0,('a'*64)+'\n' if 'ls' in args else '')
  with patch('igris.owned_jobs.subprocess.run',fixture),patch('igris.owned_jobs.time.sleep'),self.assertRaises(RuntimeError):
   remove_owned(['docker'],{},'igris-fixture-test','b'*32)

class OwnedLaunchTests(unittest.TestCase):
 def test_acknowledged_creation_before_any_start_and_private_cleanup_record(self):
  import tempfile,json
  from igris.owned_jobs import OwnedLaunch,assert_no_pending_launches,UnconfirmedLaunch
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);launch=OwnedLaunch(root,['docker'],{},'igris-test-launch','c'*32);remaining=['a'*64+'\n','',''];calls=[]
   def fixture(args,**kwargs):
    calls.append(args);return subprocess.CompletedProcess(args,0,b'a'*64+b'\n' if 'create' in args else remaining.pop(0) if 'ls' in args else '')
   with patch('igris.owned_jobs.subprocess.run',fixture),patch('igris.owned_jobs.time.sleep'):
    self.assertEqual(launch.create(['docker','create']),'a'*64)
    self.assertEqual(launch.path.stat().st_mode&0o777,0o600)
    self.assertEqual(json.loads(launch.path.read_text())['phase'],'created')
    with self.assertRaises(UnconfirmedLaunch):assert_no_pending_launches(root)
    self.assertFalse(any('start' in args for args in calls));launch.cleanup();assert_no_pending_launches(root)
 def test_unknown_creation_retains_record_and_blocks_restart(self):
  import tempfile,json
  from igris.owned_jobs import OwnedLaunch,assert_no_pending_launches,UnconfirmedLaunch
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);launch=OwnedLaunch(root,['docker'],{},'igris-test-launch','c'*32)
   with patch('igris.owned_jobs.subprocess.run',side_effect=subprocess.TimeoutExpired(['docker','create'],30)):
    with self.assertRaises(subprocess.TimeoutExpired):launch.create(['docker','create'])
   with self.assertRaises(UnconfirmedLaunch):launch.cleanup()
   with self.assertRaises(UnconfirmedLaunch):assert_no_pending_launches(root)
   self.assertIsNone(json.loads(launch.path.read_text())['container_id'])
 def test_immutable_id_mismatch_is_never_removed(self):
  with patch('igris.owned_jobs.subprocess.run',return_value=subprocess.CompletedProcess([],0,'b'*64+'\n')) as call,self.assertRaises(RuntimeError):
   remove_owned(['docker'],{},'igris-test-launch','c'*32,expected_cid='a'*64)
  self.assertEqual(call.call_count,1)
