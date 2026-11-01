"""Explicit cloud-only source/cache preparation, never a service or Mac install."""
import argparse,hashlib,io,json,os,platform,shutil,stat,sys,urllib.request,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.ops_runtime import source_digest


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    profile=json.loads((ROOT/'integrations/ops/profile.json').read_text())
    if not args.prepare:
        print('No source download, installation or service start. Pass --prepare explicitly on reviewed cloud Linux x86_64.');return
    if platform.system()!='Linux' or platform.machine()!='x86_64':raise ValueError('No Mac/ARM installation or x86 fallback authorized.')
    folder=ROOT/'runtime/ops';folder.mkdir(mode=0o700,exist_ok=True)
    if shutil.disk_usage(ROOT).free<256*1024**2:raise ValueError('Preserve at least 256MiB free disk.')
    for entry in profile['source_provenance']:
        name=Path(entry['directory']).name;target=folder/name
        if target.exists():
            if source_digest(target)!=profile['sources'][name]:raise ValueError('Existing source differs; preserved unchanged.')
            continue
        url='https://codeload.github.com/'+entry['repository']+'/zip/'+entry['revision']
        with urllib.request.urlopen(url,timeout=60) as response:raw=response.read(16*1024**2+1)
        if hashlib.sha256(raw).hexdigest()!=entry['archive_sha256']:raise ValueError('Pinned upstream archive differs.')
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries=archive.infolist()
            if len(entries)>2000 or sum(item.file_size for item in entries)>64*1024**2:raise ValueError('Archive exceeds source budget.')
            for item in entries:
                path=PurePosixPath(item.filename)
                if path.is_absolute() or '..' in path.parts or stat.S_ISLNK(item.external_attr>>16):raise ValueError('Unsafe source archive path.')
                out=target/Path(*path.parts[1:])
                if item.is_dir():out.mkdir(parents=True,exist_ok=True);continue
                out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(archive.read(item));out.chmod(0o555 if item.external_attr>>16&0o111 else 0o444)
        if source_digest(target)!=profile['sources'][name]:raise ValueError('Unmodified source tree check failed.')
    expected=profile['files']['runtime/ops/docker'];target=folder/'docker'
    source=target if target.exists() else Path(shutil.which('docker') or '/nonexistent')
    with source.open('rb') as handle:actual=hashlib.file_digest(handle,'sha256').hexdigest()
    if actual!=expected:raise ValueError('Exact reviewed existing Docker CLI required; no automatic install.')
    if not target.exists():shutil.copyfile(source,target);target.chmod(0o500)
    print('PASS: pinned unmodified source and existing Docker client prepared. No app, monitoring service or recovery started.')


if __name__=='__main__':main()
