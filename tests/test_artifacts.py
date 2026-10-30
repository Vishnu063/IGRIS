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
            (root / '.env').write_text('SYNTHETIC_PRIVATE_MARKER')
            first, second = Path(directory) / 'a.zip', Path(directory) / 'b.zip'
            build_bundle(first, source=root); build_bundle(second, source=root)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertNotIn('.env', archive.namelist())
                manifest = json.loads(archive.read('MANIFEST.json'))
                self.assertFalse(manifest['production_ready'])
                for name, digest in manifest['files'].items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
