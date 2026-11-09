"""pipeline/prepare_from_repo.py: verification of the shipped dataset and layout rebuild."""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from pipeline import prepare_from_repo as prep

FIELDS = ["tic_id", "astra_class", *prep.HASHED_FILES.keys()]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _shipped(root: Path, tics: list[int]) -> tuple[Path, Path]:
    """A miniature 'shipped' dataset: processed dirs plus a manifest hashing every file."""
    processed = root / "processed"
    rows = []
    for tic in tics:
        star = processed / f"TIC_{tic}"
        star.mkdir(parents=True)
        for name in ("flux_1000.npy", "flux_200.npy", "folded_flux_1000.npy", "folded_flux_200.npy"):
            np.save(star / name, np.full(10, tic, dtype=np.float32))
        (star / "metadata.json").write_text(json.dumps({"tic_id": tic}))
        row = {"tic_id": str(tic), "astra_class": "stable"}
        for column, filename in prep.HASHED_FILES.items():
            row[column] = _sha(star / filename)
        rows.append(row)
    manifest = root / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return processed, manifest


class VerifyShippedDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.processed, self.manifest = _shipped(self.root, [11, 12, 13])

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_intact_dataset_passes(self) -> None:
        self.assertEqual(prep.verify_processed(self.manifest, self.processed), [])
        self.assertEqual(prep.verify_manifest_file(self.manifest, _sha(self.manifest)), [])

    def test_tampered_array_is_detected(self) -> None:
        np.save(self.processed / "TIC_12" / "folded_flux_200.npy", np.zeros(10, dtype=np.float32))
        self.assertEqual(prep.verify_processed(self.manifest, self.processed),
                         ["TIC_12/folded_flux_200.npy: hash mismatch"])

    def test_missing_star_and_file_are_detected(self) -> None:
        (self.processed / "TIC_11" / "metadata.json").unlink()
        for f in (self.processed / "TIC_13").iterdir():
            f.unlink()
        (self.processed / "TIC_13").rmdir()
        errors = prep.verify_processed(self.manifest, self.processed)
        self.assertIn("TIC_11/metadata.json: missing", errors)
        self.assertIn("TIC_13: missing directory", errors)

    def test_manifest_hash_mismatch_and_absence(self) -> None:
        self.assertTrue(prep.verify_manifest_file(self.manifest, "0" * 64)[0].startswith("manifest hash mismatch"))
        self.assertTrue(prep.verify_manifest_file(self.root / "nope.csv")[0].startswith("manifest missing"))


class ShippedRepositoryTests(unittest.TestCase):
    def test_the_repository_manifest_matches_its_published_hash(self) -> None:
        self.assertEqual(prep.verify_manifest_file(prep.SHIPPED_MANIFEST), [])


if __name__ == "__main__":
    unittest.main()
