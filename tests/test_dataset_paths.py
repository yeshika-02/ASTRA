"""Where ASTRADataset looks for frozen split files (astra.config integration)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

try:
    import torch  # noqa: F401  (ASTRADataset imports torch)
except ImportError:  # pragma: no cover - depends on environment
    torch = None

from data.labels import NUM_CLASSES


def _make_stars(processed: Path, n_per_class: int = 2) -> list[str]:
    ids = []
    tic = 5000
    for label in range(NUM_CLASSES):
        for _ in range(n_per_class):
            star = processed / f"TIC_{tic}"
            star.mkdir(parents=True)
            arr = np.zeros(1000, dtype=np.float32)
            for name in ("flux_1000.npy", "flux_200.npy", "folded_flux_1000.npy", "folded_flux_200.npy"):
                np.save(star / name, arr)
            (star / "metadata.json").write_text(json.dumps({"label": label}))
            ids.append(f"TIC_{tic}")
            tic += 1
    return ids


def _write_frozen(splits: Path, train_ids: list[str]) -> None:
    splits.mkdir(parents=True, exist_ok=True)
    (splits / "train_ids.json").write_text(json.dumps(train_ids))
    (splits / "split_metadata.json").write_text(json.dumps({"train_size": len(train_ids), "split_hash": "0" * 64}))


@unittest.skipIf(torch is None, "PyTorch not installed")
class SplitsDirResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        from training.dataset import ASTRADataset

        self.Dataset = ASTRADataset
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_explicit_splits_dir_wins(self) -> None:
        processed = self.root / "anywhere" / "processed"
        ids = _make_stars(processed)
        _write_frozen(self.root / "my_splits", ids)
        ds = self.Dataset(processed, split="train", splits_dir=self.root / "my_splits")
        self.assertEqual(len(ds), len(ids))

    def test_phase6_layout_uses_sibling_splits_directory(self) -> None:
        processed = self.root / "phase6" / "processed"
        ids = _make_stars(processed)
        _write_frozen(self.root / "phase6" / "splits", ids[:NUM_CLASSES * 2])
        ds = self.Dataset(processed, split="train")
        self.assertEqual(len(ds), NUM_CLASSES * 2)

    def test_configured_processed_dir_uses_configured_splits_dir(self) -> None:
        # e.g. arrays read from astra-platform/data/processed, splits rebuilt elsewhere
        processed = self.root / "shipped" / "processed"
        splits = self.root / "rebuilt" / "splits"
        ids = _make_stars(processed)
        _write_frozen(splits, ids)
        env = {"ASTRA_PROCESSED_DIR": str(processed), "ASTRA_SPLITS_DIR": str(splits)}
        with patch.dict(os.environ, env):
            ds = self.Dataset(processed, split="train")
        self.assertEqual(len(ds), len(ids))

    def test_test_split_without_frozen_files_still_refuses(self) -> None:
        processed = self.root / "elsewhere" / "processed"
        _make_stars(processed)
        with self.assertRaisesRegex(ValueError, "Frozen Phase 6 split file required"):
            self.Dataset(processed, split="test")


if __name__ == "__main__":
    unittest.main()
