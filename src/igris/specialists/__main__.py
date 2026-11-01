"""List or manually approve one real specialist task, never an autonomous batch."""
import argparse,json
from pathlib import Path
from .live import LiveSpecialists
from .journal import record
from ..guardian.activities import OwnerActions
from ..guardian.approvals import ApprovalStore
from ..guardian.policy import Policy,Permission
from ..guardian.terminal import TerminalReview

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--list',action='store_true');parser.add_argument('--role');parser.add_argument('--context');parser.add_argument('--enable-runtime',action='store_true');parser.add_argument('--state-dir',type=Path,default=Path('runtime/specialists/state'))
    args=parser.parse_args();specialists=LiveSpecialists(enabled=args.enable_runtime)
    if args.list:print(json.dumps(specialists.choices(),indent=2));return
    if not args.role or not args.context or not args.enable_runtime:parser.error('Explicit --enable-runtime, --role and --context required.')
    terminal=TerminalReview();actions=None
    try:
        args.state_dir.mkdir(mode=0o700,parents=True,exist_ok=True);db=args.state_dir/'guardian.sqlite3'
        actions=OwnerActions(Policy('owner',frozenset({Permission.SPECIALIST})),args.state_dir,ApprovalStore(db,initialize=not db.exists()),[specialists.registration()])
        review=actions.prepare('owner','specialists.reason',specialists.arguments(args.role,args.context));choice=terminal.choose(review)
        if choice in ('approve','reject'):actions.decide('owner',review.mission_id,approve=choice=='approve',reviewed_digest=review.digest)
        else:actions.cancel('owner',review.mission_id,reason=choice)
        result=actions.run('owner',review.mission_id) if choice=='approve' else {'status':'blocked'}
        if choice=='approve':record(args.state_dir/'results.sqlite3','owner',review,result)
        print(json.dumps(result,ensure_ascii=False))
    finally:
        if actions:actions.close()
        terminal.close()
if __name__=='__main__':main()
