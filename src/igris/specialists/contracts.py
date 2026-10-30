from dataclasses import dataclass
from ..adapters.contracts import ContractError, identifier, safe_text


@dataclass(frozen=True)
class Specialist:
    id: str
    task: str
    focus: str
    checklist: tuple[str, ...]
    permissions: tuple = ()
    mode: str = 'proposal_only'

    def __post_init__(self):
        if self.permissions or self.mode != 'proposal_only':
            raise ContractError('Specialists cannot grant tool authority.')


def validate_task(profile, mission_id, task, context):
    identifier(mission_id)
    if task != profile.task:
        raise ContractError('Task outside specialist boundary.')
    return safe_text(context, 4096)


def validate_output(profile, mission_id, raw):
    if type(raw) is not dict or set(raw) != {'role', 'mission_id', 'task', 'summary', 'recommendations', 'limitations'}:
        raise ContractError('Invalid specialist response schema.')
    if (raw['role'] != profile.id or raw['mission_id'] != mission_id or raw['task'] != profile.task):
        raise ContractError('Specialist response mismatch.')
    result = {'role': profile.id, 'mission_id': identifier(mission_id), 'task': profile.task,
              'summary': safe_text(raw['summary'], 1024), 'origin': 'simulated', 'executed_actions': False}
    for key in ('recommendations', 'limitations'):
        items = raw[key]
        if type(items) is not list or not 1 <= len(items) <= 8:
            raise ContractError('Invalid specialist output list.')
        result[key] = [safe_text(item, 512) for item in items]
    return result


def contract_fixture(profile, mission_id, task, context):
    """Deterministic test fixture; not real specialist activation or reasoning."""
    validate_task(profile, mission_id, task, context)
    return validate_output(profile, mission_id, {
        'role': profile.id, 'mission_id': mission_id, 'task': profile.task,
        'summary': 'Simulated specialist checklist: ' + profile.focus,
        'recommendations': list(profile.checklist),
        'limitations': ['Fixture only; no model, commands, edits, live facts or professional certification.',
                        'Use supplied evidence; verify proposals and obtain separate execution permission.']})
