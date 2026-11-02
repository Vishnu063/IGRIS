"""Validate recorded completion delivery without starting optional services."""
import json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 tracker=json.loads((ROOT/'docs/execution/completion-progress.json').read_text());status=json.loads((ROOT/'docs/delivery/completion-status.json').read_text())
 assert len(tracker['tasks'])==14
 for row in tracker['tasks']:
  assert row['status'] in ('PASS','FAIL','BLOCKED')
  text=(ROOT/row['report']).read_text();assert 'Task: '+str(row['number'])+' / 14' in text
  assert 'Status: '+row.get('historical_task_status',row['status']) in text
  assert re.fullmatch('[a-f0-9]{40}',row['implementation_commit'])
  subprocess.run(['git','cat-file','-e',row['implementation_commit']+'^{commit}'],cwd=ROOT,check=True)
 counts={kind:sum(row['status']==kind for row in tracker['tasks']) for kind in ('PASS','BLOCKED','FAIL')}
 assert status['task_counts']==counts and status['source_commit']==tracker['tasks'][13]['implementation_commit']
 assert status['release_status']=='BLOCKED' and not any(status[key] for key in ('production_deployed','mac_installed','paid_services_activated','main_merged'))
 assert status['n8n_current_status']=='BLOCKED_SECURITY_AUDIT'
 for name in status['evidence_files']:assert (ROOT/name).is_file()
 assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='develop'
 print('PASS: all 14 task reports, current status/counts, source commits, evidence and release blockers agree.')
if __name__=='__main__':check()
