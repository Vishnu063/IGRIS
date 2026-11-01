"""Audio validation uses real files; microphone callbacks are explicit fixtures."""
import io,json,sys,tempfile,unittest,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.voice.handy import read_clip,parse_transcript,HandyAdapter
from igris.voice.capture import ManualCapture
from igris.adapters.contracts import ContractError,AdapterUnavailable
from igris.guardian.policy import Denied


def wav(frames=16000,rate=16000,channels=1):
    output=io.BytesIO()
    with wave.open(output,'wb') as audio:
        audio.setnchannels(channels);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(b'\0\0'*frames*channels)
    return output.getvalue()


class HandyTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name)
        self.path=self.root/'sample.wav';self.path.write_bytes(wav());self.path.chmod(0o600)
    def tearDown(self):self.temporary.cleanup()
    def test_real_wav_snapshot_and_schema(self):
        clip=read_clip(self.root,'sample.wav');self.assertEqual(clip.seconds,1)
        data={'schema_version':1,'model':'small','text':'Hello','audio_secs':1,'load_ms':12,'transcribe_ms':[20]}
        transcript=parse_transcript(json.dumps(data),clip)
        self.assertEqual(transcript.text,'Hello');self.assertIsNone(transcript.language)
        for field,value in [('audio_secs',2),('transcribe_ms',[float('nan')]),('schema_version',True),('model','small.en')]:
            bad=dict(data);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ContractError):parse_transcript(json.dumps(bad),clip)
    def test_traversal_absolute_symlink_private_permissions(self):
        for name in ('../sample.wav','/sample.wav','sub/sample.wav','secret.wav'):
            with self.subTest(name=name),self.assertRaises(ContractError):read_clip(self.root,name)
        (self.root/'link.wav').symlink_to(self.path)
        with self.assertRaises(Denied):read_clip(self.root,'link.wav')
        self.path.chmod(0o644)
        with self.assertRaises(Denied):read_clip(self.root,'sample.wav')
    def test_format_size_truncation_and_disabled_default(self):
        for payload in (b'bad',wav(rate=8000),wav(frames=480001),wav()[:-10],b'x'*1048577):
            self.path.write_bytes(payload)
            with self.subTest(size=len(payload)),self.assertRaises(ContractError):read_clip(self.root,'sample.wav')
        with self.assertRaises(AdapterUnavailable):HandyAdapter().transcribe(self.root,'sample.wav')
    def test_permission_cancellation_bounded_callback_fixture(self):
        streams=[]
        class Stream:
            def __init__(self,**kw):self.callback=kw['callback'];self.closed=False;streams.append(self)
            def start(self):self.callback(b'\0\0'*600000,600000,None,None)
            def stop(self):pass
            def close(self):self.closed=True
        capture=ManualCapture(self.root,stream_factory=Stream)
        with self.assertRaises(PermissionError):capture.start()
        self.assertEqual(streams,[])
        capture.start(permission_granted=True);self.assertEqual(capture.state,'recording')
        path=capture.save();self.assertTrue(streams[0].closed)
        self.assertEqual(read_clip(self.root,path.name).seconds,30)
        capture.start(permission_granted=True);capture.cancel()
        with self.assertRaises(ValueError):capture.save()
    def test_unavailable_microphone_fails_closed(self):
        def unavailable(**kw):raise OSError('fixture: no device')
        capture=ManualCapture(self.root,stream_factory=unavailable)
        with self.assertRaises(AdapterUnavailable):capture.start(permission_granted=True)
        self.assertNotEqual(capture.state,'recording')
