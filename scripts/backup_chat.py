"""Manual owner data backup/restore; never an agent tool or approval restore."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.chat_backup import create_snapshot,restore_snapshot
from igris.conversations import ConversationMemory
from igris.scoped_memory import ScopedFacts
parser=argparse.ArgumentParser();parser.add_argument('action',choices=('create','restore'));parser.add_argument('--state-dir',type=Path,required=True);parser.add_argument('--file',type=Path,required=True);parser.add_argument('--expected-sha256');parser.add_argument('--approve-data-operation',action='store_true',required=True);args=parser.parse_args()
if args.action=='create':
 memory=ConversationMemory(args.state_dir/'chat.sqlite3','owner');facts=ScopedFacts(args.state_dir/'facts.sqlite3','owner',memory) if (args.state_dir/'facts.sqlite3').exists() else None
 result=create_snapshot(args.file,memory=memory,facts=facts,actor='owner',approved=args.approve_data_operation)
else:result=restore_snapshot(args.file,args.state_dir,expected_sha256=args.expected_sha256,actor='owner',approved=args.approve_data_operation)
print(json.dumps(result))
