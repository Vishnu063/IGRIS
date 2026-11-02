"""Small trusted lazy adapter contract. Model/request data never supplies factories."""
from abc import ABC,abstractmethod
from dataclasses import asdict,dataclass
from datetime import datetime,timezone
from types import MappingProxyType
from ..guardian.activities import ExecutionProfile,ExecutionPermit
from ..guardian.policy import Denied

@dataclass(frozen=True)
class IntegrationSpec:
 name:str
 capabilities:tuple
 required_permissions:tuple
 estimated_resources:dict
 available:bool=True

class Integration(ABC):
 spec:IntegrationSpec
 @abstractmethod
 def start(self):pass
 @abstractmethod
 def shutdown(self):pass
 @abstractmethod
 def health(self):pass
 @abstractmethod
 def execute(self,arguments,cancel,permit):pass

class Catalog:
 def __init__(self,entries):
  # Explicit startup registry; never discover/import plugins named in AI output.
  self.entries=MappingProxyType(dict(entries));self.loaded={}
 def describe(self):return [asdict(spec) for spec,_ in self.entries.values()]
 def resolve(self,name):
  if name not in self.entries or not self.entries[name][0].available:raise Denied('Integration unavailable; account/platform automation is not implemented.')
  if name not in self.loaded:
   spec,factory=self.entries[name];instance=factory()
   if not isinstance(instance,Integration) or instance.spec.name!=spec.name:raise Denied('Trusted adapter contract mismatch.')
   self.loaded[name]=instance
  return self.loaded[name]
 def shutdown(self):
  errors=[]
  for adapter in self.loaded.values():
   try:adapter.shutdown()
   except Exception as error:errors.append(type(error).__name__)
  if errors:raise RuntimeError('Integration cleanup not verified.')

class Clock(Integration):
 spec=IntegrationSpec('clock',('current_time',),('read',),{'additional_processes':0,'ram_bytes':None,'note':'RAM unestimated; measure before making a target claim.'})
 def __init__(self):self.ready=False
 def start(self):self.ready=True
 def shutdown(self):self.ready=False;return {'cleanup_verified':True}
 def health(self):return {'status':'ready' if self.ready else 'stopped'}
 def normalize(self,args):
  if type(args) is not dict or args:raise Denied('Clock accepts no arguments.')
  return {}
 def execute(self,arguments,cancel,permit):
  if type(permit) is not ExecutionPermit:raise Denied('Guardian lease required.')
  permit.consume('get_current_time',self.normalize(arguments))
  if cancel.is_set():raise Denied('Clock task cancelled.')
  self.start()
  try:return {'utc':datetime.now(timezone.utc).isoformat(),'origin':'local_clock','verified':True}
  finally:self.shutdown()
 def registration(self):return ExecutionProfile('get_current_time',self.normalize,lambda cancel:{'integration':'clock','network':'none','processes':0},self.execute)

def default_catalog(*,ops_instance=None,ops_mode='manual'):
 def ops_factory():
  from .ops_lifecycle import OpsIntegration
  return OpsIntegration(ops_instance,mode=ops_mode,enabled=True)
 entries={'clock':(Clock.spec,Clock)}
 spec=IntegrationSpec('ops_pilot',('readonly_monitor','start','status','stop'),('read',),{'additional_processes':1,'ram_bytes':None,'memory_ceiling_bytes':268435456},ops_instance is not None)
 entries['ops_pilot']=(spec,ops_factory)
 for name in ('naukri','linkedin','github','gmail','browser'):
  spec=IntegrationSpec(name,('not_configured',),(),{'ram_bytes':None,'additional_processes':0},False);entries[name]=(spec,None)
 return Catalog(entries)
