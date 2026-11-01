"""Actual fixed offline worker failure/cancellation tests, not model tools."""
import json,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.isolated import IsolatedWorker,Cancelled
from igris.adapters.contracts import AdapterUnavailable,ContractError


def main():
    profile=json.loads((ROOT/'integrations/hermes-inference/profile.json').read_text())
    image=profile['container_image'];mounts=[(ROOT/'runtime/python3149/python','/opt/igris/python')]
    results=[]
    for name,code,error in (
        ('success','print("bounded success")',None),
        ('timeout','import time;time.sleep(60)',TimeoutError),
        ('failure','raise RuntimeError("fixture")',AdapterUnavailable),
        ('output_limit','print("x"*200000)',ContractError)):
        worker=IsolatedWorker();started=time.monotonic()
        try:
            output=worker.run(image,['/opt/igris/python/bin/python3.14','-I','-S','-c',code],mounts,component='worker-test',timeout=2 if name=='timeout' else 45,memory='1g')
            if error is not None or output!=b'bounded success\n':raise AssertionError('Unexpected worker outcome.')
        except (TimeoutError,AdapterUnavailable,ContractError) as exc:
            if error is None or not isinstance(exc,error):raise
        assert worker.name is None
        results.append({'case':name,'status':'PASS','seconds':time.monotonic()-started,'cleanup_verified':True})
    cancel=threading.Event();worker=IsolatedWorker(cancel=cancel);timer=threading.Timer(3,cancel.set);timer.start()
    try:
        try:worker.run(image,['/opt/igris/python/bin/python3.14','-I','-S','-c','import time;time.sleep(60)'],mounts,component='worker-test',timeout=45,memory='1g')
        except Cancelled:pass
        else:raise AssertionError('Cancellation not enforced.')
    finally:timer.cancel()
    assert worker.name is None;results.append({'case':'cancellation','status':'PASS','cleanup_verified':True})
    (ROOT/'runtime/handy/worker-live.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))


if __name__=='__main__':main()
