"""Actual pinned adapter and SQLite audit deny before any unsafe runtime launch."""
import hashlib,json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.n8n_runtime import RealN8n
from igris.guardian.activities import OwnerActions
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Policy,Permission
from igris.adapters.contracts import AdapterUnavailable
from igris.mission_control import MissionControl
adapter=RealN8n(enabled=True)
with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='quarantine-') as folder:
 root=Path(folder);store=ApprovalStore(root/'guardian.sqlite3',initialize=True);actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),root,store,[adapter.registration()])
 try:
  try:actions.prepare('owner','n8n.calculate',{'left':7,'right':5})
  except AdapterUnavailable:pass
  else:raise AssertionError('Quarantined dependency tree accepted.')
  with store._db() as db:
   assert db.execute('SELECT COUNT(*) FROM approvals').fetchone()[0]==0
   assert db.execute("SELECT COUNT(*) FROM tool_audit WHERE event='denied'").fetchone()[0]==1
 finally:actions.close()
 control=MissionControl(root/'dashboard',remember=True,enable_n8n=True)
 try:assert control.snapshot('owner')['components']['n8n']['status']=='blocked_security_audit'
 finally:control.close()
proof={'status':'PASS','release_status':'BLOCKED','actual_runtime_gate_denied':True,'guardian_denial_audited':True,'no_approval_issued':True,'dashboard_reports_blocked':True,'unsafe_workflow_executed':False,'mocked':False,'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['src/igris/integrations/n8n_runtime.py','src/igris/mission_control.py','integrations/n8n/security-status.json','scripts/test_n8n_quarantine_live.py']}}
(ROOT/'docs/validation/n8n-quarantine-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
