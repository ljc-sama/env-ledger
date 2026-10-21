"""单元测试：全部用 file:// 假下载，跑测试不需要联网。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from env_ledger import ledger  # noqa: E402


class LedgerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ledger_path = self.root / "ledger.csv"
        self.source = self.root / "payload.bin"
        self.source.write_bytes(b"hello env-ledger")
        self.url = self.source.as_uri()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def fetch_one(self, purpose: str = "unit test") -> ledger.Entry:
        return ledger.fetch(
            self.url,
            self.ledger_path,
            purpose=purpose,
            version="0.1.0",
            out_dir=self.root / "downloads",
        )

    # ---- 下载与记账 ----

    def test_fetch_saves_file_and_records_entry(self) -> None:
        entry = self.fetch_one()

        self.assertTrue(Path(entry.path).exists())
        self.assertEqual(Path(entry.path).read_bytes(), self.source.read_bytes())
        self.assertEqual(entry.file, "payload.bin")
        self.assertEqual(entry.version, "0.1.0")
        self.assertEqual(entry.purpose, "unit test")
        self.assertEqual(entry.status, "downloaded")

    def test_fetch_computes_matching_sha256(self) -> None:
        entry = self.fetch_one()
        self.assertEqual(entry.sha256, ledger.sha256_of(self.source))
        self.assertEqual(len(entry.sha256), 64)

    def test_ledger_accumulates_rows_in_order(self) -> None:
        self.fetch_one("first")
        self.fetch_one("second")

        entries = ledger.read_ledger(self.ledger_path)
        self.assertEqual(len(entries), 2)
        self.assertEqual([e.purpose for e in entries], ["first", "second"])

    def test_missing_ledger_reads_as_empty(self) -> None:
        self.assertEqual(ledger.read_ledger(self.root / "nope.csv"), [])

    def test_bad_url_raises_and_does_not_touch_ledger(self) -> None:
        with self.assertRaises(OSError):
            ledger.fetch(
                (self.root / "does-not-exist.bin").as_uri(),
                self.ledger_path,
                purpose="should fail",
                out_dir=self.root / "downloads",
            )
        self.assertEqual(ledger.read_ledger(self.ledger_path), [])

    # ---- 校验 ----

    def test_verify_reports_ok_for_untouched_file(self) -> None:
        self.fetch_one()
        results = ledger.verify_ledger(self.ledger_path)
        self.assertEqual([r.state for r in results], ["ok"])

    def test_verify_detects_modified_file(self) -> None:
        entry = self.fetch_one()
        Path(entry.path).write_bytes(b"tampered content")

        results = ledger.verify_ledger(self.ledger_path)
        self.assertEqual(results[0].state, "mismatch")

    def test_verify_detects_deleted_file(self) -> None:
        entry = self.fetch_one()
        Path(entry.path).unlink()

        results = ledger.verify_ledger(self.ledger_path)
        self.assertEqual(results[0].state, "missing")

    def test_verify_on_empty_ledger_returns_nothing(self) -> None:
        self.assertEqual(ledger.verify_ledger(self.ledger_path), [])

    # ---- 工具函数 ----

    def test_filename_from_url_handles_query_and_trailing_slash(self) -> None:
        self.assertEqual(
            ledger.filename_from_url("https://example.com/a/tool.zip?x=1"), "tool.zip"
        )
        self.assertEqual(
            ledger.filename_from_url("https://example.com/"), "download.bin"
        )

    def test_sha256_is_uppercase_hex(self) -> None:
        digest = ledger.sha256_of(self.source)
        self.assertEqual(digest, digest.upper())
        self.assertTrue(all(c in "0123456789ABCDEF" for c in digest))


if __name__ == "__main__":
    unittest.main()
