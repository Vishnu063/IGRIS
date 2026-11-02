"""One foreground reservation across entry points. Scheduling never grants permission."""
from contextlib import contextmanager
from datetime import datetime,timezone
import fcntl,hashlib,json,os,re,sqlite3,threading
from pathlib import Path
from uuid import uuid4
from .guardian.policy import Denied,Policy
from .memory import private_file
from .adapters.contracts import identifier
ROOT=Path(__file__).resolve().parents[2]
ACTIVE=frozenset({'starting','running','waiting_for_approval','stopping'})
TERMINAL=frozenset({'completed','failed','cancelled'})

def stamp():return datetime.now(timezone.utc).isoformat()
def fingerprint(kind,data):
 raw=json.dumps([kind,data],sort_keys=True,separators=(',',':'),allow_nan=False).encode()
 if len(raw)>32768:raise Denied('Bounded task identity required.')
 return hashlib.sha256(raw).hexdigest()
class ForegroundBusy(Denied):pass
class TaskAlreadyRecorded(Denied):
 def __init__(self,record):super().__init__('Task already recorded; execution will not be repeated.');self.record=record

class Cancellation:
 def __init__(self,*signals):self.signals=tuple(s for s in signals if s is not None)
 def is_set(self):return any(s.is_set() for s in self.signals)

class Foreground:
 def __init__(self,directory=None):
  self.directory=Path(directory or ROOT/'runtime/foreground').absolute();self.directory.mkdir(mode=0o700,parents=True,exist_ok=True)
  self.path=self.directory/'tasks.sqlite3';self.lockfile=self.directory/'foreground.lock';self.lock=threading.RLock();self.active=None
  for path in (self.path,self.lockfile):
   try:private_file(path,create=True)
   except FileExistsError:private_file(path)
  with self.db() as db:
   db.execute('CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, actor TEXT NOT NULL, fingerprint TEXT NOT NULL, type TEXT NOT NULL, status TEXT NOT NULL, started TEXT NOT NULL, completed TEXT, outcome TEXT NOT NULL, actions TEXT NOT NULL, verified TEXT NOT NULL, errors TEXT NOT NULL, cleanup TEXT NOT NULL)')
 @contextmanager
 def db(self):
  private_file(self.path);db=sqlite3.connect(self.path,timeout=1);db.row_factory=sqlite3.Row;db.execute('PRAGMA trusted_schema=OFF')
  try:
   with db:yield db
  finally:db.close()
 @staticmethod
 def _view(row):
  return {'task_id':row['id'],'task_type':row['type'],'status':row['status'],'started_at':row['started'],'completed_at':row['completed'],'outcome':row['outcome'],'actions_attempted':json.loads(row['actions']),'verified_outcomes':json.loads(row['verified']),'errors_or_limitations':json.loads(row['errors']),'cleanup_status':row['cleanup']}
 def lookup(self,actor,task_id,*,identity=None):
  Policy(actor);identifier(task_id)
  with self.db() as db:row=db.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
  if row is None:return None
  if row['actor']!=actor or identity is not None and row['fingerprint']!=identity:raise Denied('Task identity or owner mismatch.')
  return self._view(row)
 def begin(self,actor,kind,*,task_id=None,identity=None,cancel=None):
  Policy(actor);tid=task_id or uuid4().hex;identifier(tid)
  if type(kind) is not str or not re.fullmatch('[a-z][a-z0-9_.-]{0,63}',kind):raise Denied('Registered task type required.')
  if cancel is not None and not isinstance(cancel,threading.Event):raise Denied('Trusted task cancellation event required.')
  identity=identity or fingerprint(kind,{})
  if type(identity) is not str or not re.fullmatch('[a-f0-9]{64}',identity):raise Denied('Exact task fingerprint required.')
  prior=self.lookup(actor,tid,identity=identity)
  if prior:raise TaskAlreadyRecorded(prior)
  with self.lock:
   if self.active is not None:raise ForegroundBusy('One foreground task is already reserved.')
   handle=self.lockfile.open('rb')
   try:
    try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ForegroundBusy('Another IGRIS entry point owns the foreground task.') from None
    with self.db() as db:
     db.execute('BEGIN IMMEDIATE')
     prior=db.execute('SELECT * FROM tasks WHERE id=?',(tid,)).fetchone()
     if prior:
      if prior['actor']!=actor or prior['fingerprint']!=identity:raise Denied('Task identity mismatch.')
      raise TaskAlreadyRecorded(self._view(prior))
     if db.execute("SELECT 1 FROM tasks WHERE status IN ('starting','running','waiting_for_approval','stopping') OR cleanup='unverified' LIMIT 1").fetchone():raise ForegroundBusy('An interrupted task requires explicit cleanup review; no automatic replay.')
     if db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]>=10000:raise ForegroundBusy('Task journal capacity reached; owner archival required.')
     db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,NULL,?,?,?,?,?)',(tid,actor,identity,kind,'starting',stamp(),'not_verified','[]','[]','[]','not_started'))
    lease=TaskLease(self,handle,tid,actor,cancel);self.active=lease;return lease
   except BaseException:handle.close();raise
 def record_cancelled(self,actor,kind,task_id,identity):
  Policy(actor);identifier(task_id)
  if not re.fullmatch('[a-f0-9]{64}',identity) or not re.fullmatch('[a-z][a-z0-9_.-]{0,63}',kind):raise Denied('Typed cancelled task required.')
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
   if row:raise Denied('Task already began; cancel its live lease instead.')
   now=stamp();db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(task_id,actor,identity,kind,'cancelled',now,now,'cancelled','[]','[]',json.dumps(['Cancelled before execution; no worker started.']),'not_started'))
  return self.lookup(actor,task_id)
 def block_cleanup(self,actor,kind):
  lease_id=uuid4().hex;Policy(actor)
  with self.db() as db:
   now=stamp();db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(lease_id,actor,fingerprint(kind,{}),kind,'failed',now,now,'not_verified','[]','[]',json.dumps(['Owned component cleanup unverified; owner review required.']),'unverified'))
  return self.lookup(actor,lease_id)
 def snapshot(self,actor):
  Policy(actor)
  with self.db() as db:
   row=db.execute("SELECT * FROM tasks WHERE actor=? ORDER BY rowid DESC LIMIT 1",(actor,)).fetchone()
   active=db.execute("SELECT * FROM tasks WHERE actor=? AND status IN ('starting','running','waiting_for_approval','stopping') ORDER BY rowid DESC LIMIT 1",(actor,)).fetchone()
   dirty=db.execute("SELECT 1 FROM tasks WHERE actor=? AND cleanup='unverified' LIMIT 1",(actor,)).fetchone()
  return {'mode':'single_task','state':active['status'] if active else 'idle','active':self._view(active) if active else None,'last_result':self._view(row) if row else None,'recovery_required':bool(active and (self.active is None or self.active.task_id!=active['id']) or dirty)}
 def request_cancel(self,actor,task_id):
  with self.lock:
   lease=self.active
   if lease is None or lease.actor!=actor or lease.task_id!=task_id:raise Denied('Only the current owned task can be cancelled; restart cannot resume it.')
   lease.cancel.set();lease.transition('stopping');return self.lookup(actor,task_id)
 def recover(self,actor,cleanup_check):
  """Trusted owner maintenance only; caller must independently verify owned cleanup."""
  Policy(actor)
  if not callable(cleanup_check):raise Denied('Explicit verified cleanup inspection required.')
  with self.lock,self.lockfile.open('rb') as handle:
   if self.active:raise ForegroundBusy('Cannot recover a live task.')
   try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:raise ForegroundBusy('Another entry point remains active.') from None
   if cleanup_check() is not True:raise Denied('Cleanup not verified; task remains blocked.')
   with self.db() as db:
    db.execute("UPDATE tasks SET status='cancelled',completed=?,outcome='cancelled',cleanup='verified',errors=? WHERE actor=? AND (status IN ('starting','running','waiting_for_approval','stopping') OR cleanup='unverified')",(stamp(),json.dumps(['Owner verified cleanup after interruption; execution not resumed.']),actor))

class TaskLease:
 def __init__(self,owner,handle,task_id,actor,cancel):self.owner=owner;self.handle=handle;self.task_id=task_id;self.actor=actor;self.cancel=cancel if cancel is not None else threading.Event();self.closed=False
 def transition(self,status,*,action=None):
  if status not in ACTIVE:raise Denied('Invalid active task state.')
  with self.owner.lock:
   if self.closed or self.owner.active is not self:raise Denied('Task lease no longer active.')
   with self.owner.db() as db:
    row=db.execute('SELECT status,actions FROM tasks WHERE id=?',(self.task_id,)).fetchone()
    transitions={'starting':{'starting','running','waiting_for_approval','stopping'},'running':{'running','waiting_for_approval','stopping'},'waiting_for_approval':{'running','stopping'},'stopping':{'stopping'}}
    if status not in transitions.get(row['status'],set()):raise Denied('Invalid foreground task transition.')
    actions=json.loads(row['actions'])
    if action:
     if not re.fullmatch('[a-z][a-z0-9_.-]{0,63}',action):raise Denied('Typed action name required.')
     if len(actions)>=32:raise Denied('Action history capacity reached.')
     actions.append(action)
    db.execute('UPDATE tasks SET status=?,actions=?,cleanup=? WHERE id=?',(status,json.dumps(actions),'pending',self.task_id))
 def finish(self,*,verified=False,cleanup=True,error=None,partial=False,retained=False):
  with self.owner.lock:
   if self.closed:return self.owner.lookup(self.actor,self.task_id)
   cancelled=self.cancel.is_set();status='cancelled' if cancelled else 'completed' if verified and cleanup else 'failed'
   outcome='cancelled' if cancelled else 'partially_completed' if partial or verified and not cleanup else 'successfully_completed' if verified else 'failed' if error else 'not_verified'
   errors=[error] if error else []
   if any(type(e) is not str or not re.fullmatch('[A-Za-z][A-Za-z0-9_. -]{0,120}',e) for e in errors):errors=['Task failed; private diagnostic omitted.']
   try:
    with self.owner.db() as db:db.execute('UPDATE tasks SET status=?,completed=?,outcome=?,verified=?,errors=?,cleanup=? WHERE id=?',(status,stamp(),outcome,json.dumps(['Executor contract and outcome verified.'] if verified else []),json.dumps(errors),'retained_authorized' if retained and cleanup else 'verified' if cleanup else 'unverified',self.task_id))
   finally:self.closed=True;self.owner.active=None;self.handle.close()
   return self.owner.lookup(self.actor,self.task_id)

_default=None
_default_lock=threading.Lock()
def default_foreground():
 global _default
 with _default_lock:
  if _default is None:_default=Foreground()
  return _default
