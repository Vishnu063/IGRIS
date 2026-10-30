"""Trusted-only approval issuance and atomic action-bound single-use consumption."""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import time
from types import MappingProxyType

from .policy import Denied, Policy

RISK_CATEGORIES = MappingProxyType({
    'deployment.production': 'production_deployment',
    'file.delete': 'destructive_operation',
    'file.sensitive_change': 'sensitive_file_change',
    'message.send': 'external_communication',
    'service.paid': 'paid_service',
    'financial.transaction': 'financial_transaction',
    'scope.external_change': 'outside_scope',
    'file.create': 'file_creation',
})


def action_record(policy: Policy, workspace: Path, request: dict, environment='development'):
    if type(request) is not dict or set(request) != {'operation', 'arguments'}:
        raise Denied('Invalid approval action.')
    policy.require(request['operation'])
    if type(request['arguments']) is not dict or request['operation'] not in RISK_CATEGORIES:
        raise Denied('Unsupported approval action.')
    if environment not in ('development', 'test', 'production'):
        raise Denied('Invalid trusted environment.')
    try:
        serialized = json.dumps(request, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if len(serialized.encode()) > 16384:
            raise Denied('Approval action too large.')
        root = str(Path(workspace).resolve(strict=True))
        bound = {'actor': policy.actor, 'workspace': root, 'environment': environment,
                 'policy_version': policy.version, 'action': request}
        canonical = json.dumps(bound, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError, OSError, RecursionError):
        raise Denied('Invalid approval action.') from None
    return hashlib.sha256(canonical.encode()).hexdigest(), root


class ApprovalStore:
    """Protected operator-owned database; never hand this object/path to agents.

    Clock injection is for trusted tests only. No issuer network/request API exists.
    SQLite is not protection against same-user tampering or database rollback.
    """
    def __init__(self, path: Path, *, initialize=False, clock=time.time):
        self.path = Path(path).absolute()
        self.clock = clock
        parent = self.path.parent
        if parent.resolve(strict=True) != parent or parent.stat().st_uid != os.getuid() or stat.S_IMODE(parent.stat().st_mode) & 0o077:
            raise Denied('Approval directory must be private and trusted.')
        if initialize:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.close(fd)
        self._validate_file()
        if initialize:
            with self._db() as db:
                db.executescript('''
                    CREATE TABLE approvals (
                      id TEXT PRIMARY KEY, digest TEXT NOT NULL, actor TEXT NOT NULL,
                      operation TEXT NOT NULL, summary TEXT NOT NULL,
                      expires REAL NOT NULL, status TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0);
                    CREATE TABLE audit (
                      sequence INTEGER PRIMARY KEY, at REAL NOT NULL, approval_id TEXT,
                      actor TEXT NOT NULL, operation TEXT NOT NULL,
                      digest TEXT NOT NULL, event TEXT NOT NULL);
                ''')

    def _validate_file(self):
        info = self.path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise Denied('Approval database must be private and trusted.')

    @contextmanager
    def _db(self):
        self._validate_file()
        db = sqlite3.connect(self.path, timeout=0.5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def _now(self):
        now = self.clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            raise Denied('Trusted clock unavailable.')
        return now

    def request(self, policy, workspace, action, *, ttl_seconds=300, environment='development'):
        digest, root = action_record(policy, workspace, action, environment)
        if type(ttl_seconds) not in (int, float) or not math.isfinite(ttl_seconds) or not 0 < ttl_seconds <= 3600:
            raise Denied('Invalid approval lifetime.')
        # No body/secret values persisted: owner reviews the exact original action
        # locally and compares its digest; this summary is not a substitute.
        summary = json.dumps({'category': RISK_CATEGORIES[action['operation']], 'actor': policy.actor,
                              'workspace': root, 'environment': environment,
                              'policy_version': policy.version, 'action_sha256': digest})
        identifier = secrets.token_urlsafe(24)
        now = self._now()
        with self._db() as db:
            db.execute('INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, 0)',
                       (identifier, digest, policy.actor, action['operation'], summary, now + ttl_seconds, 'pending'))
            db.execute('INSERT INTO audit(at,approval_id,actor,operation,digest,event) VALUES (?,?,?,?,?,?)',
                       (now, identifier, policy.actor, action['operation'], digest, 'requested'))
        return {'id': identifier, 'action_sha256': digest, 'summary': json.loads(summary),
                'expires_at': now + ttl_seconds, 'status': 'pending'}

    def decide(self, identifier, *, approve: bool, reviewed_digest: str):
        """Trusted owner decision only; requires the reviewed exact action digest."""
        if type(approve) is not bool or type(identifier) is not str or type(reviewed_digest) is not str:
            raise Denied('Invalid approval decision.')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            now = self._now()
            row = db.execute('SELECT digest,actor,operation,expires,status,used FROM approvals WHERE id=?', (identifier,)).fetchone()
            if not row or row[0] != reviewed_digest or row[3] <= now or row[4] != 'pending' or row[5]:
                raise Denied('Approval decision rejected.')
            status = 'approved' if approve else 'denied'
            db.execute('UPDATE approvals SET status=? WHERE id=?', (status, identifier))
            db.execute('INSERT INTO audit(at,approval_id,actor,operation,digest,event) VALUES (?,?,?,?,?,?)',
                       (now, identifier, row[1], row[2], row[0], status))

    def consume(self, identifier, policy, workspace, action, *, environment='development'):
        digest, _ = action_record(policy, workspace, action, environment)
        if type(identifier) is not str or len(identifier) != 32:
            raise Denied('Approval required.')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            now = self._now()
            cursor = db.execute('''UPDATE approvals SET used=1 WHERE id=? AND digest=?
                                   AND actor=? AND status='approved' AND used=0 AND expires>?''',
                                (identifier, digest, policy.actor, now))
            allowed = cursor.rowcount == 1
            db.execute('INSERT INTO audit(at,approval_id,actor,operation,digest,event) VALUES (?,?,?,?,?,?)',
                       (now, identifier, policy.actor, action['operation'], digest, 'consumed' if allowed else 'rejected'))
        if not allowed:
            raise Denied('Approval missing, denied, expired, used or mismatched.')
        return digest

    def outcome(self, identifier, policy, operation, digest, *, succeeded):
        with self._db() as db:
            db.execute('INSERT INTO audit(at,approval_id,actor,operation,digest,event) VALUES (?,?,?,?,?,?)',
                       (self._now(), identifier, policy.actor, operation, digest,
                        'execution_succeeded' if succeeded else 'execution_failed'))
