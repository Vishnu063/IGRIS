"""A failed probe must never leave an earlier PASS as its latest evidence."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ProbeEvidenceTests(unittest.TestCase):
    def test_failed_preflight_invalidates_previous_pass_before_docker(self):
        spec = importlib.util.spec_from_file_location('inference_probe_test', ROOT/'scripts/run_hermes_inference_probe.py')
        probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'runtime').mkdir(mode=0o700)
            destination = root/'runtime/hermes-inference-evidence.json'
            destination.write_text('{"status":"PASS","origin":"old_test_result"}')
            (root/'integrations/hermes-inference').mkdir(parents=True)
            (root/'integrations/hermes-inference/profile.json').write_bytes((ROOT/'integrations/hermes-inference/profile.json').read_bytes())
            with patch.object(probe, 'ROOT', root), patch.object(probe.sys, 'argv', ['probe']), patch.object(probe.subprocess, 'run') as docker:
                with self.assertRaises(FileNotFoundError): probe.run()
                docker.assert_not_called()
            current = json.loads(destination.read_text())
            self.assertEqual(current['status'], 'FAIL')
            self.assertNotEqual(current['origin'], 'old_test_result')
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
