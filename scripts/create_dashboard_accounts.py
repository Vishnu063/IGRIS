"""Explicit private random local credentials; never print secrets or overwrite."""
import argparse,json,secrets,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.memory import private_file

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 args.output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 path=private_file(args.output,create=True)
 path.write_text(json.dumps({name:[secrets.token_urlsafe(32),name] for name in ('owner','viewer')},indent=2)+'\n')
 print('Created private owner/viewer account file. Inspect it locally; do not commit or paste credentials into chat.')
if __name__=='__main__':main()
