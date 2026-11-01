"""Manual disposable demonstration only. Refuses to overwrite any existing path."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT/'runtime/guardian-demo'
    destination.mkdir(mode=0o700)
    workspace = destination/'workspace';workspace.mkdir(mode=0o700)
    (workspace/'note.txt').write_text('An ordinary approved IGRIS demonstration document.\n')
    profile = destination/'tools.json'
    fd=os.open(profile,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as handle:
        json.dump({'version':1,'workspace':str(workspace),'allowed_operations':
            ['get_current_time','list_workspace_files','read_workspace_file'],'directories':['.'],
            'files':['note.txt'],'approval_required':[]},handle,indent=2)
        handle.write('\n')
    print(json.dumps({'profile':str(profile),'workspace':str(workspace),'native_tools_enabled':False}))


if __name__ == '__main__': main()
