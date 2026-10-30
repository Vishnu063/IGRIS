import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.artifacts import build_bundle


class ArtifactTests(unittest.TestCase):
    def test_bundle_hashes_reproducibility_and_private_file_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'; root.mkdir()
            (root / 'src').mkdir(); (root / 'config').mkdir()
            (root / 'README.md').write_text('development only')
            (root / 'src/app.py').write_text('print("sample")')
            (root / 'vendor/hermes-agent').mkdir(parents=True)
            (root / 'vendor/hermes-agent/LICENSE').write_text('Synthetic license fixture')
            (root / 'vendor/hermes-agent/run_agent.py').write_text('# Source fixture, never run')
            (root / 'integrations/agency-agents').mkdir(parents=True)
            (root / 'integrations/agency-agents/frontend.md').write_text('Synthetic adapted definition fixture')
            (root / 'workflows').mkdir()
            (root / 'workflows/local.json').write_text('{"active": false}')
            (root / 'config/private.db').write_text('SYNTHETIC_PRIVATE_MARKER')
            (root / '.env').write_text('SYNTHETIC_PRIVATE_MARKER')
            first, second = Path(directory) / 'a.zip', Path(directory) / 'b.zip'
            build_bundle(first, source=root); build_bundle(second, source=root)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertNotIn('.env', archive.namelist())
                self.assertNotIn('config/private.db', archive.namelist())
                for name in ('vendor/hermes-agent/LICENSE', 'vendor/hermes-agent/run_agent.py', 'integrations/agency-agents/frontend.md', 'workflows/local.json'):
                    self.assertIn(name, archive.namelist())
                manifest = json.loads(archive.read('MANIFEST.json'))
                self.assertFalse(manifest['production_ready'])
                for name, digest in manifest['files'].items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)

    def test_symlink_and_credential_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'source'; root.mkdir(); (root/'src').mkdir()
            outside = Path(directory)/'outside.py'; outside.write_text('Synthetic source')
            link = root/'src/link.py'; link.symlink_to(outside)
            with self.assertRaises(ValueError): build_bundle(Path(directory)/'bad.zip', source=root)
            link.unlink()
            (root/'src/bad.py').write_text('ghp_'+'a'*30)
            with self.assertRaises(ValueError): build_bundle(Path(directory)/'secret.zip', source=root)
