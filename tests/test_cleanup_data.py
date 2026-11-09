"""pipeline/cleanup_data.py must never delete data by default or without its log."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from pipeline import cleanup_data


def _star(processed: Path, tic: int, cls: str | None) -> Path:
    path = processed / f"TIC_{tic}"
    path.mkdir(parents=True)
    if cls is not None:
        (path / "metadata.json").write_text(json.dumps({"tic_id": tic, "astra_class": cls}))
    return path


class CleanupDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.processed = root / "processed"
        self.ok = _star(self.processed, 1, "rr_lyrae")          # successful in log -> keep
        self.solar_good = _star(self.processed, 2, "solar_like")  # catalog solar_like -> keep
        self.solar_bad = _star(self.processed, 3, "stable")      # catalog solar_like, wrong class -> delete
        self.obsolete = _star(self.processed, 4, "cepheid")      # not in log or catalog -> delete
        self.no_meta = _star(self.processed, 5, None)            # missing metadata -> delete
        self.log = root / "task.log"
        self.log.write_text("[1/9] TIC 1 (rr_lyrae) ✓\n[2/9] TIC 9 (cepheid) ✗\n", encoding="utf-8")
        self.catalog = root / "catalog.json"
        self.catalog.write_text(json.dumps([
            {"tic_id": 2, "astra_class": "solar_like"},
            {"tic_id": 3, "astra_class": "solar_like"},
        ]))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, *extra: str) -> int:
        argv = ["--log", str(self.log), "--processed-dir", str(self.processed), "--catalog", str(self.catalog), *extra]
        with redirect_stdout(io.StringIO()):
            return cleanup_data.main(argv)

    def test_log_parsing_counts_only_successes(self) -> None:
        self.assertEqual(cleanup_data.parse_successful_tics(self.log.read_text(encoding="utf-8")), {1})

    def test_plan_matches_the_original_rules(self) -> None:
        delete, keep = cleanup_data.plan_cleanup(self.processed, {1}, {2, 3})
        self.assertEqual(sorted(p.name for p in keep), ["TIC_1", "TIC_2"])
        self.assertEqual(sorted(p.name for p, _ in delete), ["TIC_3", "TIC_4", "TIC_5"])

    def test_default_is_a_dry_run(self) -> None:
        self.assertEqual(self._run(), 0)
        for path in (self.ok, self.solar_good, self.solar_bad, self.obsolete, self.no_meta):
            self.assertTrue(path.exists(), path.name)

    def test_apply_deletes_only_planned_folders(self) -> None:
        self._run("--apply")
        self.assertTrue(self.ok.exists() and self.solar_good.exists())
        self.assertFalse(self.solar_bad.exists() or self.obsolete.exists() or self.no_meta.exists())

    def test_missing_log_refuses_to_run(self) -> None:
        self.log.unlink()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self._run("--apply")
        self.assertTrue(self.obsolete.exists())

    def test_log_argument_is_required(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cleanup_data.main(["--processed-dir", str(self.processed), "--apply"])
        self.assertTrue(self.obsolete.exists())


if __name__ == "__main__":
    unittest.main()
