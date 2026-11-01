"""Fixed optional eSpeak synthesis. Text is stdin data, never shell or SSML."""
import base64,hashlib,json,os,resource,subprocess,sys,time,wave
from pathlib import Path
os.umask(0o077)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**2,2*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
data=json.loads(sys.stdin.buffer.read(8193))
if type(data) is not dict or set(data)!={'language','text'} or data['language'] not in ('en','hi','mr') or type(data['text']) is not str or not 0<len(data['text'])<=240:raise ValueError('Invalid speech request.')
# No SSML flag; controls and markup rejected by parent as well.
if any(ord(c)<32 for c in data['text']) or any(c in data['text'] for c in '<>[]'):raise ValueError('Plain text required.')
Path('/tmp/pulse-client.conf').write_text('autospawn=no\nenable-shm=no\n')
Path('/tmp/request.txt').write_text(data['text'],encoding='utf-8')
start=time.monotonic()
subprocess.run(['/usr/bin/espeak-ng','-v',{'en':'en-us','hi':'hi','mr':'mr'}[data['language']],'-s','150','-p','35','-w','/tmp/speech.wav','-b','1','-f','/tmp/request.txt'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin','HOME':'/tmp','PULSE_SERVER':'unix:/tmp/disabled-pulse','PULSE_CLIENTCONFIG':'/tmp/pulse-client.conf'},check=True,timeout=10)
path=Path('/tmp/speech.wav');raw=path.read_bytes()
with wave.open(str(path),'rb') as sound:
    seconds=sound.getnframes()/sound.getframerate()
    if sound.getnchannels()!=1 or sound.getsampwidth()!=2 or not 0<seconds<=30 or len(raw)>1500000:raise ValueError('Synthesis exceeds limit.')
print(json.dumps({'language':data['language'],'wav':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest(),'seconds':seconds,'synthesis_seconds':time.monotonic()-start,'origin':'real_espeak_ng'}))
