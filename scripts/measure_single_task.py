"""Actual Linux controller/owned-worker RSS, real inference, Ops, clock and cleanup."""
import hashlib,json,os,subprocess,sys,tempfile,threading,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.foreground import Foreground,ForegroundBusy
from igris.mission_control import MissionControl
from igris.guardian.policy import Policy,Permission,Denied
from igris.guardian.approvals import ApprovalStore
from igris.guardian.activities import OwnerActions
from igris.isolated import docker_command,docker_environment

def rss(pid):
 try:return int(next(s for s in Path('/proc/'+str(pid)+'/status').read_text().splitlines() if s.startswith('VmRSS:')).split()[1])*1024
 except (OSError,StopIteration):return None

def workers(label):
 r=subprocess.run(docker_command()+['ps','--filter','label=com.igris.runtime='+label,'--format','{{.ID}}'],env=docker_environment(),capture_output=True,text=True,check=True,timeout=5);return r.stdout.split()

def container_processes(cid):
 r=subprocess.run(docker_command()+['top',cid,'-eo','pid,comm'],env=docker_environment(),capture_output=True,text=True,timeout=5)
 if r.returncode:return []
 return [{'pid':int(row.split()[0]),'name':row.split()[1],'rss_bytes':rss(int(row.split()[0]))} for row in r.stdout.splitlines()[1:] if len(row.split())==2 and row.split()[0].isdigit()]

def main():
 rows={};decisions=[]
 with tempfile.TemporaryDirectory(dir=ROOT/'runtime/single-task',prefix='memory-') as folder:
  root=Path(folder);foreground=Foreground(root/'foreground');control=MissionControl(root/'state',remember=True,foreground=foreground)
  try:
   assert not workers('hermes-inference') and not workers('ops-session');assert control.integrations.loaded=={}
   rows['igris_idle_controller_rss_bytes']=rss(os.getpid());session=control.memory.create('owner',approved=True)
   first=control.submit('chat',{'conversation_id':session,'prompt':'What is 7 plus 5? Reply with only the integer.','mode':'chat'})
   samples=[];max_models=0;max_model_processes=0;aggregate_peak=0;rejected=False;end=time.monotonic()+210
   while time.monotonic()<end:
    ids=workers('hermes-inference');max_models=max(max_models,len(ids))
    frame=[]
    for cid in ids:frame+=container_processes(cid)
    samples+=frame;max_model_processes=max(max_model_processes,sum(row['name']=='llama-server' for row in frame));aggregate_peak=max(aggregate_peak,sum(row['rss_bytes'] or 0 for row in frame))
    if ids and not rejected:
     from igris.chat import ChatService
     from igris.adapters.hermes_chat import DockerHermesAdapter
     other=control.memory.create('owner',approved=True)
     try:ChatService('owner',control.memory,DockerHermesAdapter(),foreground=foreground).ask('owner',other,'Competing real request must be rejected.')
     except ForegroundBusy:rejected=True
     else:raise AssertionError('Competing inference was started.')
    if control.jobs[first['job_id']]['status'] not in ('queued','running'):break
    time.sleep(.3)
   result=control.jobs[first['job_id']];assert result['result']['saved'] and result['result']['reply'].strip()=='12' and rejected and max_models==1 and max_model_processes==1
   model=[r['rss_bytes'] for r in samples if r['name']=='llama-server' and r['rss_bytes']];assert model
   rows['hermes_loaded_sampled_model_peak_rss_bytes']=max(model);rows['hermes_owned_process_sampled_aggregate_peak_rss_bytes']=aggregate_peak;rows['controller_after_hermes_rss_bytes']=rss(os.getpid());assert not workers('hermes-inference')
  finally:control.close()
  # Disposable app is infrastructure under explicit test ownership, never a production target.
  from igris.integrations.ops_runtime import DisposableOpsFixture
  from igris.integrations.ops_lifecycle import OpsIntegration
  fixture=DisposableOpsFixture().start()
  try:
   adapter=OpsIntegration(fixture.config_path,enabled=True);store=ApprovalStore(root/'ops.sqlite3',initialize=True);actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),root,store,[adapter.registration()],foreground=foreground)
   def run(action):
    review=actions.prepare('owner','ops.lifecycle',adapter.arguments(action));actions.decide('owner',review.mission_id,approve=True,reviewed_digest=review.digest);value=actions.run('owner',review.mission_id);decisions.append({'action':action,'task':foreground.lookup('owner',review.mission_id)});return value
   try:
    rows['controller_before_ops_rss_bytes']=rss(os.getpid());run('start');assert adapter.process and adapter.health()['status']=='running';rows['ops_active_processes']=container_processes(adapter.process.cid);rows['ops_active_total_rss_bytes']=sum(row['rss_bytes'] or 0 for row in rows['ops_active_processes']);rows['controller_with_ops_rss_bytes']=rss(os.getpid());assert run('monitor')['observation']['health']=='healthy';run('stop');assert not workers('ops-session');rows['controller_after_ops_stop_rss_bytes']=rss(os.getpid());rows['ops_after_stop_rss_bytes']=0
   finally:adapter.shutdown();actions.close()
  finally:fixture.close()
  from igris.integrations.catalog import Clock
  class MeasuredClock(Clock):
   def start(self):super().start();rows['controller_with_lightweight_clock_rss_bytes']=rss(os.getpid())
  clock=MeasuredClock();store=ApprovalStore(root/'clock.sqlite3',initialize=True);actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),root,store,[clock.registration()],foreground=foreground)
  try:
   review=actions.prepare('owner','get_current_time',{});actions.decide('owner',review.mission_id,approve=True,reviewed_digest=review.digest);answer=actions.run('owner',review.mission_id);assert answer['verified'] and clock.health()['status']=='stopped'
  finally:actions.close()
  rows['controller_after_all_cleanup_rss_bytes']=rss(os.getpid());assert not workers('hermes-inference') and not workers('ops-session')
 proof={'status':'PASS','environment':'Managed Linux x86_64, Python '+sys.version.split()[0]+', Docker VFS; not Mac M1','method':'Current /proc/PID/status VmRSS bytes; sampled model peak during actual Hermes request; owned container PIDs discovered using exact selected Docker IDs. RSS is not unique physical RAM and includes shared/file-backed pages. Controller measurements include the stdlib test harness; target application/daemon excluded.','measurements':rows,'maximum_simultaneous_model_containers':max_models,'maximum_simultaneous_model_processes':max_model_processes,'second_entry_rejected_before_model_launch':rejected,'actual_hermes_reply':'12','ops_actions':decisions,'all_owned_workers_stopped':True,'controller_delta_after_ops_stop_bytes':rows['controller_after_ops_stop_rss_bytes']-rows['controller_before_ops_rss_bytes'],'controller_final_minus_initial_bytes':rows['controller_after_all_cleanup_rss_bytes']-rows['igris_idle_controller_rss_bytes'],'interpretation':'Owned model/Ops process RSS disappears after verified container removal. Python may retain module/allocator pages; no exact baseline return or Mac target is promised.','owner_inputs':'Automated explicit owner approval fixtures; real adapters and operations.','source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['scripts/measure_single_task.py','src/igris/foreground.py','src/igris/chat.py','src/igris/mission_control.py','src/igris/integrations/ops_lifecycle.py','src/igris/integrations/session_process.py']}}
 (ROOT/'docs/validation/single-task-memory.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof),flush=True)
if __name__=='__main__':main()
