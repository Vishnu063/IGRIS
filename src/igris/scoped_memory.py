"""Approved SQLite facts, scoped independently of embedding/model metadata."""
import hashlib,json,re
from uuid import uuid4
from .memory import Memory,CATEGORIES,knowledge_text
from .conversations import ConversationMemory
from .guardian.policy import Denied
from .adapters.contracts import identifier

class ScopedFacts(Memory):
    def __init__(self,path,owner,conversations,*,project='igris',initialize=False):
        if type(conversations) is not ConversationMemory or conversations.owner!=owner or type(project) is not str or not re.fullmatch('[a-z][a-z0-9_-]{0,40}',project):raise Denied('Trusted owner, conversations and project required.')
        self.conversations,self.project=conversations,project
        super().__init__(path,owner,initialize=initialize)
        with self._db() as db:
            if initialize:
                db.executescript('CREATE TABLE facts_owner(owner TEXT NOT NULL,version INTEGER NOT NULL);CREATE TABLE fact_scopes(id TEXT PRIMARY KEY,conversation TEXT NOT NULL,project TEXT NOT NULL);')
                db.execute('INSERT INTO facts_owner VALUES(?,1)',(owner,))
            row=db.execute('SELECT owner,version FROM facts_owner').fetchone()
            if row is None or row['owner']!=owner or row['version']!=1:raise Denied('Facts owner/schema mismatch.')
    def _scope(self,actor,conversation):
        self._authorize(actor);identifier(conversation);self.conversations.history(actor,conversation)
    def token(self,actor,conversation):
        self._scope(actor,conversation)
        return hashlib.sha256(json.dumps([self.owner,self.project,conversation,str(self.path)],separators=(',',':')).encode()).hexdigest()
    def review(self,actor,conversation):
        self._scope(actor,conversation)
        with self._db() as db:
            return [dict(row) for row in db.execute('SELECT k.* FROM knowledge k JOIN fact_scopes s ON s.id=k.id WHERE s.conversation=? AND s.project=? ORDER BY k.id',(conversation,self.project))]
    def get(self,actor,conversation,ident):
        identifier(ident)
        for row in self.review(actor,conversation):
            if row['id']==ident:return row
        raise KeyError('Fact unavailable in this conversation/project.')
    def save(self,actor,conversation,category,text,*,classification='assumption',evidence='',approved=False):
        self._scope(actor,conversation)
        if approved is not True or type(category) is not str or category not in CATEGORIES or type(classification) is not str or classification not in ('verified_fact','assumption') or type(evidence) is not str:raise Denied('Explicit approved supported fact required.')
        knowledge_text(text,512)
        if classification=='verified_fact' or evidence:knowledge_text(evidence,512)
        ident=uuid4().hex
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0]>=10000 or db.execute('SELECT COUNT(*) FROM fact_scopes WHERE conversation=? AND project=?',(conversation,self.project)).fetchone()[0]>=1000:raise Denied('Fact capacity reached.')
            db.execute('INSERT INTO knowledge VALUES(?,?,?,?,?,1)',(ident,category,text,classification,evidence))
            db.execute('INSERT INTO fact_scopes VALUES(?,?,?)',(ident,conversation,self.project))
        return self.get(actor,conversation,ident)
    def correct(self,actor,conversation,ident,revision,text,*,approved=False):
        self.get(actor,conversation,ident);knowledge_text(text,512)
        if approved is not True or type(revision) is not int:raise Denied('Approved revision-bound correction required.')
        super().correct(actor,ident,revision,text,approved=True)
        return self.get(actor,conversation,ident)
    def delete(self,actor,conversation,ident,revision,*,approved=False):
        self._scope(actor,conversation);identifier(ident)
        if approved is not True or type(revision) is not int:raise Denied('Explicit revision-bound deletion required.')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT k.revision FROM knowledge k JOIN fact_scopes s ON s.id=k.id WHERE k.id=? AND s.conversation=? AND s.project=?',(ident,conversation,self.project)).fetchone()
            if row is None or row['revision']!=revision:raise Denied('Fact scope/revision mismatch.')
            db.execute('DELETE FROM fact_scopes WHERE id=?',(ident,));db.execute('DELETE FROM knowledge WHERE id=?',(ident,))
    def revision_digest(self,actor):
        self._authorize(actor)
        with self._db() as db:rows=[dict(row) for row in db.execute('SELECT k.id,k.revision,s.project,s.conversation FROM knowledge k JOIN fact_scopes s ON s.id=k.id ORDER BY k.id')]
        return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
