"""Manually started warm model transport; never starts itself or restores authority."""
import hashlib,hmac,json,os,selectors,subprocess,tempfile,time,threading
from uuid import uuid4
from .hermes_chat import DockerHermesAdapter,CONTROLS,MAX_PACKET,ROOT,RuntimeBusy
from .contracts import AdapterUnavailable,ContractError
from ..guardian.readonly import unique
from ..owned_jobs import OwnedLaunch

def encoded(body):return json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
class WarmDockerHermesAdapter(DockerHermesAdapter):
 def __init__(self,**kwargs):
  super().__init__(**kwargs);self.process=None;self.launch=None;self.slot=None;self.buffer=bytearray();self.sequence=0;self.metrics=[];self.active=False;self.turn_lock=threading.Lock()
 def start(self):
  if self.active or self.process is not None or self.cancel.is_set():raise AdapterUnavailable('Explicit fresh warm session required.')
  self._preflight();self.slot=self._slot();self.slot.__enter__()
  from ..isolated import docker_command,docker_environment
  base=docker_command();env=docker_environment();name='igris-hermes-warm-'+uuid4().hex[:12];marker=uuid4().hex
  try:
   prior=subprocess.run(base+['ps','--all','--filter','label=com.igris.runtime=hermes-inference','--format','{{.ID}}'],env=env,capture_output=True,text=True,check=True,timeout=10)
   if prior.stdout.strip():raise AdapterUnavailable('An unfinished worker requires owner review.')
   args=base+['create','--rm','--pull=never','--interactive','--name',name,'--label','com.igris.runtime=hermes-inference','--label','com.igris.owner='+marker,'--network','none','--read-only','--user',f'{os.getuid()}:{os.getgid()}','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','3g','--cpus','2','--tmpfs','/tmp:rw,noexec,nosuid,size=268435456,mode=1777','--workdir','/tmp','--env','HOME=/tmp/igris-home','--env','HERMES_HOME=/tmp/igris-home/hermes','--env','HERMES_DISABLE_LAZY_INSTALLS=1','--env','PYTHONDONTWRITEBYTECODE=1','--env','NO_PROXY=127.0.0.1,localhost']
   mounts=['runtime/python3149','runtime/hermes-venv','runtime/llama-b11960','runtime/'+self.profile['model_file'],'vendor/hermes-agent','src/igris','integrations/hermes-inference/profile.json','integrations/agency-agents']+['scripts/'+name for name in ('hermes_inference_worker.py','hermes_chat_worker.py','hermes_tool_worker.py','hermes_specialist_worker.py','hermes_warm_worker.py')]
   for relative in mounts:
    path=self.root/relative
    if path.is_symlink() or not path.exists():raise ContractError('Unsafe fixed warm worker mount.')
    args+=['--mount',f'type=bind,src={path},dst={path},readonly']
   args+=[self.profile['container_image'],str(self.root/'runtime/hermes-venv/bin/python'),'-I',str(self.root/'scripts/hermes_warm_worker.py')]
   self.launch=OwnedLaunch(self.runtime,base,env,name,marker);self.cleanup_verified=False;cid=self.launch.create(args);self.log=tempfile.TemporaryFile(dir=self.runtime)
   self.key=os.urandom(32);self.started=time.monotonic();self.process=subprocess.Popen(base+['start','--attach','--interactive',cid],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,env=env)
   self.process.stdin.write(self.key.hex().encode()+b'\n');self.process.stdin.flush();ready=self._receive(90)
   if set(ready)!={'kind','controls','model_sha256','metrics'} or ready['kind']!='ready' or ready['controls']!=CONTROLS or ready['model_sha256']!=self.profile['model_sha256']:raise ContractError('Invalid warm runtime identity.')
   self.startup_metrics=ready['metrics'];self.active=True;return self
  except BaseException:self.close();raise
 def _receive(self,timeout):
  deadline=time.monotonic()+timeout
  with selectors.DefaultSelector() as poll:
   poll.register(self.process.stdout,selectors.EVENT_READ)
   while True:
    if self.cancel.is_set() or time.monotonic()-self.started>900:raise AdapterUnavailable('Warm session cancelled or expired; manual restart required.')
    if b'\n' in self.buffer:
     line,_,rest=self.buffer.partition(b'\n');self.buffer=bytearray(rest);body=json.loads(line,object_pairs_hook=unique)
     if type(body) is not dict or 'mac' not in body:raise ContractError('Unsigned warm frame.')
     signature=body.pop('mac')
     if type(signature) is not str or not hmac.compare_digest(signature,hmac.new(self.key,encoded(body),hashlib.sha256).hexdigest()):raise ContractError('Warm frame authentication failed.')
     return body
    if time.monotonic()>deadline:raise TimeoutError('Warm worker deadline.')
    for _,_ in poll.select(.1):
     data=os.read(self.process.stdout.fileno(),8192)
     if not data:raise AdapterUnavailable('Warm worker stopped; no automatic restart.')
     self.buffer.extend(data)
     if len(self.buffer)>65536:raise ContractError('Oversized warm response.')
 def _run(self,mode,payload=None):
  if not self.turn_lock.acquire(blocking=False):raise RuntimeBusy('Another warm request is active.')
  try:return self._run_turn(mode,payload)
  finally:self.turn_lock.release()
 def _run_turn(self,mode,payload=None):
  if not self.active or mode not in ('chat','tools','specialist') or self.sequence>=20:raise AdapterUnavailable('Start a new warm session explicitly; mode or lifetime unavailable.')
  try:
   self._preflight() # Preserve original asset/source checks on every request.
   if self.cancel.is_set():raise AdapterUnavailable('Warm inference stopped.')
   self.sequence+=1;body={'sequence':self.sequence,'mode':mode,'payload':payload};frame=dict(body,mac=hmac.new(self.key,encoded(body),hashlib.sha256).hexdigest());raw=json.dumps(frame,ensure_ascii=False).encode()+b'\n'
   if len(raw)>MAX_PACKET+1024:raise ContractError('Bounded warm request required.')
   self.process.stdin.write(raw);self.process.stdin.flush();message=self._receive(180)
   if set(message)!={'kind','sequence','result','metrics'} or message['kind']!='result' or message['sequence']!=self.sequence:raise ContractError('Warm response correlation failure.')
   result=message['result']
   if type(result) is not dict or result.get('origin')!='real_local_inference' or result.get('controls')!=CONTROLS or result.get('model_sha256')!=self.profile['model_sha256']:raise ContractError('Warm security controls mismatch.')
   self.metrics.append(message['metrics']);return result
  except BaseException:self.close();raise
 def close(self):
  self.active=False
  try:
   if self.process is not None:
    if self.process.poll() is None:self.process.kill()
    self.process.wait(timeout=5)
    self.process.stdin.close();self.process.stdout.close();self.process=None
   if self.launch is not None:self.launch.cleanup();self.launch=None;self.cleanup_verified=True
  finally:
   if hasattr(self,'log'):self.log.close()
   self.key=b'';self.buffer.clear()
   if self.slot is not None:self.slot.__exit__(None,None,None);self.slot=None
 def __enter__(self):return self.start()
 def __exit__(self,*_):self.close()
