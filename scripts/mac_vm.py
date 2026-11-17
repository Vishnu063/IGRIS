"""Owner-invoked dedicated Mac VM operations. Never a model-accessible tool."""
import hashlib,json,os,re,subprocess,tarfile,tempfile,shutil,stat
from pathlib import Path,PurePosixPath
from mac_package import Blocked,ROOT,check,vm_command,digest

def validate_instance(instance,root):
    """Lima v2.3.0 pkg/limatype/lima_instance.go and lima_yaml.go schemas."""
    config=instance.get('config',{})
    expected={'name':'igris','arch':'aarch64','vmType':'vz','cpus':2,'memory':4*1024**3,'disk':24*1024**3,'dir':str(Path(root)/'vm-state/igris')}
    if any(instance.get(k)!=v for k,v in expected.items()) or instance.get('errors') or instance.get('autoStartedIdentifier'):raise Blocked('Dedicated native VZ instance/resource identity differs; no emulation or autostart accepted.')
    if config.get('mounts') or config.get('provision') or config.get('copyToHost') or config.get('additionalDisks'):raise Blocked('Host sharing or unreviewed provisioning denied.')
    if config.get('rosetta',{}).get('enabled') is not False or config.get('rosetta',{}).get('binfmt') is not False:raise Blocked('Rosetta/emulation must be explicitly disabled.')
    if config.get('ssh',{}).get('forwardAgent') is not False or config.get('ssh',{}).get('forwardX11') is not False:raise Blocked('Agent/X11 forwarding denied.')
    if config.get('containerd',{}).get('system') is not False or config.get('containerd',{}).get('user') is not False:raise Blocked('Unrequested containerd services denied.')
    forwards=config.get('portForwards',[])
    if len(forwards)!=2:raise Blocked('Exact loopback-only forwarding policy required.')
    first,last=forwards
    if any(row.get(key) for row in forwards for key in ('hostSocket','guestSocket')):raise Blocked('Socket forwarding denied.')
    if any(first.get(k)!=v for k,v in {'guestIP':'127.0.0.1','guestPort':8765,'hostIP':'127.0.0.1','hostPort':8765}.items()) or last.get('ignore') is not True or last.get('guestPortRange')!=[1,65535]:raise Blocked('Public or unreviewed port forwarding denied.')
    return instance

def inspect_instance(binary,env,root):
    raw=subprocess.check_output([binary,'list','--json','igris'],env=env,text=True,timeout=10)
    rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(rows)!=1 or type(rows[0]) is not dict:raise Blocked('Exactly one dedicated Lima instance required.')
    return validate_instance(rows[0],root)

def measure_host(instance):
    # Read only pid/ppid/rss, never unrelated argv/environment/credentials.
    raw=subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,rss='],text=True,timeout=5)
    rows=[tuple(map(int,line.split())) for line in raw.splitlines() if len(line.split())==3]
    owned={instance.get('hostAgentPID',0),instance.get('driverPID',0)}-{0};changed=True
    while changed:
        more={pid for pid,parent,rss in rows if parent in owned};changed=not more<=owned;owned|=more
    swap=subprocess.check_output(['/usr/sbin/sysctl','-n','vm.swapusage'],text=True,timeout=5).strip()
    match=re.search(r'used\s*=\s*([0-9.]+)([KMG])',swap)
    if not match:raise Blocked('Mac swap measurement unavailable.')
    return {'host_vm_process_rss_bytes':sum(rss*1024 for pid,_,rss in rows if pid in owned),'host_vm_process_count':sum(pid in owned for pid,_,_ in rows),'host_swap_used_bytes':int(float(match[1])*{'K':1024,'M':1024**2,'G':1024**3}[match[2]]),'physical_memory_bytes':int(subprocess.check_output(['/usr/sbin/sysctl','-n','hw.memsize'],text=True,timeout=5)),'method':'Current ps RSS of Lima-reported host-agent/driver PIDs and descendants; shared pages may be counted more than once. Total host swap via sysctl; not unique physical RAM.'}

def extract_lima(archive,target):
    """No tar extractall reliance on the owner's older Python tar filters."""
    target=Path(target).absolute()
    if target.resolve()!=target:raise Blocked('Canonical extraction directory required.')
    target.mkdir(mode=0o700,exist_ok=True)
    with tarfile.open(archive) as source:
        members=source.getmembers()
        if len(members)>10000 or sum(m.size for m in members)>512*1024**2:raise Blocked('Lima expansion exceeds reviewed bounds.')
        links=[]
        for member in members:
            parts=PurePosixPath(member.name)
            if parts.is_absolute() or '..' in parts.parts or len(member.name)>512:raise Blocked('Unsafe archive path.')
            path=target.joinpath(*parts.parts)
            if path==target:
                if not member.isdir():raise Blocked('Unexpected archive root.')
                continue
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.parent.resolve()!=path.parent or path.is_symlink():raise Blocked('Archive symlink parent denied.')
            if member.isdir():path.mkdir(exist_ok=True)
            elif member.isfile():
                fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o755 if member.mode&0o111 else 0o644)
                with os.fdopen(fd,'wb') as out,source.extractfile(member) as inp:shutil.copyfileobj(inp,out)
            elif member.issym():links.append((path,member.linkname))
            else:raise Blocked('Archive special/hard-linked file denied.')
        for path,name in links:
            if Path(name).is_absolute() or not (path.parent/name).resolve().is_relative_to(target.resolve()):raise Blocked('Archive link escape denied.')
            path.symlink_to(name)

def verify_lima(target):
    target=Path(target);manifest_path=target/'igris-install-manifest.json'
    if manifest_path.is_symlink():raise Blocked('Unknown Lima installation preserved.')
    record=json.loads(manifest_path.read_text())
    if set(record)!={'files','links','directories','version'} or record['version']!='v2.3.0' or not record['files']:raise Blocked('Exact Lima installation manifest required.')
    for name,want in record['files'].items():
        relative=PurePosixPath(name);path=target/name
        if relative.is_absolute() or '..' in relative.parts or path.resolve()!=path or not path.is_file() or digest(path)!=want:raise Blocked('Modified Lima file preserved; execution denied.')
    for name,want in record['links'].items():
        relative=PurePosixPath(name);path=target/name
        if relative.is_absolute() or '..' in relative.parts or not path.is_symlink() or os.readlink(path)!=want:raise Blocked('Modified Lima link preserved.')
    for name in record['directories']:
        relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or (target/name).is_symlink():raise Blocked('Unrecognized Lima directory preserved.')
    return record

def install_lima(root,allow_downloads):
    check(root)
    if not allow_downloads:raise Blocked('Explicit --allow-downloads required for the pinned Lima binaries; no Homebrew/global install.')
    target=Path(root)/'lima'
    if target.exists():raise Blocked('Existing Lima files preserved; no overwrite.')
    from fetch_hermes_probe_assets import fetch
    pins=json.loads((ROOT/'packaging/macos/assets.json').read_text())['lima']
    with tempfile.TemporaryDirectory(dir=root,prefix='lima-download-') as folder:
        for item in pins['artifacts']:
            archive=fetch(Path(folder),item['name'],item['url'],item['sha256'],item['bytes'])
            extract_lima(archive,target)
    files={str(p.relative_to(target)):digest(p) for p in target.rglob('*') if p.is_file() and not p.is_symlink()}
    links={str(p.relative_to(target)):os.readlink(p) for p in target.rglob('*') if p.is_symlink()}
    (target/'igris-install-manifest.json').write_text(json.dumps({'files':files,'links':links,'directories':[str(p.relative_to(target)) for p in target.rglob('*') if p.is_dir() and not p.is_symlink()],'version':pins['version']},indent=2)+'\n')
    (target/'igris-install-manifest.json').chmod(0o600)
    result=subprocess.check_output([str(target/'bin/limactl'),'--version'],text=True,timeout=5).strip()
    if result!='limactl version 2.3.0':raise Blocked('Unexpected native Lima version; retained for review.')
    print('Installed pinned Lima under the private IGRIS directory only. No VM, model or login item started.')
    return 0

def perform(args,root):
    root=Path(root);check(root)
    if args.action=='install-lima':return install_lima(root,args.allow_downloads)
    # Reuse exact pinned binary, isolated LIMA_HOME, and override checks.
    command,env=vm_command(root,'stop-vm');binary=command[0]
    shell=[binary,'shell','igris']
    if args.action=='uninstall-lima':
        target=root/'lima';record=verify_lima(target)
        result=subprocess.check_output([binary,'list','--json'],env=env,text=True,timeout=10)
        if result.strip() not in ('','[]'):raise Blocked('VM profiles remain; stop, back up and explicitly remove only the dedicated profile first.')
        for name in record['files']:(target/name).unlink()
        for name in record['links']:(target/name).unlink()
        (target/'igris-install-manifest.json').unlink()
        for path in sorted((target/name for name in record['directories']),key=lambda p:len(p.parts),reverse=True):
            try:path.rmdir()
            except OSError:pass
        try:target.rmdir()
        except OSError:pass
        print('Removed unchanged manifest-listed Lima files only; retained unknown files, VM control history and user data.');return 0
    instance=inspect_instance(binary,env,root)
    if args.action=='measure':print(json.dumps(measure_host(instance),indent=2));return 0
    if args.action=='bootstrap-guest':
        if not args.allow_downloads or not re.fullmatch('[a-f0-9]{40}',args.commit or ''):raise Blocked('Explicit --allow-downloads and an exact reviewed --commit are required for guest packages/model.')
        return subprocess.run(shell+['bash','-s','--',args.commit],input=(ROOT/'packaging/macos/bootstrap_guest.sh').read_bytes(),env=env,check=False).returncode
    if args.action=='prepare-runtime':
        if not args.allow_downloads:raise Blocked('Explicit --allow-downloads required for native guest packages/model.')
        return subprocess.run(shell+['sg','docker','-c','python3 IGRIS/scripts/prepare_arm64_runtime.py --allow-downloads'],env=env,check=False).returncode
    if args.action=='verify-guest':
        samples=[measure_host(instance)];process=subprocess.Popen(shell+['sg','docker','-c','python3 IGRIS/scripts/verify_native_guest.py'],env=env)
        interrupted=False
        try:
            while process.poll() is None:
                try:process.wait(timeout=1)
                except subprocess.TimeoutExpired:samples.append(measure_host(instance))
        except BaseException:interrupted=True;raise
        finally:
            interrupted=interrupted or process.poll() is None or process.returncode!=0
            if interrupted:
                try:process.terminate();process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
                finally:
                    # Remote SSH interruption alone is not cleanup evidence.
                    # Stop only this dedicated, identity-checked VM, preserving disk.
                    subprocess.run([binary,'stop','igris'],env=env,check=True,timeout=60)
        samples.append(measure_host(instance))
        record={'guest_exit_code':process.returncode,'host':'actual native Apple Silicon macOS','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'baseline':samples[0],'after':samples[-1],'peak_vm_process_rss_bytes':max(s['host_vm_process_rss_bytes'] for s in samples),'peak_host_swap_used_bytes':max(s['host_swap_used_bytes'] for s in samples),'human_usability_accepted':False}
        target=root/'host-measurements.json'
        if target.exists() and (target.is_symlink() or target.stat().st_uid!=os.getuid()):raise Blocked('Unknown measurement file preserved.')
        fd=os.open(target,os.O_CREAT|os.O_WRONLY|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as stream:json.dump(record,stream,indent=2);stream.write('\n')
        print(json.dumps(record,indent=2));return process.returncode
    if args.action=='export-accounts':
        target=root/'dashboard-accounts.json'
        if target.exists() or target.is_symlink():raise Blocked('Existing local credential file preserved.')
        code="from pathlib import Path;import sys;sys.path.insert(0,'IGRIS/src');from igris.memory import private_file;sys.stdout.buffer.write(private_file(Path('IGRIS/runtime/mission-control/accounts.json')).read_bytes())"
        raw=subprocess.check_output(shell+['python3','-c',code],env=env,timeout=10)
        data=json.loads(raw)
        if set(data)!={'owner','viewer'} or any(type(v) is not list or len(v)!=2 or v[1]!=k or type(v[0]) is not str or len(v[0])<32 for k,v in data.items()):raise Blocked('Unexpected private account response.')
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(raw)
        print('Exported private dashboard credentials into IGRIS control directory. Do not paste the file into chat.');return 0
    if args.action=='start':
        try:
            if instance['status']=='Stopped':subprocess.run([binary,'start','igris'],env=env,check=True)
            inspect_instance(binary,env,root)
            # Explicit owner startup only: guest Docker, never host Docker.
            subprocess.run(shell+['sudo','systemctl','start','docker.service'],env=env,check=True)
            subprocess.run(shell+['sg','docker','-c','python3 IGRIS/scripts/verify_native_guest.py --check'],env=env,check=True)
            script='cd IGRIS && PYTHONPATH=src exec python3 -m igris.mission_control --remember --accounts-file runtime/mission-control/accounts.json --tools-config runtime/guardian-demo/tools.json'
            return subprocess.run(shell+['sg','docker','-c',script],env=env,check=False).returncode
        finally:
            # Release dedicated VM RAM after terminal shutdown/startup failure.
            # This never stops another Lima profile or an unrelated host process.
            subprocess.run([binary,'stop','igris'],env=env,check=True,timeout=60)
    raise Blocked('Unsupported dedicated VM operation.')
