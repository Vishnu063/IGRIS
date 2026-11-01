"""Fifteen real scoped Hermes tasks. Owner decisions are explicit test fixtures."""
import hashlib,json,sys,tempfile,time,threading,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.specialists.live import LiveSpecialists
from igris.guardian.activities import OwnerActions
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Policy,Permission,Denied
CASES=[
 ('frontend','Write valid HTML for an email label associated with an email input. Put the for attribute on the label and the matching id on the input. Return only these two HTML elements.',r'(?i)<label[^>]*for=',r'(?i)<input[^>]*id='),
 ('backend','Design an HTTP API to create a task with a nonempty title. State the create method, success status and validation failure behavior.',r'POST',r'201'),
 ('mobile','Propose offline behavior for a mobile notes app. Explain how to preserve unsynced notes without a network and flag conflicts.',r'(?i)(local|offline)',r'(?i)(sync|conflict)'),
 ('ai_engineer','A retrieval assistant confuses untrusted documents with system instructions. Propose a source citation check and permission boundary.',r'(?i)(source|citat)',r'(?i)(permission|trust|boundar)'),
 ('devops','A small HTTP service needs a health probe. Explain a read-only /health endpoint and why a failed probe should not automatically authorize a restart.',r'(?i)health',r'(?i)(approv|authoriz|manual)'),
 ('security_privacy','A server logs Authorization header values. Identify the concrete credential exposure risk and recommend redaction without logging the raw value.',r'(?i)(credential|token|secret)',r'(?i)(redact|mask|remov)'),
 ('testing','Function clamp(x) returns 0 for x<0, 10 for x>10, otherwise x. Propose exact boundary test cases around 0 and 10.',r'0',r'10'),
 ('code_reviewer','Review Python: def add_item(item, items=[]): items.append(item); return items. Identify the shared mutable default bug and recommend a None default.',r'(?i)(mutable|shar)',r'None'),
 ('ui_ux','An approval dialog only shows an unlabeled green icon. Propose accessible Approve and Reject controls and visible action details.',r'(?i)approv',r'(?i)reject'),
 ('database','SQLite query SELECT * FROM events WHERE owner_id=? ORDER BY created_at DESC LIMIT 20 is slow. Recommend a composite index and verify with EXPLAIN QUERY PLAN.',r'owner_id',r'(?i)(index|explain)'),
 ('research','Supplied source A says a trial used 20 participants and found 12 preferred option B. Summarize only this evidence and give one limitation; no external research.',r'12',r'20'),
 ('project_manager','Plan a two-day delivery: day 1 implement a small API, day 2 test and owner review. State dependencies and an approval milestone; do not claim deployment.',r'(?i)(test|review)',r'(?i)(approv|owner)'),
 ('incident_response','Evidence: container state exited, exit code 137, OOMKilled=true. Distinguish the confirmed OOM kill from hypotheses about memory growth and propose read-only checks.',r'(?i)(OOM|memory)',r'(?i)(hypoth|possib|could|check)'),
 ('voice_ai','Propose manual push-to-talk controls with a visible recording indicator, stop, and text fallback. No always-on microphone.',r'(?i)(stop|manual)',r'(?i)text'),
 ('minimal_change','Bug: def average(xs): return sum(xs)/len(xs) fails for empty input. Propose only an empty-list guard that raises ValueError; preserve nonempty behavior.',r'ValueError',r'(?i)(empty|if not xs|len\(xs\))')]

def main():
 import re
 out=ROOT/'runtime/specialists';out.mkdir(mode=0o700,exist_ok=True);observed=[]
 with tempfile.TemporaryDirectory(dir=out) as folder:
  root=Path(folder);specialists=LiveSpecialists(enabled=True);store=ApprovalStore(root/'guardian.sqlite3',initialize=True)
  actions=OwnerActions(Policy('owner',frozenset({Permission.SPECIALIST})),root,store,[specialists.registration()])
  try:
   chosen=[case for case in CASES if not sys.argv[1:] or case[0] in sys.argv[1:]]
   if sys.argv[1:] and len(chosen)!=len(sys.argv[1:]):raise ValueError('Unknown or duplicate role selection.')
   for role,context,*checks in chosen:
    args=specialists.arguments(role,context);review=actions.prepare('owner','specialists.reason',args)
    try:actions.run('owner',review.mission_id)
    except Denied:pass
    else:raise AssertionError('Missing owner grant executed.')
    actions.decide('owner',review.mission_id,approve=True,reviewed_digest=review.digest)
    start=time.monotonic();result=actions.run('owner',review.mission_id);elapsed=time.monotonic()-start
    accepted=all(re.search(check,result['text']) for check in checks)
    observed.append({'role':role,'prompt':context,'result':result,'wall_seconds':elapsed,'correctness_checks':checks,'passed':accepted})
    (out/'live-partial.json').write_text(json.dumps(observed,ensure_ascii=False,indent=2)+'\n')
    print(role+': '+('PASS' if accepted else 'FAIL')+' '+result['text'],flush=True)
    # Complete the bounded evaluation matrix and preserve every failed answer.
    # A failed case keeps overall acceptance FAIL; it is never relabelled.
   with store._db() as db:used=db.execute('SELECT SUM(used) FROM approvals').fetchone()[0]
   assert used==len(chosen)
  finally:actions.close()
 proof={'status':'PASS' if all(item['passed'] for item in observed) else 'FAIL','source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['src/igris/specialists/live.py','scripts/hermes_specialist_worker.py','src/igris/adapters/hermes_chat.py','scripts/test_specialists_live.py']},'responses':observed,'approvals_consumed':used,'owner_inputs':'Automated trusted owner fixtures, not model decisions.','real_vs_simulated':'All fifteen responses generated by actual role-conditioned Hermes with native tools disabled; no autonomous edits or external research.'}
 (out/('live.json' if not sys.argv[1:] else 'selected-live.json')).write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 if proof['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
