"""Actual SQLite and private-file tests; dialogue is clearly synthetic fixture data."""
import hashlib,json,sys,tempfile,unittest,subprocess
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.chat_backup import create_snapshot,restore_snapshot
from igris.conversations import ConversationMemory,ConversationBusy
from igris.scoped_memory import ScopedFacts
from igris.guardian.policy import Denied
class ChatBackupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runtime');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.memory=ConversationMemory(self.root/'chat.sqlite3','owner',initialize=True);self.conversation=self.memory.create('owner',approved=True);self.facts=ScopedFacts(self.root/'facts.sqlite3','owner',self.memory,initialize=True)
  mid=uuid4().hex;request,_=self.memory.reserve('owner',self.conversation,mid,'Synthetic context fixture.');self.memory.complete('owner',self.conversation,request,mid,'Synthetic answer.','a'*64,1,origin='simulated');self.fact=self.facts.save('owner',self.conversation,'project','Approved fixture.',approved=True)
 def backup(self):return create_snapshot(self.root/'snapshot.json',memory=self.memory,facts=self.facts,actor='owner',approved=True)
 def test_restore_data_without_authority(self):
  proof=self.backup();result=restore_snapshot(self.root/'snapshot.json',self.root/'restored',expected_sha256=proof['sha256'],actor='owner',approved=True);self.assertFalse(result['execution_resumed']);self.assertEqual(result['approvals_restored'],0)
  memory=ConversationMemory(self.root/'restored/chat.sqlite3','owner');self.assertEqual(memory.history('owner',self.conversation),self.memory.history('owner',self.conversation));facts=ScopedFacts(self.root/'restored/facts.sqlite3','owner',memory);self.assertEqual(facts.get('owner',self.conversation,self.fact['id']),self.fact);self.assertNotEqual(facts.token('owner',self.conversation),self.facts.token('owner',self.conversation))
 def test_tamper_owner_and_existing_target_denied(self):
  proof=self.backup()
  for actor,digest in [('model',proof['sha256']),('owner','b'*64)]:
   with self.assertRaises(Denied):restore_snapshot(self.root/'snapshot.json',self.root/'new',expected_sha256=digest,actor=actor,approved=True)
  with self.assertRaises(FileExistsError):restore_snapshot(self.root/'snapshot.json',self.root,expected_sha256=proof['sha256'],actor='owner',approved=True)
  data=json.loads((self.root/'snapshot.json').read_text());data['approvals']=['forged'];raw=json.dumps(data).encode();(self.root/'snapshot.json').write_bytes(raw)
  with self.assertRaises(Denied):restore_snapshot(self.root/'snapshot.json',self.root/'new',expected_sha256=hashlib.sha256(raw).hexdigest(),actor='owner',approved=True)
 def test_pending_reservation_prevents_backup(self):
  self.memory.reserve('owner',self.conversation,uuid4().hex,'Pending fixture.')
  with self.assertRaises(ConversationBusy):self.backup()

 def test_cli_without_optional_mem0_facts(self):
  source=self.root/'text-only';source.mkdir(mode=0o700);memory=ConversationMemory(source/'chat.sqlite3','owner',initialize=True);memory.create('owner',approved=True)
  command=[sys.executable,str(ROOT/'scripts/backup_chat.py')];snapshot=self.root/'text-snapshot.json'
  created=subprocess.run(command+['create','--state-dir',str(source),'--file',str(snapshot),'--approve-data-operation'],capture_output=True,text=True,check=True);sha=json.loads(created.stdout)['sha256']
  restored=subprocess.run(command+['restore','--state-dir',str(self.root/'text-restored'),'--file',str(snapshot),'--expected-sha256',sha,'--approve-data-operation'],capture_output=True,text=True,check=True);result=json.loads(restored.stdout)
  self.assertEqual(result['facts'],0);self.assertEqual(result['approvals_restored'],0);self.assertFalse(result['execution_resumed'])
