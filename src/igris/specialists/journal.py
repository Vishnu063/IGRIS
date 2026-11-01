"""Private owner-side result journal; never mounted in the reasoning worker."""
import json,sqlite3,time
from pathlib import Path
from ..memory import private_file
from ..guardian.activities import canonical
from ..guardian.policy import Denied

def record(path,actor,review,result):
 if actor!=review.actor or result.get('mission_id')!=review.mission_id:raise Denied('Specialist result owner/correlation mismatch.')
 payload=canonical(result);path=Path(path).absolute()
 path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 try:private_file(path,create=True)
 except FileExistsError:pass
 private_file(path)
 db=sqlite3.connect(path)
 try:
  with db:
   db.execute('CREATE TABLE IF NOT EXISTS specialist_results(mission TEXT PRIMARY KEY, actor TEXT NOT NULL, role TEXT NOT NULL, at REAL NOT NULL, action_digest TEXT NOT NULL, result TEXT NOT NULL)')
   db.execute('INSERT INTO specialist_results VALUES(?,?,?,?,?,?)',(review.mission_id,actor,result['role'],time.time(),review.digest,payload))
 finally:db.close()
