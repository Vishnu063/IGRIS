"""Review retained real answers; structural checks never execute model code."""
import ast,hashlib,json,re,sqlite3,sys
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Tags(HTMLParser):
 def __init__(self):super().__init__();self.tags=[]
 def handle_starttag(self,tag,attrs):self.tags.append((tag,dict(attrs)))
def main():
 folder=ROOT/'runtime/specialists'
 original=json.loads((folder/'attempt-two.json').read_text())
 remaining=json.loads((folder/'remaining-live.json').read_text())['responses']
 corrections=json.loads((folder/'corrections-live.json').read_text())['responses']
 final=json.loads((folder/'final-corrections-live.json').read_text())['responses']
 voice=json.loads((folder/'voice-controls-live.json').read_text())['responses']
 selected={item['role']:item for item in original+remaining+corrections+final+voice}
 sys.path.insert(0,str(ROOT/'src'))
 from igris.reused_agents import specialist_definition
 assert len(selected)==15
 for role,item in selected.items():assert item['result']['definition_sha256']==hashlib.sha256(specialist_definition(role).encode()).hexdigest()
 assert all(item['passed'] and item['result']['origin']=='real_local_inference' and not item['result']['executed_actions'] for item in selected.values())
 tags=Tags();tags.feed(selected['frontend']['result']['text'])
 labels=[attrs['for'] for tag,attrs in tags.tags if tag=='label' and 'for' in attrs]
 inputs=[attrs['id'] for tag,attrs in tags.tags if tag=='input' and 'id' in attrs]
 assert labels and labels==inputs
 code=re.search(r'```python\s*(.*?)```',selected['code_reviewer']['result']['text'],re.S).group(1)
 tree=ast.parse(code);function=tree.body[0];assert isinstance(function,ast.FunctionDef) and function.name=='add_item'
 assert isinstance(function.args.defaults[0],ast.Constant) and function.args.defaults[0].value is None
 backend_code=selected['backend']['result']['text']
 match=re.search(r'```(?:python)?\s*(.*?)```',backend_code,re.S)
 backend_tree=ast.parse(match.group(1) if match else backend_code)
 assert any(isinstance(node,ast.FunctionDef) and node.name=='valid_title' for node in ast.walk(backend_tree))
 index=re.search(r'CREATE INDEX [a-zA-Z_]+ ON events \(owner_id, created_at DESC\);',selected['database']['result']['text']).group()
 db=sqlite3.connect(':memory:')
 try:
  db.execute('CREATE TABLE events(owner_id TEXT,created_at REAL)');db.execute(index)
  plan=db.execute('EXPLAIN QUERY PLAN SELECT * FROM events WHERE owner_id=? ORDER BY created_at DESC LIMIT 20',('owner',)).fetchall()
  assert 'INDEX' in str(plan) and 'TEMP B-TREE' not in str(plan)
 finally:db.close()
 proof={'status':'PASS','responses':list(selected.values()),'structural_checks':['Generated frontend label for matches input id.','Generated review fix has None default, parsed with AST; model code not executed.','Generated exact-shape index tested against real disposable SQLite query planner.'],
 'rejected_attempts':{'frontend':'First keyword check missed reversed HTML attributes; rejected on manual review.','backend':'Unsupported advice to omit authentication/audit; replaced with explicit project requirements task.','mobile':'Unrequested cloud database recommendation; replaced with explicit offline-only constraints.','ai_engineer':'Incorrect injection/hash/schema explanation; rejected. Classifier-metric task separately verified.','devops':'Earlier policy answer omitted requested approval details/inferred a cause; replaced with concrete Docker evidence classification.', 'project_manager':'Imported FluxUI and later requests/@app.route despite standard-library scope; adapted definition corrected, then re-tested.', 'voice_ai':'Omitted Stop and later suggested placeholder transcription; replaced with explicit cancel/discard/no-fabrication state task.'},
 'owner_inputs':'Automated owner fixtures; model never approves.','quality_limitations':'These fifteen scoped checks establish real role-conditioned responses, not general professional competence. Rejected security advice remains preserved. Human review required.',
 'definition_integrity_checked':True,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['src/igris/specialists/live.py','scripts/hermes_specialist_worker.py','src/igris/adapters/hermes_chat.py','scripts/test_specialists_live.py','scripts/test_specialist_corrections_live.py','scripts/test_specialist_final_corrections_live.py','scripts/test_voice_specialist_controls_live.py','scripts/verify_specialist_results.py']}}
 path=ROOT/'docs/validation/specialists-live.json';path.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print('PASS: fifteen genuine selected responses and generated-code structural checks; prior rejected answers preserved separately.')
if __name__=='__main__':main()
