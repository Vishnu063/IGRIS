"""Explicitly started offline model session; fresh actual Hermes agent per turn."""
import contextlib,hashlib,hmac,io,json,select,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(1,str(ROOT/'scripts'))
from igris.guardian.readonly import unique
from igris.adapters.hermes_chat import CONTROLS,MAX_PACKET
from hermes_inference_worker import reasoning_session
import hermes_chat_worker,hermes_tool_worker,hermes_specialist_worker

def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sign(key,body):return dict(body,mac=hmac.new(key,encode(body),hashlib.sha256).hexdigest())
def main():
 keyraw=sys.stdin.buffer.readline(130)
 if len(keyraw)!=65:raise ValueError('Private transport handshake required.')
 key=bytes.fromhex(keyraw.decode().strip());transport=sys.stdout;started=time.monotonic();sequence=0
 def send(body):transport.write(json.dumps(sign(key,body),ensure_ascii=False)+'\n');transport.flush()
 with contextlib.redirect_stdout(io.StringIO()):
  with reasoning_session(agent_factory=True) as (factory,profile,opener,credential):
   send({'kind':'ready','controls':CONTROLS,'model_sha256':profile['model_sha256'],'metrics':factory.metrics})
   while sequence<20 and time.monotonic()-started<900:
    if not select.select([sys.stdin.buffer],[],[],60)[0]:break
    raw=sys.stdin.buffer.readline(MAX_PACKET+1025)
    if not raw:break
    if len(raw)>MAX_PACKET+1024 or not raw.endswith(b'\n'):raise ValueError('Bounded signed frame required.')
    packet=json.loads(raw,object_pairs_hook=unique)
    if type(packet) is not dict or set(packet)!={'sequence','mode','payload','mac'}:raise ValueError('Invalid frame.')
    signature=packet.pop('mac')
    if type(signature) is not str or not hmac.compare_digest(signature,hmac.new(key,encode(packet),hashlib.sha256).hexdigest()) or type(packet['sequence']) is not int or packet['sequence']!=sequence+1:raise ValueError('Invalid transport authority or replay.')
    sequence+=1;mode=packet['mode'];payload=packet['payload']
    if mode not in ('chat','tools','specialist') or type(payload) is not dict:raise ValueError('Unregistered warm request mode.')
    @contextlib.contextmanager
    def fresh():yield factory(),profile,opener,credential
    output=io.StringIO();tick=time.monotonic()
    with contextlib.redirect_stdout(output):
     {'chat':hermes_chat_worker,'tools':hermes_tool_worker,'specialist':hermes_specialist_worker}[mode].main(session=fresh,input_stream=io.BytesIO(json.dumps(payload).encode()))
    result=None
    for line in reversed(output.getvalue().splitlines()):
     try:value=json.loads(line)
     except ValueError:continue
     if type(value) is dict and value.get('origin')=='real_local_inference':result=value;break
    if result is None or result.get('controls')!=CONTROLS:raise ValueError('Verified real response required.')
    status=Path('/proc/'+str(factory.engine_pid)+'/status').read_text();rss=int(next(line for line in status.splitlines() if line.startswith('VmHWM:')).split()[1])
    if mode=='tools':result['model_maxrss_kib']=rss
    send({'kind':'result','sequence':sequence,'result':result,'metrics':{'generation_and_agent_seconds':time.monotonic()-tick,'model_peak_rss_kib':rss,'fresh_agent':True}})
if __name__=='__main__':main()
