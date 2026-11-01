import io,os,sys,tempfile,threading,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.markitdown_runtime import Documents,document_parts,validate_document,MAX_INPUT
from igris.guardian.policy import Denied
from igris.adapters.contracts import AdapterUnavailable
class DocumentBoundaryTests(unittest.TestCase):
 def test_invalid_paths(self):
  for name in ('/etc/passwd','../a.pdf','a/../b.pdf','.env.html','secret.pdf','a.exe','a.PDF','a\\b.pdf'):
   with self.assertRaises(Denied):document_parts(name)
 def test_archive_boundaries(self):
  for name,data in [('../escape.xml','x'),('/a.xml','x'),('word/vbaProject.bin','x'),('a.xml','<!DOCTYPE evil>'),('a.rels','<Relationship TargetMode="External"/>'),('a.xml','A'*100000)]:
   out=io.BytesIO()
   with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:archive.writestr(name,data)
   with self.assertRaises(Denied):validate_document(out.getvalue(),'.docx')
  for raw in (b'',b'x'*(MAX_INPUT+1)):
   with self.assertRaises(Denied):validate_document(raw,'.html')
 def test_workspace_and_file_boundary(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as folder:
   root=Path(folder);(root/'a.html').write_text('example');adapter=Documents(root,['a.html'])
   with self.assertRaises(AdapterUnavailable):adapter.scope(threading.Event())
   with self.assertRaises(Denied):adapter.read('other.html')
   with self.assertRaises(Denied):adapter.execute({'path':'a.html'},threading.Event(),None)
   (root/'b.html').symlink_to('/etc/passwd')
   with self.assertRaises(OSError):Documents(root,['b.html']).read('b.html')
   os.link(root/'a.html',root/'hard.html')
   with self.assertRaises(Denied):adapter.read('a.html')
