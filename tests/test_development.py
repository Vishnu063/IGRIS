import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.request import urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.development import create_webapp
from igris.guardian.policy import Policy, Permission


class DevelopmentTests(unittest.TestCase):
    def test_sample_build_database_api_and_frontend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = create_webapp(Path(directory), 'sample', Policy('owner', frozenset({Permission.FILE_MODIFY})))
            source = (root / 'app.py').read_text()
            compile(source, str(root / 'app.py'), 'exec')  # Build/syntax validation, no package install.
            spec = importlib.util.spec_from_file_location('reviewed_sample_app', root / 'app.py')
            app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(app)  # Only our reviewed generated template, no third-party code.
            store = app.Store(str(root / 'sample.db'))
            store.add('Synthetic item')
            store.add("quote ' stays data")
            with self.assertRaises(ValueError): store.add('')
            http = app.server(store)
            thread = threading.Thread(target=http.serve_forever, daemon=True); thread.start()
            try:
                base = f'http://127.0.0.1:{http.server_port}'
                with urlopen(base + '/api/items', timeout=2) as response:
                    records = json.load(response)
                self.assertEqual(len(records), 2)
                with urlopen(base + '/', timeout=2) as response:
                    page = response.read().decode()
                self.assertIn("fetch('/api/items')", page)
                self.assertIn('textContent', page)
                self.assertNotIn('innerHTML', page)
            finally:
                http.shutdown(); http.server_close(); thread.join()
