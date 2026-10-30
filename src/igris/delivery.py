"""Revisioned local delivery tracking, never deployment or acceptance authority."""
from dataclasses import dataclass, replace
import re
from types import MappingProxyType
from uuid import uuid4

from .business import safe_text

NEXT = MappingProxyType(dict(zip(
    ('requirements', 'scoped', 'developing', 'testing', 'awaiting_approval', 'approved', 'deployment_prepared', 'maintenance'),
    ('scoped', 'developing', 'testing', 'awaiting_approval', 'approved', 'deployment_prepared', 'maintenance', 'delivered'))))


@dataclass(frozen=True)
class ClientProject:
    id: str
    requirements: str
    scope: tuple
    state: str = 'requirements'
    revision: int = 1
    artifact_sha256: str | None = None
    history: tuple = ()


class DeliveryTracker:
    """Trusted operator record API; origin is asserted, not independently proven."""
    def __init__(self): self._projects = {}

    def create(self, requirements, scope):
        if type(scope) is not tuple or not 1 <= len(scope) <= 20:
            raise ValueError('Explicit scope required.')
        p = ClientProject(uuid4().hex, safe_text(requirements), tuple(safe_text(s, 512) for s in scope))
        self._projects[p.id] = p
        return p

    def get(self, identifier): return self._projects[identifier]

    def advance(self, identifier, revision, target, *, evidence_ref, origin, artifact_sha256=None):
        p = self.get(identifier)
        if type(revision) is not int or revision != p.revision or target != NEXT.get(p.state):
            raise ValueError('Stale revision or invalid delivery transition.')
        if origin not in ('simulated', 'operator_recorded'):
            raise ValueError('Explicit evidence origin required.')
        reference = safe_text(evidence_ref, 256)
        digest = p.artifact_sha256
        if target in ('awaiting_approval', 'approved', 'deployment_prepared', 'maintenance', 'delivered'):
            if type(artifact_sha256) is not str or not re.fullmatch('[a-f0-9]{64}', artifact_sha256):
                raise ValueError('Exact artifact digest required.')
            if digest is not None and digest != artifact_sha256:
                raise ValueError('Artifact changed; create a new reviewed delivery revision.')
            digest = artifact_sha256
        event = (target, reference, origin)
        self._projects[identifier] = replace(p, state=target, revision=p.revision+1,
            artifact_sha256=digest, history=p.history+(event,))
        return self.get(identifier)


def ops_job_snapshot(job):
    """Read-only projection of the pinned Ops Pilot freelance job schema.

    Deliberately excludes upstream approvals, credentials, descriptions/payments.
    No upstream status grants Guardian permission or local delivery completion.
    """
    if type(job) is not dict or type(job.get('id')) is not str or not re.fullmatch('[a-f0-9]{12}', job['id']):
        raise ValueError('Invalid Ops Pilot job.')
    if type(job.get('revision')) is not int or job['revision'] < 1:
        raise ValueError('Invalid upstream revision.')
    return {'upstream_id': job['id'], 'revision': job['revision'],
            'title': safe_text(job.get('title'), 512), 'reported_state': safe_text(job.get('state'), 80),
            'origin': 'imported_unverified', 'permissions_imported': False}
