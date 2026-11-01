"""Actual malformed-PDF worker failure and owned cleanup, no mocked parser."""
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.markitdown_runtime import Documents
from igris.guardian.activities import OwnerActions
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Policy,Permission
from igris.adapters.contracts import AdapterUnavailable
with tempfile.TemporaryDirectory(dir=ROOT/'runtime/markitdown') as folder:
 root=Path(folder);(root/'broken.pdf').write_bytes(b'%PDF-1.7\ninvalid PDF body');adapter=Documents(root,['broken.pdf'],enabled=True);store=ApprovalStore(root/'guardian.sqlite3',initialize=True);actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),root,store,[adapter.registration()])
 try:
  review=actions.prepare('owner','documents.convert',{'path':'broken.pdf'});actions.decide('owner',review.mission_id,approve=True,reviewed_digest=review.digest)
  try:actions.run('owner',review.mission_id)
  except AdapterUnavailable as error:
   assert type(error) is AdapterUnavailable and str(error)=='Isolated worker failed; private output not published.', 'A genuine parser worker failure is required.'
  else:raise AssertionError('Malformed PDF accepted.')
  assert not actions.status('owner')['pending']
 finally:actions.close()
proof={'status':'PASS','real_malformed_pdf_denied':True,'owned_worker_cleanup_verified':True,'mocked':False}
(ROOT/'docs/validation/markitdown-failure-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
