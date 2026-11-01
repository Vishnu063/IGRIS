"""Real formant WAV generation and real Hermes text-language replies. No mic/playback."""
import hashlib,json,sys,time,tempfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.voice.speech import SpeechOutput
from igris.isolated import IsolatedWorker
from igris.adapters.hermes_chat import DockerHermesAdapter,ChatRequest
from uuid import uuid4

def main():
    results=[];output=ROOT/'runtime/speech/audio';output.mkdir(mode=0o700,exist_ok=True)
    examples={'en':('Igris is ready.','Reply in one short English sentence: greet the user.'),
              'hi':('नमस्ते। मैं आपकी सहायता के लिए तैयार हूँ।','हिंदी में एक छोटे वाक्य में नमस्ते कहें।'),
              'mr':('नमस्कार. मी तुमच्या मदतीसाठी तयार आहे.','मराठीमध्ये एका छोट्या वाक्यात नमस्कार म्हणा.')}
    for language,(text,prompt) in examples.items():
        target=output/(language+'-'+uuid4().hex+'.wav')
        started=time.monotonic();metadata=SpeechOutput(enabled=True).synthesize(text,language,target);wall=time.monotonic()-started
        started=time.monotonic();reply=DockerHermesAdapter().reply(ChatRequest(uuid4().hex,prompt));chat=time.monotonic()-started
        if language in ('hi','mr') and not any('\u0900'<=c<='\u097f' for c in reply.text):raise ValueError('Requested script not observed.')
        results.append({'language':language,'speech':metadata,'speech_wall_seconds':wall,'wav_bytes':target.stat().st_size,
            'text_prompt':prompt,'real_hermes_reply':reply.text,'hermes_wall_seconds':chat,
            'recognition':'NOT_TESTED: language human audio unavailable in reviewed fixtures and cloud Handy disk requirement exceeds current free disk',
            'quality':'NOT_VERIFIED: no native-speaker listening review or physical playback; script check is not fluency proof'})
        (ROOT/'runtime/speech/live.json').write_text(json.dumps({'status':'RUNNING','observations':results},indent=2,ensure_ascii=False)+'\n')
        print(language+': actual WAV and Hermes reply generated',flush=True)
    files=['src/igris/isolated.py','src/igris/voice/speech.py','integrations/speech/worker.py','integrations/speech/profile.json','scripts/test_speech_live.py']
    evidence={'status':'PASS_AVAILABLE_MECHANICS','verified_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),
        'task_acceptance':'BLOCKED','observations':results,'mac_and_mic':'BLOCKED: authorized hardware unavailable',
        'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}}
    (ROOT/'runtime/speech/live.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n')

if __name__=='__main__':main()
