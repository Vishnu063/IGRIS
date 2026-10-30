"""Private operator-approved SQLite knowledge; data can never grant permissions."""
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import stat
from uuid import uuid4

from .guardian.policy import Denied, Policy
from .guardian.secrets import redact

CATEGORIES = frozenset({'project', 'preference', 'incident', 'solution'})


def private_file(path, *, create=False):
    path = Path(path).absolute()
    parent = path.parent
    if parent.resolve(strict=True) != parent or parent.stat().st_uid != os.getuid() or stat.S_IMODE(parent.stat().st_mode) & 0o077:
        raise Denied('Storage parent must be private and trusted.')
    if create:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(fd)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise Denied('Storage file must be private and trusted.')
    return path


def knowledge_text(value, maximum=4096):
    if type(value) is not str or not value.strip() or len(value) > maximum or redact(value) != value:
        raise ValueError('Sensitive or invalid knowledge rejected.')
    return value


class Memory:
    """Owner identity is trusted startup configuration, never an agent argument.

    Actor on each call must come from trusted authentication. Python objects and
    same-user processes are not isolation boundaries. No rule/evaluator exists.
    """
    def __init__(self, path, owner, *, initialize=False):
        self.owner = Policy(owner).actor
        self.path = private_file(path, create=initialize)
        if initialize:
            with self._db() as db:
                db.execute('CREATE TABLE knowledge (id TEXT PRIMARY KEY, category TEXT, text TEXT, classification TEXT, evidence TEXT, revision INTEGER)')

    @contextmanager
    def _db(self):
        private_file(self.path)
        db = sqlite3.connect(self.path, timeout=1)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA secure_delete=ON')
        try:
            with db: yield db
        finally: db.close()

    def _authorize(self, actor):
        if actor != self.owner: raise Denied('Memory access denied.')

    def put(self, actor, category, text, *, classification='assumption', evidence='', approved=False):
        self._authorize(actor)
        if approved is not True or category not in CATEGORIES or classification not in ('assumption', 'verified_fact'):
            raise Denied('Approved supported knowledge required.')
        knowledge_text(text)
        if classification == 'verified_fact': knowledge_text(evidence, 512)
        elif evidence: knowledge_text(evidence, 512)
        identifier = uuid4().hex
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0] >= 10000:
                raise ValueError('Memory capacity reached.')
            db.execute('INSERT INTO knowledge VALUES (?,?,?,?,?,1)', (identifier, category, text, classification, evidence))
        return identifier

    def get(self, actor, identifier):
        self._authorize(actor)
        with self._db() as db: row = db.execute('SELECT * FROM knowledge WHERE id=?', (identifier,)).fetchone()
        if row is None: raise KeyError('Knowledge unavailable.')
        return dict(row)

    def correct(self, actor, identifier, revision, text, *, approved=False):
        self._authorize(actor)
        if approved is not True or type(revision) is not int: raise Denied('Approved correction required.')
        knowledge_text(text)
        with self._db() as db:
            # A correction invalidates previous factual evidence until re-reviewed.
            result = db.execute("UPDATE knowledge SET text=?, classification='assumption', evidence='', revision=revision+1 WHERE id=? AND revision=?", (text, identifier, revision))
            if result.rowcount != 1: raise ValueError('Stale or missing knowledge.')

    def delete(self, actor, identifier):
        self._authorize(actor)
        with self._db() as db: db.execute('DELETE FROM knowledge WHERE id=?', (identifier,))

    def backup(self, actor, destination):
        self._authorize(actor)
        target = private_file(destination, create=True)
        out = sqlite3.connect(target)
        try:
            with self._db() as db: db.backup(out)
        finally: out.close()
        return target
