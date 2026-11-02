"""Protocol unit checks use real pipes and synthetic signed peer frames, not inference."""
import hashlib,hmac,json,os,sys,threading,time,types,unittest,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.adapters.hermes_warm import WarmDockerHermesAdapter,encoded
from igris.adapters.hermes_chat import ChatRequest
from igris.adapters.contracts import AdapterUnavailable,ContractError
from uuid import uuid4
class WarmBoundaryTests(unittest.TestCase):
 def test_no_automatic_start(self):
  adapter=WarmDockerHermesAdapter()
  with self.assertRaises(AdapterUnavailable):adapter.reply(ChatRequest(uuid4().hex,'Hello.'))
  self.assertIsNone(adapter.process)
 def test_concurrent_request_fails_closed(self):
  adapter=WarmDockerHermesAdapter();adapter.turn_lock.acquire()
  try:
   with self.assertRaises(AdapterUnavailable):adapter.reply(ChatRequest(uuid4().hex,'Hello.'))
  finally:adapter.turn_lock.release()
  self.assertIsNone(adapter.process)
 def test_invalid_signed_peer_frames(self):
  for raw in (b'{"kind":"result"}\n',b'{"kind":"result","mac":"forged"}\n',b'{"kind":"result","kind":"ready","mac":"forged"}\n',b'x'*65537):
   adapter=WarmDockerHermesAdapter();read,write=os.pipe();stream=os.fdopen(read,'rb',buffering=0);adapter.process=types.SimpleNamespace(stdout=stream);adapter.started=time.monotonic();adapter.key=b'fixture transport key only'
   def writer():
    try:
     with os.fdopen(write,'wb') as handle:handle.write(raw)
    except BrokenPipeError:pass
   thread=threading.Thread(target=writer);thread.start()
   try:
    with self.assertRaises((ContractError,ValueError,PermissionError)):adapter._receive(2)
   finally:stream.close();thread.join(2)
 def test_explicit_mem0_conflict(self):
  result=subprocess.run([sys.executable,'-m','igris.chat','--remember','--warm-runtime','--enable-mem0'],cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')),capture_output=True,text=True)
  self.assertEqual(result.returncode,2);self.assertIn('reserves the model slot',result.stderr)
