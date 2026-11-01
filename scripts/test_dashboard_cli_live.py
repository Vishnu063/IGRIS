"""Actual manual CLI/authentication/disposable target/shutdown, no inference."""
import base64,json,os,re,signal,subprocess,sys,tempfile,time,http.client
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.isolated import docker_command,docker_environment

def main():
 with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='task7-cli-') as folder:
  root=Path(folder);accounts=root/'accounts.json'
  result=subprocess.run([sys.executable,str(ROOT/'scripts/create_dashboard_accounts.py'),'--output',str(accounts)],capture_output=True,text=True,check=True,timeout=5)
  data=json.loads(accounts.read_text());assert all(value[0] not in result.stdout for value in data.values()) and accounts.stat().st_mode&0o777==0o600
  log=(root/'cli.log').open('w+');env=dict(os.environ,PYTHONPATH=str(ROOT/'src'))
  process=subprocess.Popen([sys.executable,'-m','igris.mission_control','--remember','--accounts-file',str(accounts),'--state-dir',str(root/'state'),'--port','0','--ops-demo'],cwd=ROOT,env=env,stdout=log,stderr=log)
  cid=None
  try:
   deadline=time.monotonic()+30
   while True:
    log.flush();log.seek(0);text=log.read();match=re.search(r'http://127.0.0.1:([0-9]+)',text)
    if match:break
    if process.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Manual dashboard startup failed; private log not published.')
    time.sleep(.1)
   conn=http.client.HTTPConnection('127.0.0.1',int(match[1]),timeout=3)
   try:
    auth='Basic '+base64.b64encode(('owner:'+data['owner'][0]).encode()).decode();conn.request('GET','/api/state',headers={'Authorization':auth});response=conn.getresponse();view=json.loads(response.read());assert response.status==200
   finally:conn.close()
   assert view['components']['ops_pilot']['status']=='configured_on_request';cid=view['components']['ops_pilot']['target_container_id']
   assert view['components']['n8n']['status']=='disabled' and not view['jobs']
   process.send_signal(signal.SIGINT);assert process.wait(timeout=35)==0
  finally:
   if process.poll() is None:process.send_signal(signal.SIGINT);process.wait(timeout=35)
   log.close()
  assert cid
  remaining=subprocess.run(docker_command()+['ps','--all','--filter','id='+cid,'--format','{{.ID}}'],env=docker_environment(),capture_output=True,text=True,check=True,timeout=5);assert not remaining.stdout.strip()
 proof={'status':'PASS','actual_cli':True,'private_random_accounts':True,'no_credentials_in_stdout':True,'ops_demo_created_and_removed':True,'inference':'Not invoked; optional integrations remain on request.','exit_code':0}
 (ROOT/'runtime/task7/cli-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
