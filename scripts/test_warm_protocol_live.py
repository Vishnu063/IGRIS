"""Actual warm worker rejects a forged signed frame before any model inference."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.adapters.hermes_warm import WarmDockerHermesAdapter
from igris.adapters.contracts import AdapterUnavailable
from igris.adapters.hermes_chat import ChatRequest
from igris.adapters.hermes_warm import encoded
from uuid import uuid4
import hmac
started=time.monotonic();cases=[]
for attack in ('forged','replay'):
 adapter=WarmDockerHermesAdapter()
 try:
  adapter.start()
  if attack=='replay':
   request=ChatRequest(uuid4().hex,'What is 5 plus 6? Reply with only the integer.');reply=adapter.reply(request);assert reply.text.strip()=='11'
   body={'sequence':1,'mode':'chat','payload':request.payload()};frame=dict(body,mac=hmac.new(adapter.key,encoded(body),hashlib.sha256).hexdigest())
  else:frame={'sequence':1,'mode':'chat','payload':ChatRequest(uuid4().hex,'What is 7 plus 5? Reply with only the integer.').payload(),'mac':'forged'}
  adapter.process.stdin.write(json.dumps(frame).encode()+b'\n');adapter.process.stdin.flush()
  try:adapter._receive(10)
  except AdapterUnavailable:cases.append(attack+'_denied_before_inference')
  else:raise AssertionError('Invalid transport request accepted.')
 finally:adapter.close()
 assert adapter.cleanup_verified and not adapter.active
proof={'status':'PASS','actual_cases':cases,'current_transport_real_response':'11','cleanup_verified':True,'inference_calls_for_invalid_requests':0,'seconds':round(time.monotonic()-started,3),'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['scripts/hermes_warm_worker.py','src/igris/adapters/hermes_warm.py','scripts/test_warm_protocol_live.py']}}
(ROOT/'docs/validation/warm-protocol-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
