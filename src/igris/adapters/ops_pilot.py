"""Simulation port only. Real Ops Pilot audit begins in Step 16."""
from dataclasses import dataclass
import re
from typing import Protocol
from .contracts import AdapterUnavailable, ContractError, identifier, safe_text


@dataclass(frozen=True)
class InspectionRequest:
    mission_id: str
    application: str

    def __post_init__(self):
        identifier(self.mission_id)
        if type(self.application) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', self.application):
            raise ContractError('Invalid fixture application.')


@dataclass(frozen=True)
class Snapshot:
    mission_id: str
    application: str
    health: str
    container: str
    evidence: tuple[str, ...]
    origin: str = 'simulated'

    def __post_init__(self):
        InspectionRequest(self.mission_id, self.application)
        if self.origin != 'simulated' or self.health not in ('healthy', 'unhealthy', 'unknown') or self.container not in ('running', 'stopped', 'unknown'):
            raise ContractError('Invalid simulated snapshot.')
        if type(self.evidence) is not tuple or not 1 <= len(self.evidence) <= 8:
            raise ContractError('Invalid evidence list.')
        object.__setattr__(self, 'evidence', tuple(safe_text(item, 512) for item in self.evidence))


class OpsPilotAdapter(Protocol):
    def inspect(self, request: InspectionRequest) -> Snapshot: ...


class MockOpsPilotAdapter:
    connectivity = 'simulated_only'

    def inspect(self, request):
        if type(request) is not InspectionRequest:
            raise ContractError('Invalid inspection request.')
        return Snapshot(request.mission_id, request.application, 'unhealthy', 'stopped',
                        ('Synthetic endpoint check failed.', 'Synthetic container fixture is stopped.'))


class UnavailableOpsPilotAdapter:
    connectivity = 'not_connected'

    def inspect(self, request):
        raise AdapterUnavailable('Real Ops Pilot interface has not been audited or connected.')
