"""Prepare exact production approval requests; real production execution is absent."""
from dataclasses import dataclass
import re
from .guardian.policy import Denied
from .guardian.secrets import prompt_text


class DeploymentBlocked(Denied):
    pass


@dataclass(frozen=True)
class DeploymentIntent:
    target: str
    version: str
    scope: tuple[str, ...]
    expected_changes: tuple[str, ...]
    artifact_sha256: str

    def __post_init__(self):
        if type(self.target) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', self.target):
            raise ValueError('Exact deployment target required.')
        if type(self.version) is not str or not re.fullmatch(r'[a-f0-9]{40,64}', self.version):
            raise ValueError('Immutable version required.')
        if type(self.artifact_sha256) is not str or not re.fullmatch(r'[a-f0-9]{64}', self.artifact_sha256):
            raise ValueError('Exact artifact hash required.')
        if type(self.scope) is not tuple or not 1 <= len(self.scope) <= 20 or any(type(x) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', x) for x in self.scope):
            raise ValueError('Explicit deployment scope required.')
        if (type(self.expected_changes) is not tuple or not 1 <= len(self.expected_changes) <= 20
                or any(type(x) is not str or not x.strip() or len(x) > 300 or prompt_text(x) != x for x in self.expected_changes)):
            raise ValueError('Bounded non-sensitive expected changes required.')

    def action(self):
        return {'operation': 'deployment.production', 'arguments': {
            'environment': 'production', 'target': self.target, 'version': self.version,
            'scope': list(self.scope), 'expected_changes': list(self.expected_changes),
            'artifact_sha256': self.artifact_sha256}}


class DeploymentGate:
    def __init__(self, policy, workspace, approvals):
        self.policy, self.workspace, self.approvals = policy, workspace, approvals

    def request(self, intent):
        if type(intent) is not DeploymentIntent:
            raise ValueError('Typed reviewed deployment intent required.')
        self.policy.require('deployment.production')
        pending = self.approvals.request(self.policy, self.workspace, intent.action(), environment='production')
        return {'approval': pending, 'review': intent.action()['arguments'], 'deployed': False}

    def rehearse_approval(self, intent, approval_id):
        """Consumes a test-owner approval only; returns no execution capability."""
        if type(intent) is not DeploymentIntent:
            raise ValueError('Typed deployment intent required.')
        self.policy.require('deployment.production')
        self.approvals.consume(approval_id, self.policy, self.workspace, intent.action(), environment='production')
        return {'status': 'approval_validated_only', 'deployed': False, 'execution_available': False}

    def deploy(self, intent, approval_id=None):
        # No provider callback exists. Even a valid reference cannot activate one.
        raise DeploymentBlocked('Production execution is unavailable in this plan; explicit owner approval and a separately verified deployment boundary are required.')
