"""Trusted fixed Ops worker lifecycle; no model-controlled image/argv/mounts."""
import hashlib,hmac,json,os,selectors,subprocess,tempfile,threading,time
from pathlib import Path
from uuid import uuid4
from ..isolated import docker_command,docker_environment,Cancelled
from ..owned_jobs import OwnedLaunch,assert_no_pending_launches,UnconfirmedLaunch
from ..adapters.contracts import AdapterUnavailable,ContractError
from ..adapters.hermes_chat import DockerHermesAdapter
from ..memory import private_file
from ..guardian.readonly import unique
ROOT=Path(__file__).resolve().parents[3]
def encoded(body):return json.dumps(body,sort_keys=True,separators=(',',':')).encode()
class OpsProcess:
 def __init__(self):self.process=None;self.launch=None;self.buffer=bytearray();self.sequence=0;self.cleanup_verified=True;self.mutex=threading.Lock();self.pid=None
 def start(self,profile,mounts,packet,cancel):
  if self.process is not None:raise AdapterUnavailable('Ops process already owned.')
  base=docker_command();env=docker_environment();self.root=ROOT/'runtime/ops/session-control';self.root.mkdir(mode=0o700,exist_ok=True)
  self.lockpath=self.root/'session.lock'
  try:private_file(self.lockpath,create=True)
  except FileExistsError:private_file(self.lockpath)
  self.lock=self.lockpath.open('rb');import fcntl
  try:
   try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:raise AdapterUnavailable('Another Ops session is active.') from None
   assert_no_pending_launches(self.root)
   with DockerHermesAdapter()._slot():
    prior=subprocess.run(base+['ps','--all','--filter','label=com.igris.runtime=ops-session','--format','{{.ID}}'],env=env,capture_output=True,text=True,check=True,timeout=5)
    if prior.stdout.strip():raise AdapterUnavailable('An earlier Ops session requires cleanup review.')
    if cancel.is_set():raise Cancelled('Ops startup cancelled.')
    name='igris-ops-session-'+uuid4().hex[:12];marker=uuid4().hex
    args=base+['create','--rm','--pull=never','--interactive','--name',name,'--label','com.igris.runtime=ops-session','--label','com.igris.owner='+marker,'--network','none','--read-only','--user',f'{os.getuid()}:{os.getgid()}','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','256m','--cpus','1','--pids-limit','64','--tmpfs','/tmp:rw,noexec,nosuid,size=33554432,mode=1777','--workdir','/tmp']
    for source,target in mounts:
     source=Path(source).absolute()
     if source.resolve(strict=True)!=source or not source.is_relative_to(ROOT):raise ContractError('Fixed reviewed Ops mount required.')
     args+=['--mount',f'type=bind,src={source},dst={target},readonly']
    args+=[profile['image'],'/opt/igris/python/bin/python3.14','-I','-S','/opt/igris/session_worker.py'];self.launch=OwnedLaunch(self.root,base,env,name,marker);self.cleanup_verified=False;self.cid=self.launch.create(args);self.log=tempfile.TemporaryFile(dir=self.root);self.key=os.urandom(32)
    if cancel.is_set():raise Cancelled('Ops startup cancelled.')
    self.process=subprocess.Popen(base+['start','--attach','--interactive',self.cid],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,env=env)
    self.process.stdin.write(json.dumps(dict(packet,transport_key=self.key.hex())).encode()+b'\n');self.process.stdin.flush();ready=self.receive(cancel,30)
    if ready.get('kind')!='ready' or ready.get('origin')!='real_ops_pilot_session' or type(ready.get('pid')) is not int:raise ContractError('Actual Ops startup acknowledgement required.')
    self.pid=ready['pid'];self.rss_kib=ready['rss_kib'];return ready
  except BaseException:self.close();raise
 def receive(self,cancel,timeout):
  end=time.monotonic()+timeout
  with selectors.DefaultSelector() as events:
   events.register(self.process.stdout,selectors.EVENT_READ)
   while True:
    if cancel.is_set():raise Cancelled('Ops task cancelled.')
    if time.monotonic()>end:raise TimeoutError('Ops session deadline exceeded.')
    if b'\n' in self.buffer:
     line,_,rest=self.buffer.partition(b'\n');self.buffer=bytearray(rest);body=json.loads(line,object_pairs_hook=unique);signature=body.pop('mac')
     if type(signature) is not str or not hmac.compare_digest(signature,hmac.new(self.key,encoded(body),hashlib.sha256).hexdigest()):raise ContractError('Ops response authentication failed.')
     return body
    for _,_ in events.select(.1):
     data=os.read(self.process.stdout.fileno(),8192)
     if not data:raise AdapterUnavailable('Ops process stopped; manual restart required.')
     self.buffer.extend(data)
     if len(self.buffer)>131072:raise ContractError('Ops output limit.')
 def monitor(self,review,cancel,timeout):
  if not self.mutex.acquire(blocking=False):raise AdapterUnavailable('Another Ops operation is active.')
  try:
   if self.process is None or self.process.poll() is not None:raise AdapterUnavailable('Ops session not started.')
   self.sequence+=1;body={'sequence':self.sequence,'request_id':review.request_id,'mission_id':review.mission_id};self.process.stdin.write(json.dumps(dict(body,mac=hmac.new(self.key,encoded(body),hashlib.sha256).hexdigest())).encode()+b'\n');self.process.stdin.flush();result=self.receive(cancel,timeout)
   if result.get('kind')!='result' or result.get('sequence')!=self.sequence:raise ContractError('Ops response correlation failed.')
   self.rss_kib=result['rss_kib'];return result['data']
  finally:self.mutex.release()
 def health(self):return {'status':'running' if self.process is not None and self.process.poll() is None else 'stopped','container_id':getattr(self,'cid',None),'cleanup_verified':self.cleanup_verified}
 def close(self):
  try:
   if self.process is not None:
    if not self.process.stdin.closed:self.process.stdin.close()
    try:self.process.wait(timeout=3)
    except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
    self.process.stdout.close();self.process=None
   if self.launch is not None:
    try:self.launch.cleanup()
    except Exception:raise UnconfirmedLaunch('Ops worker cleanup unverified; owned launch record retained.') from None
    self.launch=None
   self.cleanup_verified=True;self.pid=None
  finally:
   if hasattr(self,'log'):self.log.close()
   if hasattr(self,'key'):self.key=b''
   if hasattr(self,'lock'):self.lock.close()
