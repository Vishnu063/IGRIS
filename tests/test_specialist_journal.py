import json,sqlite3,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.specialists.journal import record
from igris.guardian.policy import Denied
class SpecialistJournalTests(unittest.TestCase):
 def test_private_correlated_result(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'results.sqlite3';review=SimpleNamespace(actor='owner',mission_id='a'*32,digest='b'*64)
   result={'mission_id':'a'*32,'role':'frontend','text':'Use a label.'}
   with self.assertRaises(Denied):record(path,'model',review,result)
   self.assertFalse(path.exists());record(path,'owner',review,result)
   self.assertEqual(path.stat().st_mode&0o777,0o600)
   with sqlite3.connect(path) as db:self.assertEqual(json.loads(db.execute('SELECT result FROM specialist_results').fetchone()[0]),result)
