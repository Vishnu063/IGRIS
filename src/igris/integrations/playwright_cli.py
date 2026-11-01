"""Manual local workflow invocation; decisions only from the controlling terminal."""
import argparse,json,sys
from pathlib import Path
from .playwright_runtime import OwnedBrowser,ROOT
from ..guardian.activities import OwnerActions
from ..guardian.approvals import ApprovalStore
from ..guardian.policy import Policy,Permission
from ..guardian.terminal import TerminalReview


def main():
    parser=argparse.ArgumentParser(description='Inspect one owned offline test site; no general browsing.')
    parser.add_argument('--enable-runtime',action='store_true',required=True)
    parser.add_argument('--state-dir',type=Path,default=ROOT/'runtime/playwright/state')
    args=parser.parse_args();terminal=TerminalReview();actions=None
    try:
        args.state_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
        path=args.state_dir/'guardian.sqlite3';store=ApprovalStore(path,initialize=not path.exists())
        adapter=OwnedBrowser(enabled=args.enable_runtime)
        actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),args.state_dir,store,[adapter.registration()])
        review=actions.prepare('owner','browser.inspect',{'site':'owned_acceptance','action':'inspect_and_screenshot'})
        choice=terminal.choose(review)
        if choice in ('approve','reject'):
            actions.decide('owner',review.mission_id,approve=choice=='approve',reviewed_digest=review.digest)
        else:actions.cancel('owner',review.mission_id,reason=choice)
        result=actions.run('owner',review.mission_id) if choice=='approve' else {'status':'blocked','decision':choice,'executed':False}
        print('IGRIS_BROWSER_RESULT '+json.dumps(result,sort_keys=True),flush=True)
        return 0 if result['status']=='completed' else 2
    finally:
        if actions:actions.close()
        terminal.close()


if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:print('Browser cancelled.',file=sys.stderr);raise SystemExit(130)
    except Exception as exc:print('Browser blocked or failed ('+type(exc).__name__+'); no result accepted.',file=sys.stderr);raise SystemExit(1)
