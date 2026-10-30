"""Immutable, explicit capabilities from trusted operator configuration only."""
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType


class Denied(PermissionError):
    """Sanitized denial; never echo action arguments."""


class Permission(str, Enum):
    READ = 'read'
    FILE_MODIFY = 'file_modify'
    TERMINAL = 'terminal'
    GIT = 'git'
    CLOUD = 'cloud'
    DEPLOY = 'deploy'
    FINANCIAL = 'financial'
    COMMUNICATE = 'communicate'


OPERATIONS = MappingProxyType({
    'file.read': Permission.READ,
    'file.create': Permission.FILE_MODIFY,
    'python.version': Permission.TERMINAL,
    'git.status': Permission.GIT,
    'cloud.inspect': Permission.CLOUD,
    'deployment.production': Permission.DEPLOY,
    'financial.transaction': Permission.FINANCIAL,
    'message.send': Permission.COMMUNICATE,
    'service.paid': Permission.FINANCIAL,
    'file.delete': Permission.FILE_MODIFY,
    'file.sensitive_change': Permission.FILE_MODIFY,
    'scope.external_change': Permission.FILE_MODIFY,
})


@dataclass(frozen=True)
class Policy:
    actor: str
    permissions: frozenset[Permission] = frozenset()
    version: str = '1'

    def __post_init__(self):
        if (type(self.actor) is not str or not self.actor or len(self.actor) > 80
                or not self.actor.isascii() or not all(c.isalnum() or c in '-_.' for c in self.actor)):
            raise Denied('Invalid trusted actor.')
        if (type(self.permissions) is not frozenset
                or any(type(p) is not Permission for p in self.permissions)):
            raise Denied('Invalid trusted permissions.')
        if type(self.version) is not str or self.version != '1':
            raise Denied('Unsupported policy version.')

    def require(self, operation: str) -> None:
        if type(operation) is not str or operation not in OPERATIONS:
            raise Denied('Unknown operation.')
        if OPERATIONS[operation] not in self.permissions:
            raise Denied('Permission denied.')
