"""Actual locks/SQLite/subprocess restart; no AI connectivity is inferred."""
import json,os,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.foreground import Foreground,ForegroundBusy,TaskAlreadyRecorded,fingerprint
from igris.guardian.policy import Denied
class ForegroundTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.controller=Foreground(self.root/'tasks')
 def test_only_one_task_across_instances_and_approval_wait(self):
  first=self.controller.begin('owner','chat');first.transition('running',action='hermes.reply');first.transition('waiting_for_approval')
  try:
   for other in (self.controller,Foreground(self.root/'tasks')):
    with self.assertRaises(ForegroundBusy):other.begin('owner','specialists.reason')
   self.assertEqual(self.controller.snapshot('owner')['state'],'waiting_for_approval')
  finally:first.finish(verified=True)
  second=self.controller.begin('owner','clock');second.finish(verified=True);self.assertEqual(self.controller.snapshot('owner')['state'],'idle')
 def test_duplicate_and_changed_retry_never_execute(self):
  task_id=uuid4().hex;identity=fingerprint('chat',{'context':'synthetic'});task=self.controller.begin('owner','chat',task_id=task_id,identity=identity);task.finish(verified=True)
  reopened=Foreground(self.root/'tasks')
  with self.assertRaises(TaskAlreadyRecorded):reopened.begin('owner','chat',task_id=task_id,identity=identity)
  with self.assertRaises(Denied):reopened.begin('owner','chat',task_id=task_id,identity=fingerprint('chat',{}))
 def test_real_process_crash_blocks_new_work_until_owner_review(self):
  task_id=uuid4().hex
  code='import sys;sys.path.insert(0,sys.argv[1]);from igris.foreground import Foreground;c=Foreground(sys.argv[2]);t=c.begin("owner","chat",task_id=sys.argv[3]);t.transition("running")'
  subprocess.run([sys.executable,'-I','-c',code,str(ROOT/'src'),str(self.root/'tasks'),task_id],check=True)
  with self.assertRaises(ForegroundBusy):self.controller.begin('owner','chat')
  with self.assertRaises(TaskAlreadyRecorded):self.controller.begin('owner','chat',task_id=task_id)
  with self.assertRaises(Denied):self.controller.recover('owner',lambda:False)
  # Child created no worker; observed child exit verifies all resources it started.
  self.controller.recover('owner',lambda:True);self.assertEqual(self.controller.lookup('owner',task_id)['status'],'cancelled')
  task=self.controller.begin('owner','clock');task.finish(verified=True)
 def test_cancel_and_uncertain_cleanup_are_not_success(self):
  task=self.controller.begin('owner','chat');self.controller.request_cancel('owner',task.task_id)
  self.assertEqual(self.controller.snapshot('owner')['state'],'stopping');self.assertTrue(task.cancel.is_set())
  result=task.finish(verified=True);self.assertEqual(result['status'],'cancelled')
  task=self.controller.begin('owner','ops.lifecycle');result=task.finish(verified=True,cleanup=False)
  self.assertEqual(result['outcome'],'partially_completed');self.assertEqual(result['cleanup_status'],'unverified')
  with self.assertRaises(ForegroundBusy):self.controller.begin('owner','chat')
 def test_structured_outcomes_and_actor_isolation(self):
  for kwargs,expected in [({},'not_verified'),({'error':'Failure'},'failed'),({'verified':True},'successfully_completed'),({'verified':True,'retained':True},'successfully_completed')]:
   task=self.controller.begin('owner','clock');result=task.finish(**kwargs);self.assertEqual(result['outcome'],expected)
   self.assertEqual(set(result),{'task_id','task_type','status','started_at','completed_at','outcome','actions_attempted','verified_outcomes','errors_or_limitations','cleanup_status'})
   with self.assertRaises(Denied):self.controller.lookup('other',task.task_id)
