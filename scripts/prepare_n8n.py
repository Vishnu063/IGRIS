"""Explicit Linux development preparation. No Mac/global install or service start."""
import argparse,base64,hashlib,io,json,os,platform,re,shutil,signal,subprocess,tarfile,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def load_lock(folder=None):
    folder=Path(folder) if folder else ROOT/'integrations/n8n/lock'
    manifest=json.loads((folder/'manifest.json').read_text());packages={};seen=set()
    for part in manifest['parts']:
        name=part['file']
        if not re.fullmatch(r'part-[0-9]{3}\.json',name) or name in seen:raise ValueError('Invalid lock partition.')
        seen.add(name);raw=(folder/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=part['sha256']:raise ValueError('Dependency lock partition changed.')
        entries=json.loads(raw)['packages']
        if set(entries)&set(packages):raise ValueError('Duplicate dependency record.')
        packages.update(entries)
    lock={key:packages if key=='packages' else manifest['header'][key] for key in manifest['root_order']}
    raw=(json.dumps(lock,indent=2)+'\n').encode()
    if hashlib.sha256(raw).hexdigest()!=manifest['original_sha256']:raise ValueError('Dependency lock reconstruction differs.')
    return raw,manifest['package_json']


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--install',action='store_true');args=parser.parse_args()
    raw,package=load_lock();profile=json.loads((ROOT/'integrations/n8n/profile.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=profile['package_lock_sha256']:raise ValueError('Lock not approved by runtime profile.')
    print('PASS: exact dependency lock reconstructed; no runtime activated.',flush=True)
    if not args.install:return
    if platform.system()!='Linux' or platform.machine()!='x86_64':raise ValueError('Reviewed cloud Linux x86_64 only; no Mac/ARM installation.')
    import sys,threading
    sys.path.insert(0,str(ROOT/'src'))
    from igris.integrations.n8n_runtime import RUNTIME,tree_digest
    if RUNTIME.exists():
        if tree_digest(RUNTIME,threading.Event())!=profile['runtime_tree_sha256']:raise ValueError('Existing runtime differs; preserved unchanged.')
        print('PASS: existing runtime matches pinned tree; no files changed.');return
    node=Path(shutil.which('node') or '/nonexistent')
    with node.open('rb') as source:node_hash=hashlib.file_digest(source,'sha256').hexdigest()
    if node_hash!=profile['native_provenance']['node_sha256']:raise ValueError('Exact reviewed managed Node binary required; no automatic replacement.')
    if shutil.disk_usage('/tmp').free<4*1024**3:raise ValueError('At least 4 GiB disposable temporary disk required; no downloads started.')
    RUNTIME.mkdir(mode=0o700)
    (RUNTIME/'package.json').write_text(package);(RUNTIME/'package.json').chmod(0o600)
    (RUNTIME/'package-lock.json').write_bytes(raw);(RUNTIME/'package-lock.json').chmod(0o600)
    allowed=('PATH','HOME','TMPDIR','TMP','TEMP','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy','SSL_CERT_FILE','SSL_CERT_DIR','LANG','LC_ALL')
    env={k:os.environ[k] for k in allowed if k in os.environ}
    env['NODE_EXTRA_CA_CERTS']='/etc/ssl/certs/ca-certificates.crt'
    with tempfile.TemporaryDirectory(prefix='igris-n8n-prepare-',dir='/tmp') as cache:
        with tempfile.TemporaryFile() as log:
            process=subprocess.Popen(['npm','ci','--prefix',str(RUNTIME),'--userconfig=/dev/null','--globalconfig=/dev/null','--registry=https://registry.npmjs.org','--logs-max=0','--cache='+cache,'--ignore-scripts','--omit=optional','--audit=false','--fund=false'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            started=time.monotonic()
            try:
                while process.poll() is None:
                    if shutil.disk_usage('/tmp').free<512*1024**2 or time.monotonic()-started>600:raise RuntimeError('Preparation disk/deadline guard stopped installation; candidate retained for inspection.')
                    time.sleep(1)
                if process.returncode:raise RuntimeError('Locked dependency preparation failed; private output withheld.')
            finally:
                if process.poll() is None:
                    os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
    native=profile['native_provenance']
    with urllib.request.urlopen(native['sqlite_url'],timeout=60) as response:asset=response.read(2*1024**2+1)
    if hashlib.sha256(asset).hexdigest()!=native['sqlite_archive_sha256']:raise ValueError('SQLite release asset differs.')
    with tarfile.open(fileobj=io.BytesIO(asset)) as archive:
        member=archive.getmember('build/Release/node_sqlite3.node')
        if not member.isfile() or member.size>8*1024**2:raise ValueError('Unexpected native asset.')
        binding=archive.extractfile(member).read()
    if hashlib.sha256(binding).hexdigest()!=native['sqlite_binding_sha256']:raise ValueError('Native binding differs.')
    target=RUNTIME/'node_modules/sqlite3/build/Release/node_sqlite3.node';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(binding);target.chmod(0o600)
    shutil.copyfile(node,RUNTIME/'node');(RUNTIME/'node').chmod(0o700)
    if tree_digest(RUNTIME,threading.Event())!=profile['runtime_tree_sha256']:raise ValueError('Candidate differs from verified runtime. Review and real tests required; activation denied.')
    print('PASS: pinned optional runtime prepared; no workflow/service started.')


if __name__=='__main__':main()
