"""Actual owned-container failure, real deadline and cancellation; no runtime mocks."""
import hashlib,json,subprocess,sys,tempfile,threading,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.ops_runtime import DisposableOpsFixture
from igris.integrations.ops_lifecycle import OpsIntegration
from igris.guardian.activities import OwnerActions
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Policy,Permission,Denied
from igris.foreground import Foreground
from igris.isolated import docker_command,docker_environment,Cancelled
from igris.adapters.contracts import AdapterUnavailable

def main():
 observations=[]
 with tempfile.TemporaryDirectory(dir=ROOT/'runtime/single-task',prefix='failures-') as folder:
  root=Path(folder);foreground=Foreground(root/'foreground');fixture=DisposableOpsFixture().start()
  try:
   for scenario in ('timeout','failure','cancel'):
    mode='manual' if scenario=='failure' else 'on_demand';adapter=OpsIntegration(fixture.config_path,mode=mode,enabled=True,timeout=.001 if scenario=='timeout' else 90);store=ApprovalStore(root/(scenario+'.sqlite3'),initialize=True);actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),root,store,[adapter.registration()],foreground=foreground)
    def approve(action):
     review=actions.prepare('owner','ops.lifecycle',adapter.arguments(action));actions.decide('owner',review.mission_id,approve=True,reviewed_digest=review.digest);return review
    try:
     if scenario=='failure':
      review=approve('start');actions.run('owner',review.mission_id);cid=adapter.process.cid
      # Test-induced failure is scoped to the acknowledged component ID and marker,
      # never the monitored application or an arbitrary user's process.
      inspected=subprocess.run(docker_command()+['inspect','--format','{{index .Config.Labels "com.igris.owner"}}',cid],env=docker_environment(),capture_output=True,text=True,check=True)
      assert inspected.stdout.strip()==adapter.process.launch.marker
      subprocess.run(docker_command()+['kill',cid],env=docker_environment(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
      adapter.process.process.wait(timeout=5)
     review=approve('monitor');start=time.monotonic()
     if scenario=='cancel':
      with ThreadPoolExecutor(1) as pool:
       future=pool.submit(actions.run,'owner',review.mission_id);end=time.monotonic()+30
       while adapter.process is None or adapter.process.process is None:
        if future.done():future.result();raise AssertionError('No live component observed for cancellation.')
        if time.monotonic()>end:raise TimeoutError('Component not observed.')
        time.sleep(.01)
       actions.cancel('owner',review.mission_id)
       try:future.result(timeout=20)
       except (Cancelled,Denied):pass
       else:raise AssertionError('Cancellation ignored.')
     else:
      try:actions.run('owner',review.mission_id)
      except TimeoutError:
       assert scenario=='timeout'
      except AdapterUnavailable:
       assert scenario=='failure'
      else:raise AssertionError('Injected real failure was falsely successful.')
     record=foreground.lookup('owner',review.mission_id);assert record['status'] in ('failed','cancelled') and record['cleanup_status']=='verified' and adapter.process is None and adapter.proxy is None
     observations.append({'scenario':scenario,'status':'PASS','task':record,'seconds':time.monotonic()-start});print(scenario+': real failure/cancellation cleanup PASS',flush=True)
    finally:adapter.shutdown();actions.close()
  finally:fixture.close()
 remaining=subprocess.run(docker_command()+['ps','--all','--filter','label=com.igris.runtime=ops-session','--format','{{.ID}}'],env=docker_environment(),capture_output=True,text=True,check=True);assert not remaining.stdout.strip()
 proof={'status':'PASS','scenarios':observations,'remaining_owned_sessions':0,'real':True,'mocked':False,'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['src/igris/integrations/ops_lifecycle.py','src/igris/integrations/session_process.py','scripts/test_single_task_ops_failures.py']}}
 (ROOT/'docs/validation/single-task-ops-failures.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
