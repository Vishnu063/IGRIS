"""One in-flight simulated batch; exact approval enforced inside Guardian."""
from dataclasses import dataclass
import json
import hashlib
from pathlib import Path
from threading import BoundedSemaphore
from uuid import uuid4

from ..adapters.contracts import AdapterUnavailable, ContractError, identifier
from ..guardian.executor import execute
from .contracts import validate_task
from .registry import profile


class SchedulerBusy(RuntimeError):
    pass


def validate_batch(raw):
    if type(raw) is not dict or set(raw) != {'recommendation_id', 'mission_id', 'tasks'}:
        raise ContractError('Invalid specialist batch schema.')
    identifier(raw['recommendation_id']); identifier(raw['mission_id'])
    tasks = raw['tasks']
    if type(tasks) is not list or not 1 <= len(tasks) <= 2:
        raise ContractError('A batch must contain one or two specialists.')
    seen = set()
    normalized = []
    for item in tasks:
        if type(item) is not dict or set(item) not in ({'role', 'task', 'context'}, {'role', 'task', 'context', 'definition_sha256'}):
            raise ContractError('Invalid specialist task schema.')
        spec = profile(item['role'])
        if spec.id in seen:
            raise ContractError('Duplicate specialist in batch.')
        seen.add(spec.id)
        context = validate_task(spec, raw['mission_id'], item['task'], item['context'])
        definition_hash = hashlib.sha256(spec.definition().encode()).hexdigest()
        if 'definition_sha256' in item and item['definition_sha256'] != definition_hash:
            raise ContractError('Specialist definition changed after recommendation.')
        normalized.append({'role': spec.id, 'task': spec.task, 'context': context, 'definition_sha256': definition_hash})
    return {'recommendation_id': raw['recommendation_id'], 'mission_id': raw['mission_id'], 'tasks': normalized}


@dataclass(frozen=True)
class Recommendation:
    id: str
    roles: tuple[str, ...]
    mode: str = 'simulated_only'
    requires_approval: bool = True


class SpecialistScheduler:
    def __init__(self, policy, workspace, approvals, *, mode='simulated_only'):
        if mode != 'simulated_only':
            raise AdapterUnavailable('Live specialist models are not connected.')
        self.policy, self.workspace, self.approvals = policy, Path(workspace), approvals
        self._recommendations = {}
        self._slot = BoundedSemaphore(1)

    def recommend(self, mission_id, tasks):
        batch = validate_batch({'recommendation_id': uuid4().hex, 'mission_id': mission_id, 'tasks': tasks})
        if len(self._recommendations) >= 64:
            raise ContractError('Recommendation capacity reached; explicitly forget old recommendations.')
        self._recommendations[batch['recommendation_id']] = json.dumps(batch, sort_keys=True, allow_nan=False)
        return Recommendation(batch['recommendation_id'], tuple(item['role'] for item in batch['tasks']))

    def _batch(self, recommendation_id):
        identifier(recommendation_id)
        if recommendation_id not in self._recommendations:
            raise ContractError('Recommend specialists before requesting activation.')
        return json.loads(self._recommendations[recommendation_id])

    def request(self, recommendation_id):
        batch = self._batch(recommendation_id)
        action = {'operation': 'specialists.fixture', 'arguments': batch}
        pending = self.approvals.request(self.policy, self.workspace, action)
        return {'approval': pending, 'review': batch, 'activation_started': False}

    def run(self, recommendation_id, approval_id=None):
        if not self._slot.acquire(blocking=False):
            raise SchedulerBusy('One batch is already in flight; no unbounded queue is maintained.')
        try:
            batch = self._batch(recommendation_id)
            return execute(self.policy, self.workspace,
                           {'operation': 'specialists.fixture', 'arguments': batch, 'approval_id': approval_id},
                           approval_store=self.approvals.path)
        finally:
            self._slot.release()

    def forget(self, recommendation_id):
        self._recommendations.pop(recommendation_id, None)  # Does not create/revive execution authority.
