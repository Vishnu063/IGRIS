"""Owner-approved conversation storage using the existing private Memory backend."""
from contextlib import contextmanager
from uuid import uuid4

from .adapters.contracts import identifier
from .adapters.hermes_chat import chat_text, response_text
from .guardian.policy import Denied
from .memory import Memory


class ConversationBusy(RuntimeError): pass


class ConversationMemory(Memory):
    """Chat data is never policy/approval data. Owner is bound in the database."""
    def __init__(self, path, owner, *, initialize=False):
        super().__init__(path, owner, initialize=initialize)
        with self._db() as db:
            if initialize:
                db.executescript('''
                    CREATE TABLE chat_owner(owner TEXT NOT NULL, schema_version INTEGER NOT NULL);
                    CREATE TABLE conversations(id TEXT PRIMARY KEY, active TEXT, revision INTEGER NOT NULL);
                    CREATE TABLE exchanges(sequence INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
                        conversation TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                        mission_id TEXT NOT NULL, user_text TEXT NOT NULL, assistant_text TEXT,
                        state TEXT NOT NULL, origin TEXT NOT NULL, model_sha256 TEXT, api_calls INTEGER);
                ''')
                db.execute('INSERT INTO chat_owner VALUES (?,1)', (self.owner,))
            row = db.execute('SELECT owner,schema_version FROM chat_owner').fetchone()
            if row is None or row['owner'] != self.owner or row['schema_version'] != 1:
                raise Denied('Conversation database owner/schema mismatch.')

    @contextmanager
    def _db(self):
        with super()._db() as db:
            db.execute('PRAGMA foreign_keys=ON')
            yield db

    def create(self, actor, *, approved=False):
        self._authorize(actor)
        if approved is not True: raise Denied('Explicit conversation storage consent required.')
        ident = uuid4().hex
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT COUNT(*) FROM conversations').fetchone()[0] >= 100:
                raise ValueError('Conversation capacity reached; delete an old session.')
            db.execute('INSERT INTO conversations VALUES (?,NULL,0)', (ident,))
        return ident

    @staticmethod
    def _session(db, conversation):
        identifier(conversation)
        row = db.execute('SELECT active,revision FROM conversations WHERE id=?', (conversation,)).fetchone()
        if row is None: raise KeyError('Conversation unavailable.')
        return row

    @staticmethod
    def _window(db, conversation):
        rows = db.execute("SELECT user_text,assistant_text FROM exchanges WHERE conversation=? AND state='completed' ORDER BY sequence DESC LIMIT 6", (conversation,)).fetchall()
        retained, total = [], 0
        for row in rows:
            size = len((row['user_text']+row['assistant_text']).encode())
            if total+size > 16384: break
            retained.append(row); total += size
        return tuple(item for row in reversed(retained) for item in (('user', row['user_text']), ('assistant', row['assistant_text'])))

    def history(self, actor, conversation):
        self._authorize(actor)
        with self._db() as db:
            self._session(db, conversation)
            return self._window(db, conversation)

    def reserve(self, actor, conversation, mission_id, text):
        self._authorize(actor); identifier(mission_id); chat_text(text)
        request = uuid4().hex
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._session(db, conversation)
            if row['active'] is not None: raise ConversationBusy('Conversation has an unfinished request; review it before retrying.')
            if db.execute('SELECT COUNT(*) FROM exchanges').fetchone()[0] >= 10000:
                raise ValueError('Chat storage capacity reached.')
            window = self._window(db, conversation)
            db.execute('INSERT INTO exchanges(request_id,conversation,mission_id,user_text,state,origin) VALUES (?,?,?,?,?,?)',
                       (request, conversation, mission_id, text, 'pending', 'unverified'))
            db.execute('UPDATE conversations SET active=? WHERE id=?', (request, conversation))
        return request, window

    def complete(self, actor, conversation, request, mission_id, text, model_sha256, api_calls, *, origin):
        self._authorize(actor); identifier(request); identifier(mission_id)
        text = response_text(text)
        # Reuse the typed evidence validator. Simulations remain explicitly labeled.
        from .adapters.hermes_chat import ChatReply
        ChatReply(request, text, model_sha256, api_calls, origin)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._session(db, conversation)
            if row['active'] != request: raise ValueError('Stale conversation completion rejected.')
            cursor = db.execute("UPDATE exchanges SET assistant_text=?,state='completed',origin=?,model_sha256=?,api_calls=? WHERE request_id=? AND conversation=? AND mission_id=? AND state='pending'",
                (text, origin, model_sha256, api_calls, request, conversation, mission_id))
            if cursor.rowcount != 1: raise ValueError('Conversation correlation mismatch.')
            db.execute('UPDATE conversations SET active=NULL,revision=revision+1 WHERE id=?', (conversation,))

    def abort(self, actor, conversation, request):
        self._authorize(actor); identifier(request)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._session(db, conversation)
            if row['active'] != request: return False
            db.execute("UPDATE exchanges SET state='failed',origin='unverified' WHERE request_id=? AND conversation=? AND state='pending'", (request, conversation))
            db.execute('UPDATE conversations SET active=NULL WHERE id=?', (conversation,))
        return True

    def forget(self, actor, conversation):
        self._authorize(actor)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if self._session(db, conversation)['active'] is not None:
                raise ConversationBusy('Stop the unfinished turn before deleting its session.')
            db.execute('DELETE FROM conversations WHERE id=?', (conversation,))

    def sessions(self, actor):
        self._authorize(actor)
        with self._db() as db:
            return tuple(dict(row) for row in db.execute('SELECT id,revision,active FROM conversations ORDER BY rowid DESC LIMIT 100'))
