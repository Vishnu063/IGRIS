"""Optional bounded speech output. No playback or microphone starts on import."""
import base64,hashlib,io,json,math,threading,wave
from pathlib import Path
from .languages import route_language
from ..adapters.contracts import ContractError,AdapterUnavailable
from ..adapters.hermes_chat import response_text
from ..isolated import IsolatedWorker,Cancelled
from ..memory import private_file
ROOT=Path(__file__).resolve().parents[3]


def language_review(text,*,preferred=None):
    route=route_language(text,preferred=preferred)
    # Script cannot reliably separate Hindi/Marathi or Romanized Indic speech.
    return {'language':preferred,'candidates':route.languages,'confidence':'owner_selected' if preferred else 'low',
            'needs_confirmation':preferred is None,'method':'manual' if preferred else 'text_script_heuristic',
            'speech_language_detected':False}


def speech_text(text):
    text=response_text(text)
    if not 0<len(text)<=240 or any(ord(c)<32 or c in '<>[]' for c in text):raise ContractError('Bounded plain speech text required; use text fallback for longer responses.')
    return text


class SpeechOutput:
    def __init__(self,*,enabled=False):
        self.enabled=enabled is True;self.muted=False;self.cancel=threading.Event()
        self.worker=IsolatedWorker(cancel=self.cancel)

    def stop(self):self.cancel.set()
    def mute(self,value=True):
        if type(value) is not bool:raise ContractError('Explicit mute control required.')
        self.muted=value
        if value:self.stop()

    def synthesize(self,text,language,destination):
        if not self.enabled or self.muted:raise AdapterUnavailable('Voice output disabled or muted.')
        if self.cancel.is_set():raise Cancelled('Speech stopped; restart explicitly.')
        if language not in ('en','hi','mr'):raise ContractError('Confirm supported language before synthesis.')
        payload=json.dumps({'language':language,'text':speech_text(text)},ensure_ascii=False).encode()
        profile=json.loads((ROOT/'integrations/speech/profile.json').read_text())
        raw=self.worker.run(profile['image'],['/opt/igris/python/bin/python3.14','-I','-S','/opt/igris/worker.py'],
            [(ROOT/'runtime/python3149/python','/opt/igris/python'),(ROOT/'integrations/speech/worker.py','/opt/igris/worker.py')],
            component='speech',memory='1g',timeout=30,payload=payload,output_limit=2097152)
        result=json.loads(raw)
        if type(result) is not dict or set(result)!={'language','wav','sha256','seconds','synthesis_seconds','origin'} or result['language']!=language or result['origin']!='real_espeak_ng':raise ContractError('Invalid speech response.')
        if any(type(result[k]) not in (int,float) or not math.isfinite(result[k]) or result[k]<=0 for k in ('seconds','synthesis_seconds')):raise ContractError('Invalid speech measurements.')
        audio=base64.b64decode(result.pop('wav'),validate=True)
        if len(audio)>1500000 or hashlib.sha256(audio).hexdigest()!=result['sha256']:raise ContractError('Speech integrity mismatch.')
        with wave.open(io.BytesIO(audio),'rb') as sound:
            seconds=sound.getnframes()/sound.getframerate()
            if sound.getnchannels()!=1 or sound.getsampwidth()!=2 or not 0<seconds<=30 or seconds!=result['seconds']:raise ContractError('Invalid speech WAV.')
        path=private_file(Path(destination).absolute(),create=True)
        try:path.write_bytes(audio)
        except BaseException:path.unlink();raise
        return result
