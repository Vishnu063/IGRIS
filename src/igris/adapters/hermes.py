"""IGRIS-owned reasoning contract, not an invented Hermes upstream API."""
from dataclasses import dataclass
from typing import Protocol

from .contracts import AdapterUnavailable, ContractError, identifier, safe_text


@dataclass(frozen=True)
class PlannerRequest:
    mission_id: str
    prompt: str

    def __post_init__(self):
        identifier(self.mission_id)
        object.__setattr__(self, 'prompt', safe_text(self.prompt))


@dataclass(frozen=True)
class Plan:
    route: str
    summary: str
    origin: str

    def __post_init__(self):
        if self.route not in ('inspect_fixture', 'summarize') or self.origin != 'simulated':
            raise ContractError('Unsupported plan or evidence origin.')
        object.__setattr__(self, 'summary', safe_text(self.summary))


class HermesAdapter(Protocol):
    def plan(self, request: PlannerRequest) -> Plan: ...


def parse_mock_plan(raw) -> Plan:
    if type(raw) is not dict or set(raw) != {'route', 'summary'}:
        raise ContractError('Invalid planner response schema.')
    if type(raw['route']) is not str:
        raise ContractError('Invalid planner route.')
    # Origin is assigned by this mock adapter, never accepted from a response.
    return Plan(raw['route'], raw['summary'], 'simulated')


class MockHermesAdapter:
    connectivity = 'simulated_only'

    def __init__(self, response=None):
        self._response = dict(response) if response is not None else {
            'route': 'inspect_fixture', 'summary': 'Simulated plan: inspect the approved fixture and prepare a report.'}

    def plan(self, request: PlannerRequest) -> Plan:
        if type(request) is not PlannerRequest:
            raise ContractError('Invalid planner request.')
        return parse_mock_plan(self._response)


class UnavailableHermesAdapter:
    connectivity = 'not_connected'

    def plan(self, request: PlannerRequest) -> Plan:
        raise AdapterUnavailable('Hermes live integration is not configured or verified.')


def select_hermes(mode='disabled') -> HermesAdapter:
    if mode == 'mock':
        return MockHermesAdapter()
    if mode in ('disabled', 'real'):
        return UnavailableHermesAdapter()
    raise ContractError('Unknown planner mode.')
