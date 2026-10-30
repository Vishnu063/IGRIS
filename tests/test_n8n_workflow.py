import json
from pathlib import Path
import shutil
import subprocess
import unittest


class WorkflowDefinitionTests(unittest.TestCase):
    def test_inactive_authenticated_template_and_code_contract(self):
        root = Path(__file__).resolve().parents[1]
        workflow = json.loads((root / 'workflows/n8n-readonly-fixture.json').read_text())
        self.assertIs(workflow['active'], False)
        self.assertEqual(workflow['nodes'][0]['parameters']['authentication'], 'headerAuth')
        self.assertNotIn('credentials', workflow['nodes'][0])
        node = shutil.which('node')
        if node is None:
            self.skipTest('Node unavailable; n8n code-node JS not executed.')
        code = workflow['nodes'][1]['parameters']['jsCode']
        script = """const assert = require('node:assert/strict');
const fn = new Function('$json', process.argv[1]);
const body = {schema_version:1,mission_id:'a'.repeat(32),workflow:'inspect_fixture',input:{application:'fixture-app'}};
const result = fn({body});
assert.equal(result[0].json.status,'completed');
assert.equal(result[0].json.mission_id,body.mission_id);
assert.throws(()=>fn({body:{...body,command:'injected'}}));
assert.throws(()=>fn({body:{...body,input:{application:'app;command'}}}));
assert.throws(()=>fn({body:{...body,workflow:'deploy'}}));
console.log('PASS: trusted code-node function; n8n runtime not tested.');"""
        result = subprocess.run([node, '-e', script, code], capture_output=True, text=True, timeout=3, check=True)
        self.assertIn('PASS:', result.stdout)
