"""Real scheduling/SQLite, explicitly synthetic cooperative inference for races."""
import json,sys,tempfile,threading,time,unittest
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.foreground import Foreground,ForegroundBusy,TaskAlreadyRecorded
from igris.chat import ChatService
from igris.conversations import ConversationMemory
from igris.mission_control import MissionControl,validate_decision
from igris.adapters.hermes_chat import ChatReply
from igris.adapters.contracts import AdapterUnavailable
from igris.guardian.policy import Denied
class CooperativeFixture:
 def __init__(self,*,cancel):self.cancel=cancel;self.entered=threading.Event();self.release=threading.Event();self.calls=0
 def reply(self,request):
  self.calls+=1;self.entered.set()
  while not self.release.wait(.01):
   if self.cancel.is_set():raise AdapterUnavailable('Synthetic cancellation fixture.')
  return ChatReply(request.request_id,'Synthetic unit fixture response.','a'*64,1)
class SingleTaskControlTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.foreground=Foreground(self.root/'foreground');self.control=MissionControl(self.root/'state',remember=True,backend_factory=CooperativeFixture,foreground=self.foreground);self.addCleanup(self.control.close)
 def wait(self,predicate):
  deadline=time.monotonic()+3
  while time.monotonic()<deadline:
   if predicate():return
   time.sleep(.01)
  self.fail('Fixture condition timed out.')
 def test_second_queued_task_does_not_launch_competing_worker_and_cancel_is_responsive(self):
  a=self.control.memory.create('owner',approved=True);b=self.control.memory.create('owner',approved=True)
  first=self.control.submit('chat',{'conversation_id':a,'prompt':'First synthetic request','mode':'chat'});self.assertTrue(self.control.backend.entered.wait(2))
  second=self.control.submit('chat',{'conversation_id':b,'prompt':'Second synthetic request','mode':'chat'})
  self.assertEqual(self.control.backend.calls,1);self.control.cancel_task(second['job_id']);start=time.monotonic();self.control.cancel_task(first['job_id']);self.assertLess(time.monotonic()-start,.2)
  self.wait(lambda:self.foreground.snapshot('owner')['state']=='idle');self.assertEqual(self.control.backend.calls,1);self.assertEqual(self.foreground.lookup('owner',first['job_id'])['status'],'cancelled')
 def test_retry_identity_is_stable_and_changed_arguments_rejected(self):
  a=self.control.memory.create('owner',approved=True);ident=uuid4().hex;body={'conversation_id':a,'prompt':'Synthetic retry','mode':'chat','request_id':ident}
  self.control.submit('chat',body);self.assertTrue(self.control.backend.entered.wait(2));self.assertTrue(self.control.submit('chat',body)['duplicate'])
  with self.assertRaises(Denied):self.control.submit('chat',dict(body,prompt='Changed retry'))
  self.control.backend.release.set();self.wait(lambda:self.foreground.lookup('owner',ident)['status']=='completed')
  self.assertTrue(self.control.submit('chat',body)['duplicate']);self.assertEqual(self.control.backend.calls,1)
 def test_idle_no_optional_workers_and_emergency_stop(self):
  self.assertEqual(self.control.integrations.loaded,{});self.assertEqual(self.control.backend.calls,0);self.assertEqual(self.foreground.snapshot('owner')['state'],'idle')
  a=self.control.memory.create('owner',approved=True);self.control.submit('chat',{'conversation_id':a,'prompt':'Synthetic stop','mode':'chat'});self.assertTrue(self.control.backend.entered.wait(2));start=time.monotonic();self.control.emergency_stop();self.assertLess(time.monotonic()-start,.2);self.wait(lambda:self.control.stopped)
  with self.assertRaises(Denied):self.control.submit('chat',{'conversation_id':a,'prompt':'No automatic restart','mode':'chat'})
 def test_numeric_confirmation_is_typed_metadata_but_not_authority(self):
  # Exact owner-control validation accepts numeric digest characters. Untrusted
  # free text still uses canonical redaction; private Guardian digest is rechecked.
  mid=uuid4().hex;digest='123456789012'+'a'*52
  pending={'source':'profile','review':{'action_sha256':digest}}
  data={'mission_id':mid,'source':'profile','approve':True,'action_sha256':digest,'confirmation':digest[:12]}
  validate_decision(data,pending)
  for changed in (dict(data,confirmation='forged'),dict(data,approve='APPROVE'),dict(data,action_sha256='b'*64)):
   with self.assertRaises(Denied):validate_decision(changed,pending)
  from igris.guardian.activities import canonical
  with self.assertRaises(Denied):canonical({'message':'Call 123456789012'})
