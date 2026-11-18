"""Real disposable files; Lima command responses are explicitly simulated.

No Mac, VM, native Rosetta or real socket-forwarding acceptance is implied.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
try:
    import mac_vm_policy as policy
    import mac_package
    from mac_package import Blocked, PACKAGE, check, digest, install
    from mac_vm import validate_instance
finally:
    sys.path.remove(str(ROOT/'scripts'))
import test_mac_archive as archive_fixtures


class MacVMPolicyTests(unittest.TestCase):
    def setup_original(self, folder):
        root = Path(folder)/'private'
        install(root)
        original = (PACKAGE/'migrations/lima-v1.yaml').read_bytes()
        (root/'lima.yaml').write_bytes(original)
        manifest = json.loads((root/'manifest.json').read_bytes())
        manifest['files']['lima.yaml'] = digest(root/'lima.yaml')
        (root/'manifest.json').write_text(json.dumps(manifest))
        instance_dir = root/'vm-state/igris'
        instance_dir.mkdir(parents=True)
        (instance_dir/'lima.yaml').write_bytes(original)
        (instance_dir/'disk').write_bytes(b'preserve guest disk')
        (root/'owner-notes.txt').write_text('preserve owner notes')
        instance = archive_fixtures.MacArchiveTests().instance(root)
        instance['status'] = 'Running'
        instance['config']['rosetta'] = {'enabled': False, 'binfmt': False}
        forwards = instance['config']['portForwards']
        forwards[0]['proto'] = 'any'
        forwards[1].update(guestIP='127.0.0.1', guestIPMustBeZero=False)
        return root, instance

    def simulated_lima(self, root, instance, *, fail=False, unexpected=False):
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            self.assertIs(kwargs['check'], True)
            self.assertLessEqual(kwargs['timeout'], 60)
            if command[1] == 'stop':
                instance['status'] = 'Stopped'
            elif command[1] == 'edit':
                self.assertEqual(command, ['limactl-fixture', 'edit', '--tty=false',
                                           '--set', policy.EXPRESSION, 'igris'])
                self.assertEqual(instance['status'], 'Stopped')
                if fail:
                    raise subprocess.CalledProcessError(1, command)
                instance['config'].pop('rosetta')
                instance['config']['portForwards'][0]['proto'] = 'tcp'
                instance['config']['portForwards'][1].update(
                    guestIP='0.0.0.0', guestIPMustBeZero=False, proto='any')
                if unexpected:
                    instance['config']['env'] = {'UNEXPECTED': 'value'}
                (root/'vm-state/igris/lima.yaml').write_bytes((PACKAGE/'lima.yaml').read_bytes())
            else:
                self.fail('Unreviewed simulated command '+repr(command))
            return subprocess.CompletedProcess(command, 0)
        return calls, run

    def test_original_policy_is_blocked_until_explicit_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            root, instance = self.setup_original(folder)
            check(root, allow_legacy=True)
            with self.assertRaises(Blocked):
                check(root)
            with self.assertRaises(Blocked):
                validate_instance(instance, root)
            validate_instance(instance, root, legacy=True)
            self.assertEqual(digest(PACKAGE/'migrations/lima-v1.yaml'),
                             '61f3197f6fcd2e4573ba7ec1959b736dccb51c3de9344bc2f32c7bd44416fc8f')

    def test_original_profile_can_be_stopped_but_not_started(self):
        with tempfile.TemporaryDirectory() as folder:
            root, instance = self.setup_original(folder)
            with patch.object(mac_package.shutil, 'which', return_value='limactl-fixture'), \
                    patch.object(mac_package.subprocess, 'check_output', return_value='limactl version 2.3.0'):
                command, env = mac_package.vm_command(root, 'stop-vm')
                self.assertEqual(command, ['limactl-fixture', 'stop', 'igris'])
                self.assertEqual(env['LIMA_HOME'], str(root/'vm-state'))
                with self.assertRaises(Blocked):
                    mac_package.vm_command(root, 'start-vm')

    def test_interruption_after_stop_never_restarts_or_grants_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            root, instance = self.setup_original(folder)
            calls = []
            def interrupted(command, **kwargs):
                calls.append(command[1])
                if command[1] == 'stop':
                    instance['status'] = 'Stopped'
                else:
                    raise KeyboardInterrupt
            with patch.object(policy, 'read_instance', side_effect=lambda *a: copy.deepcopy(instance)), \
                    patch.object(policy.subprocess, 'run', side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    policy.migrate_policy('limactl-fixture', {}, root)
            self.assertEqual(calls, ['stop', 'edit', 'stop'])
            self.assertEqual(instance['status'], 'Stopped')
            with self.assertRaises(Blocked): check(root)

    def test_simulated_migration_stops_only_owned_vm_and_preserves_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root, instance = self.setup_original(folder)
            calls, run = self.simulated_lima(root, instance)
            with patch.object(policy, 'read_instance', side_effect=lambda *a: copy.deepcopy(instance)), \
                    patch.object(policy.subprocess, 'run', side_effect=run):
                result = policy.migrate_policy('limactl-fixture', {}, root)
                self.assertEqual(result['migration'], 'PASS_VM_LEFT_STOPPED')
                self.assertEqual(result['policy'], 'PASS')
                self.assertEqual(policy.migrate_policy('limactl-fixture', {}, root)['migration'], 'ALREADY_APPLIED')
            self.assertEqual([call[1] for call in calls], ['stop', 'edit'])
            check(root)
            self.assertEqual((root/'vm-state/igris/disk').read_bytes(), b'preserve guest disk')
            self.assertEqual((root/'owner-notes.txt').read_text(), 'preserve owner notes')
            snapshot = root/result['snapshot_directory']
            self.assertEqual((snapshot/'instance.yaml').read_bytes(), (PACKAGE/'migrations/lima-v1.yaml').read_bytes())
            self.assertEqual(snapshot.stat().st_mode & 0o777, 0o700)
            self.assertEqual((snapshot/'instance.yaml').stat().st_mode & 0o777, 0o600)

    def test_edit_failure_leaves_stopped_vm_pending_and_startup_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            root, instance = self.setup_original(folder)
            calls, run = self.simulated_lima(root, instance, fail=True)
            with patch.object(policy, 'read_instance', side_effect=lambda *a: copy.deepcopy(instance)), \
                    patch.object(policy.subprocess, 'run', side_effect=run):
                with self.assertRaisesRegex(Blocked, 'migration interrupted or failed'):
                    policy.migrate_policy('limactl-fixture', {}, root)
                self.assertEqual(instance['status'], 'Stopped')
                with self.assertRaisesRegex(Blocked, 'Previous migration incomplete'):
                    policy.migrate_policy('limactl-fixture', {}, root)
            with self.assertRaises(Blocked):
                check(root)
            self.assertEqual(len(calls), 3)
            self.assertEqual(json.loads((root/'vm-policy-migration.json').read_bytes())['status'], 'PENDING')

    def test_unknown_instance_yaml_preserved_without_stopping(self):
        with tempfile.TemporaryDirectory() as folder:
            root, instance = self.setup_original(folder)
            path = root/'vm-state/igris/lima.yaml'
            path.write_text('owner modifications')
            with patch.object(policy, 'read_instance', return_value=instance), \
                    patch.object(policy.subprocess, 'run') as run:
                with self.assertRaisesRegex(Blocked, 'not the exact shipped original'):
                    policy.migrate_policy('limactl-fixture', {}, root)
                run.assert_not_called()
            self.assertEqual(path.read_text(), 'owner modifications')
            self.assertFalse((root/'vm-policy-migration.json').exists())

    def test_unexpected_effective_change_blocks_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            root, instance = self.setup_original(folder)
            before = (root/'manifest.json').read_bytes()
            calls, run = self.simulated_lima(root, instance, unexpected=True)
            with patch.object(policy, 'read_instance', side_effect=lambda *a: copy.deepcopy(instance)), \
                    patch.object(policy.subprocess, 'run', side_effect=run):
                with self.assertRaisesRegex(Blocked, 'Unexpected effective policy changes'):
                    policy.migrate_policy('limactl-fixture', {}, root)
            self.assertEqual((root/'manifest.json').read_bytes(), before)
            self.assertEqual(instance['status'], 'Stopped')

    def test_inspection_omits_model_credentials_and_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            root, instance = self.setup_original(folder)
            instance['config']['env'] = {'PRIVATE': 'do-not-print-owner-data'}
            with patch.object(policy, 'read_instance', return_value=instance):
                result = policy.inspect_policy('limactl-fixture', {}, root)
            self.assertEqual(result['policy'], 'BLOCKED_REQUIRES_MIGRATION')
            self.assertNotIn('do-not-print-owner-data', json.dumps(result))
            self.assertTrue(result['recognized_original_yaml'])

    def test_effective_rosetta_and_forwarding_changes_are_denied(self):
        with tempfile.TemporaryDirectory() as folder:
            good = archive_fixtures.MacArchiveTests().instance(folder)
            for label in ('effective-rosetta', 'missing-rosetta', 'legacy-rosetta',
                          'reverse', 'static', 'dashboard-udp', 'dashboard-range',
                          'loopback-ignore', 'wildcard-only-ignore', 'udp-only-ignore', 'block-device'):
                bad = copy.deepcopy(good)
                c = bad['config']
                a, b = c['portForwards']
                if label == 'effective-rosetta': c['vmOpts']['vz']['rosetta']['enabled'] = True
                if label == 'missing-rosetta': c.pop('vmOpts')
                if label == 'legacy-rosetta': c['rosetta'] = {'enabled': True}
                if label == 'reverse': b['reverse'] = True
                if label == 'static': a['static'] = True
                if label == 'dashboard-udp': a['proto'] = 'any'
                if label == 'dashboard-range': a['guestPortRange'] = [1, 65535]
                if label == 'loopback-ignore': b['guestIP'] = '127.0.0.1'
                if label == 'wildcard-only-ignore': b['guestIPMustBeZero'] = True
                if label == 'udp-only-ignore': b['proto'] = 'udp'
                if label == 'block-device': c['blockDevices'] = ['/dev/disk-fixture']
                with self.subTest(label=label), self.assertRaises(Blocked):
                    validate_instance(bad, folder)

    def test_symlink_hardlink_writable_and_oversized_configs_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root/'original';original.write_bytes(b'preserve')
            link = root/'link';link.symlink_to(original)
            with self.assertRaises(Blocked): policy.private_read(link)
            link.unlink();os.link(original, link)
            with self.assertRaises(Blocked): policy.private_read(link)
            link.unlink();original.chmod(0o666)
            with self.assertRaises(Blocked): policy.private_read(original)
            original.chmod(0o600);original.write_bytes(b'x'*65537)
            with self.assertRaises(Blocked): policy.private_read(original)
