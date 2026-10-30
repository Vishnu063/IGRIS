import hashlib, json, os, sys, tempfile, unittest, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from igris.backup import create_backup, restore_backup, rollback_plan
from igris.config import load_settings
from igris.memory import Memory
from igris.guardian.policy import Denied


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.memory = Memory(self.root/'memory.db', 'owner', initialize=True)
        self.ident = self.memory.put('owner', 'project', 'Synthetic project knowledge', approved=True)
        self.archive = self.root/'snapshot.zip'
        self.record = create_backup(self.archive, settings=load_settings('test', environ={}), state={'projects': []}, memory=self.memory, actor='owner')

    def test_real_restore_after_memory_loss_no_automatic_resume(self):
        self.memory.delete('owner', self.ident)
        restored = restore_backup(self.archive, self.root/'restored', expected_sha256=self.record['sha256'])
        self.assertFalse(restored['execution_resumed'])
        copy = Memory(self.root/'restored/memory.db', 'owner')
        self.assertEqual(copy.get('owner', self.ident)['text'], 'Synthetic project knowledge')
        self.assertEqual(copy.path.stat().st_mode & 0o777, 0o600)
        with zipfile.ZipFile(self.archive) as z:
            self.assertEqual(set(z.namelist()), {'memory.db', 'configuration.json', 'project-state.json', 'manifest.json'})
        self.assertFalse(rollback_plan('a'*40, 'b'*64)['production_execution_available'])

    def test_corruption_wrong_hash_path_traversal_and_production_denied(self):
        with self.assertRaises(ValueError): restore_backup(self.archive, self.root/'bad', expected_sha256='0'*64)
        with self.assertRaises(Denied): restore_backup(self.archive, self.root/'prod', expected_sha256=self.record['sha256'], environment='production')
        malicious = self.root/'malicious.zip'
        with zipfile.ZipFile(malicious, 'w') as z: z.writestr('../escape', b'unsafe')
        os.chmod(malicious, 0o600)
        digest = hashlib.sha256(malicious.read_bytes()).hexdigest()
        with self.assertRaises(ValueError): restore_backup(malicious, self.root/'escaped', expected_sha256=digest)
        self.assertFalse((self.root/'escape').exists())
        self.assertFalse((self.root/'escaped').exists())

    def test_approval_and_sensitive_state_never_backed_up(self):
        for state in ({'approvals': []}, {'projects': [{'id': 'a'*32, 'state': 'password: synthetic', 'origin': 'simulated'}]}):
            with self.assertRaises(ValueError): create_backup(self.root/'bad.zip', settings=load_settings('test', environ={}), state=state, memory=self.memory, actor='owner')
