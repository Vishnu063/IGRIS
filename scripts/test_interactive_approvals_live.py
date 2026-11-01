"""Real Hermes + CLI controlling terminal + Guardian. Owner inputs are PTY fixtures."""
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from igris.guardian.approvals import ApprovalStore
from igris.guardian.secrets import findings


def record(data):
    with tempfile.NamedTemporaryFile('w',dir=ROOT/'runtime',delete=False) as handle:
        json.dump(data,handle,indent=2);handle.write('\n');name=Path(handle.name)
    name.replace(ROOT/'runtime/interactive-approval-live.json')


def main():
    record({'status':'RUNNING','origin':'not_yet_verified'})
    observations=[]
    with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='approval-live-') as name:
        root=Path(name);workspace=root/'workspace';workspace.mkdir(mode=0o700)
        config=root/'tools.json';config.write_text(json.dumps({'version':1,'workspace':str(workspace),
            'allowed_operations':['get_current_time'],'directories':[],'files':[],'approval_required':['get_current_time']}));config.chmod(0o600)
        for decision in ('approve','reject'):
            state=root/decision
            pid,master=pty.fork()
            if pid==0:
                os.chdir(ROOT)
                env=dict(os.environ,PYTHONPATH=str(ROOT/'src'))
                os.execvpe(sys.executable,[sys.executable,'-m','igris.chat','--remember','--state-dir',str(state),
                    '--tools-config',str(config),'--interactive-approvals'],env)
            received=b'';deadline=time.monotonic()+210;done=False
            def until(marker):
                nonlocal received
                while marker not in received:
                    if time.monotonic()>deadline:raise TimeoutError('Live terminal acceptance timed out.')
                    if select.select([master],[],[],.2)[0]:
                        try:chunk=os.read(master,8192)
                        except OSError:raise RuntimeError('CLI exited before acceptance marker.') from None
                        if not chunk:raise RuntimeError('CLI terminal closed.')
                        received+=chunk
                        if len(received)>32768:raise ValueError('Unexpected terminal output volume.')
                value=received;received=b'';return value
            start=time.monotonic()
            try:
                until(b'You: ')
                os.write(master,b'IGRIS, tell me the current time using your tool.\n')
                review_output=until(b'(anything else cancels): ')
                digest=re.search(rb'"action_sha256":\s*"([a-f0-9]{64})"',review_output).group(1).decode()
                assert b'"operation": "get_current_time"' in review_output and b'"risk": "read_only"' in review_output
                store=ApprovalStore(state/'guardian.sqlite3')
                with store._db() as db:
                    assert db.execute('SELECT status,used FROM approvals').fetchone()==('pending',0)
                    assert db.execute("SELECT COUNT(*) FROM tool_audit WHERE event IN ('authorized','completed')").fetchone()[0]==0
                before=time.monotonic()
                os.write(master,(('APPROVE '+digest[:12]) if decision=='approve' else 'REJECT').encode()+b'\n')
                result_output=until(b'You: ')
                decision_seconds=time.monotonic()-before
                if decision=='approve':assert b'IGRIS: Guardian executed get_current_time.' in result_output
                else:assert b'Action rejected.' in result_output and b'Guardian executed' not in result_output
                os.write(master,b'/exit\n')
                while time.monotonic()<deadline:
                    waited,status=os.waitpid(pid,os.WNOHANG)
                    if waited:
                        assert os.waitstatus_to_exitcode(status)==0;done=True;break
                    time.sleep(.1)
                assert done,'CLI did not stop'
                with store._db() as db:
                    approval=db.execute('SELECT status,used FROM approvals').fetchone()
                    audit=[r[0] for r in db.execute('SELECT event FROM audit')]
                    tool_events=[r[0] for r in db.execute('SELECT event FROM tool_audit')]
                import sqlite3
                with sqlite3.connect(state/'chat.sqlite3') as db:
                    exchange=db.execute('SELECT state,origin,model_sha256,api_calls FROM exchanges').fetchone()
                    assert db.execute('SELECT active FROM conversations').fetchone()[0] is None
                if decision=='approve':assert approval==('approved',1) and exchange[0]=='completed' and exchange[1]=='real_local_inference' and exchange[3]==1
                else:assert approval==('denied',0) and exchange[0]=='failed' and 'completed' not in tool_events
                observations.append({'decision_fixture':decision,'origin':'real_Hermes_CLI_PTY_Guardian',
                    'action_reviewed':{'operation':'get_current_time','arguments':{},'risk':'read_only'},
                    'no_execution_before_decision':True,'approval_state':approval,'approval_events':audit,
                    'tool_events':tool_events,'exchange':exchange,'post_decision_seconds':decision_seconds,
                    'end_to_end_seconds':time.monotonic()-start})
                print(decision+': PASS (actual model, terminal, broker)',flush=True)
            finally:
                if not done:
                    try:os.killpg(pid,signal.SIGINT)
                    except ProcessLookupError:pass
                    try:os.waitpid(pid,0)
                    except ChildProcessError:pass
                os.close(master)
    files=['src/igris/chat.py','src/igris/controller.py','src/igris/conversations.py',
           *[str(p.relative_to(ROOT)) for p in (ROOT/'src/igris/guardian').glob('*.py')],
           'scripts/test_interactive_approvals_live.py']
    data={'status':'PASS','verified_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),
          'observations':observations,'owner_inputs':'synthetic PTY owner decisions; not real human ergonomic testing',
          'mocked_inference_or_tools':False,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(files)}}
    if findings(json.dumps(data)):raise ValueError('Evidence requires secret review.')
    record(data)


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        record({'status':'STOPPED' if isinstance(exc,KeyboardInterrupt) else 'FAIL','error_class':type(exc).__name__});raise
