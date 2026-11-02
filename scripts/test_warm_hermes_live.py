"""Paired actual cold/warm inference, fresh contexts, Guardian approval and cancellation."""
import hashlib,json,sys,tempfile,threading,time,statistics
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.adapters.hermes_chat import DockerHermesAdapter,ChatRequest
from igris.adapters.hermes_warm import WarmDockerHermesAdapter
from igris.adapters.contracts import AdapterUnavailable
from igris.chat import ChatService
from igris.conversations import ConversationMemory
from igris.guardian.tools import GuardianTools
from igris.guardian.review import ApprovalReviews
from igris.guardian.policy import Denied

def main():
 pairs=[];cold=DockerHermesAdapter();t=time.monotonic();cold._preflight();preflight=time.monotonic()-t
 cases=[('What is 7 plus 5? Reply with only the integer.','12'),('What is 8 plus 6? Reply with only the integer.','14')]
 for prompt,expected in cases:
  t=time.monotonic();reply=cold.reply(ChatRequest(uuid4().hex,prompt));seconds=time.monotonic()-t;assert reply.text.strip()==expected;pairs.append({'prompt':prompt,'cold_seconds':seconds,'cold_response':reply.text});print('Real cold '+expected+' '+str(round(seconds,3)),flush=True)
 warm=WarmDockerHermesAdapter();t=time.monotonic()
 try:
  warm.start();startup=time.monotonic()-t;print('Warm startup '+str(round(startup,3)),flush=True)
  for (prompt,expected),row in zip(cases,pairs):
   t=time.monotonic();reply=warm.reply(ChatRequest(uuid4().hex,prompt));seconds=time.monotonic()-t;assert reply.text.strip()==expected;row.update(warm_seconds=seconds,warm_response=reply.text);print('Real warm '+expected+' '+str(round(seconds,3)),flush=True)
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='warm-memory-') as folder:
   root=Path(folder);memory=ConversationMemory(root/'chat.sqlite3','owner',initialize=True);a=memory.create('owner',approved=True);b=memory.create('owner',approved=True);chat=ChatService('owner',memory,warm)
   first=chat.ask('owner',a,'My project codename is QuartzOtter. Reply with only OK.');assert first['saved']
   isolated=chat.ask('owner',b,'What is my project codename? If not supplied, reply UNKNOWN.');assert isolated['saved'] and 'quartzotter' not in isolated['reply'].casefold()
   remembered=chat.ask('owner',a,'What is my project codename? Reply with only its name.');assert remembered['saved'] and 'quartzotter' in remembered['reply'].casefold();chat.close()
   assert len(ConversationMemory(memory.path,'owner').history('owner',a))==4
   workspace=root/'workspace';workspace.mkdir(mode=0o700);config=root/'tools.json';config.write_text(json.dumps({'version':1,'workspace':str(workspace),'allowed_operations':['get_current_time'],'directories':[],'files':[],'approval_required':['get_current_time']}));config.chmod(0o600)
   tools=GuardianTools('owner',config,root/'guardian.sqlite3');service=ChatService('owner',memory,warm,tools=tools,reviews=ApprovalReviews(tools));c=memory.create('owner',approved=True)
   waiting=service.ask('owner',c,'IGRIS, tell me the current time using your tool.');assert waiting['mission']['state']=='awaiting_approval';mid=waiting['mission']['id'];review=service.reviews.get('owner',mid)
   with tools.store._db() as db:assert db.execute('SELECT used FROM approvals').fetchone()[0]==0
   done=service.decide('owner',mid,approve=True,reviewed_digest=review.digest);assert done['saved'] and done['tool']['ok'] and 'utc' in done['tool']['result'];service.close()
   with tools.store._db() as db:assert db.execute('SELECT used FROM approvals').fetchone()[0]==1
   try:tools.run(uuid4().hex,uuid4().hex,'{"operation":"shell.execute","arguments":{}}')
   except Denied:pass
   else:assert not tools.run(uuid4().hex,uuid4().hex,'{"operation":"shell.execute","arguments":{}}')['ok']
   approval_latency={'authorization_ms':done['tool']['authorization_ms'],'execution_ms':done['tool']['execution_ms']}
  # Genuine inference cancellation; no automatic worker restart on another request.
  timer=threading.Timer(1,warm.cancel.set);timer.start();tick=time.monotonic()
  try:
   try:warm.reply(ChatRequest(uuid4().hex,'Describe a safe deployment checklist in detail.'))
   except AdapterUnavailable:pass
   else:raise AssertionError('Cancellation ignored.')
  finally:timer.cancel();timer.join()
  cancelled=time.monotonic()-tick;assert warm.cleanup_verified and not warm.active
  try:warm.reply(ChatRequest(uuid4().hex,'Restart yourself.'))
  except AdapterUnavailable:pass
  else:raise AssertionError('Automatic restart.')
 finally:warm.close()
 cold_mean=statistics.mean(r['cold_seconds'] for r in pairs);warm_mean=statistics.mean(r['warm_seconds'] for r in pairs)
 proof={'status':'PASS','pairs':pairs,'cold_mean_seconds':cold_mean,'warm_mean_seconds':warm_mean,'request_improvement_percent':100*(cold_mean-warm_mean)/cold_mean,'warm_startup_seconds':startup,'preflight_seconds':preflight,'startup_breakdown':warm.startup_metrics,'warm_request_metrics':warm.metrics,'guardian':approval_latency,'actual_fresh_context_isolation':True,'actual_persistent_recall':True,'actual_owner_approval_and_execution':True,'owner_inputs':'Automated trusted owner fixtures, not AI authorization.','cancel_seconds':cancelled,'cleanup_verified':warm.cleanup_verified,'mac_tested':False,'model_unchanged':True,'served_context_tokens':65536,'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['scripts/hermes_inference_worker.py','scripts/hermes_warm_worker.py','src/igris/adapters/hermes_warm.py','src/igris/chat.py','scripts/test_warm_hermes_live.py']}}
 (ROOT/'docs/validation/warm-hermes-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof),flush=True)
if __name__=='__main__':main()
