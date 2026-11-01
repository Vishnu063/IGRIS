"""Real Mem0/ONNX/Qdrant, Guardian, SQLite and memory-enriched Hermes test.

All facts are synthetic owner fixtures. All model/backend execution is actual.
"""
import hashlib,json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.scoped_memory import ScopedFacts
from igris.conversations import ConversationMemory
from igris.semantic_memory import SemanticMemory
from igris.adapters.hermes_chat import DockerHermesAdapter
from igris.chat import ChatService
from igris.guardian.policy import Policy,Permission,Denied
from igris.guardian.activities import OwnerActions
from igris.guardian.approvals import ApprovalStore

def main():
 out=ROOT/'runtime/mem0';observations=[]
 with tempfile.TemporaryDirectory(dir=out,prefix='acceptance-') as folder:
  root=Path(folder);memory=ConversationMemory(root/'chat.sqlite3','owner',initialize=True)
  conversation=memory.create('owner',approved=True);other=memory.create('owner',approved=True)
  base=ChatService('owner',memory,DockerHermesAdapter())
  first=base.ask('owner',conversation,'Reply with only READY.');assert first['saved'];previous=memory.history('owner',conversation)
  print('Actual initial Hermes conversation persisted.',flush=True)
  facts=ScopedFacts(root/'facts.sqlite3','owner',memory,initialize=True)
  policy=Policy('owner',frozenset({Permission.READ,Permission.FILE_MODIFY}));service=SemanticMemory(facts,policy,enabled=True)
  store=ApprovalStore(root/'guardian.sqlite3',initialize=True);actions=OwnerActions(policy,root,store,[service.registration()])
  def run(arguments):
   review=actions.prepare('owner','memory.manage',arguments)
   try:actions.run('owner',review.mission_id)
   except Denied:pass
   else:raise AssertionError('Unapproved memory mutation succeeded.')
   actions.decide('owner',review.mission_id,approve=True,reviewed_digest=review.digest)
   result=actions.run('owner',review.mission_id)
   try:actions.run('owner',review.mission_id)
   except Denied:pass
   else:raise AssertionError('Memory approval replay succeeded.')
   return result
  def save(convo,text,category='project'):
   return run({'kind':'save','conversation_id':convo,'category':category,'text':text,'classification':'verified_fact','evidence':'Explicit synthetic owner acceptance fixture.'})['fact']
  try:
   target=save(conversation,'We deploy our web application to the Mumbai AWS region.')
   irrelevant=save(conversation,'The interface theme should be dark.','preference')
   foreign=save(other,'Client documents must be stored in Berlin.')
   result=service.search('owner',conversation,'Where is the preferred hosting location?',probe=True)
   assert result['backend']=='real_mem0_local' and result['facts'][0]['id']==target['id'] and result['extraction_probe_denied']
   assert foreign['id'] not in [row['id'] for row in result['facts']]
   observations.append({'case':'real_semantic_retrieval','result':result})
   print('Actual semantic retrieval and fail-closed extraction probe PASS.',flush=True)
   for actor,convo in [('model',conversation),('owner',other)]:
    try:facts.get(actor,convo,target['id'])
    except (Denied,KeyError):pass
    else:raise AssertionError('Cross-scope fact exposed.')
   reopened_facts=ScopedFacts(facts.path,'owner',ConversationMemory(memory.path,'owner'))
   restarted=SemanticMemory(reopened_facts,policy,enabled=True)
   restarted_result=restarted.search('owner',conversation,'preferred hosting location')
   assert restarted_result['facts'][0]['id']==target['id'];observations.append({'case':'new_service_process_worker_persistence','result':restarted_result})
   chat=ChatService('owner',memory,DockerHermesAdapter(),knowledge=restarted)
   reply=chat.ask('owner',conversation,'Which AWS region is recorded in my approved memory? Reply briefly.')
   assert reply['saved'] and 'mumbai' in reply['reply'].casefold() and reply['memory']['backend']=='real_mem0_local'
   assert 'berlin' not in reply['reply'].casefold() and memory.history('owner',conversation)[:2]==previous
   observations.append({'case':'real_memory_enriched_hermes','reply':reply['reply'],'memory':reply['memory']})
   print('Actual memory-enriched Hermes reply PASS.',flush=True)
   changed=run({'kind':'correct','conversation_id':conversation,'id':target['id'],'revision':1,'text':'We deploy our web application to the Hyderabad AWS region.'})['fact']
   assert changed['revision']==2 and changed['classification']=='assumption'
   after=restarted.search('owner',conversation,'preferred hosting location');assert after['facts'][0]['revision']==2 and 'Hyderabad' in after['facts'][0]['text']
   run({'kind':'delete','conversation_id':conversation,'id':target['id'],'revision':2})
   deleted=restarted.search('owner',conversation,'preferred hosting location');assert target['id'] not in [row['id'] for row in deleted['facts']]
   observations.append({'case':'correction_and_deletion','after_correction':after,'after_deletion':deleted})
   fallback=SemanticMemory(facts,policy,enabled=False).search('owner',conversation,'dark theme');assert fallback['backend']=='sqlite_keyword_fallback' and fallback['facts'][0]['id']==irrelevant['id']
   assert len(memory.history('owner',conversation))==4 and memory.history('owner',other)==()
   with store._db() as db:used=db.execute('SELECT SUM(used) FROM approvals').fetchone()[0]
   assert used==5;observations.append({'case':'sqlite_fallback','result':fallback})
   print('Actual correction, deletion, scope denial and fallback PASS.',flush=True)
  finally:actions.close();base.close()
 proof={'status':'PASS','observations':observations,'approvals_consumed':used,'facts':'Synthetic explicit owner-approved fixtures, never customer data.','mocked_integrations':False,'real':'Actual Mem0 2.2.1, FastEmbed/MiniLM ONNX, embedded Qdrant, SQLite and Hermes.','source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['src/igris/scoped_memory.py','src/igris/semantic_memory.py','src/igris/integrations/mem0_runtime.py','src/igris/isolated.py','src/igris/chat.py','integrations/mem0/worker.py','integrations/mem0/profile.json','scripts/test_mem0_live.py']}}
 (out/'live.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
