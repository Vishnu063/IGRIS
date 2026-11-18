"""Real controller/HTTP/SQLite; device and inference fixtures explicitly synthetic."""
import json,secrets,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.foreground import Foreground
from igris.mission_control import MissionControl
from igris.dashboard import make_server
from igris.guardian.policy import Denied
from igris.adapters.hermes_chat import ChatReply
from igris.voice.native import LocalClient,NativeHelper
from igris.adapters.contracts import AdapterUnavailable,ContractError
class Fixture:
    def __init__(self,*,cancel):self.calls=0
    def reply(self,request):self.calls+=1;return ChatReply(request.request_id,'Synthetic unit voice response.','a'*64,1)
class NativeVoiceControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.control=MissionControl(self.root/'state',remember=True,foreground=Foreground(self.root/'foreground'),backend_factory=Fixture);self.addCleanup(self.control.close)
        self.secret=secrets.token_urlsafe(32);self.path=self.root/'accounts.json';self.path.write_text(json.dumps({'owner':[self.secret,'owner']}));self.path.chmod(0o600)
        self.server=make_server({'owner':(self.secret,'owner')},control=self.control);self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01},daemon=True);self.thread.start();self.addCleanup(self.close_server)
        self.client=LocalClient(self.path,self.server.server_port);self.client.api('/api/state');self.session=self.client.api('/api/session',{})['conversation_id']
    def close_server(self):self.server.shutdown();self.server.server_close();self.thread.join(2)
    def finish(self,reservation,**kw):return self.client.api('/api/voice/finish',dict(task_id=reservation['task_id'],nonce=reservation['nonce'],prompt='',conversation_id=self.session,mode='chat',cancel=True,**kw))
    def test_voice_reservation_blocks_competing_worker_and_exact_nonce(self):
        review=self.client.api('/api/voice/reserve',{})
        with self.assertRaises(Denied):self.control.submit('chat',{'conversation_id':self.session,'prompt':'Competing task','mode':'chat'})
        with self.assertRaises(AdapterUnavailable):self.client.api('/api/voice/finish',dict(task_id=review['task_id'],nonce='forged',prompt='Untrusted transcript',conversation_id=self.session,mode='chat',cancel=False))
        self.assertEqual(self.control.backend.calls,0);self.finish(review)
        with self.assertRaises(AdapterUnavailable):self.finish(review)
        self.assertIsNone(self.control.foreground.active)
    def test_finalized_input_dispatches_once_and_voice_cannot_approve(self):
        review=self.client.api('/api/voice/reserve',{})
        result=self.client.api('/api/voice/finish',{'task_id':review['task_id'],'nonce':review['nonce'],'prompt':'Synthetic finalized text','conversation_id':self.session,'mode':'chat','cancel':False})
        deadline=time.monotonic()+3
        while not self.control.backend.calls and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(self.control.backend.calls,1)
        with self.assertRaises(AdapterUnavailable):self.client.api('/api/voice/finish',{'task_id':review['task_id'],'nonce':review['nonce'],'prompt':'Replay','conversation_id':self.session,'mode':'chat','cancel':False})
        with self.assertRaises(ContractError):self.client.api('/api/decision',{})
    def test_expiry_and_emergency_stop_release_native_reservation(self):
        review=self.client.api('/api/voice/reserve',{})
        self.control.native_voice['deadline']=time.monotonic()-1;self.control.wake.set();end=time.monotonic()+2
        while self.control.foreground.active and time.monotonic()<end:time.sleep(.01)
        self.assertIsNone(self.control.foreground.active)
        self.assertEqual(self.control.foreground.lookup('owner',review['task_id'])['status'],'cancelled')
        self.client.api('/api/voice/reserve',{});self.control.emergency_stop();self.control.worker.join(3)
        self.assertIsNone(self.control.foreground.active)
    def test_audio_output_reservation_completes_without_inference(self):
        review=self.client.api('/api/voice/reserve',{})
        result=self.client.api('/api/voice/finish',{'task_id':review['task_id'],'nonce':review['nonce'],'prompt':'','conversation_id':self.session,'mode':'output','cancel':False})
        self.assertEqual(result['task']['status'],'completed');self.assertEqual(self.control.backend.calls,0)
    def test_linux_cannot_masquerade_as_native_mac_helper(self):
        with patch('igris.voice.native.platform.system',return_value='Linux'):
            with self.assertRaises(AdapterUnavailable):NativeHelper(threading.Event())
    def test_denied_or_cancelled_capture_deletes_owned_audio_and_releases_lease(self):
        from igris.voice import native
        for failure in (AdapterUnavailable('Synthetic OS permission denial.'),KeyboardInterrupt()):
            class DeviceFixture:
                def __init__(self,cancel):pass
                def run(self,operation,**arguments):
                    self_path=Path(arguments['path']);self_path.write_bytes(b'Synthetic partial audio, no microphone accessed.')
                    raise failure
            argv=['igris.voice.native','--accounts-file',str(self.path),'--port',str(self.server.server_port),'--record','1','--allow-microphone','--language','mr']
            with patch.object(native,'ROOT',self.root),patch.object(native,'NativeHelper',DeviceFixture),patch.object(sys,'argv',argv),patch('builtins.input',return_value=''):
                with self.assertRaises(type(failure)):native.main()
            self.assertEqual(list((self.root/'runtime/native-voice').iterdir()),[])
            self.assertIsNone(self.control.foreground.active)
            self.assertEqual(self.control.backend.calls,0)
