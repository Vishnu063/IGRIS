"""Trusted owner review workflow; never called with model-supplied decisions."""
from dataclasses import dataclass
import json
import time

from .policy import Denied
from .secrets import redact
from .tools import GuardianTools


@dataclass(frozen=True)
class ActionReview:
    id: str
    mission_id: str
    request_id: str
    action_json: str
    binding_json: str
    workspace: str
    digest: str
    expires_at: float
    deadline: float
    actor: str
    risk: str = 'read_only'

    def public(self):
        return {'id':self.id,'mission_id':self.mission_id,'request_id':self.request_id,
                'action':json.loads(self.action_json),'target':self.workspace,'risk':self.risk,
                'actor':self.actor,'action_sha256':self.digest,'expires_at':self.expires_at}


class ApprovalReviews:
    """Only an authenticated CLI/UI controller holds this object, never Hermes."""
    def __init__(self, tools, *, timeout=60, ttl=300, monotonic=time.monotonic):
        if type(tools) is not GuardianTools: raise Denied('Trusted Guardian wiring required.')
        if type(timeout) not in (int,float) or not 0<timeout<=60 or type(ttl) not in (int,float) or not 0<ttl<=300:
            raise Denied('Invalid review deadlines.')
        self.tools,self.timeout,self.ttl,self.monotonic=tools,timeout,ttl,monotonic
        self._pending={};self._approved=set()

    def _authorize(self, actor):
        if actor!=self.tools.policy.actor: raise Denied('Owner review access denied.')

    def prepare(self, actor, request_id, mission_id, raw):
        self._authorize(actor)
        if mission_id in self._pending or len(self._pending)>=64: raise Denied('Review capacity or duplicate request.')
        result=self.tools.prepare(request_id,mission_id,raw)
        if not result['ok'] or not result['review']['approval_required']: return result,None
        data=result['review']
        action_json=json.dumps(data['action'],sort_keys=True,separators=(',',':'))
        if redact(action_json)!=action_json: raise Denied('Sensitive action cannot be reviewed.')
        record=self.tools.store.request(self.tools.policy,self.tools.scope.workspace,data['action'],
            ttl_seconds=self.ttl,environment=data['environment'],binding=data['binding'])
        if record['action_sha256']!=data['action_sha256']:
            self.tools.store.close(record['id'],self.tools.policy,record['action_sha256'])
            raise Denied('Prepared action digest changed.')
        review=ActionReview(record['id'],mission_id,request_id,action_json,json.dumps(data['binding'],sort_keys=True),
            data['workspace'],record['action_sha256'],record['expires_at'],self.monotonic()+self.timeout,actor)
        self._pending[mission_id]=review
        return result,review

    def get(self, actor, mission_id):
        self._authorize(actor)
        if mission_id not in self._pending: raise Denied('No pending owner review.')
        return self._pending[mission_id]

    def expiry(self, review):
        if self.tools.store._now()>=review.expires_at:return 'expired'
        if self.monotonic()>=review.deadline:return 'timed_out'
        return None

    def decide(self, actor, mission_id, *, approve, reviewed_digest):
        review=self.get(actor,mission_id)
        reason=self.expiry(review)
        if reason:
            self.cancel(actor,mission_id,reason=reason);raise Denied('Owner review deadline elapsed.')
        if type(approve) is not bool or reviewed_digest!=review.digest:
            self.tools.store.tool_event(self.tools.policy,review.request_id,mission_id,'unregistered','unavailable','decision_rejected')
            raise Denied('Exact owner review decision required.')
        self.tools.store.decide(review.id,approve=approve,reviewed_digest=reviewed_digest)
        if approve:self._approved.add(mission_id)
        return review

    def approved(self, actor, mission_id):
        review=self.get(actor,mission_id)
        if self.expiry(review) or mission_id not in self._approved: raise Denied('Current owner approval required.')
        return review

    def cancel(self, actor, mission_id, *, reason='cancelled'):
        review=self.get(actor,mission_id)
        self.tools.store.close(review.id,self.tools.policy,review.digest,reason=reason)
        self._approved.discard(mission_id);self._pending.pop(mission_id,None)

    def finish(self, actor, mission_id):
        if mission_id in self._pending:self.cancel(actor,mission_id)
