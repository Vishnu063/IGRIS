"""Real loopback dashboard/chat/auth/stop/logout acceptance, no inference mock."""
import base64,hashlib,http.client,json,secrets,socket,subprocess,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.dashboard import make_server
from igris.mission_control import MissionControl
from igris.foreground import Foreground
from igris.isolated import docker_command,docker_environment
from measure_single_task import container_processes

def container_memory(cid):
    # Daemon cgroup counters work even when its PID namespace differs from ours.
    class Unix(http.client.HTTPConnection):
        def connect(self):
            self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(2);self.sock.connect('/var/run/docker.sock')
    client=Unix('localhost',timeout=2)
    try:
        client.request('GET','/containers/'+cid+'/stats?stream=false&one-shot=true');response=client.getresponse();raw=response.read(65537)
        if response.status!=200 or len(raw)>65536:return None
        data=json.loads(raw).get('memory_stats',{});value=data.get('usage')
        return value if type(value) is int and value>0 else None
    except (OSError,ValueError):return None
    finally:client.close()

def verify():
    info=json.loads(subprocess.check_output(docker_command()+['info','--format','{{json .}}'],env=docker_environment(),text=True,timeout=10))
    limits={key:info.get(key) for key in ('MemoryLimit','SwapLimit','CpuCfsPeriod','CpuCfsQuota','PidsLimit')}
    with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='http-acceptance-') as folder:
        root=Path(folder);control=MissionControl(root/'state',remember=True,foreground=Foreground(root/'foreground'))
        accounts={name:(secrets.token_urlsafe(32),name) for name in ('owner','viewer')}
        server=make_server(accounts,control=control);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start();csrf=None
        def api(path,data=None,role='owner',overrides=None):
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            headers={'Authorization':'Basic '+base64.b64encode((role+':'+accounts[role][0]).encode()).decode()}
            if data is not None:headers.update({'Origin':'http://127.0.0.1:'+str(server.server_port),'X-IGRIS-CSRF':csrf or '', 'Content-Type':'application/json'})
            headers.update(overrides or {})
            try:
                conn.request('GET' if data is None else 'POST',path,body=None if data is None else json.dumps(data),headers=headers);r=conn.getresponse();raw=r.read(524289)
                assert len(raw)<=524288
                return r.status,json.loads(raw) if 'application/json' in r.getheader('Content-Type','') else None
            finally:conn.close()
        sampled_model_peak=0;sampled_owned_peak=0;container_memory_peak=0
        def wait(predicate,timeout=210):
            nonlocal sampled_model_peak,sampled_owned_peak,container_memory_peak
            end=time.monotonic()+timeout
            while time.monotonic()<end:
                status,state=api('/api/state');assert status==200
                ids=workers().split();processes=[row for cid in ids for row in container_processes(cid)]
                for cid in ids:container_memory_peak=max(container_memory_peak,container_memory(cid) or 0)
                sampled_model_peak=max([sampled_model_peak]+[r['rss_bytes'] or 0 for r in processes if r['name']=='llama-server'])
                sampled_owned_peak=max(sampled_owned_peak,sum(r['rss_bytes'] or 0 for r in processes))
                if predicate(state):return state
                time.sleep(.2)
            raise TimeoutError('Actual dashboard condition failed.')
        def workers():
            return subprocess.check_output(docker_command()+['ps','--all','--filter','label=com.igris.runtime=hermes-inference','--format','{{.ID}}'],env=docker_environment(),text=True,timeout=5).strip()
        try:
            assert api('/api/state',overrides={'Authorization':'Basic invalid'})[0]==401
            csrf=api('/api/state')[1]['csrf'];assert 'csrf' not in api('/api/state',role='viewer')[1]
            assert api('/api/session',{},role='viewer')[0]==403
            assert api('/api/session',{},overrides={'Origin':'http://foreign.invalid'})[0]==403
            assert api('/api/session',{},overrides={'X-IGRIS-CSRF':'forged'})[0]==403
            session=api('/api/session',{})[1]['conversation_id']
            started=time.monotonic();job=api('/api/chat',{'conversation_id':session,'prompt':'What is 7 plus 5? Reply only with the integer.','mode':'chat'})[1]['job_id']
            state=wait(lambda s:any(j['id']==job and j['status'] not in ('queued','running') for j in s['jobs']))
            result=next(j for j in state['jobs'] if j['id']==job)['result'];assert result['saved'] and result['reply'].strip()=='12'
            chat_seconds=time.monotonic()-started;assert len(api('/api/history/'+session)[1]['history'])==2
            job=api('/api/chat',{'conversation_id':session,'prompt':'Explain a long mathematical argument.','mode':'chat'})[1]['job_id']
            deadline=time.monotonic()+40
            while not workers():
                if time.monotonic()>deadline:raise TimeoutError('No actual worker for cancellation.')
                time.sleep(.1)
            started=time.monotonic();assert api('/api/cancel',{'task_id':job})[0]==202
            wait(lambda s:s['foreground']['state']=='idle',35);assert not workers();cancel_seconds=time.monotonic()-started
            assert api('/api/logout',{})[0]==200
            assert api('/api/state')[0]==401 and api('/api/session',{})[0]==401
            control.worker.join(35);assert control.stopped and not workers()
            paths=['scripts/verify_dashboard_http.py','src/igris/mission_control.py','src/igris/adapters/hermes_chat.py','src/igris/adapters/native_runtime.py','src/igris/guardian/kernel.py','scripts/hermes_chat_worker.py']
            return {'status':'PASS','resource_enforcement':'PASS' if all(v is True for v in limits.values()) else 'BLOCKED','daemon_resource_capabilities':limits,'inference':'real_Hermes','reply':'12','authenticated_chat_seconds':chat_seconds,'cancel_and_verified_cleanup_seconds':cancel_seconds,'logout_cached_credential_revoked':True,'owner_viewer_csrf_origin_denials':True,'emergency_stop_no_restart':control.stop_event.is_set(),'native_browser_ui':'NOT_TESTED','mac_hardware':'NOT_TESTED','owner_inputs':'Automated trusted HTTP fixtures, not model approval.','sampled_model_peak_rss_bytes':sampled_model_peak or None,'sampled_owned_process_aggregate_peak_rss_bytes':sampled_owned_peak or None,'sampled_model_container_cgroup_usage_peak_bytes':container_memory_peak or None,'controller_peak_rss_bytes':state['resources']['dashboard_rss_bytes'],'memory_method':'Daemon raw cgroup memory usage includes cache, not RSS. Local /proc VmRSS is unavailable when Docker PIDs are outside this PID namespace (null, never zero-memory success). Controller getrusage peak at chat completion. Not Mac measurements.','source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
        finally:
            server.shutdown();server.server_close();thread.join(3);control.close()
if __name__=='__main__':
    proof=verify();target=ROOT/'runtime/mac-readiness';target.mkdir(parents=True,exist_ok=True);(target/'dashboard-http.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
