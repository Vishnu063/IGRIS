"""Recovery workflow ports; only the explicitly named fixture simulator is usable."""
from dataclasses import dataclass
from pathlib import Path

from .adapters.contracts import AdapterUnavailable
from .guardian.executor import execute


@dataclass(frozen=True)
class RecoveryResult:
    status: str
    verified: bool
    origin: str
    container_running: bool | None
    application_healthy: bool | None
    retry_allowed: bool = False
    reason: str = ''


class SimulatedRecovery:
    def __init__(self, policy, workspace: Path, approvals):
        self.policy, self.workspace, self.approvals = policy, Path(workspace), approvals

    def request(self, arguments):
        # A request is pending only. Neither provider nor Guardian is auto-approved.
        action = {'operation': 'ops.recovery.fixture', 'arguments': arguments}
        return self.approvals.request(self.policy, self.workspace, action)

    def run(self, arguments, approval_id=None):
        response = execute(self.policy, self.workspace,
                           {'operation': 'ops.recovery.fixture', 'arguments': arguments, 'approval_id': approval_id},
                           approval_store=self.approvals.path)
        if not response['ok']:
            return RecoveryResult('rejected_or_failed', False, 'simulated', None, None,
                                  reason=response.get('reason', 'Guardian execution failed.'))
        result = response['result']
        return RecoveryResult(result['status'], result['verified'], result['origin'],
                              result['container_running'], result['application_healthy'], reason=result['reason'])


class LiveOpsRecovery:
    def request(self, *args, **kwargs):
        raise AdapterUnavailable('Live recovery blocked: provider-side Guardian enforcement is not verified.')

    def run(self, *args, **kwargs):
        raise AdapterUnavailable('Live recovery blocked: no provider mutation transport is enabled.')
