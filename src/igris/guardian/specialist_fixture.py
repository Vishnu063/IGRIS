"""Independent fixed-fixture boundary, never a model/plugin/tool executor."""
from pathlib import Path
from .approvals import ApprovalStore
from .policy import Denied
from ..specialists.scheduling import validate_batch
from ..specialists.registry import profile
from ..specialists.contracts import contract_fixture


def run(policy, root, request, approval_path, environment):
    policy.require('specialists.fixture')
    batch = validate_batch(request['arguments'])
    if batch != request['arguments']:
        raise Denied('Sanitize specialist input before requesting approval.')
    if str(approval_path) == '-':
        raise Denied('Specialist approval required.')
    location = Path(approval_path).resolve(strict=True)
    if location.is_relative_to(root.resolve()):
        raise Denied('Approval store must be outside workspace.')
    store = ApprovalStore(location)
    action = {'operation': 'specialists.fixture', 'arguments': batch}
    reference = request.get('approval_id')
    digest = store.consume(reference, policy, root, action, environment=environment)
    try:
        # Max two requested roles, serially, only AFTER exact approval consumption.
        results = [contract_fixture(profile(item['role']), batch['mission_id'], item['task'], item['context'])
                   for item in batch['tasks']]
        store.outcome(reference, policy, action['operation'], digest, succeeded=True)
        return {'origin': 'simulated', 'results': results, 'live_models_loaded': 0,
                'executed_actions': False, 'max_batch_size': 2}
    except Exception:
        store.outcome(reference, policy, action['operation'], digest, succeeded=False)
        raise
