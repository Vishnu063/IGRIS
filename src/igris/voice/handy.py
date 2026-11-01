"""Optional offline Handy file transcription. Default disabled; no keyboard API."""
from dataclasses import dataclass,field
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tempfile
import wave

from ..adapters.contracts import AdapterUnavailable,ContractError
from ..adapters.hermes_chat import response_text
from ..isolated import IsolatedWorker
from ..memory import private_file

ROOT=Path(__file__).resolve().parents[3]
MAX_AUDIO=30


@dataclass(frozen=True)
class AudioClip:
    payload: bytes=field(repr=False)
    seconds: float
    sha256: str


def read_clip(workspace,name):
    if type(name) is not str or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,79}\.wav',name) or '..' in name:
        raise ContractError('One approved WAV filename required; no path traversal.')
    if any(word in name.lower() for word in ('secret','password','credential','token','customer')):
        raise ContractError('Sensitive audio filename denied.')
    path=private_file(Path(workspace).absolute()/name)
    with path.open('rb') as source:payload=source.read(1048577)
    if len(payload)>1048576:raise ContractError('Audio file exceeds limit.')
    try:
        with wave.open(io.BytesIO(payload),'rb') as audio:
            frames=audio.getnframes()
            if (audio.getnchannels()!=1 or audio.getsampwidth()!=2 or audio.getframerate()!=16000
                    or audio.getcomptype()!='NONE' or not 0<frames<=16000*MAX_AUDIO):
                raise ContractError('Expected 16 kHz mono 16-bit PCM WAV, at most 30 seconds.')
            data=audio.readframes(frames)
            if len(data)!=frames*2:raise ContractError('Truncated audio denied.')
    except (wave.Error,EOFError):raise ContractError('Invalid bounded PCM WAV.') from None
    return AudioClip(payload,frames/16000,hashlib.sha256(payload).hexdigest())


@dataclass(frozen=True)
class Transcript:
    text: str
    seconds: float
    load_ms: float
    inference_ms: tuple
    origin: str='real_handy_transcription'
    # The upstream JSON has no language label; never fabricate one.
    language: str|None=None


def parse_transcript(raw,clip):
    from ..guardian.readonly import unique
    data=json.loads(raw,object_pairs_hook=unique)
    if type(data) is not dict or set(data)!={'schema_version','model','text','audio_secs','load_ms','transcribe_ms'}:
        raise ContractError('Unexpected Handy worker response schema.')
    if type(data['schema_version']) is not int or data['schema_version']!=1 or data['model']!='small':
        raise ContractError('Unexpected Handy model or protocol.')
    for value in (data['audio_secs'],data['load_ms']):
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ContractError('Invalid transcription timing.')
    if abs(data['audio_secs']-clip.seconds)>.01:raise ContractError('Audio correlation mismatch.')
    times=data['transcribe_ms']
    if type(times) is not list or len(times)!=1 or type(times[0]) not in (int,float) or not math.isfinite(times[0]) or not 0<=times[0]<=180000:
        raise ContractError('Invalid actual transcription result.')
    return Transcript(response_text(data['text']),data['audio_secs'],data['load_ms'],tuple(times))


class HandyAdapter:
    def __init__(self,*,enabled=False,cancel=None):
        self.enabled=enabled is True
        self.profile=json.loads((ROOT/'integrations/handy/profile.json').read_text())
        self.worker=IsolatedWorker(cancel=cancel)

    def transcribe(self,workspace,name):
        if not self.enabled:raise AdapterUnavailable('Handy disabled; text chat remains available.')
        clip=read_clip(workspace,name)
        profile=self.profile
        model=ROOT/'runtime/handy'/profile['model_file']
        if not model.is_file() or model.is_symlink():raise AdapterUnavailable('Prepare verified Handy assets explicitly.')
        with model.open('rb') as source:
            if hashlib.file_digest(source,'sha256').hexdigest()!=profile['model_sha256']:raise ContractError('ASR model integrity failure.')
        requests=ROOT/'runtime/handy/requests';requests.mkdir(mode=0o700,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=requests,prefix='clip-') as folder:
            path=private_file(Path(folder)/'audio.wav',create=True)
            path.write_bytes(clip.payload)
            output=self.worker.run(profile['image'],['/usr/bin/python3','-I','-S','/opt/igris/worker.py'],
                [(path,'/input/audio.wav'),(model,'/models/ggml-small.bin'),(ROOT/'integrations/handy/worker.py','/opt/igris/worker.py')],component='handy')
        return parse_transcript(output,clip)
