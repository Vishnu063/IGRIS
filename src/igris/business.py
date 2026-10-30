"""Local business planning records; never evidence of customers or earnings."""
from dataclasses import dataclass, replace
from types import MappingProxyType
from uuid import uuid4

from .guardian.secrets import prompt_text

FOCUS = frozenset({'devops', 'aws', 'websites', 'ai_automation',
                   'business_automation', 'maintenance', 'digital_products'})
BUSINESS_TRANSITIONS = MappingProxyType({
    'research': frozenset({'evaluating', 'cancelled'}),
    'evaluating': frozenset({'proposal_draft', 'cancelled'}),
    'proposal_draft': frozenset({'delivery_planning', 'cancelled'}),
    'delivery_planning': frozenset({'closed', 'cancelled'}),
})


def safe_text(value, limit=2048):
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValueError('Invalid business text.')
    return prompt_text(value)


@dataclass(frozen=True)
class BusinessMission:
    id: str
    focus: str
    objective: str
    state: str = 'research'
    technical_mission_ids: tuple = ()
    category: str = 'business'


class BusinessController:
    """Trusted operator API. Records do not activate agents or external actions."""
    def __init__(self):
        self._missions = {}

    def create(self, focus, objective):
        if focus not in FOCUS:
            raise ValueError('Unsupported business focus.')
        mission = BusinessMission(uuid4().hex, focus, safe_text(objective))
        self._missions[mission.id] = mission
        return mission

    def get(self, identifier):
        return self._missions[identifier]

    def move(self, identifier, state):
        mission = self.get(identifier)
        if state not in BUSINESS_TRANSITIONS.get(mission.state, ()):
            raise ValueError('Invalid business transition.')
        self._missions[identifier] = replace(mission, state=state)
        return self.get(identifier)

    def link_technical(self, identifier, technical_id):
        # A reference only: it cannot change a technical mission or permissions.
        if type(technical_id) is not str or len(technical_id) != 32 or any(c not in '0123456789abcdef' for c in technical_id):
            raise ValueError('Invalid technical mission reference.')
        mission = self.get(identifier)
        self._missions[identifier] = replace(mission, technical_mission_ids=tuple(dict.fromkeys((*mission.technical_mission_ids, technical_id))))
        return self.get(identifier)
