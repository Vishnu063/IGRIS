"""Owner-approved logical chat/fact snapshots; never restores execution authority."""
import hashlib,json,re,os
from contextlib import nullcontext
from pathlib import Path
from uuid import uuid4
from .conversations import ConversationMemory,ConversationBusy
from .scoped_memory import ScopedFacts
from .memory import private_file,knowledge_text,CATEGORIES
from .adapters.hermes_chat import ChatRequest,ChatReply,chat_text
from .adapters.contracts import identifier
from .guardian.approvals import ApprovalStore
from .guardian.policy import Denied
from .guardian.readonly import unique
MAX_BYTES=16*1024*1024

def validate(data,actor):
 if type(data) is not dict or set(data)!={'format','owner','conversations','facts'} or data['format']!='igris_chat_data_only_v1' or data['owner']!=actor:raise Denied('Owner-bound data-only snapshot required.')
 if type(data['conversations']) is not list or len(data['conversations'])>100 or type(data['facts']) is not list or len(data['facts'])>10000:raise Denied('Snapshot capacity exceeded.')
 seen=set();requests=set();facts=set();total=0
 for conversation in data['conversations']:
  if type(conversation) is not dict or set(conversation)!={'id','revision','exchanges'}:raise Denied('Invalid conversation snapshot.')
  ident=identifier(conversation['id'])
  if ident in seen or type(conversation['revision']) is not int or conversation['revision']<0 or type(conversation['exchanges']) is not list:raise Denied('Invalid or duplicate conversation.')
  seen.add(ident)
  for row in conversation['exchanges']:
   if type(row) is not dict or set(row)!={'request_id','mission_id','user_text','assistant_text','origin','model_sha256','api_calls'}:raise Denied('Only completed dialogue data supported.')
   request=identifier(row['request_id']);identifier(row['mission_id']);chat_text(row['user_text']);ChatReply(request,row['assistant_text'],row['model_sha256'],row['api_calls'],row['origin'])
   if request in requests:raise Denied('Duplicate exchange.')
   requests.add(request);total+=1
   if total>10000:raise Denied('Exchange capacity exceeded.')
 counts={}
 for row in data['facts']:
  if type(row) is not dict or set(row)!={'id','category','text','classification','evidence','revision','conversation','project'}:raise Denied('Only scoped fact data supported.')
  ident=identifier(row['id']);conversation=identifier(row['conversation']);project=row['project']
  if ident in facts or conversation not in seen or type(project) is not str or not re.fullmatch('[a-z][a-z0-9_-]{0,40}',project) or row['category'] not in CATEGORIES or row['classification'] not in ('verified_fact','assumption') or type(row['revision']) is not int or row['revision']<1 or type(row['evidence']) is not str:raise Denied('Invalid scoped fact.')
  facts.add(ident);knowledge_text(row['text'],512)
  if row['evidence'] or row['classification']=='verified_fact':knowledge_text(row['evidence'],512)
  key=(conversation,project);counts[key]=counts.get(key,0)+1
  if counts[key]>1000:raise Denied('Scoped fact capacity exceeded.')
 return data

def create_snapshot(destination,*,memory,facts,actor,approved=False):
 if approved is not True or type(memory) is not ConversationMemory or memory.owner!=actor or (facts is not None and (type(facts) is not ScopedFacts or facts.conversations.path!=memory.path or facts.owner!=actor)):raise Denied('Explicit trusted owner data-backup approval required.')
 with memory._db() as chat:
  chat.execute('BEGIN IMMEDIATE')
  if chat.execute('SELECT 1 FROM conversations WHERE active IS NOT NULL').fetchone() or chat.execute("SELECT 1 FROM exchanges WHERE state='pending'").fetchone():raise ConversationBusy('Stop or recover pending requests before taking a backup.')
  with (facts._db() if facts is not None else nullcontext(None)) as knowledge:
   if knowledge is not None:knowledge.execute('BEGIN IMMEDIATE')
   sessions=[]
   for row in chat.execute('SELECT id,revision FROM conversations ORDER BY rowid'):
    exchanges=[dict(e) for e in chat.execute("SELECT request_id,mission_id,user_text,assistant_text,origin,model_sha256,api_calls FROM exchanges WHERE conversation=? AND state='completed' ORDER BY sequence",(row['id'],))]
    sessions.append(dict(row,exchanges=exchanges))
   session_ids={row['id'] for row in sessions}
   fact_rows=[dict(row) for row in knowledge.execute('SELECT k.*,s.conversation,s.project FROM knowledge k JOIN fact_scopes s ON s.id=k.id ORDER BY k.id') if row['conversation'] in session_ids] if knowledge is not None else []
   data=validate({'format':'igris_chat_data_only_v1','owner':actor,'conversations':sessions,'facts':fact_rows},actor)
 raw=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 if len(raw)>MAX_BYTES:raise Denied('Snapshot size exceeded.')
 path=private_file(destination,create=True);path.write_bytes(raw)
 return {'sha256':hashlib.sha256(raw).hexdigest(),'conversations':len(sessions),'facts':len(fact_rows),'credentials_included':False,'approvals_included':False,'automatic_execution':False}

def restore_snapshot(source,destination,*,expected_sha256,actor,approved=False):
 if approved is not True or type(expected_sha256) is not str or not re.fullmatch('[a-f0-9]{64}',expected_sha256):raise Denied('Exact owner-approved snapshot digest required.')
 path=private_file(source)
 with path.open('rb') as stream:raw=stream.read(MAX_BYTES+1)
 if len(raw)>MAX_BYTES or hashlib.sha256(raw).hexdigest()!=expected_sha256:raise Denied('Snapshot identity mismatch.')
 data=validate(json.loads(raw,object_pairs_hook=unique),actor)
 target=Path(destination).absolute();parent=target.parent
 if parent.resolve(strict=True)!=parent or parent.stat().st_uid!=os.getuid() or parent.stat().st_mode&0o077:raise Denied('Private canonical restore parent required.')
 target.mkdir(mode=0o700) # Never overwrite live state, index, credentials or approvals.
 memory=ConversationMemory(target/'chat.sqlite3',actor,initialize=True);facts=ScopedFacts(target/'facts.sqlite3',actor,memory,initialize=True)
 with memory._db() as chat:
  chat.execute('BEGIN IMMEDIATE')
  for row in data['conversations']:
   chat.execute('INSERT INTO conversations VALUES(?,NULL,?)',(row['id'],row['revision']))
   for exchange in row['exchanges']:
    chat.execute("INSERT INTO exchanges(request_id,conversation,mission_id,user_text,assistant_text,state,origin,model_sha256,api_calls) VALUES(?,?,?,?,?,'completed',?,?,?)",(exchange['request_id'],row['id'],exchange['mission_id'],exchange['user_text'],exchange['assistant_text'],exchange['origin'],exchange['model_sha256'],exchange['api_calls']))
 with facts._db() as db:
  db.execute('BEGIN IMMEDIATE')
  for row in data['facts']:
   db.execute('INSERT INTO knowledge VALUES(?,?,?,?,?,?)',tuple(row[k] for k in ('id','category','text','classification','evidence','revision')));db.execute('INSERT INTO fact_scopes VALUES(?,?,?)',(row['id'],row['conversation'],row['project']))
 store=ApprovalStore(target/'guardian.sqlite3',initialize=True);store.enable_tool_audit()
 return {'restored':True,'conversations':len(data['conversations']),'facts':len(data['facts']),'approvals_restored':0,'pending_requests_restored':0,'credentials_restored':False,'execution_resumed':False,'semantic_index_restored':False}
