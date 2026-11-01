"""Owner-selected, approved single-role reasoning; no role grants tool authority."""
import hashlib,threading
from uuid import uuid4
from .registry import CATALOG,profile
from ..adapters.contracts import ContractError
from ..adapters.hermes_chat import DockerHermesAdapter,ChatRequest,chat_text
from ..guardian.activities import ExecutionProfile,ExecutionPermit
from ..guardian.policy import Denied
from ..reused_agents import specialist_definition

class LiveSpecialists:
    def __init__(self,*,enabled=False):self.enabled=enabled is True;self.slot=threading.Lock()
    def choices(self):return [{'role':role,'task':profile(role).task,'focus':profile(role).focus,'tools':[]} for role in CATALOG]
    def normalize(self,raw):
        if type(raw) is not dict or set(raw)!={'role','task','context','definition_sha256'}:raise ContractError('Explicit role, bounded task/context and reviewed definition required.')
        spec=profile(raw['role'])
        if raw['task']!=spec.task or type(raw['context']) is not str:raise ContractError('Task outside specialist boundary.')
        chat_text(raw['context'])
        if not raw['context'].strip():raise ContractError('Nonempty supplied task context required.')
        digest=hashlib.sha256(specialist_definition(spec.id).encode()).hexdigest()
        if raw['definition_sha256']!=digest:raise Denied('Specialist definition changed.')
        return dict(raw)
    def arguments(self,role,context):return self.normalize({'role':role,'task':profile(role).task,'context':context,'definition_sha256':hashlib.sha256(specialist_definition(role).encode()).hexdigest()})
    def scope(self,cancel):
        if not self.enabled:raise Denied('Specialist execution disabled.')
        if cancel.is_set():raise Denied('Specialist cancelled.')
        return {'mode':'real_local_inference','model_sha256':DockerHermesAdapter().profile['model_sha256'],
                'definitions':{role:hashlib.sha256(specialist_definition(role).encode()).hexdigest() for role in CATALOG},'native_tools':False,'concurrency':1,'methodology_excerpt_chars':1800}
    def execute(self,raw,cancel,permit):
        if not self.enabled or type(permit) is not ExecutionPermit:raise Denied('Guardian specialist lease required.')
        if not self.slot.acquire(blocking=False):raise Denied('Another specialist is active.')
        try:
            self.normalize(raw);review=permit.consume('specialists.reason',raw)
            reply=DockerHermesAdapter(cancel=cancel).specialist(ChatRequest(review.request_id,raw['context']),raw['role'])
            if cancel.is_set():raise Denied('Specialist cancelled; result discarded.')
            return dict(reply,task=raw['task'],mission_id=review.mission_id,executed_actions=False)
        finally:self.slot.release()
    def registration(self):return ExecutionProfile('specialists.reason',self.normalize,self.scope,self.execute)
