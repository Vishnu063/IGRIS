"""Explicit real Handy/Hermes mechanics test with synthetic speech, never a mic test."""
from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json,os,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.voice.handy import HandyAdapter,read_clip
from igris.chat import ChatService
from igris.conversations import ConversationMemory
from igris.adapters.hermes_chat import DockerHermesAdapter
from igris.isolated import IsolatedWorker,Cancelled
from igris.guardian.secrets import findings


def main():
    destination=ROOT/'runtime/handy/live.json'
    destination.write_text(json.dumps({'status':'RUNNING'}))
    audio=ROOT/'runtime/handy/audio';clip=read_clip(audio,'sample.wav')
    started=time.monotonic();transcript=HandyAdapter(enabled=True).transcribe(audio,'sample.wav');asr_wall=time.monotonic()-started
    destination.write_text(json.dumps({'status':'ASR_COMPLETE','transcript':asdict(transcript),'asr_wall_seconds':asr_wall},ensure_ascii=False))
    import re
    if not re.search(r'(?:seven|7)\s*(?:plus|\+)\s*(?:five|5)',transcript.text.lower()):raise ValueError('Actual ASR did not preserve arithmetic intent.')
    with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='handy-chat-') as folder:
        memory=ConversationMemory(Path(folder)/'chat.sqlite3','owner',initialize=True)
        conversation=memory.create('owner',approved=True)
        service=ChatService('owner',memory,DockerHermesAdapter())
        started=time.monotonic()
        try:result=service.ask('owner',conversation,transcript.text)
        finally:service.close()
        chat_wall=time.monotonic()-started
        if not result['saved'] or '12' not in result['reply']:raise ValueError('Actual Hermes answer not verified.')
        if len(memory.history('owner',conversation))!=2:raise ValueError('Conversation not persisted.')
    files=['src/igris/voice/handy.py','src/igris/isolated.py','integrations/handy/worker.py','integrations/handy/profile.json','scripts/test_handy_live.py']
    data={'status':'PASS','verified_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),
          'fixture':'ffmpeg flite synthetic English speech; no human recording or hardware acceptance',
          'audio_sha256':clip.sha256,'transcript':asdict(transcript),'asr_wall_seconds':asr_wall,
          'chat_wall_seconds':chat_wall,'chat_reply':result['reply'],'persisted':True,
          'inference_and_transcription':'real Handy v0.9.8 Whisper Small and real Hermes Qwen3.5-2B; no mocks',
          'physical_microphone':'BLOCKED: no authorized microphone/Mac','model_tools':'disabled; existing Guardian tool wiring unchanged',
          'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}}
    if findings(json.dumps(data)):raise ValueError('Evidence requires secret review.')
    destination.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n');print(json.dumps(data,ensure_ascii=False))


if __name__=='__main__':main()
