"""Manual component console; exact approvals use only the controlling terminal."""
import argparse,json,sys
from pathlib import Path
from .ops_lifecycle import OpsIntegration,ROOT
from ..guardian.activities import OwnerActions
from ..guardian.approvals import ApprovalStore
from ..guardian.policy import Policy,Permission
from ..guardian.terminal import TerminalReview
from ..foreground import default_foreground

def main():
 parser=argparse.ArgumentParser(description='Explicit disposable-target Ops lifecycle, no production or remediation.')
 parser.add_argument('--state-dir',type=Path,default=ROOT/'runtime/ops/lifecycle-state');parser.add_argument('--instance',type=Path,required=True);parser.add_argument('--mode',choices=('manual','on_demand','monitoring'),default='manual');parser.add_argument('--enable-runtime',action='store_true',required=True);args=parser.parse_args()
 directory=args.state_dir.absolute();directory.mkdir(mode=0o700,parents=True,exist_ok=True);path=directory/'guardian.sqlite3';store=ApprovalStore(path,initialize=not path.exists());adapter=OpsIntegration(args.instance,mode=args.mode,enabled=args.enable_runtime);foreground=default_foreground();terminal=TerminalReview();actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),directory,store,[adapter.registration()],foreground=foreground)
 try:
  print('Ops component is stopped. Commands: start, status, probe, stop, exit. Decisions require the separate owner terminal challenge.')
  while True:
   try:command=input('Ops: ').strip()
   except EOFError:break
   if command=='exit':break
   if command not in ('start','status','probe','stop'):print('Unknown command.');continue
   review=None
   try:
    review=actions.prepare('owner','ops.lifecycle',adapter.arguments('monitor' if command=='probe' else command));choice=terminal.choose(review)
    if choice not in ('approve','reject'):actions.cancel('owner',review.mission_id,reason=choice);continue
    actions.decide('owner',review.mission_id,approve=choice=='approve',reviewed_digest=review.digest)
    if choice=='approve':
     result=actions.run('owner',review.mission_id);print(json.dumps({'task':foreground.lookup('owner',review.mission_id),'result':result}))
   except Exception as error:print('Operation blocked or failed: '+type(error).__name__)
 finally:
  try:actions.close()
  finally:
   try:adapter.shutdown()
   except Exception:foreground.block_cleanup('owner','ops.lifecycle');raise
   finally:terminal.close()
if __name__=='__main__':
 try:raise SystemExit(main())
 except KeyboardInterrupt:print('Ops cancelled; tracked cleanup attempted.',file=sys.stderr);raise SystemExit(130)
