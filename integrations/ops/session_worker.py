"""Private bounded resident Ops component; no background polling or model access."""
import hashlib,hmac,json,os,resource,select,sys,time
sys.path.insert(0,'/opt/igris')
from worker import Session

def encoded(body):return json.dumps(body,sort_keys=True,separators=(',',':')).encode()
def main():
 raw=sys.stdin.buffer.readline(8193)
 if len(raw)>8192:raise ValueError('Oversized session setup.')
 request=json.loads(raw);key=bytes.fromhex(request.pop('transport_key'));sequence=0
 if len(key)!=32:raise ValueError('Private transport required.')
 session=Session(request);started=time.monotonic()
 def send(body):print(json.dumps(dict(body,mac=hmac.new(key,encoded(body),hashlib.sha256).hexdigest())),flush=True)
 try:
  send({'kind':'ready','origin':'real_ops_pilot_session','pid':os.getpid(),'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
  while sequence<16 and time.monotonic()-started<3600:
   if not select.select([sys.stdin.buffer],[],[],min(3600,3600-(time.monotonic()-started)))[0]:break
   raw=sys.stdin.buffer.readline(8193)
   if not raw:break
   if len(raw)>8192 or not raw.endswith(b'\n'):raise ValueError('Bounded session frame required.')
   body=json.loads(raw);signature=body.pop('mac')
   if set(body)!={'sequence','request_id','mission_id'} or type(body['sequence']) is not int or body['sequence']!=sequence+1 or type(signature) is not str or not hmac.compare_digest(signature,hmac.new(key,encoded(body),hashlib.sha256).hexdigest()):raise ValueError('Foreign or replayed session frame.')
   sequence+=1;result=session.monitor(body['request_id'],body['mission_id']);send({'kind':'result','sequence':sequence,'data':result,'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
 finally:session.close()
if __name__=='__main__':main()
