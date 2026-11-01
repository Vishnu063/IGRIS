"""Trusted chat wiring into the existing Guardian executor; no security decisions."""
import hashlib
from pathlib import Path

from .approvals import ApprovalStore
from .executor import execute
from .policy import Denied, Permission, Policy
from .readonly import ToolScope
from ..adapters.contracts import identifier


class GuardianTools:
    def __init__(self, owner, config, store_path, *, policy=None):
        self.policy = policy if policy is not None else Policy(owner,frozenset({Permission.READ}))
        if self.policy.actor != owner: raise Denied('Tool actor mismatch.')
        self.config = Path(config).absolute()
        self.scope = ToolScope.load(self.config)
        self.store_path = Path(store_path).absolute()
        if self.store_path.is_relative_to(self.scope.workspace): raise Denied('Store must be outside test workspace.')
        # Database creation/migration is trusted startup, never model-facing.
        self.store = ApprovalStore(self.store_path,initialize=not self.store_path.exists())
        self.store.enable_tool_audit()

    def run(self, request_id, mission_id, raw, *, approval_id=None):
        identifier(request_id);identifier(mission_id)
        result = execute(self.policy,self.scope.workspace,
            {'request_id':request_id,'mission_id':mission_id,'proposal':raw,'approval_id':approval_id},
            approval_store=self.store.path,tool_config=self.config)
        result['proposal_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
        return result

    def prepare(self, request_id, mission_id, raw):
        identifier(request_id);identifier(mission_id)
        return execute(self.policy,self.scope.workspace,
            {'request_id':request_id,'mission_id':mission_id,'proposal':raw,'approval_id':None},
            approval_store=self.store.path,tool_config=self.config,prepare=True)
