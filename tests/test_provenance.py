"""astra.provenance: experiment records must name the code, environment, seed and data (SP-16)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra import provenance

ROOT = Path(__file__).resolve().parent.parent


def _git_available() -> bool:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True).returncode == 0
    except OSError:
        return False


class GitInfoTests(unittest.TestCase):
    @unittest.skipUnless(_git_available(), "not a git checkout")
    def test_reports_the_checked_out_commit(self) -> None:
        expected = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        info = provenance.git_info(ROOT)
        self.assertEqual(info["commit"], expected)
        self.assertRegex(info["commit"], r"^[0-9a-f]{40}$")
        self.assertIsInstance(info["dirty"], bool)

    @unittest.skipUnless(_git_available(), "not a git checkout")
    def test_works_from_any_working_directory(self) -> None:
        # The old metadata code ran git in the caller's cwd and recorded "unknown" elsewhere.
        expected = provenance.git_info(ROOT)["commit"]
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                self.assertEqual(provenance.git_info()["commit"], expected)
            finally:
                os.chdir(previous)

    def test_outside_a_repository_gives_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(provenance.git_info(Path(tmp)), {"commit": None, "branch": None, "dirty": None})

    def test_missing_git_binary_gives_none(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            self.assertIsNone(provenance.git_info(ROOT)["commit"])


class EnvironmentAndDataTests(unittest.TestCase):
    def test_environment_lists_versions(self) -> None:
        env = provenance.environment()
        self.assertRegex(env["python"], r"^\d+\.\d+\.\d+")
        self.assertIn("numpy", env["packages"])
        self.assertIsNotNone(env["packages"]["numpy"])
        self.assertIsNone(provenance.package_versions(("surely-not-an-installed-package",))[
            "surely-not-an-installed-package"])

    def test_data_fingerprint_hashes_split_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            splits = Path(tmp)
            for split in ("train", "val", "test"):
                (splits / f"{split}_ids.json").write_bytes(b"[]")
            (splits / "split_metadata.json").write_text(json.dumps({"split_hash": "abc"}), encoding="utf-8")
            data = provenance.data_fingerprint(splits / "missing.csv", splits)
        self.assertIsNone(data["manifest_sha256"])
        self.assertEqual(data["split_hash"], "abc")
        self.assertEqual(data["split_file_sha256"]["test"],
                         "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945")

    def test_shipped_manifest_hash(self) -> None:
        data = provenance.data_fingerprint(ROOT / "astra-platform/data/scientific_dataset_freeze_v2.csv", ROOT / "nope")
        self.assertEqual(data["manifest_sha256"], "f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58")

    def test_collect_has_every_section(self) -> None:
        record = provenance.collect(seed=7, data={"split_hash": "x"}, device="cpu")
        self.assertEqual(set(record), {"created_utc", "git", "environment", "device", "seed", "data"})
        self.assertEqual((record["seed"], record["device"]), (7, "cpu"))
        self.assertTrue(re.match(r"^\d{4}-\d\d-\d\dT.*Z$", record["created_utc"]))
        json.dumps(record)  # must be serialisable as-is


if __name__ == "__main__":
    unittest.main()
