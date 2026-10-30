"""One explicitly simulated mission with real local Guardian artifact enforcement."""
from pathlib import Path

from .adapters.contracts import AdapterUnavailable, ContractError
from .adapters.hermes import Plan, PlannerRequest
from .adapters.n8n import WorkflowRequest, WorkflowResult
from .adapters.ops_pilot import InspectionRequest, Snapshot
from .controller import TaskOutcome
from .guardian.executor import execute
from .guardian.policy import Denied


class SimulatedInspection:
    """Trusted adapters/policy/workspace/store; no live operational authority."""
    def __init__(self, policy, workspace, approvals, hermes, n8n, ops_pilot):
        self.policy = policy
        self.workspace = Path(workspace).resolve(strict=True)
        self.approvals = approvals
        self.hermes, self.n8n, self.ops_pilot = hermes, n8n, ops_pilot
        self._pending = {}

    def __call__(self, context):
        if context.actor != self.policy.actor:
            return TaskOutcome('blocked', 'Trusted actor mismatch.', 'simulated')
        try:
            self.policy.require('file.read')
            self.policy.require('file.create')
            if context.mission_id not in self._pending:
                if context.approval_id is not None:
                    return TaskOutcome('failed', 'No pending action matches this mission.', 'simulated')
                plan = self.hermes.plan(PlannerRequest(context.mission_id, context.prompt))
                if type(plan) is not Plan or plan.route != 'inspect_fixture' or plan.origin != 'simulated':
                    raise ContractError('Unsupported planning result.')
                workflow = self.n8n.run(WorkflowRequest(context.mission_id, 'fixture-app'))
                if (type(workflow) is not WorkflowResult or workflow.mission_id != context.mission_id
                        or workflow.origin != 'simulated' or workflow.status != 'completed'):
                    raise ContractError('Unverified workflow result.')
                snapshot = self.ops_pilot.inspect(InspectionRequest(context.mission_id, 'fixture-app'))
                if (type(snapshot) is not Snapshot or snapshot.mission_id != context.mission_id
                        or snapshot.application != 'fixture-app' or snapshot.origin != 'simulated'):
                    raise ContractError('Unverified inspection result.')
                text = ('SIMULATED INSPECTION — NOT A REAL SERVICE CHECK\n'
                        f'Mission: {context.mission_id}\n'
                        f'Workflow: {workflow.summary}\n'
                        f'Fixture health: {snapshot.health}\n'
                        f'Fixture container: {snapshot.container}\n'
                        + '\n'.join(snapshot.evidence) + '\nNo recovery action executed.\n')
                action = {'operation': 'file.create', 'arguments': {
                    'path': f'artifacts/inspection-{context.mission_id}.txt', 'text': text}}
                record = self.approvals.request(self.policy, self.workspace, action)
                self._pending[context.mission_id] = (action, record['id'])
                return TaskOutcome('approval_required', 'Simulation prepared; owner review required for local artifact.',
                                   'simulated', approval_request_id=record['id'])
            action, pending_id = self._pending[context.mission_id]
            if context.approval_id is None:
                return TaskOutcome('approval_required', 'Owner review required for local artifact.',
                                   'simulated', approval_request_id=pending_id)
            # Never trust the controller, model or reference alone: broker consumes
            # the exact approval inside its process immediately before file creation.
            request = dict(action, approval_id=context.approval_id)
            result = execute(self.policy, self.workspace, request, approval_store=self.approvals.path)
            if not result['ok']:
                return TaskOutcome('failed', 'Guardian rejected artifact execution or execution failed.', 'simulated')
            evidence = execute(self.policy, self.workspace, {'operation': 'file.read', 'arguments': {
                'path': action['arguments']['path']}})
            verified = evidence['ok'] and evidence['result']['text'] == action['arguments']['text']
            if not verified:
                return TaskOutcome('failed', 'Artifact verification failed; reconcile state before retry.', 'simulated')
            return TaskOutcome('success', 'Simulated mission completed; approved local artifact verified. No real service checked.',
                               'simulated', True)
        except AdapterUnavailable:
            return TaskOutcome('blocked', 'A required integration is unavailable; no live fallback was attempted.', 'simulated')
        except Denied:
            return TaskOutcome('blocked', 'Required permission or approval-store access denied.', 'simulated')
        except (ContractError, OSError, ValueError):
            return TaskOutcome('failed', 'Integration contract or approval preparation failed.', 'simulated')
