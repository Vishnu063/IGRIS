"""Real disposable archive extraction; no Mac binary or VM execution."""
import importlib.util,io,json,sys,tarfile,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
try:
    from mac_vm import extract_lima,verify_lima,validate_instance
    from mac_package import Blocked,digest
finally:sys.path.remove(str(ROOT/'scripts'))
class MacArchiveTests(unittest.TestCase):
    def instance(self,root):
        return {'name':'igris','arch':'aarch64','vmType':'vz','cpus':2,'memory':4*1024**3,'disk':24*1024**3,'dir':str(Path(root)/'vm-state/igris'),'config':{'mounts':[],'rosetta':{'enabled':False,'binfmt':False},'ssh':{'forwardAgent':False,'forwardX11':False},'containerd':{'system':False,'user':False},'portForwards':[{'guestIP':'127.0.0.1','guestPort':8765,'hostIP':'127.0.0.1','hostPort':8765},{'ignore':True,'guestPortRange':[1,65535]}]}}
    def test_actual_instance_schema_requires_native_limits_and_no_sharing(self):
        with tempfile.TemporaryDirectory() as folder:
            data=self.instance(folder);validate_instance(data,folder)
            for key,value in [('vmType','qemu'),('arch','x86_64'),('memory',8*1024**3),('autoStartedIdentifier','login-item')]:
                bad=json.loads(json.dumps(data));bad[key]=value
                with self.assertRaises(Blocked):validate_instance(bad,folder)
            for change in ('home','socket','rosetta'):
                bad=json.loads(json.dumps(data))
                if change=='home':bad['config']['mounts']=[{'location':'~'}]
                if change=='socket':bad['config']['portForwards'][0]['hostSocket']='/var/run/docker.sock'
                if change=='rosetta':bad['config']['rosetta']['enabled']=True
                with self.assertRaises(Blocked):validate_instance(bad,folder)
    def archive(self,folder,name,*,link=None,hard=False):
        path=Path(folder)/'input.tar'
        with tarfile.open(path,'w') as a:
            m=tarfile.TarInfo(name)
            if link is not None:m.type=tarfile.LNKTYPE if hard else tarfile.SYMTYPE;m.linkname=link;a.addfile(m)
            else:m.size=4;a.addfile(m,io.BytesIO(b'test'))
        return path
    def test_traversal_symlink_escape_and_hardlink_rejected(self):
        for name,link,hard in [('../escape',None,False),('/tmp/escape',None,False),('link','../../outside',False),('link','outside',True)]:
            with tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(Blocked):extract_lima(self.archive(folder,name,link=link,hard=hard),Path(folder)/'lima')
                self.assertFalse((Path(folder)/'escape').exists())
    def test_known_file_manifest_and_modified_file_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'lima';extract_lima(self.archive(folder,'bin/limactl'),root)
            manifest={'version':'v2.3.0','files':{'bin/limactl':digest(root/'bin/limactl')},'links':{},'directories':['bin']}
            (root/'igris-install-manifest.json').write_text(json.dumps(manifest));verify_lima(root)
            (root/'bin/limactl').write_text('user replacement')
            with self.assertRaises(Blocked):verify_lima(root)
            self.assertEqual((root/'bin/limactl').read_text(),'user replacement')
