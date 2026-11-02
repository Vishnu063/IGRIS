"""Public version-only vulnerability audit; no credentials, prompts or paid services."""
import hashlib,json,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from email.parser import Parser
ROOT=Path(__file__).resolve().parents[1]
roots={'hermes':ROOT/'runtime/hermes-venv/lib/python3.14/site-packages','mem0':ROOT/'runtime/mem0/venv/lib/python3.14/site-packages','markitdown':ROOT/'runtime/markitdown/venv/lib/python3.14/site-packages'}
records={}
for component,root in roots.items():
 if not root.is_dir():raise RuntimeError('Expected optional runtime unavailable; do not silently omit audit.')
 for path in root.glob('*.dist-info/METADATA'):
  metadata=Parser().parsestr(path.read_text());key=(metadata['Name'],metadata['Version']);row=records.setdefault(key,{'name':key[0],'version':key[1],'components':[],'license_expression':metadata.get('License-Expression'),'license_metadata':(metadata.get('License') or '')[:180]});row['components'].append(component)
rows=sorted(records.values(),key=lambda row:row['name'].casefold());vulnerabilities=[];failures=[]
for start in range(0,len(rows),50):
 batch=rows[start:start+50];payload=json.dumps({'queries':[{'package':{'name':row['name'],'ecosystem':'PyPI'},'version':row['version']} for row in batch]}).encode()
 try:
  request=urllib.request.Request('https://api.osv.dev/v1/querybatch',data=payload,headers={'Content-Type':'application/json'});response=json.load(urllib.request.urlopen(request,timeout=45))
  if len(response.get('results',[]))!=len(batch):raise RuntimeError('Incomplete OSV result.')
  for row,result in zip(batch,response['results']):
   if type(result) is not dict or result.get('error'):
    failures.append({'package':row['name'],'error_type':'IncompletePackageResult'});continue
   for issue in result.get('vulns',[]):vulnerabilities.append({'package':row['name'],'version':row['version'],'components':row['components'],'id':issue['id']})
 except Exception as error:failures.append({'batch_start':start,'error_type':type(error).__name__})
proof={'status':'BLOCKED' if failures or vulnerabilities else 'PASS','source':'OSV public PyPI version queries','queried_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'package_count':len(rows),'inventory':rows,'vulnerabilities':vulnerabilities,'query_failures':failures,'scope':'Installed optional Python environments only; no claim about OS/npm/kernel or unaudited native binaries.','network_data':'Public package names/versions only; no credentials, prompts, files or account data.'}
(ROOT/'docs/validation/dependency-audit.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k!='inventory'}))
