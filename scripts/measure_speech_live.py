"""Fixed developer benchmark; never a tool available to Hermes."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.isolated import IsolatedWorker
program='''import contextlib,io,json,resource,runpy
output=io.StringIO()
with contextlib.redirect_stdout(output):runpy.run_path('/opt/igris/worker.py',run_name='__main__')
data=json.loads(output.getvalue());data.pop('wav')
data['espeak_peak_rss_kib']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
data['python_peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(json.dumps(data))'''
profile=json.loads((ROOT/'integrations/speech/profile.json').read_text());results=[]
for language,text in [('en','Igris is ready.'),('hi','नमस्ते। मैं तैयार हूँ।'),('mr','नमस्कार. मी तयार आहे.')]:
    raw=IsolatedWorker().run(profile['image'],['/opt/igris/python/bin/python3.14','-I','-S','-c',program],
        [(ROOT/'runtime/python3149/python','/opt/igris/python'),(ROOT/'integrations/speech/worker.py','/opt/igris/worker.py')],
        component='speech-benchmark',memory='1g',timeout=30,payload=json.dumps({'language':language,'text':text},ensure_ascii=False).encode())
    results.append(json.loads(raw))
(ROOT/'runtime/speech/performance.json').write_text(json.dumps({'observations':results,'platform':'Linux x86_64; no Mac measurement','worker_sha256':hashlib.sha256((ROOT/'integrations/speech/worker.py').read_bytes()).hexdigest()},indent=2)+'\n')
print(json.dumps(results))
