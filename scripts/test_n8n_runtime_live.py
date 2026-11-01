"""Real IGRIS terminal -> Guardian -> n8n CLI/SQLite acceptance; PTY owner fixtures."""
import hashlib,json,os,pty,re,select,signal,sqlite3,sys,tempfile,time
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.guardian.approvals import ApprovalStore
from igris.guardian.secrets import findings


def main():
    rows=[];destination=ROOT/'runtime/n8n/live.json';destination.write_text(json.dumps({'status':'RUNNING'}))
    with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='n8n-live-') as folder:
        for choice in ('approve','reject'):
            state=Path(folder)/choice;started=time.monotonic();pid,master=pty.fork();done=False
            if pid==0:
                os.chdir(ROOT);env=dict(os.environ,PYTHONPATH=str(ROOT/'src'))
                os.execvpe(sys.executable,[sys.executable,'-m','igris.integrations.n8n_cli','--enable-runtime','--left','7','--right','5','--state-dir',str(state)],env)
            received=b'';deadline=time.monotonic()+300
            try:
                while b'(anything else cancels): ' not in received:
                    if time.monotonic()>deadline:raise TimeoutError('Review preparation deadline elapsed.')
                    if select.select([master],[],[],.2)[0]:
                        chunk=os.read(master,8192)
                        if not chunk:raise RuntimeError('CLI closed before review.')
                        received+=chunk
                        if len(received)>32768:raise ValueError('Unexpected output volume.')
                digest=re.search(rb'"action_sha256":\s*"([a-f0-9]{64})"',received).group(1).decode()
                assert b'"operation": "n8n.calculate"' in received
                store=ApprovalStore(state/'guardian.sqlite3')
                with store._db() as db:
                    assert db.execute('SELECT status,used FROM approvals').fetchone()==('pending',0)
                    assert db.execute("SELECT COUNT(*) FROM audit WHERE event='consumed'").fetchone()[0]==0
                os.write(master,(('APPROVE '+digest[:12]) if choice=='approve' else 'REJECT').encode()+b'\n')
                output=b''
                while time.monotonic()<deadline:
                    if select.select([master],[],[],.2)[0]:
                        try:chunk=os.read(master,8192)
                        except OSError:chunk=b''
                        output+=chunk
                        if len(output)>32768:raise ValueError('Unexpected result volume.')
                    waited,status=os.waitpid(pid,os.WNOHANG)
                    if waited:
                        done=True;code=os.waitstatus_to_exitcode(status);break
                assert done,'CLI did not exit'
                marker=b'IGRIS_N8N_RESULT '
                if marker not in output:
                    raise RuntimeError('No verified workflow response; CLI output '+output[-1024:].decode(errors='replace'))
                result=json.loads(output.split(marker)[-1].splitlines()[0])
                with store._db() as db:
                    approval=db.execute('SELECT status,used FROM approvals').fetchone()
                    events=[item[0] for item in db.execute('SELECT event FROM audit')]
                if choice=='approve':
                    assert code==0 and result['origin']=='real_n8n_cli' and result['output']=={'left':7,'right':5,'total':12} and approval==('approved',1)
                    assert 'execution_succeeded' in events
                else:assert code==2 and result['executed'] is False and approval==('denied',0) and 'consumed' not in events
                rows.append({'decision_fixture':choice,'result':result,'approval':approval,'audit_events':events,'wall_seconds':time.monotonic()-started})
                destination.write_text(json.dumps({'status':'RUNNING','observations':rows},indent=2)+'\n')
                print(choice+': real n8n acceptance PASS',flush=True)
            finally:
                if not done:
                    try:os.killpg(pid,signal.SIGINT)
                    except ProcessLookupError:pass
                    try:os.waitpid(pid,0)
                    except ChildProcessError:pass
                os.close(master)
    files=['src/igris/guardian/activities.py','src/igris/guardian/approvals.py','src/igris/guardian/policy.py','src/igris/isolated.py',
           'src/igris/integrations/n8n_runtime.py','src/igris/integrations/n8n_cli.py','integrations/n8n/worker.py','integrations/n8n/profile.json','workflows/n8n-bounded-calculation.json','scripts/test_n8n_runtime_live.py']
    data={'status':'PASS','verified_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),'observations':rows,
        'owner_inputs':'automated PTY owner fixtures; no model approval','inference':'not used; real native n8n calculation through IGRIS Guardian',
        'external_workflows':'disabled; no service/account/HTTP endpoint connected',
        'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}}
    if findings(json.dumps(data)):raise ValueError('Evidence requires secret review.')
    destination.write_text(json.dumps(data,indent=2)+'\n')

if __name__=='__main__':main()
