"""Explicit local Ops Pilot read; no production target or remediation interface."""
import argparse,json,sys
from pathlib import Path
from .ops_runtime import ROOT,DisposableOpsFixture,RealOpsMonitor
from ..guardian.activities import OwnerActions
from ..guardian.approvals import ApprovalStore
from ..guardian.policy import Policy,Permission
from ..guardian.terminal import TerminalReview


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enable-runtime',action='store_true',required=True)
    target=parser.add_mutually_exclusive_group(required=True);target.add_argument('--demo',action='store_true');target.add_argument('--instance',type=Path)
    parser.add_argument('--state-dir',type=Path,default=ROOT/'runtime/ops/state')
    args=parser.parse_args();terminal=TerminalReview();fixture=None;actions=None
    try:
        if args.demo:fixture=DisposableOpsFixture().start()
        adapter=RealOpsMonitor(fixture.config_path if fixture else args.instance,enabled=args.enable_runtime)
        args.state_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
        path=args.state_dir/'guardian.sqlite3';store=ApprovalStore(path,initialize=not path.exists())
        actions=OwnerActions(Policy('owner',frozenset({Permission.READ})),args.state_dir,store,[adapter.registration()])
        review=actions.prepare('owner','ops.monitor',{'container_id':adapter.config['container_id']})
        choice=terminal.choose(review)
        if choice in ('approve','reject'):actions.decide('owner',review.mission_id,approve=choice=='approve',reviewed_digest=review.digest)
        else:actions.cancel('owner',review.mission_id,reason=choice)
        result=actions.run('owner',review.mission_id) if choice=='approve' else {'status':'blocked','executed':False}
        print(json.dumps(result,sort_keys=True),flush=True);return 0 if choice=='approve' else 2
    finally:
        try:
            if actions:actions.close()
        finally:
            try:
                if fixture:fixture.close()
            finally:terminal.close()


if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:print('Monitoring cancelled.',file=sys.stderr);raise SystemExit(130)
    except Exception as exc:print('Monitoring blocked or failed ('+type(exc).__name__+'); no result accepted.',file=sys.stderr);raise SystemExit(1)
