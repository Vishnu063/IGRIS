import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.reused_agents import ROOT, specialist_definition, hermes_core_spec, activate_hermes
from igris.adapters.contracts import AdapterUnavailable
from igris.specialists.registry import CATALOG


class ReuseTests(unittest.TestCase):
    def test_every_role_uses_copied_original_methodology(self):
        manifest=json.loads((ROOT/'integrations/agency-agents/manifest.json').read_text())
        self.assertEqual(set(manifest['roles']),set(CATALOG))
        for role,item in manifest['roles'].items():
            original=(ROOT/'vendor/agency-agents'/item['source']).read_bytes()
            self.assertEqual(hashlib.sha256(original).hexdigest(),item['source_sha256'])
            definition=specialist_definition(role)
            self.assertIn('IGRIS operating constraints',definition)
            self.assertIn('Adapted upstream methodology',definition)
            self.assertNotIn('On-call engineers must have the authority to take emergency actions without multi-level approval chains',definition)
            self.assertGreater(len(definition),2000)
    def test_hermes_copy_integrity_and_actual_empty_tool_branch(self):
        manifest=json.loads((ROOT/'docs/integrations/hermes-source-manifest.json').read_text())
        self.assertGreater(len(manifest['local_sha256']),1000)
        for path,digest in manifest['local_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/'vendor/hermes-agent'/path).read_bytes()).hexdigest(),digest)
        tree=ast.parse((ROOT/'vendor/hermes-agent/agent/agent_init.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_load_tools')
        # Execute the actual copied function, not a rewritten imitation. The early
        # no-tool branch must return before any upstream imports/discovery.
        scope={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'copied_tool_loader','exec'),scope)
        agent=SimpleNamespace()
        scope['_load_tools'](agent,[],None)
        self.assertEqual(agent.tools,[]);self.assertEqual(agent.valid_tool_names,set())
    def test_core_spec_reuses_actual_constructor_and_activation_is_honest(self):
        spec=hermes_core_spec('explicit-model',role='frontend')
        self.assertTrue(Path(spec['source']).exists())
        self.assertEqual(spec['kwargs']['enabled_toolsets'],[])
        self.assertIn('Frontend Developer',spec['kwargs']['ephemeral_system_prompt'])
        with self.assertRaises(AdapterUnavailable):activate_hermes()
