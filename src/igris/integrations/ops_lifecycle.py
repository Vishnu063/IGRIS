"""Explicit Ops lifecycle; existing Guardian and exact read-only target stay authoritative."""
import json,tempfile,threading
from pathlib import Path
from .catalog import Integration,IntegrationSpec
from .ops_runtime import RealOpsMonitor,ROOT
from ..guardian.activities import ExecutionProfile,ExecutionPermit
from ..guardian.policy import Denied
from ..guardian.docker_read_proxy import ExactDockerReads
from ..isolated import Cancelled
from ..adapters.contracts import AdapterUnavailable
class OpsIntegration(Integration):
 spec=IntegrationSpec('ops_pilot',('readonly_monitor','start','status','stop'),('read',),{'additional_processes':1,'memory_ceiling_bytes':268435456,'ram_bytes':None,'note':'Ceiling is enforcement, not a measured or promised working set.'})
 def __init__(self,instance,*,mode='manual',enabled=False,timeout=90):
  if mode not in ('manual','on_demand','monitoring'):raise Denied('Explicit Ops operating mode required.')
  if type(timeout) not in (int,float) or not 0<timeout<=90:raise Denied('Bounded trusted Ops timeout required.')
  self.timeout=timeout
  self.mode=mode;self.monitor=RealOpsMonitor(instance,enabled=enabled);self.process=None;self.proxy=None;self.folder=None;self.temporary=None;self.mutex=threading.RLock();self.start_review=None
 def normalize(self,raw):
  if type(raw) is not dict or set(raw)!={'action','container_id','mode'} or raw['action'] not in ('start','status','monitor','stop') or raw['mode']!=self.mode:raise Denied('Exact Ops action, target and configured mode required.')
  self.monitor.normalize({'container_id':raw['container_id']})
  if self.mode=='on_demand' and raw['action']=='start':raise Denied('On-demand components start only inside their approved monitor task.')
  return dict(raw)
 def arguments(self,action):return self.normalize({'action':action,'container_id':self.monitor.config['container_id'],'mode':self.mode})
 def scope(self,cancel):
  try:return dict(self.monitor.scope(cancel),lifecycle_mode=self.mode,execution_timeout_seconds=self.timeout,component_id=self.process.cid if self.process else None,session_limits={'probes':16,'seconds':3600},allowed_actions=['start','status','monitor','stop'],background_polling=False)
  except BaseException:
   self.shutdown();raise
 def start(self,arguments=None,cancel=None,permit=None):
  if arguments!=self.arguments('start') or cancel is None or type(permit) is not ExecutionPermit:raise Denied('Use the exact Guardian-approved lifecycle start action.')
  return self.execute(arguments,cancel,permit)
 def _start(self,review,cancel):
  if self.process is not None:
   if self.process.health()['status']!='running':raise AdapterUnavailable('Prior Ops worker stopped; explicitly stop and start a new session.')
   return {'reused':True,'status':'running'}
  from .session_process import OpsProcess
  self.temporary=tempfile.TemporaryDirectory(dir=ROOT/'runtime/ops',prefix='session-');self.folder=Path(self.temporary.name)
  try:
   self.proxy=ExactDockerReads(self.folder/'docker.sock',self.monitor.config['container_id'],self.monitor.config['daemon_id'],self.monitor.read_key).start();self.process=OpsProcess()
   packet={'container_id':self.monitor.config['container_id'],'read_key':self.monitor.read_key,'fixture_marker':self.monitor.config['fixture_marker'],'request_id':review.request_id,'mission_id':review.mission_id}
   mounts=[(ROOT/'runtime/python3149/python','/opt/igris/python'),(ROOT/'runtime/ops/docker','/opt/igris/bin/docker'),(ROOT/'runtime/ops/ops-pilot','/opt/igris/ops'),(ROOT/'runtime/ops/triage','/opt/igris/triage'),(ROOT/'integrations/ops/worker.py','/opt/igris/worker.py'),(ROOT/'integrations/ops/session_worker.py','/opt/igris/session_worker.py'),(self.proxy.path,'/input/docker.sock'),(self.monitor.socket_path,'/input/app.sock')]
   ready=self.process.start(self.monitor.profile,mounts,packet,cancel);self.start_review=review.digest;return {'status':'running','reused':False,'component_rss_kib':ready['rss_kib']}
  except BaseException:self.shutdown();raise
 def health(self):
  return dict(self.process.health() if self.process else {'status':'stopped','cleanup_verified':True},mode=self.mode,target=self.monitor.config['container_id'],background_polling=False)
 def shutdown(self):
  # Never stop/remove the monitored container. Only this connector/proxy are owned here.
  with self.mutex:
   if self.process is not None:self.process.close();self.process=None
   if self.proxy is not None:self.proxy.close();self.proxy=None
   if self.temporary is not None:self.temporary.cleanup();self.temporary=None;self.folder=None
   self.start_review=None;return {'cleanup_verified':True,'component_stopped':True,'monitored_application_stopped':False}
 def execute(self,arguments,cancel,permit):
  if type(permit) is not ExecutionPermit:raise Denied('Guardian lifecycle lease required.')
  arguments=self.normalize(arguments);review=permit.consume('ops.lifecycle',arguments)
  if not self.mutex.acquire(blocking=False):raise Denied('An Ops lifecycle task is already active.')
  try:
   if cancel.is_set():raise Cancelled('Ops lifecycle task cancelled.')
   action=arguments['action']
   if action=='stop':return dict(self.shutdown(),origin='real_ops_lifecycle',verified=True,status='completed')
   if action=='status':return {'origin':'real_ops_lifecycle','verified':True,'status':'completed','health':self.health()}
   try:
    if action=='start':return dict(self._start(review,cancel),origin='real_ops_lifecycle',verified=True,mode=self.mode,monitoring_collection='foreground_probes_only',resource_disposition='retained_authorized')
    if self.process is None and self.mode!='on_demand':raise Denied('Manual and monitoring modes require a separately approved explicit start.')
    if self.process is None:self._start(review,cancel)
    from ..adapters.hermes_chat import DockerHermesAdapter
    with DockerHermesAdapter()._slot():data=self.process.monitor(review,cancel,self.timeout)
    observation=self.monitor.parse(data,review,list(self.proxy.events[-32:]))
    if cancel.is_set():raise Cancelled('Monitoring cancelled; result discarded.')
    return {'origin':'real_ops_lifecycle','status':'completed','verified':True,'mode':self.mode,'observation':observation,'resource_disposition':'stopped_after_task' if self.mode=='on_demand' else 'retained_authorized'}
   except BaseException:
    self.shutdown();raise
   finally:
    if self.mode=='on_demand':self.shutdown()
  finally:self.mutex.release()
 def registration(self):return ExecutionProfile('ops.lifecycle',self.normalize,self.scope,self.execute)
