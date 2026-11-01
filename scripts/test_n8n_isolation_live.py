"""Fixed developer OS probe in the same restricted n8n profile; not a workflow mock."""
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.isolated import IsolatedWorker
from igris.integrations.n8n_runtime import RUNTIME
program=r'''import errno,json,os,socket
from pathlib import Path
status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
assert os.getuid()>0 and int(status['CapEff'].strip(),16)==0 and status['NoNewPrivs'].strip()=='1'
root_ro=any(line.split()[1]=='/' and 'ro' in line.split()[3].split(',') for line in Path('/proc/mounts').read_text().splitlines())
assert root_ro and not Path('/var/run/docker.sock').exists()
try:Path('/opt/igris/node_modules/.igris-write-probe').write_text('probe')
except OSError as exc:assert exc.errno==errno.EROFS
else:raise AssertionError('Runtime mount unexpectedly writable')
s=socket.socket();s.settimeout(.2)
try:s.connect(('192.0.2.1',9))
except OSError as exc:assert exc.errno==errno.ENETUNREACH;egress_errno=exc.errno
else:raise AssertionError('External network unexpectedly reachable')
finally:s.close()
limits={name:Path('/sys/fs/cgroup/'+name).read_text().strip() for name in ('memory.max','pids.max','cpu.max')}
assert limits['memory.max']=='2147483648' and limits['pids.max']=='128'
quota,period=map(int,limits['cpu.max'].split());assert quota==2*period
print(json.dumps({'uid':os.getuid(),'capabilities_effective':0,'no_new_privileges':True,'root_readonly':root_ro,'runtime_mount_readonly':True,'docker_socket_present':False,'external_network_errno':egress_errno,'limits':limits}))'''
profile=json.loads((ROOT/'integrations/n8n/profile.json').read_text())
raw=IsolatedWorker().run(profile['image'],['/opt/igris/python/bin/python3.14','-I','-S','-c',program],[(ROOT/'runtime/python3149/python','/opt/igris/python'),(RUNTIME/'node_modules','/opt/igris/node_modules')],component='n8n',mount_profile='n8n-test-runtime',timeout=30,memory='2g')
proof={'status':'PASS','profile':'same pinned n8n image, flags and runtime mounts; fixed developer OS probe','observed':json.loads(raw),'source_sha256':hashlib.sha256((ROOT/'src/igris/isolated.py').read_bytes()).hexdigest()}
(ROOT/'runtime/n8n/isolation-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
