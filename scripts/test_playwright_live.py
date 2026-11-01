"""Real browser acceptance; automated owner decisions are explicit test fixtures."""
import hashlib,json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.playwright_runtime import OwnedBrowser
from igris.guardian.activities import OwnerActions
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Policy,Permission,Denied
from igris.adapters.contracts import AdapterUnavailable
from igris.isolated import Cancelled

def main():
 start=time.monotonic();adapter=OwnedBrowser(enabled=True)
 with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='browser-acceptance-') as folder:
  path=Path(folder);policy=Policy('owner',frozenset({Permission.READ}));store=ApprovalStore(path/'guardian.sqlite3',initialize=True);actions=OwnerActions(policy,path,store,[adapter.registration()]);checks=[]
  for args in ({'site':'https://example.org','action':'inspect_and_screenshot'},{'site':'owned_acceptance','action':'submit'},{'site':'owned_acceptance','action':'inspect_and_screenshot','javascript':'evil'}):
   try:actions.prepare('owner','browser.inspect',args)
   except Denied:checks.append('unauthorized_arguments_denied')
   else:raise AssertionError('Unauthorized action accepted.')
  args={'site':'owned_acceptance','action':'inspect_and_screenshot'};review=actions.prepare('owner','browser.inspect',args)
  try:actions.run('owner',review.mission_id)
  except Denied:checks.append('missing_approval_denied')
  else:raise AssertionError('Approval bypass.')
  actions.decide('owner',review.mission_id,approve=True,reviewed_digest=review.digest);result=actions.run('owner',review.mission_id)
  try:actions.run('owner',review.mission_id)
  except Denied:checks.append('replay_denied')
  assert '7 + 5 = 12' in result['text'] and result['blocked_requests']==3
  review=actions.prepare('owner','browser.inspect',args);actions.decide('owner',review.mission_id,approve=True,reviewed_digest=review.digest)
  timer=threading.Timer(1,lambda:actions.cancel('owner',review.mission_id));timer.start()
  try:
   try:actions.run('owner',review.mission_id)
   except Cancelled:checks.append('actual_worker_cancellation_and_namespace_cleanup')
   else:raise AssertionError('Cancellation was ignored.')
  finally:timer.cancel();timer.join();actions.close()
 proof={'status':'PASS','result':result,'checks':checks,'owner_inputs':'Automated trusted owner fixtures, not AI approval.','elapsed_seconds':round(time.monotonic()-start,3),'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['src/igris/integrations/playwright_runtime.py','integrations/playwright/worker.py','scripts/test_playwright_live.py']}}
 (ROOT/'docs/validation/playwright-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
