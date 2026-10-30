"""Static validation of this deliberately JSON-formatted, valid YAML workflow."""
import ast
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def check():
    workflow = json.loads((ROOT / '.github/workflows/ci.yml').read_text())
    assert workflow['on'] == {'workflow_dispatch': None}, 'No automatic billable execution authorized'
    assert workflow['permissions'] == {'contents': 'read'}
    assert shutil.which('node'), 'Node required for workflow JS tests; do not silently skip'
    for job in workflow['jobs'].values():
        assert job['timeout-minutes'] <= 10
        for step in job['steps']:
            if 'uses' in step:
                assert re.fullmatch(r'actions/[a-z-]+@[0-9a-f]{40}', step['uses'])
    for path in (ROOT / 'src').rglob('*.py'):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): names = [item.name.split('.')[0] for item in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level: names = [(node.module or '').split('.')[0]]
            else: continue
            assert all(name in sys.stdlib_module_names or name == 'igris' for name in names), 'Review new dependency'
    print('PASS: workflow structure, pinned actions, manual-only trigger and standard-library runtime imports.')


if __name__ == '__main__': check()
