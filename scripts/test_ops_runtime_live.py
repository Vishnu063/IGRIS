"""Real unmodified Ops Pilot -> restricted proxy -> actual disposable Docker app."""
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.ops_runtime import DisposableOpsFixture,RealOpsMonitor,source_digest
from igris.guardian.activities import OwnerActions
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Policy,Permission,Denied
from igris.guardian.docker_read_proxy import ExactDockerReads,UnixHTTP


def main():
    destination=ROOT/'runtime/ops/live.json';destination.write_text(json.dumps({'status':'RUNNING'}));observations=[]
    fixture=DisposableOpsFixture()
    try:
        fixture.start();adapter=RealOpsMonitor(fixture.config_path,enabled=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'runtime/ops',prefix='authority-') as folder:
            store=ApprovalStore(Path(folder)/'guardian.sqlite3',initialize=True)
            actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),Path(folder),store,[adapter.registration()])
            try:
                for state in ('running','stopped'):
                    if state=='stopped':fixture.stop_application()
                    start=time.monotonic();review=actions.prepare('owner','ops.monitor',{'container_id':fixture.cid})
                    # Explicit owner fixture, not AI authorization. The same terminal/UI service is reused.
                    actions.decide('owner',review.mission_id,approve=True,reviewed_digest=review.digest)
                    result=actions.run('owner',review.mission_id)
                    expected='running' if state=='running' else 'exited'
                    assert result['origin']=='real_ops_pilot' and result['container_id']==fixture.cid
                    assert result['container_state']==expected,result
                    assert result['health']==('healthy' if state=='running' else 'unhealthy'),result
                    assert not result['remediation_enabled'] and not result['issues'],result
                    assert any(e['kind']=='inspect' and e['status']==200 for e in result['transport_audit'])
                    assert any(e['kind']=='logs' and e['status']==200 for e in result['transport_audit'])
                    observations.append({'application_state':state,'monitoring':result,'wall_seconds':time.monotonic()-start})
                    destination.write_text(json.dumps({'status':'RUNNING','observations':observations},indent=2)+'\n');print(state+': actual Ops Pilot/Docker monitoring PASS',flush=True)
                with store._db() as db:
                    assert db.execute("SELECT COUNT(*) FROM approvals WHERE used=1").fetchone()[0]==2
                    audit=[row[0] for row in db.execute('SELECT event FROM audit')]
                with tempfile.TemporaryDirectory(dir=ROOT/'runtime/ops',prefix='denials-') as denied:
                    proxy=ExactDockerReads(Path(denied)/'docker.sock',fixture.cid,adapter.config['daemon_id'],adapter.read_key).start()
                    try:
                        cases=[('GET','/containers/'+'0'*64+'/json',adapter.read_key),('POST','/containers/'+fixture.cid+'/restart',adapter.read_key),('GET','/info','0'*64)]
                        outcomes=[]
                        for method,path,key in cases:
                            conn=UnixHTTP(proxy.path)
                            try:
                                conn.request(method,path,headers={'X-IGRIS-Read-Key':key});response=conn.getresponse();response.read();outcomes.append(response.status)
                            finally:conn.close()
                        assert outcomes==[403,403,401]
                        assert all(e['status']!=200 for e in proxy.events)
                    finally:proxy.close()
            finally:actions.close()
        assert all(source_digest(ROOT/'runtime/ops'/name)==expected for name,expected in adapter.profile['sources'].items()),'Upstream copy changed'
    finally:fixture.close()
    files=['src/igris/guardian/docker_read_proxy.py','src/igris/integrations/ops_runtime.py','src/igris/adapters/ops_monitoring.py','integrations/ops/worker.py','integrations/ops/fixture_app.py','integrations/ops/profile.json','scripts/test_ops_runtime_live.py']
    proof={'status':'PASS','verified_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),'observations':observations,'denials':{'other_target':403,'restart':403,'invalid_read_credential':401},
        'approval_events':audit,'upstream_unmodified':True,'fixture_cleanup_verified':True,'owner_authorization':'Explicit automated owner fixtures; real Guardian/SQLite/ExecutionPermit, no model approval.',
        'runtime':'Actual pinned Ops Pilot Pilot library and default DockerAdapter, actual Docker CLI and daemon, actual Docker application and HTTP-over-Unix health.',
        'mocked_integrations':False,'remediation':'disabled; no restart or production action executed','source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}}
    destination.write_text(json.dumps(proof,indent=2)+'\n')

if __name__=='__main__':main()
