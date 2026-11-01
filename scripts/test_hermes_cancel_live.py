"""Cancel a real tracked reasoning worker; do not fabricate an inference result."""
import concurrent.futures,json,sys,threading,time
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.adapters.hermes_chat import DockerHermesAdapter,ChatRequest
from igris.adapters.contracts import AdapterUnavailable
from igris.isolated import docker_command,docker_environment
import subprocess

def main():
 stop=threading.Event();adapter=DockerHermesAdapter(cancel=stop);seen=False
 with concurrent.futures.ThreadPoolExecutor(1) as pool:
  job=pool.submit(adapter.reply,ChatRequest(uuid4().hex,'Explain how to review a small program.'))
  deadline=time.monotonic()+30
  while time.monotonic()<deadline:
   result=subprocess.run(docker_command()+['ps','--filter','label=com.igris.runtime=hermes-inference','--format','{{.Names}}'],env=docker_environment(),capture_output=True,text=True,check=True,timeout=5)
   if result.stdout.strip():seen=True;break
   if job.done():job.result();raise AssertionError('Worker completed before cancellation observation.')
   time.sleep(.1)
  assert seen,'No real tracked worker observed.'
  start=time.monotonic();stop.set()
  try:job.result(timeout=20)
  except AdapterUnavailable:pass
  else:raise AssertionError('Cancelled worker returned a response.')
  elapsed=time.monotonic()-start
 result=subprocess.run(docker_command()+['ps','--all','--filter','label=com.igris.runtime=hermes-inference','--format','{{.ID}}'],env=docker_environment(),capture_output=True,text=True,check=True,timeout=5)
 assert not result.stdout.strip()
 proof={'status':'PASS','actual_worker_observed':True,'response_discarded':True,'cleanup_verified':True,'cancellation_seconds':elapsed,'scope':'Only adapter-tracked worker; no broad stop command.'}
 (ROOT/'runtime/hermes-cancel-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
