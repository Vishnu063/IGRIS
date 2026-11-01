"""Trusted development reporting helper, never an IGRIS tool or authority source."""
from datetime import datetime
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
TITLES=['Interactive Guardian approvals','Handy voice input','Multilingual voice responses','Real n8n integration',
        'Ops Pilot monitoring integration','Activate fifteen specialists','Mission Control dashboard','Mem0 semantic memory',
        'Authorized Playwright browser','MarkItDown documents','Pydantic AI evaluation','Performance optimization',
        'Mac M1 installation package','Final security and end-to-end verification']


def initial():
    return {'baseline_commit':'c4a46851a1f42b47327864a2e29f501622c6e9bc','branch':'develop',
        'tasks':[{'number':i+1,'title':title,'status':'PENDING','implementation_commit':None,'capabilities':[],
                  'external_requirements':[],'implementation_status':'PENDING','external_verification':'PENDING'} for i,title in enumerate(TITLES)],
        'production_deployed':False,'mac_installed':False,'paid_services_activated':False}


def render(tracker):
    lines=['# IGRIS completion progress','', '| Task | Title | Acceptance | Implementation | External verification | Commit |','| --- | --- | --- | --- | --- | --- |']
    for item in tracker['tasks']:
        lines.append(f"| {item['number']} | {item['title']} | {item['status']} | {item.get('implementation_status','PENDING')} | {item.get('external_verification','PENDING')} | {item['implementation_commit'] or '—'} |")
    lines+=['','Statuses apply to actual acceptance, not merely code presence.','', '## Actual working capabilities','']
    for item in tracker['tasks']:
        for value in item['capabilities']:lines.append(f"- Task {item['number']}: {value}")
    lines+=['','## External requirements','']
    for item in tracker['tasks']:
        for value in item['external_requirements']:lines.append(f"- Task {item['number']}: {value}")
    (ROOT/'docs/execution/completion-progress.md').write_text('\n'.join(lines).rstrip()+'\n')


def main():
    tracker_file=ROOT/'docs/execution/completion-progress.json'
    if len(sys.argv)==2 and sys.argv[1]=='--initialize':
        if tracker_file.exists():raise ValueError('Existing progress must be preserved.')
        tracker=initial()
    else:
        if len(sys.argv)!=2:raise ValueError('One private outcome file required.')
        data=json.loads(Path(sys.argv[1]).read_text());number=data['task']
        if type(number) is not int or not 1<=number<=14 or data['status'] not in ('PASS','FAIL','BLOCKED'):
            raise ValueError('Invalid task/status.')
        tracker=json.loads(tracker_file.read_text())
        if any(t['status']=='PENDING' for t in tracker['tasks'][:number-1]):raise ValueError('Earlier tasks must be recorded first.')
        sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        files=subprocess.check_output(['git','show','--format=','--name-only',sha],cwd=ROOT,text=True).splitlines()
        report=['IGRIS EXECUTION REPORT','',f'Task: {number} / 14',f'Title: {TITLES[number-1]}',f"Status: {data['status']}",
                '',f"Recorded: {datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()}",'']
        fields=[('Implemented','implemented'),('Real versus simulated','classification'),('Tests and results','tests'),
                ('Security review','security'),('Performance','performance'),('Known limitations','limitations'),
                ('External requirements','external_requirements')]
        for label,key in fields:
            report += [label+':','']+['- '+str(x) for x in data.get(key,[])]+['']
        report+=['Files changed:','']+['- '+x for x in files]+['','Commands executed:','']
        report += ['$ '+cmd.removeprefix('$ ') for cmd in data.get('commands',[])]+['','Git commit:','',
            '- Verified implementation: '+sha,'- This report is recorded in a following documentation commit; remote tip is checked after publication.','',
            'Git delivery:','',data.get('delivery','Connected GitHub App publishes the exact staged tree using expected-head fast-forward; remote branch SHA is verified separately. Git CLI authentication unavailable.'),'',
            'Next task:','',f'- {number+1 if number<14 else "Final delivery; stop."}','', 'Approval required:','',
            '- No for authorized development/push. Mac access, production, main merge, paid services and new host privileges remain unauthorized.','']
        relative=f'docs/execution/completion-task-{number:02}.md'
        (ROOT/relative).write_text('\n'.join(report).rstrip()+'\n')
        tracker['tasks'][number-1].update(status=data['status'],implementation_commit=sha,report=relative,
            implementation_status=data.get('implementation_status','VERIFIED' if data['status']=='PASS' else 'TESTED_PARTIAL'),
            external_verification=data.get('external_verification','NOT_REQUIRED' if not data.get('external_requirements') else 'BLOCKED'),
            capabilities=data.get('capabilities',[]),external_requirements=data.get('external_requirements',[]))
    tracker_file.write_text(json.dumps(tracker,indent=2,ensure_ascii=False)+'\n');render(tracker)


if __name__=='__main__':main()
