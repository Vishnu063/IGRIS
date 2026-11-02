"""Registered execution profiles reuse Guardian Policy, ActionReview and ApprovalStore.

Only trusted CLI/UI setup supplies profiles. Models never receive this service,
profile callables, approval databases, decisions or worker transports.
"""
from dataclasses import dataclass
import hashlib,json,threading,time
from pathlib import Path
from types import MappingProxyType
from uuid import uuid4
from .approvals import ApprovalStore,RISK_CATEGORIES
from .policy import Policy,Denied
from .review import ActionReview
from .secrets import redact
from ..adapters.contracts import identifier,ContractError
from ..isolated import Cancelled


def canonical(value):
    def inspect(item,depth=0):
        if depth>32:raise Denied('Action data nesting exceeds limit.')
        if type(item) is str:
            if redact(item)!=item:raise Denied('Sensitive action text denied.')
        elif type(item) is dict:
            for key,child in item.items():
                if type(key) is not str or redact(key+':')!=key+':':raise Denied('Sensitive or invalid action field.')
                inspect(child,depth+1)
        elif type(item) is list:
            for child in item:inspect(child,depth+1)
        elif type(item) not in (int,float,bool,type(None)):raise Denied('JSON action data required.')
    inspect(value)
    try:output=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
    except (ValueError,TypeError,RecursionError):raise Denied('Invalid action data.') from None
    if len(output.encode())>16384:raise Denied('Oversized action data.')
    return output


@dataclass(frozen=True)
class ExecutionProfile:
    operation: str
    normalize: object
    scope: object
    execute: object


@dataclass(frozen=True)
class ExecutionPermit:
    """Opaque process-local Guardian lease; never accepted from JSON/model data."""
    issuer: object
    review: ActionReview

    def consume(self,operation,arguments):
        if type(self.issuer) is not OwnerActions:raise Denied('Unrecognized Guardian execution lease issuer.')
        return OwnerActions._consume_permit(self.issuer,self,operation,arguments)


class OwnerActions:
    """Process-local proposals, explicit owner decisions, exact single-use authority.

    Restart has no pending snapshots and cannot automatically execute database
    approvals. Python/same-user tampering and database rollback are not isolation.
    """
    def __init__(self,policy,workspace,store,profiles,*,timeout=60,ttl=300,monotonic=time.monotonic,foreground=None):
        if type(policy) is not Policy or type(store) is not ApprovalStore:raise Denied('Existing Guardian authority required.')
        if type(timeout) not in (int,float) or not 0<timeout<=60 or type(ttl) not in (int,float) or not 0<ttl<=300:raise Denied('Bounded review lifetime required.')
        entries={}
        for profile in profiles:
            if type(profile) is not ExecutionProfile or profile.operation in entries or profile.operation not in RISK_CATEGORIES or not all(callable(x) for x in (profile.normalize,profile.scope,profile.execute)):raise Denied('Invalid trusted execution profile.')
            policy.require(profile.operation);entries[profile.operation]=profile
        from ..foreground import default_foreground
        self.foreground=foreground if foreground is not None else default_foreground()
        self.policy,self.workspace,self.store=policy,Path(workspace).resolve(strict=True),store
        self.profiles=MappingProxyType(entries);self.timeout,self.ttl,self.monotonic=timeout,ttl,monotonic
        self._pending={};self._preparing={};self._history={};self._lock=threading.RLock();self._stopped=False
        store.enable_tool_audit()

    def _owner(self,actor):
        if type(actor) is not str or actor!=self.policy.actor:
            self._deny('unavailable','unavailable');raise Denied('Authenticated owner action required.')

    def _deny(self,request_id,mission_id):
        self.store.tool_event(self.policy,request_id,mission_id,'unregistered','unavailable','denied')

    def prepare(self,actor,operation,arguments,*,mission_id=None,request_id=None,task_identity=None,task_cancel=None):
        self._owner(actor);mid=mission_id or uuid4().hex;rid=request_id or uuid4().hex
        event=task_cancel if task_cancel is not None else threading.Event();reserved=False;lease=None
        try:
            identifier(mid);identifier(rid)
            with self._lock:
                if self._stopped or mid in self._pending or mid in self._preparing or len(self._pending)+len(self._preparing)>=64:raise Denied('Action stopped, duplicate or capacity reached.')
                if type(operation) is not str or operation not in self.profiles:raise Denied('Unregistered execution profile.')
                self.policy.require(operation);profile=self.profiles[operation]
                self._preparing[mid]=event;reserved=True
            raw=canonical(arguments)
            from ..foreground import fingerprint
            lease=self.foreground.begin(actor,operation,task_id=mid,identity=task_identity or fingerprint(operation,json.loads(raw)),cancel=event)
            lease.transition('starting',action=operation)
            if event.is_set():raise Cancelled('Task cancelled before preparation.')
            normalized=profile.normalize(json.loads(raw))
            if type(normalized) is not dict:raise Denied('Typed action arguments required.')
            action={'operation':operation,'arguments':normalized};action_json=canonical(action)
            scope_data=profile.scope(event)
            if type(scope_data) is not dict or not scope_data:raise Denied('Verified execution scope required.')
            scope=canonical(scope_data);binding={'mission_id':mid,'request_id':rid,'scope_sha256':hashlib.sha256(scope.encode()).hexdigest()}
            with self._lock:
                if self._stopped or event.is_set():raise Cancelled('Preparation cancelled.')
                record=self.store.request(self.policy,self.workspace,action,environment='test',binding=binding,ttl_seconds=self.ttl)
                review=ActionReview(record['id'],mid,rid,action_json,canonical(binding),str(self.workspace),record['action_sha256'],record['expires_at'],self.monotonic()+self.timeout,actor,RISK_CATEGORIES[operation])
                self._pending[mid]={'review':review,'profile':profile,'raw':raw,'scope':scope,'cancel':event,'approved':False,'running':False,'lease':lease}
                lease.transition('waiting_for_approval')
                return review
        except BaseException as error:
            from ..owned_jobs import UnconfirmedLaunch
            if lease:lease.finish(error=type(error).__name__,cleanup=not isinstance(error,UnconfirmedLaunch))
            self._deny(rid,mid);raise
        finally:
            if reserved:
                with self._lock:self._preparing.pop(mid,None)

    def _job(self,actor,mid):
        self._owner(actor)
        if mid not in self._pending:raise Denied('No current action snapshot; prepare again after restart.')
        return self._pending[mid]

    def _expiry(self,review,*,decision=True):
        if self.store._now()>=review.expires_at:return 'expired'
        if decision and self.monotonic()>=review.deadline:return 'timed_out'
        return None

    def review(self,actor,mid):
        with self._lock:return self._job(actor,mid)['review']

    def decide(self,actor,mid,*,approve,reviewed_digest):
        with self._lock:
            job=self._job(actor,mid);review=job['review'];reason=self._expiry(review)
            if reason:self.cancel(actor,mid,reason=reason);raise Denied('Owner decision expired.')
            if job['running'] or type(approve) is not bool or reviewed_digest!=review.digest:
                self._deny(review.request_id,mid);raise Denied('Exact owner decision required.')
            self.store.decide(review.id,approve=approve,reviewed_digest=reviewed_digest)
            job['approved']=approve
            if not approve:self.cancel(actor,mid,reason='rejected')
            return review

    def run(self,actor,mid):
        with self._lock:
            job=self._job(actor,mid);review=job['review']
            if not job['approved'] or job['running'] or self._stopped:
                self._deny(review.request_id,mid);raise Denied('Current explicit owner approval required.')
            job['lease'].transition('running')
            job['running']=True
        consumed=False;succeeded=False;failure=None;cleanup=True;retained=False;partial=False
        try:
            profile=job['profile'];self.policy.require(profile.operation)
            action={'operation':profile.operation,'arguments':profile.normalize(json.loads(job['raw']))}
            if canonical(action)!=review.action_json or canonical(profile.scope(job['cancel']))!=job['scope']:raise Denied('Action arguments, runtime or scope changed.')
            with self._lock:
                reason=self._expiry(review,decision=False)
                if self._stopped or job['cancel'].is_set() or reason:raise Denied('Action cancelled, stopped or expired.')
                self.store.consume(review.id,self.policy,self.workspace,action,environment='test',binding=json.loads(review.binding_json));consumed=True
                permit=ExecutionPermit(self,review);job.update(permit=permit,permit_used=False,consumed=True)
            result=profile.execute(action['arguments'],job['cancel'],permit)
            if not job['permit_used']:raise Denied('Execution profile did not validate its Guardian lease.')
            if job['cancel'].is_set():raise Cancelled('Owner cancelled; result discarded.')
            if type(result) is not dict or not result:raise ContractError('Validated execution result required.')
            if ('verified' in result and result['verified'] is not True) or result.get('status') in ('failed','cancelled','not_verified'):raise ContractError('Executor did not verify its outcome.')
            canonical(result);succeeded=True;retained=result.get('resource_disposition')=='retained_authorized'
            return result
        except BaseException as error:
            from ..owned_jobs import UnconfirmedLaunch
            from ..semantic_memory import PartialMemoryCommit
            partial=isinstance(error,PartialMemoryCommit)
            failure=type(error).__name__;cleanup=not isinstance(error,UnconfirmedLaunch)
            raise
        finally:
            with self._lock:
                if consumed:self.store.outcome(review.id,self.policy,profile.operation,review.digest,succeeded=succeeded)
                else:
                    self._deny(review.request_id,mid)
                    self.store.close(review.id,self.policy,review.digest,reason='cancelled')
                self._history[mid]={'status':'completed' if succeeded else 'cancelled' if job['cancel'].is_set() else 'failed','operation':review.public()['action']['operation']}
                if len(self._history)>128:self._history.pop(next(iter(self._history)))
                self._pending.pop(mid,None)
                job['lease'].finish(verified=succeeded,cleanup=cleanup,error=failure,retained=retained,partial=partial)

    def _consume_permit(self,permit,operation,arguments):
        with self._lock:
            if type(permit) is not ExecutionPermit:raise Denied('Guardian execution lease required.')
            review=permit.review;job=self._job(self.policy.actor,review.mission_id)
            if job.get('permit') is not permit or not job.get('consumed') or job.get('permit_used') or not job['running'] or self._stopped or job['cancel'].is_set() or self._expiry(review,decision=False):
                raise Denied('Execution lease missing, used, cancelled or expired.')
            action=json.loads(review.action_json)
            self.policy.require(operation)
            if operation!=action['operation'] or canonical(arguments)!=canonical(action['arguments']):raise Denied('Execution lease action mismatch.')
            job['permit_used']=True
            return review

    def cancel(self,actor,mid,*,reason='cancelled'):
        with self._lock:
            job=self._job(actor,mid);review=job['review'];job['cancel'].set()
            self.store.close(review.id,self.policy,review.digest,reason=reason if reason in ('expired','timed_out') else 'cancelled')
            if not job['running']:
                job['lease'].finish(error='Owner rejected or cancelled action')
                self._pending.pop(mid,None);self._history[mid]={'status':reason,'operation':review.public()['action']['operation']}
                if len(self._history)>128:self._history.pop(next(iter(self._history)))

    def status(self,actor):
        self._owner(actor)
        with self._lock:return {'stopped':self._stopped,'preparing':list(self._preparing),'pending':[dict(job['review'].public(),status='running' if job['running'] else 'approved' if job['approved'] else 'awaiting_approval') for job in self._pending.values()], 'history':dict(self._history)}

    def stop(self,actor):
        self._owner(actor)
        with self._lock:
            self._stopped=True
            for event in self._preparing.values():event.set()
            for mid in tuple(self._pending):self.cancel(actor,mid)

    def close(self):self.stop(self.policy.actor)
