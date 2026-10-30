"""Fixed lazy metadata registry. No arbitrary imports or plugin discovery."""
from importlib import import_module
from types import MappingProxyType
from ..adapters.contracts import ContractError

CATALOG = MappingProxyType({
    'frontend': ('development', 'frontend_plan'), 'backend': ('development', 'backend_plan'),
    'mobile': ('development', 'mobile_plan'), 'ai_engineer': ('development', 'ai_plan'),
    'devops': ('development', 'devops_plan'),
})


def profile(role):
    if type(role) is not str or role not in CATALOG:
        raise ContractError('Unknown specialist.')
    group, _ = CATALOG[role]
    return import_module('igris.specialists.' + group).PROFILES[role]


def recommend(task):
    matches = tuple(role for role, (_, supported) in CATALOG.items() if task == supported)
    if not matches:
        raise ContractError('No specialist supports that task.')
    return matches  # Recommendation only; no worker is invoked.
