"""dataset_audit.run_audit(require_raw=...) for layouts without raw light curves."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from data.labels import CLASS_NAMES
from pipeline.dataset_audit import run_audit
from tests.test_phase6_pipeline import _write_sample


class AuditRawRequirementTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "phase6"
        tic = 2000
        for class_index, cls in enumerate(CLASS_NAMES):
            for offset in range(2):
                _write_sample(self.root, tic, cls, f"group_{tic}", 10.0 + class_index, -20.0 - offset)
                tic += 1

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_complete_layout_passes_either_way(self) -> None:
        self.assertEqual(run_audit(self.root)["overall_status"], "PASS")
        status = run_audit(self.root, require_raw=False)
        self.assertEqual((status["overall_status"], status["missing_raw_files"]), ("PASS", 0))

    def test_missing_raw_files_fail_by_default(self) -> None:
        shutil.rmtree(self.root / "raw")
        status = run_audit(self.root)
        self.assertEqual(status["overall_status"], "FAIL")
        self.assertTrue(status["raw_files_required"])

    def test_missing_raw_files_are_counted_when_not_required(self) -> None:
        shutil.rmtree(self.root / "raw")
        status = run_audit(self.root, require_raw=False)
        self.assertEqual(status["overall_status"], "PASS")
        self.assertEqual(status["missing_raw_files"], 2 * len(CLASS_NAMES))
        self.assertFalse(status["raw_files_required"])
        written = json.loads((self.root / "audits" / "audit_status.json").read_text(encoding="utf-8"))
        self.assertFalse(written["raw_files_required"])
        report = (self.root / "audits" / "preprocessing_consistency_report.md").read_text(encoding="utf-8")
        self.assertIn("Missing raw files: 10 (raw files required: False)", report)

    def test_a_present_but_altered_raw_file_still_fails(self) -> None:
        raw = next((self.root / "raw").rglob("*.npz"))
        raw.write_bytes(b"tampered")
        self.assertEqual(run_audit(self.root, require_raw=False)["overall_status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
