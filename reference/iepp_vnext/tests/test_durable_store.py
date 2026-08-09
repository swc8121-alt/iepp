from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from durable_store import SQLiteCanonicalStore


class DurableStoreTests(unittest.TestCase):
    def test_restart_persists_head(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.db"
            initial, next_head = sha256(b"i").digest(), sha256(b"n").digest()
            store = SQLiteCanonicalStore(path)
            store.enroll("e", initial)
            self.assertEqual(store.compare_and_swap("e", 0, initial, 1, next_head, b"1" * 32),
                             (True, "COMMITTED"))
            store.close()
            reopened = SQLiteCanonicalStore(path)
            self.assertEqual((reopened.read("e").counter, reopened.read("e").head), (1, next_head))
            reopened.close()

    def test_concurrent_successors_exactly_one_commits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.db"
            initial = sha256(b"i").digest()
            first, second = SQLiteCanonicalStore(path), SQLiteCanonicalStore(path)
            first.enroll("e", initial)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(store.compare_and_swap, "e", 0, initial, 1,
                                       sha256(label).digest(), label * 32)
                           for store, label in ((first, b"a"), (second, b"b"))]
                results = [future.result() for future in futures]
            self.assertEqual(sum(int(ok) for ok, _ in results), 1)
            first.close(); second.close()

    def test_injected_failure_rolls_back_both_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteCanonicalStore(Path(directory) / "registry.db")
            initial, evidence = sha256(b"i").digest(), b"x" * 32
            store.enroll("e", initial)
            self.assertEqual(store.compare_and_swap("e", 0, initial, 1, sha256(b"n").digest(), evidence, True),
                             (False, "INJECTED_ROLLBACK"))
            self.assertEqual(store.read("e").counter, 0)
            self.assertIsNone(store.connection.execute(
                "SELECT 1 FROM accepted_evidence WHERE evidence_id = ?", (evidence,)).fetchone())
            store.close()


if __name__ == "__main__":
    unittest.main()
