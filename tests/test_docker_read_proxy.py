"""Actual Unix HTTP and filtering; backing Docker responses are synthetic fixtures."""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.guardian.docker_read_proxy import ExactDockerReads,UnixHTTP

class ReadProxyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.cid='a'*64;self.key='b'*64;self.calls=[]
        def backend(path):
            self.calls.append(path)
            if path.endswith('/info'):body={'ID':'fixture-daemon','RegistryConfig':{'not_forwarded':'fixture'}}
            elif '/json' in path:body={'Id':self.cid,'Name':'/fixture','Image':'sha256:fixture','State':{'Status':'running','Running':True,'ExitCode':0,'OOMKilled':False},'Config':{'Image':'fixture','Env':['DO_NOT_FORWARD=fixture'],'Tty':False},'RestartCount':0}
            else:return 200,{'Content-Type':'application/vnd.docker.raw-stream'},b'synthetic bounded log'
            return 200,{'Content-Type':'application/json','Set-Cookie':'not_forwarded=fixture'},json.dumps(body).encode()
        self.proxy=ExactDockerReads(self.root/'proxy.sock',self.cid,'fixture-daemon',self.key,backend=backend).start();self.addCleanup(self.proxy.close)
    def request(self,path,method='GET',key=None,body=None):
        conn=UnixHTTP(self.proxy.path)
        try:
            conn.request(method,path,headers={'X-IGRIS-Read-Key':self.key if key is None else key},body=body)
            result=conn.getresponse();return result.status,dict(result.getheaders()),result.read()
        finally:conn.close()
    def test_auth_scope_and_mutations_rejected_before_backend(self):
        for path,method,key in [('/info','GET','c'*64),('/info','GET','é'),('/containers/'+self.cid+'/restart','POST',None),('/containers/'+'f'*64+'/json','GET',None),('/containers/'+self.cid+'/logs','GET',None),('/containers/'+self.cid+'/logs?tail=101','GET',None),('/containers/'+self.cid+'/logs?tail=1&tail=2','GET',None),('/v1.50/../info','GET',None),('http://example.invalid/info','GET',None)]:
            with self.subTest(path=path):self.assertIn(self.request(path,method,key)[0],(401,403))
        self.assertEqual(self.calls,[])
        self.assertNotIn(self.key,json.dumps(self.proxy.events))
    def test_actual_unix_roundtrip_filters_private_metadata(self):
        status,headers,raw=self.request('/v1.50/containers/'+self.cid+'/json')
        self.assertEqual(status,200);self.assertEqual(json.loads(raw)['State']['Status'],'running')
        self.assertNotIn(b'DO_NOT_FORWARD',raw);self.assertNotIn('Set-Cookie',headers)
        self.assertEqual(json.loads(self.request('/info')[2]),{'ID':'fixture-daemon'})
        self.assertEqual(self.request('/containers/'+self.cid+'/logs?stdout=1&stderr=1&tail=100')[0],200)
    def test_get_with_body_cannot_smuggle_mutation(self):
        self.assertEqual(self.request('/info',body=b'x')[0],403);self.assertEqual(self.calls,[])
