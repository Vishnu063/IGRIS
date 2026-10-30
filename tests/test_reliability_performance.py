"""Step 48: bounded, local-only performance and reliability checks.

These tests exercise actual IGRIS Memory persistence. They do not certify Mac
hardware, external services, concurrency isolation, or production throughput.
"""
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from igris.memory import Memory
from igris.guardian.policy import Denied


class ReliabilityPerformanceTests(unittest.TestCase):
    def test_memory_repeated_writes_reads_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = Memory(root / "memory.db", "owner", initialize=True)
            started = time.monotonic()
            identifiers = []
            for index in range(100):
                identifiers.append(memory.put("owner", "incident", f"Synthetic incident {index}", approved=True))
            reopened = Memory(root / "memory.db", "owner")
            for index, identifier in enumerate(identifiers):
                self.assertEqual(reopened.get("owner", identifier)["text"], f"Synthetic incident {index}")
            elapsed = time.monotonic() - started
            # Diagnostic only: speed is machine-dependent, so no arbitrary
            # pass/fail threshold is treated as production performance evidence.
            print(f"Step48 local memory: 100 writes + 100 reads in {elapsed:.3f}s")

    def test_repeated_denied_access_does_not_grant_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(Path(directory) / "memory.db", "owner", initialize=True)
            identifier = memory.put("owner", "project", "Synthetic test project", approved=True)
            for _ in range(100):
                with self.assertRaises(Denied):
                    memory.get("untrusted", identifier)
            self.assertEqual(memory.get("owner", identifier)["text"], "Synthetic test project")

    def test_reopen_and_backup_preserve_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = Memory(root / "memory.db", "owner", initialize=True)
            identifier = memory.put("owner", "solution", "Synthetic recovery", approved=True)
            backup = memory.backup("owner", root / "backup.db")
            self.assertEqual(Memory(backup, "owner").get("owner", identifier)["text"], "Synthetic recovery")


if __name__ == "__main__":
    unittest.main()
