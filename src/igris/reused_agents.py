"""Load copied/adapted definitions and prepare the copied Hermes core contract."""
import hashlib
import json
from pathlib import Path
from .adapters.contracts import AdapterUnavailable, ContractError

ROOT = Path(__file__).resolve().parents[2]


def specialist_definition(role):
    manifest = json.loads((ROOT / 'integrations/agency-agents/manifest.json').read_text())
    if type(role) is not str or role not in manifest['roles']:
        raise ContractError('Unknown adapted specialist.')
    item = manifest['roles'][role]
    path = ROOT / item['adapted']
    if path.is_symlink() or not path.resolve().is_relative_to(ROOT / 'integrations/agency-agents'):
        raise ContractError('Unsafe adapted definition path.')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != item['adapted_sha256']:
        raise ContractError('Adapted definition changed; review and refresh manifest first.')
    return raw.decode('utf-8')


def hermes_core_spec(model, *, role=None):
    if type(model) is not str or not model.strip() or len(model) > 200:
        raise ContractError('Explicit model selection required.')
    return {'source': str(ROOT / 'vendor/hermes-agent/run_agent.py'), 'class': 'AIAgent',
            'revision': '2d2808ee84549f9836b0056750265058e5488a8a',
            'kwargs': {'model': model, 'enabled_toolsets': [], 'max_iterations': 1,
                       'skip_context_files': True, 'load_soul_identity': False,
                       'skip_memory': True, 'skip_background_review': True,
                       'save_trajectories': False, 'verbose_logging': False,
                       'quiet_mode': True, 'checkpoints_enabled': False,
                       'ephemeral_system_prompt': specialist_definition(role) if role else 'You are IGRIS. Propose only; Guardian independently authorizes all actions.'}}


def activate_hermes(*args, **kwargs):
    raise AdapterUnavailable('Copied Hermes runtime awaits isolated Python 3.14 setup, dependency/provider/cost verification and execution-boundary validation. No live activation performed.')
