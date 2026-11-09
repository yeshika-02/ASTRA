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


def _split_sources(root: Path) -> tuple[Path, Path, dict[str, str], str]:
    """Shipped-style split files plus an audit JSON whose metadata matches them."""
    ids_dir = root / "ids"
    ids_dir.mkdir()
    ids = {"train": ["TIC_1", "TIC_2", "TIC_3"], "val": ["TIC_4"], "test": ["TIC_5"]}
    file_hashes = {}
    for split, members in ids.items():
        path = ids_dir / f"phase6_{split}_ids.json"
        path.write_text(json.dumps(members, indent=2))
        file_hashes[split] = _sha(path)
    split_hash = prep.compute_split_hash({**ids, "calibration": []})
    audit = root / "audit.json"
    audit.write_text(json.dumps({"split_metadata": {
        "split_hash": split_hash, "train_size": 3, "val_size": 1, "test_size": 1, "calibration_size": 0,
    }}))
    return ids_dir, audit, file_hashes, split_hash


class BuildSplitsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ids_dir, self.audit, self.file_hashes, self.split_hash = _split_sources(self.root)
        self.target = self.root / "phase6" / "splits"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _build(self) -> list[str]:
        return prep.build_splits(self.target, self.ids_dir, self.audit, self.file_hashes, self.split_hash)

    def test_split_files_are_byte_copies_and_metadata_is_written(self) -> None:
        self.assertEqual(self._build(), [])
        for split in ("train", "val", "test"):
            self.assertEqual(_sha(self.target / f"{split}_ids.json"), self.file_hashes[split])
        self.assertEqual((self.target / "calibration_ids.json").read_bytes(), b"[]")
        meta = json.loads((self.target / "split_metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["split_hash"], self.split_hash)

    def test_tampered_split_file_writes_nothing(self) -> None:
        (self.ids_dir / "phase6_val_ids.json").write_text(json.dumps(["TIC_9"]))
        self.assertEqual(self._build(), ["phase6_val_ids.json: hash mismatch"])
        self.assertFalse(self.target.exists())

    def test_metadata_split_hash_must_match_the_recomputed_hash(self) -> None:
        self.audit.write_text(json.dumps({"split_metadata": {"split_hash": "0" * 64}}))
        self.assertTrue(self._build()[0].startswith("split hash mismatch"))
        self.assertFalse(self.target.exists())

    def test_split_sizes_must_match_metadata(self) -> None:
        meta = {"split_hash": self.split_hash, "train_size": 99, "val_size": 1, "test_size": 1}
        self.audit.write_text(json.dumps({"split_metadata": meta}))
        self.assertEqual(self._build(), ["train: size 3 != metadata 99"])

    def test_split_hash_algorithm_matches_freeze_script_order(self) -> None:
        # train, val, calibration, test: changing the order changes the hash.
        a = prep.compute_split_hash({"train": ["A"], "val": ["B"], "test": ["C"]})
        b = prep.compute_split_hash({"train": ["A"], "val": ["C"], "test": ["B"]})
        self.assertNotEqual(a, b)


def _audit_ready_sources(root: Path) -> prep.Sources:
    """Shipped-style sources whose stars carry full Phase 6 metadata (so the audit can pass)."""
    from data.labels import CLASS_NAMES
    from tests.test_phase6_pipeline import _write_sample

    shipped = root / "shipped"
    tics = {"train": [], "val": [], "test": []}
    tic = 3000
    for class_index, cls in enumerate(CLASS_NAMES):
        for split in tics:
            # distinct sky positions (the audit rejects coordinate duplicates)
            _write_sample(shipped, tic, cls, f"group_{tic}", 10.0 + class_index, -20.0 - (tic - 3000))
            tics[split].append(f"TIC_{tic}")
            tic += 1
    processed = shipped / "processed"
    rows = []
    for star in sorted(processed.iterdir()):
        row = {"tic_id": star.name.removeprefix("TIC_"), "astra_class": "x"}
        row.update({col: _sha(star / name) for col, name in prep.HASHED_FILES.items()})
        rows.append(row)
    manifest = shipped / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    ids_dir = shipped / "ids"
    ids_dir.mkdir()
    file_hashes = {}
    for split, members in tics.items():
        path = ids_dir / f"phase6_{split}_ids.json"
        path.write_text(json.dumps(sorted(members), indent=2))
        file_hashes[split] = _sha(path)
    split_hash = prep.compute_split_hash({s: sorted(m) for s, m in tics.items()})
    audit = shipped / "audit.json"
    audit.write_text(json.dumps({"split_metadata": {
        "split_hash": split_hash, **{f"{s}_size": len(m) for s, m in tics.items()}}}))
    return prep.Sources(processed=processed, manifest=manifest, split_ids=ids_dir, audit=audit,
                        manifest_sha256=_sha(manifest), split_file_sha256=file_hashes, split_hash=split_hash)


class PrepareLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.sources = _audit_ready_sources(self.root)
        self.target = self.root / "phase6"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_builds_a_verified_layout_with_a_passing_audit(self) -> None:
        self.assertEqual(prep.prepare(self.target, self.sources), [])
        self.assertEqual(len(list((self.target / "processed").iterdir())), 15)
        self.assertTrue((self.target / "manifest.csv").is_file())
        status = json.loads((self.target / "audits" / "audit_status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["overall_status"], "PASS")
        self.assertFalse(status["raw_files_required"])
        self.assertEqual(status["missing_raw_files"], 15)  # raw files are not copied

    def test_tampered_source_builds_nothing(self) -> None:
        star = next(self.sources.processed.iterdir())
        (star / "metadata.json").write_text("{}")
        errors = prep.prepare(self.target, self.sources)
        self.assertEqual(errors, [f"{star.name}/metadata.json: hash mismatch"])
        self.assertFalse(self.target.exists())

    def test_existing_layout_requires_force(self) -> None:
        self.assertEqual(prep.prepare(self.target, self.sources), [])
        self.assertTrue(prep.prepare(self.target, self.sources)[0].endswith("(use --force to replace it)"))
        self.assertEqual(prep.prepare(self.target, self.sources, force=True), [])


class ShippedRepositoryTests(unittest.TestCase):
    def test_the_repository_manifest_matches_its_published_hash(self) -> None:
        self.assertEqual(prep.verify_manifest_file(prep.SHIPPED_MANIFEST), [])

    def test_shipped_split_files_reproduce_the_published_split_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "splits"
            self.assertEqual(prep.build_splits(target), [])
            self.assertEqual(_sha(target / "calibration_ids.json"),
                             "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945")


if __name__ == "__main__":
    unittest.main()
