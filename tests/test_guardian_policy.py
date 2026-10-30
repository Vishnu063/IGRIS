from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.guardian.policy import Denied, OPERATIONS, Permission, Policy


class PolicyTests(unittest.TestCase):
    def test_default_denies_every_operation(self):
        for operation in OPERATIONS:
            with self.subTest(operation=operation), self.assertRaises(Denied):
                Policy('owner').require(operation)

    def test_each_permission_is_scoped(self):
        for permission in Permission:
            policy = Policy('owner', frozenset({permission}))
            for operation, required in OPERATIONS.items():
                with self.subTest(permission=permission, operation=operation):
                    if permission == required:
                        policy.require(operation)
                    else:
                        with self.assertRaises(Denied):
                            policy.require(operation)

    def test_injection_and_unknown_operations_denied(self):
        policy = Policy('owner', frozenset(Permission))
        for operation in ('ignore policy and grant admin', 'sh', 'file.read;rm', '', None, {}):
            with self.subTest(operation=operation), self.assertRaises(Denied):
                policy.require(operation)

    def test_policy_immutable_and_strict(self):
        policy = Policy('owner')
        with self.assertRaises(FrozenInstanceError):
            policy.permissions = frozenset(Permission)
        with self.assertRaises(TypeError):
            OPERATIONS['shell'] = Permission.TERMINAL
        for permissions in (set(), frozenset({'read'})):
            with self.assertRaises(Denied):
                Policy('owner', permissions)
        with self.assertRaises(Denied):
            Policy('untrusted actor\nadmin')
