"""training.dataset.ASTRADataset: frozen-split loading, leakage guards, tensors, augmentation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

try:
    import torch
except ImportError:  # pragma: no cover - depends on environment
    torch = None

from data.labels import CLASS_NAMES, NUM_CLASSES

PER_CLASS_PER_SPLIT = 3


def _write_star(processed: Path, tic: int, label: int) -> None:
    star = processed / f"TIC_{tic}"
    star.mkdir(parents=True)
    raw = np.linspace(-1.0, 1.0, 1000, dtype=np.float32) + tic
    folded = np.cos(np.linspace(0, 2 * np.pi, 1000, dtype=np.float32))
    np.save(star / "flux_1000.npy", raw)
    np.save(star / "flux_200.npy", raw[::5])
    np.save(star / "folded_flux_1000.npy", folded)
    np.save(star / "folded_flux_200.npy", folded[::5])
    (star / "metadata.json").write_text(json.dumps({"label": label, "astra_class": CLASS_NAMES[label]}))


def _build_phase6(root: Path) -> dict[str, list[str]]:
    """Create root/phase6/{processed,splits} with every class present in every split."""
    processed = root / "phase6" / "processed"
    splits_dir = root / "phase6" / "splits"
    splits_dir.mkdir(parents=True)
    ids: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    tic = 1000
    for split in ids:
        for label in range(NUM_CLASSES):
            for _ in range(PER_CLASS_PER_SPLIT):
                _write_star(processed, tic, label)
                ids[split].append(f"TIC_{tic}")
                tic += 1
    _write_splits(splits_dir, ids)
    return ids


def _write_splits(splits_dir: Path, ids: dict[str, list[str]], sizes: dict[str, int] | None = None) -> None:
    for split, members in ids.items():
        (splits_dir / f"{split}_ids.json").write_text(json.dumps(members))
    meta = {f"{s}_size": (sizes or {}).get(s, len(m)) for s, m in ids.items()}
    meta["split_hash"] = "0" * 64
    (splits_dir / "split_metadata.json").write_text(json.dumps(meta))


@unittest.skipIf(torch is None, "PyTorch not installed")
class FrozenSplitTests(unittest.TestCase):
    def setUp(self) -> None:
        from training.dataset import ASTRADataset

        self.Dataset = ASTRADataset
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ids = _build_phase6(self.root)
        self.processed = self.root / "phase6" / "processed"
        self.splits_dir = self.root / "phase6" / "splits"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _tic_ids(self, ds) -> set[str]:
        return {s["tic_id"] for s in ds._samples}

    def test_each_split_loads_exactly_its_frozen_ids(self) -> None:
        for split in ("train", "val", "test"):
            with self.subTest(split=split):
                ds = self.Dataset(self.processed, split=split, use_folded=True)
                self.assertEqual(self._tic_ids(ds), set(self.ids[split]))
                self.assertEqual(len(ds), NUM_CLASSES * PER_CLASS_PER_SPLIT)

    def test_size_mismatch_with_split_metadata_is_rejected(self) -> None:
        _write_splits(self.splits_dir, self.ids, sizes={"train": 999})
        with self.assertRaisesRegex(ValueError, "Sample count mismatch"):
            self.Dataset(self.processed, split="train")

    def test_overlap_between_train_and_val_is_rejected(self) -> None:
        leaked = dict(self.ids)
        leaked["val"] = self.ids["val"][1:] + [self.ids["train"][0]]
        _write_splits(self.splits_dir, leaked)
        with self.assertRaisesRegex(ValueError, "Leakage detected"):
            self.Dataset(self.processed, split="val")

    def test_split_missing_a_class_is_rejected(self) -> None:
        # Keep only stars of label 0..3 in the train split.
        ds = self.Dataset(self.processed, split="train")
        keep = [s["tic_id"] for s in ds._samples if s["label"] != NUM_CLASSES - 1]
        reduced = dict(self.ids, train=keep)
        _write_splits(self.splits_dir, reduced)
        with self.assertRaisesRegex(ValueError, "Label representation failure"):
            self.Dataset(self.processed, split="train")

    def test_stars_with_invalid_labels_or_missing_files_are_skipped(self) -> None:
        bad_label = self.processed / self.ids["train"][0] / "metadata.json"
        bad_label.write_text(json.dumps({"label": 99}))
        (self.processed / self.ids["train"][1] / "flux_1000.npy").unlink()
        # The frozen size check then fails, which is the intended outcome: a broken
        # star must not silently shrink a frozen split.
        with self.assertRaisesRegex(ValueError, "Sample count mismatch"):
            self.Dataset(self.processed, split="train")

    def test_items_have_expected_shapes_and_dtypes(self) -> None:
        single = self.Dataset(self.processed, split="train", use_folded=False)
        x, y = single[0]
        self.assertEqual(tuple(x.shape), (1, 1000))
        self.assertEqual(y.dtype, torch.long)
        dual = self.Dataset(self.processed, split="train", use_folded=True)
        x2, _ = dual[0]
        self.assertEqual(tuple(x2.shape), (2, 1000))
        self.assertEqual(x2.dtype, torch.float32)

    def test_class_weights_are_inverse_frequency(self) -> None:
        ds = self.Dataset(self.processed, split="train")
        expected = torch.full((NUM_CLASSES,), 1.0)  # balanced: total / (C * count) = 1
        self.assertTrue(torch.allclose(ds.class_weights, expected))

    def test_temporal_shift_augmentation_moves_only_the_raw_channel(self) -> None:
        ds = self.Dataset(self.processed, split="train", use_folded=True, augment=True)
        clean = self.Dataset(self.processed, split="train", use_folded=True, augment=False)[0][0]
        # random.random() is consulted for noise, scale, shift, mask in that order:
        # enable only the shift, and fix the shift amount.
        with patch("training.dataset.random.random", side_effect=[1.0, 1.0, 0.0, 1.0]), patch(
            "training.dataset.random.randint", return_value=7
        ):
            augmented = ds[0][0]
        self.assertTrue(torch.equal(augmented[0], torch.roll(clean[0], shifts=7)))
        self.assertTrue(torch.equal(augmented[1], clean[1]))


@unittest.skipIf(torch is None, "PyTorch not installed")
class SplitFallbackTests(unittest.TestCase):
    def test_test_split_requires_frozen_files(self) -> None:
        from training.dataset import ASTRADataset

        with tempfile.TemporaryDirectory() as tmp:
            processed = Path(tmp) / "other" / "processed"
            for i, label in enumerate(range(NUM_CLASSES)):
                _write_star(processed, 2000 + i, label)
            with self.assertRaisesRegex(ValueError, "Frozen Phase 6 split file required"):
                ASTRADataset(processed, split="test")

    def test_dynamic_train_val_split_is_disjoint_and_complete(self) -> None:
        # Documents current behaviour: without frozen files, train/val fall back to a
        # random GroupShuffleSplit (grouped by TIC id, i.e. one star per group).
        from training.dataset import ASTRADataset

        with tempfile.TemporaryDirectory() as tmp:
            processed = Path(tmp) / "other" / "processed"
            for i in range(40):
                _write_star(processed, 3000 + i, i % NUM_CLASSES)
            train = ASTRADataset(processed, split="train", val_fraction=0.25)
            val = ASTRADataset(processed, split="val", val_fraction=0.25)
            train_ids = {s["tic_id"] for s in train._samples}
            val_ids = {s["tic_id"] for s in val._samples}
            self.assertFalse(train_ids & val_ids)
            self.assertEqual(len(train_ids | val_ids), 40)


if __name__ == "__main__":
    unittest.main()
