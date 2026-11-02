"""Real Hermes context restored as data; genuine old Guardian approval cannot resume."""
import hashlib,json,sys,tempfile
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.chat_backup import create_snapshot,restore_snapshot
from igris.chat import ChatService
from igris.conversations import ConversationMemory
from igris.scoped_memory import ScopedFacts
from igris.guardian.tools import GuardianTools
from igris.guardian.review import ApprovalReviews
from igris.adapters.hermes_chat import DockerHermesAdapter
with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='backup-live-') as folder:
 root=Path(folder);source=root/'source';source.mkdir(mode=0o700);memory=ConversationMemory(source/'chat.sqlite3','owner',initialize=True);conversation=memory.create('owner',approved=True);facts=ScopedFacts(source/'facts.sqlite3','owner',memory,initialize=True);chat=ChatService('owner',memory,DockerHermesAdapter())
 first=chat.ask('owner',conversation,'My project codename is CedarLynx. Reply only OK.');assert first['saved'];chat.close()
 fact=facts.save('owner',conversation,'project','The project region is Mumbai.',approved=True)
 workspace=root/'workspace';workspace.mkdir(mode=0o700);config=root/'tools.json';config.write_text(json.dumps({'version':1,'workspace':str(workspace),'allowed_operations':['get_current_time'],'directories':[],'files':[],'approval_required':['get_current_time']}));config.chmod(0o600)
 tools=GuardianTools('owner',config,source/'guardian.sqlite3');reviews=ApprovalReviews(tools);request,mission=uuid4().hex,uuid4().hex;proposal='{"operation":"get_current_time","arguments":{}}';prepared,review=reviews.prepare('owner',request,mission,proposal);reviews.decide('owner',mission,approve=True,reviewed_digest=review.digest)
 with tools.store._db() as db:assert tuple(db.execute('SELECT status,used FROM approvals').fetchone())==('approved',0)
 proof=create_snapshot(root/'snapshot.json',memory=memory,facts=facts,actor='owner',approved=True);restored=root/'restored';result=restore_snapshot(root/'snapshot.json',restored,expected_sha256=proof['sha256'],actor='owner',approved=True)
 imported=ConversationMemory(restored/'chat.sqlite3','owner');imported_facts=ScopedFacts(restored/'facts.sqlite3','owner',imported);assert imported.history('owner',conversation)==memory.history('owner',conversation) and imported_facts.get('owner',conversation,fact['id'])==fact
 restored_tools=GuardianTools('owner',config,restored/'guardian.sqlite3');denial=restored_tools.run(request,mission,proposal,approval_id=review.id);assert not denial['ok']
 with restored_tools.store._db() as db:assert db.execute('SELECT COUNT(*) FROM approvals').fetchone()[0]==0
 recovered=ChatService('owner',imported,DockerHermesAdapter());answer=recovered.ask('owner',conversation,'What is my project codename? Reply with only the name.');assert answer['saved'] and 'cedarlynx' in answer['reply'].casefold();recovered.close();reviews.finish('owner',mission)
 artifact={'status':'PASS','actual_real_chat_before_backup':first['reply'],'actual_real_recall_after_restore':answer['reply'],'data_restored':result,'old_approved_unused_action_denied':not denial['ok'],'snapshot_sha256':proof['sha256'],'facts_preserved':True,'approvals_restored':0,'mocked':False,'owner_inputs':'Explicit synthetic owner fixture data and decisions.','source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['src/igris/chat_backup.py','scripts/test_chat_backup_live.py']}}
(ROOT/'docs/validation/chat-backup-live.json').write_text(json.dumps(artifact,indent=2)+'\n');print(json.dumps(artifact))
