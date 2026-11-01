"""Actual approved n8n worker cancellation, during CLI startup; owner decisions are fixtures."""
import hashlib,json,subprocess,sys,tempfile,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.guardian.activities import OwnerActions
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Policy,Permission
from igris.integrations.n8n_runtime import RealN8n
from igris.isolated import docker_command,docker_environment,Cancelled

with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='n8n-cancel-') as folder:
    root=Path(folder);store=ApprovalStore(root/'guardian.sqlite3',initialize=True)
    actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),root,store,[RealN8n(enabled=True).registration()])
    review=actions.prepare('owner','n8n.calculate',{'left':1,'right':2})
    actions.decide('owner',review.mission_id,approve=True,reviewed_digest=review.digest)
    with ThreadPoolExecutor(1) as pool:
        pending=pool.submit(actions.run,'owner',review.mission_id);deadline=time.monotonic()+100;observed=None
        while time.monotonic()<deadline:
            if pending.done():pending.result();raise AssertionError('Workflow finished before cancellation observation.')
            result=subprocess.run(docker_command()+['ps','--filter','label=com.igris.component=n8n','--format','{{.Names}}'],env=docker_environment(),capture_output=True,text=True,check=True,timeout=5)
            for name in result.stdout.splitlines():
                top=subprocess.run(docker_command()+['top',name,'-eo','pid,args'],env=docker_environment(),capture_output=True,text=True,timeout=5)
                recognized=any('/n8n/bin/n8n' in line or 'n8n ' in line for line in top.stdout.splitlines()[1:])
                (ROOT/'runtime/n8n/cancel-observer.json').write_text(json.dumps({'returncode':top.returncode,'n8n_cli_recognized':recognized,'process_count':max(0,len(top.stdout.splitlines())-1),'error':top.stderr[:512]}))
                if top.returncode==0 and recognized:observed=name;break
            if observed:break
            time.sleep(.3)
        assert observed,'Actual Node startup not observed'
        start=time.monotonic();actions.cancel('owner',review.mission_id)
        try:pending.result(timeout=30)
        except Cancelled:pass
        else:raise AssertionError('Cancellation did not discard result.')
        elapsed=time.monotonic()-start
    remaining=subprocess.run(docker_command()+['ps','--all','--filter','name=^/'+observed+'$','--format','{{.ID}}'],env=docker_environment(),capture_output=True,text=True,check=True,timeout=5)
    assert not remaining.stdout.strip()
    with store._db() as db:
        approval=db.execute('SELECT status,used FROM approvals').fetchone();events=[row[0] for row in db.execute('SELECT event FROM audit')]
    assert approval==('approved',1) and 'execution_failed' in events
    assert actions.status('owner')['history'][review.mission_id]['status']=='cancelled'
    actions.close()
    proof={'status':'PASS','scope':'Actual approved n8n CLI startup process cancelled; no claim of transactional rollback or remote n8n API cancellation.',
           'owner_authorization':'explicit automated owner fixture; real Policy/ApprovalStore/ExecutionPermit',
           'observed_node_process':True,'owned_container_removed':True,'cancellation_seconds':elapsed,'approval':approval,'audit_events':events,
           'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('src/igris/guardian/activities.py','src/igris/integrations/n8n_runtime.py','src/igris/isolated.py','scripts/test_n8n_cancel_live.py')}}
    (ROOT/'runtime/n8n/cancel-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
