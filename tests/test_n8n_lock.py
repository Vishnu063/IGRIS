import runpy,shutil,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
load_lock=runpy.run_path(str(ROOT/'scripts/prepare_n8n.py'))['load_lock']

class N8nLockTests(unittest.TestCase):
    def test_complete_pinned_lock_and_tamper_denial(self):
        import json
        raw,package=load_lock();data=json.loads(raw)
        self.assertEqual(json.loads(package)['dependencies']['n8n'],'2.45.7')
        self.assertEqual(data['packages']['node_modules/n8n']['version'],'2.45.7')
        with tempfile.TemporaryDirectory() as temporary:
            target=Path(temporary)/'lock';shutil.copytree(ROOT/'integrations/n8n/lock',target)
            part=target/'part-001.json';part.write_bytes(part.read_bytes()+b' ')
            with self.assertRaises(ValueError):load_lock(target)
