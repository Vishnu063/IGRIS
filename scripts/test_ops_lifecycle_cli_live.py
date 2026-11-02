"""Actual controlling-terminal approval channel; explicit automated owner fixtures."""
import hashlib,json,os,pty,re,select,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.ops_runtime import DisposableOpsFixture

def main():
 observations=[];fixture=DisposableOpsFixture().start()
 try:
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime/single-task',prefix='ops-cli-') as folder:
   pid,fd=pty.fork()
   if pid==0:
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'));os.chdir(ROOT);os.execvpe(sys.executable,[sys.executable,'-m','igris.integrations.ops_lifecycle_cli','--enable-runtime','--instance',str(fixture.config_path),'--state-dir',str(Path(folder)/'state')],env)
   buffer=b'';done=False
   def until(marker):
    nonlocal buffer
    end=time.monotonic()+45
    while marker not in buffer:
     if time.monotonic()>end:raise TimeoutError('Ops owner terminal timeout.')
     if select.select([fd],[],[],.1)[0]:
      chunk=os.read(fd,8192)
      if not chunk:raise RuntimeError('Owner console closed.')
      buffer+=chunk
      if len(buffer)>65536:raise ValueError('Owner output cap exceeded.')
    output=buffer;buffer=b'';return output
   try:
    until(b'Ops: ')
    for action in ('status','start','probe','stop'):
     os.write(fd,action.encode()+b'\n');review=until(b'(anything else cancels): ');digest=re.search(rb'"action_sha256":\s*"([a-f0-9]{64})"',review).group(1).decode();os.write(fd,('APPROVE '+digest[:12]+'\n').encode());reply=until(b'Ops: ')
     result=next(json.loads(row) for row in reply.decode().splitlines() if row.startswith('{"task":'))
     assert result['task']['status']=='completed' and result['result']['verified']
     if action=='status':assert result['result']['health']['status']=='stopped'
     observations.append({'action':action,'task_status':result['task']['status'],'cleanup_status':result['task']['cleanup_status']})
    os.write(fd,b'exit\n');end=time.monotonic()+10
    while time.monotonic()<end:
     observed,status=os.waitpid(pid,os.WNOHANG)
     if observed:assert os.waitstatus_to_exitcode(status)==0;done=True;break
     time.sleep(.1)
    assert done
   finally:
    if not done:
     try:os.kill(pid,2);os.waitpid(pid,0)
     except ProcessLookupError:pass
    os.close(fd)
 finally:fixture.close()
 proof={'status':'PASS','real_pty':True,'real_ops_worker':True,'observations':observations,'owner_inputs':'Automated trusted PTY fixture decisions, not model approval.','source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['src/igris/integrations/ops_lifecycle_cli.py','scripts/test_ops_lifecycle_cli_live.py']}}
 (ROOT/'docs/validation/single-task-ops-cli-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
