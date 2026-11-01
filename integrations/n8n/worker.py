"""Real private n8n CLI invocation. No public endpoint, arbitrary node or workflow."""
import hashlib,json,os,re,resource,secrets,sqlite3,subprocess,sys,tempfile,time
from pathlib import Path
os.umask(0o077)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(120,120))

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate request key.')
        result[key]=value
    return result

request=json.loads(sys.stdin.buffer.read(32769),object_pairs_hook=unique)
if type(request) is not dict or set(request)!={'schema_version','request_id','mission_id','arguments'} or type(request['schema_version']) is not int or request['schema_version']!=1:raise ValueError('Invalid workflow request.')
for key in ('request_id','mission_id'):
    if type(request[key]) is not str or not re.fullmatch('[a-f0-9]{32}',request[key]):raise ValueError('Invalid workflow correlation.')
args=request['arguments']
if type(args) is not dict or set(args)!={'left','right','workflow_sha256'} or any(type(args[k]) is not int or not -1000<=args[k]<=1000 for k in ('left','right')):raise ValueError('Invalid arithmetic input.')
workflow=json.loads(Path('/opt/igris/template.json').read_text())
if len(workflow['nodes'])!=2 or [n['type'] for n in workflow['nodes']]!=['n8n-nodes-base.manualTrigger','n8n-nodes-base.set'] or workflow['active'] is not False:raise ValueError('Unreviewed workflow nodes.')
assignments=workflow['nodes'][1]['parameters']['assignments']['assignments']
assignments[0]['value']=args['left'];assignments[1]['value']=args['right'];assignments[2]['value']='={{ ('+str(args['left'])+') + ('+str(args['right'])+') }}'
raw=json.dumps(workflow,sort_keys=True,separators=(',',':')).encode()
if hashlib.sha256(raw).hexdigest()!=args['workflow_sha256']:raise ValueError('Approved workflow hash mismatch.')
Path('/tmp/calculation.json').write_bytes(raw)
Path('/tmp/n8n-home').mkdir(mode=0o700)
env={'PATH':'/opt/igris:/usr/bin:/bin','HOME':'/tmp/n8n-home','N8N_USER_FOLDER':'/tmp/n8n-home','DB_TYPE':'sqlite',
     'DB_SQLITE_DATABASE':'/tmp/n8n-state.sqlite','N8N_LOG_LEVEL':'info','N8N_DIAGNOSTICS_ENABLED':'false',
     'N8N_VERSION_NOTIFICATIONS_ENABLED':'false','N8N_TEMPLATES_ENABLED':'false','N8N_COMMUNITY_PACKAGES_ENABLED':'false',
     'N8N_LICENSE_AUTO_RENEW_ENABLED':'false','N8N_ENCRYPTION_KEY':secrets.token_hex(32),'N8N_BLOCK_ENV_ACCESS_IN_NODE':'true',
     'NODES_INCLUDE':json.dumps(['n8n-nodes-base.manualTrigger','n8n-nodes-base.set']),'N8N_RUNNERS_MODE':'internal',
     'N8N_RUNNERS_MAX_CONCURRENCY':'1','N8N_RUNNERS_BROKER_LISTEN_ADDRESS':'127.0.0.1','N8N_LISTEN_ADDRESS':'127.0.0.1',
     'NODE_OPTIONS':'--no-node-snapshot --max-old-space-size=1024','NO_PROXY':'127.0.0.1,localhost','LC_ALL':'C.UTF-8'}
cli=['/opt/igris/node','/opt/igris/node_modules/n8n/bin/n8n'];started=time.monotonic()
# SQLite native binding and installed CLI version are actually loaded in this container.
probe=subprocess.run(['/opt/igris/node','-e','require("/opt/igris/node_modules/sqlite3"); require("/opt/igris/node_modules/isolated-vm");'],env=env,capture_output=True,timeout=10)
if probe.returncode:raise RuntimeError('Compatible native runtime unavailable.')
version=subprocess.run(cli+['--version'],env=env,capture_output=True,text=True,timeout=10,check=True)
if version.stdout.strip()!='2.45.7':raise ValueError('Pinned n8n version mismatch.')
with tempfile.TemporaryFile() as logs:
    process=subprocess.run(cli+['import:workflow','--input=/tmp/calculation.json'],stdout=logs,stderr=subprocess.STDOUT,env=env,timeout=70)
    if process.returncode:raise RuntimeError('Workflow import failed.')
with tempfile.TemporaryFile() as output:
    process=subprocess.run(cli+['execute','--id='+workflow['id'],'--rawOutput'],stdout=output,stderr=subprocess.STDOUT,env=env,timeout=90)
    output.seek(0);body=output.read(1048577).decode('utf-8')
if process.returncode or len(body)>1048576:raise RuntimeError('Workflow execution failed or result exceeds limit.')
parsed=None;decoder=json.JSONDecoder(object_pairs_hook=unique)
for match in re.finditer(r'(?m)^\{',body):
    try:
        candidate,end=decoder.raw_decode(body[match.start():])
        if not body[match.start()+end:].strip():parsed=candidate
    except ValueError:continue
if type(parsed) is not dict or parsed.get('data',{}).get('resultData',{}).get('error'):raise ValueError('No successful real workflow result.')
actual=parsed['data']['resultData']['runData']['Calculation'][0]['data']['main'][0][0]['json']
expected={'left':args['left'],'right':args['right'],'total':args['left']+args['right']}
if actual!=expected:raise ValueError('Actual n8n output mismatch.')
with sqlite3.connect('file:/tmp/n8n-state.sqlite?mode=ro',uri=True) as db:
    rows=db.execute('SELECT id,status,workflowId FROM execution_entity').fetchall()
if len(rows)!=1 or rows[0][1:]!=('success',workflow['id']):raise ValueError('Successful execution record not verified.')
print(json.dumps({'schema_version':1,'request_id':request['request_id'],'mission_id':request['mission_id'],
      'workflow_sha256':args['workflow_sha256'],'execution_id':str(rows[0][0]),'status':'completed','output':actual,
      'origin':'real_n8n_cli','elapsed_seconds':time.monotonic()-started}))
