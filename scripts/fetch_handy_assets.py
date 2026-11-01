"""Explicit public pinned downloads only; no application/model runs or Mac changes."""
import hashlib
import json
from pathlib import Path
import platform
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def fetch(url,path,expected,maximum):
    if path.exists():
        with path.open('rb') as existing: digest=hashlib.file_digest(existing,'sha256').hexdigest()
        if digest!=expected:raise ValueError('Existing task asset differs; preserved unchanged.')
        return
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    temporary=None
    try:
        with urllib.request.urlopen(url,timeout=60) as source,tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as target:
            temporary=Path(target.name);sha=hashlib.sha256();size=0
            while chunk:=source.read(1024*1024):
                size+=len(chunk)
                if size>maximum:raise ValueError('Asset exceeds declared budget.')
                sha.update(chunk);target.write(chunk)
        if sha.hexdigest()!=expected:raise ValueError('Asset integrity failure.')
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():temporary.unlink()


def main():
    if platform.system()!='Linux' or platform.machine()!='x86_64':raise ValueError('Reviewed cloud runtime only; no Mac installation.')
    p=json.loads((ROOT/'integrations/handy/profile.json').read_text())
    folder=ROOT/'runtime/handy'
    fetch(p['package_url'],folder/'Handy.deb',p['package_sha256'],64*1024**2)
    fetch(p['model_url'],folder/p['model_file'],p['model_sha256'],512*1024**2)
    print('PASS: public Handy release and Whisper Small hashes verified; nothing activated.')


if __name__=='__main__':main()
