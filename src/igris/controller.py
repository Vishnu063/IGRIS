"""Synchronous, in-memory mission controller; registered handlers are trusted code."""
from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType
from uuid import uuid4

from .guardian.policy import Policy
from .guardian.secrets import prompt_text


class MissionError(ValueError):
    pass


class State(str, Enum):
    REQUESTED = 'requested'
    PLANNED = 'planned'
    READY = 'ready'
    RUNNING = 'running'
    AWAITING_APPROVAL = 'awaiting_approval'
    VERIFYING = 'verifying'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    BLOCKED = 'blocked'


TRANSITIONS = MappingProxyType({
    State.REQUESTED: frozenset({State.PLANNED}),
    State.PLANNED: frozenset({State.READY, State.BLOCKED}),
    State.READY: frozenset({State.RUNNING}),
    State.RUNNING: frozenset({State.VERIFYING, State.AWAITING_APPROVAL, State.BLOCKED, State.FAILED}),
    State.AWAITING_APPROVAL: frozenset({State.READY}),
    State.VERIFYING: frozenset({State.SUCCEEDED, State.FAILED}),
})


@dataclass(frozen=True)
class TaskContext:
    mission_id: str
    actor: str
    prompt: str
    approval_id: str | None = None


@dataclass(frozen=True)
class TaskOutcome:
    status: str
    message: str
    origin: str = 'unverified'
    verified: bool = False
    approval_request_id: str | None = None

    def __post_init__(self):
        if self.status not in ('success', 'failed', 'blocked', 'approval_required'):
            raise MissionError('Invalid outcome status.')
        if self.origin not in ('local', 'simulated', 'real', 'unverified') or type(self.verified) is not bool:
            raise MissionError('Invalid evidence classification.')
        if type(self.message) is not str or len(self.message) > 8192:
            raise MissionError('Invalid outcome message.')
        if self.approval_request_id is not None and (type(self.approval_request_id) is not str or len(self.approval_request_id) != 32):
            raise MissionError('Invalid approval reference.')


@dataclass(frozen=True)
class Mission:
    id: str
    actor: str
    route: str
    prompt: str
    state: State = State.REQUESTED
    history: tuple[State, ...] = (State.REQUESTED,)
    message: str = ''
    origin: str = 'unverified'
    approval_request_id: str | None = None


class MissionController:
    def __init__(self, actor: str, routes: dict):
        # Actor and route implementations come from trusted startup, not a body.
        self.actor = Policy(actor).actor
        if type(routes) is not dict or any(type(name) is not str or not callable(handler) for name, handler in routes.items()):
            raise MissionError('Invalid trusted routes.')
        self.routes = MappingProxyType(dict(routes))
        self._missions = {}

    def create(self, request: str, route: str) -> Mission:
        if type(request) is not str or not request.strip() or len(request.encode()) > 8192:
            raise MissionError('Invalid mission request.')
        if type(route) is not str or route not in self.routes:
            raise MissionError('Unknown mission route.')
        mission = Mission(uuid4().hex, self.actor, route, prompt_text(request))
        self._missions[mission.id] = mission
        return mission

    def get(self, identifier: str) -> Mission:
        if type(identifier) is not str or identifier not in self._missions:
            raise MissionError('Unknown mission.')
        return self._missions[identifier]

    def _move(self, identifier, target, **changes):
        current = self.get(identifier)
        if target not in TRANSITIONS.get(current.state, frozenset()):
            raise MissionError('Invalid mission transition.')
        current = replace(current, state=target, history=current.history + (target,), **changes)
        self._missions[identifier] = current
        return current

    def run(self, identifier: str, *, approval_id=None) -> Mission:
        current = self.get(identifier)
        if current.state == State.REQUESTED:
            if approval_id is not None:
                raise MissionError('Unexpected approval reference.')
            self._move(identifier, State.PLANNED)
            current = self._move(identifier, State.READY)
        elif current.state == State.AWAITING_APPROVAL:
            if type(approval_id) is not str or len(approval_id) != 32:
                raise MissionError('Approval reference required.')
            # This only resumes routing. The actual executor must validate it.
            current = self._move(identifier, State.READY)
        else:
            raise MissionError('Mission is not runnable.')
        self._move(identifier, State.RUNNING)
        try:
            outcome = self.routes[current.route](TaskContext(current.id, self.actor, current.prompt, approval_id))
            if type(outcome) is not TaskOutcome:
                raise MissionError('Invalid handler result.')
        except Exception:
            return self._move(identifier, State.FAILED, message='Task handler failed.', origin='unverified')
        fields = {'message': prompt_text(outcome.message), 'origin': outcome.origin,
                  'approval_request_id': outcome.approval_request_id}
        if outcome.status == 'approval_required':
            if outcome.approval_request_id is None:
                return self._move(identifier, State.FAILED, message='Missing approval request reference.')
            return self._move(identifier, State.AWAITING_APPROVAL, **fields)
        if outcome.status in ('blocked', 'failed'):
            return self._move(identifier, State.BLOCKED if outcome.status == 'blocked' else State.FAILED, **fields)
        self._move(identifier, State.VERIFYING, **fields)
        if not outcome.verified or outcome.origin == 'unverified':
            return self._move(identifier, State.FAILED, message='Task outcome lacks verified evidence.')
        return self._move(identifier, State.SUCCEEDED)

    def report(self, identifier):
        mission = self.get(identifier)
        return {'id': mission.id, 'actor': mission.actor, 'route': mission.route,
                'state': mission.state.value, 'message': mission.message,
                'evidence_origin': mission.origin, 'approval_request_id': mission.approval_request_id,
                'history': [state.value for state in mission.history]}
