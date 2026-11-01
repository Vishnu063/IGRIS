"""Read-only metadata/source evaluation; no model/provider/agent activation."""
import hashlib,io,json,subprocess,sys,time,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.guardian.readonly import parse_proposal,components
from pydantic import BaseModel,ConfigDict,TypeAdapter,field_validator
from typing import Literal,Union
class Empty(BaseModel):model_config=ConfigDict(strict=True,extra='forbid')
class PathArgs(Empty):
 path:str
 @field_validator('path')
 @classmethod
 def bounded(cls,value):components(value,directory=True);return value
class TimeTool(Empty):operation:Literal['get_current_time'];arguments:Empty
class ReadTool(Empty):operation:Literal['read_workspace_file','list_workspace_files'];arguments:PathArgs
adapter=TypeAdapter(Union[TimeTool,ReadTool])
cases=[('time','{"operation":"get_current_time","arguments":{}}'),('read','{"operation":"read_workspace_file","arguments":{"path":"report.txt"}}'),('extra','{"operation":"get_current_time","arguments":{"extra":1}}'),('shell','{"operation":"shell.execute","arguments":{}}'),('absolute','{"operation":"read_workspace_file","arguments":{"path":"/etc/passwd"}}'),('traversal','{"operation":"read_workspace_file","arguments":{"path":"../x.txt"}}'),('bool_path','{"operation":"read_workspace_file","arguments":{"path":true}}'),('duplicate','{"operation":"get_current_time","operation":"get_current_time","arguments":{}}')]
rows=[]
for name,raw in cases:
 row={'case':name}
 for label,validate in [('guardian',parse_proposal),('standalone_pydantic_strict',adapter.validate_json)]:
  try:validate(raw)
  except Exception:row[label]='denied'
  else:row[label]='accepted'
 rows.append(row)
assert all(row['guardian']==('accepted' if row['case'] in ('time','read') else 'denied') for row in rows)
assert rows[-1]['standalone_pydantic_strict']=='accepted'
metadata=[]
for name in ('pydantic-ai','pydantic-ai-slim'):
 raw=urllib.request.urlopen('https://pypi.org/pypi/'+name+'/2.64.0/json',timeout=30).read();data=json.loads(raw);wheel=next(x for x in data['urls'] if x['filename'].endswith('.whl'))
 row={'name':name,'version':'2.64.0','metadata_sha256':hashlib.sha256(raw).hexdigest(),'license':data['info'].get('license_expression'),'base_requirements':[x for x in data['info']['requires_dist'] if ';' not in x],'wheel_bytes':wheel['size'],'wheel_sha256':wheel['digests']['sha256']}
 if name.endswith('slim'):
  payload=urllib.request.urlopen(wheel['url'],timeout=30).read();assert hashlib.sha256(payload).hexdigest()==row['wheel_sha256'];archive=zipfile.ZipFile(io.BytesIO(payload));files=[n for n in archive.namelist() if n.endswith('.py')]
  source=archive.read('pydantic_ai/agent/__init__.py').decode();row['source_review']={'python_files':len(files),'supports_output_type':'output_type' in source,'has_model_tool_orchestration':'toolsets' in source,'agent_source_sha256':hashlib.sha256(source.encode()).hexdigest()}
 metadata.append(row)
measurements={}
for label,statement in [('guardian_core','from igris.guardian.readonly import parse_proposal'),('standalone_pydantic','from pydantic import BaseModel, TypeAdapter')]:
 times=[]
 for _ in range(5):
  code='import sys,time;sys.path.insert(0,'+repr(str(ROOT/'src'))+');start=time.perf_counter();'+statement+';print(time.perf_counter()-start)'
  times.append(float(subprocess.check_output([sys.executable,'-I','-c',code],text=True)))
 measurements[label]={'import_seconds':times,'median_seconds':sorted(times)[2]}
proof={'status':'PASS','decision':'Do not integrate Pydantic AI; retain Hermes and Guardian.','validation':rows,'packages':metadata,'startup':measurements,'pydantic_version':__import__('pydantic').__version__,'framework_startup':'Not measured; Pydantic AI was inspected as an inert hash-verified wheel, not installed or imported.','network':'HTTPS package metadata/source retrieval for audit only; no provider request.','limitations':['Schema validation is not authorization, containment, isolation or approval. Duplicate JSON still needs the existing strict parser.','Standalone Pydantic is an optional future schema convenience, not an architectural benefit requiring another agent framework.']}
(ROOT/'docs/validation/pydantic-ai-evaluation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':pass
