"""Real Ops lifecycle/Guardian/owned Docker fixture; automated owner approval fixtures."""
import hashlib,json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.ops_runtime import DisposableOpsFixture
from igris.integrations.ops_lifecycle import OpsIntegration
from igris.guardian.activities import OwnerActions
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Policy,Permission,Denied
from igris.foreground import Foreground
from igris.isolated import docker_command,docker_environment
import subprocess

def main():
 observations=[]
 with tempfile.TemporaryDirectory(dir=ROOT/'runtime/single-task',prefix='ops-') as directory:
  root=Path(directory);foreground=Foreground(root/'foreground')
  with_fixture=DisposableOpsFixture().start()
  try:
   for mode in ('manual','on_demand','monitoring'):
    adapter=OpsIntegration(with_fixture.config_path,mode=mode,enabled=True);store=ApprovalStore(root/(mode+'.sqlite3'),initialize=True);actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),root,store,[adapter.registration()],foreground=foreground)
    def run(action,approve=True):
     review=actions.prepare('owner','ops.lifecycle',adapter.arguments(action))
     try:actions.run('owner',review.mission_id)
     except Denied:pass
     else:raise AssertionError('Missing approval executed.')
     actions.decide('owner',review.mission_id,approve=approve,reviewed_digest=review.digest)
     return actions.run('owner',review.mission_id) if approve else None
    try:
     assert adapter.health()['status']=='stopped'
     if mode in ('manual','monitoring'):
      try:run('monitor')
      except Denied:pass
      else:raise AssertionError('Manual auto-start.')
      assert adapter.process is None;run('start',False);assert adapter.process is None
      started=run('start');assert started['verified'] and adapter.health()['status']=='running';cid=adapter.process.cid
     first=run('monitor');assert first['verified'] and first['observation']['container_state']=='running' and first['observation']['health']=='healthy'
     if mode=='on_demand':assert adapter.process is None and adapter.proxy is None
     else:
      second=run('monitor');assert adapter.process.cid==cid and second['observation']['health']=='healthy'
      run('stop');assert adapter.process is None and adapter.proxy is None
     observations.append({'mode':mode,'status':'PASS','observation':first,'cleanup_verified':adapter.health()['cleanup_verified']});print(mode+': real start/probe/cleanup PASS',flush=True)
    finally:adapter.shutdown();actions.close()
   from igris.guardian.docker_read_proxy import daemon_read
   code,_,raw=daemon_read('/containers/'+with_fixture.cid+'/json');assert code==200 and json.loads(raw)['State']['Running']
  finally:with_fixture.close()
 result=subprocess.run(docker_command()+['ps','--all','--filter','label=com.igris.runtime=ops-session','--format','{{.ID}}'],env=docker_environment(),capture_output=True,text=True,check=True);assert not result.stdout.strip()
 proof={'status':'PASS','observations':observations,'monitored_application_preserved_until_explicit_fixture_cleanup':True,'remaining_ops_sessions':0,'owner_decisions':'Automated trusted fixtures, not AI authorization.','real':True,'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['src/igris/integrations/ops_lifecycle.py','src/igris/integrations/session_process.py','integrations/ops/worker.py','integrations/ops/session_worker.py','src/igris/foreground.py']}}
 (ROOT/'docs/validation/single-task-ops-live.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
