"""Command-line interface of the training scripts (SP-10): --seed, --data-dir, --out-dir."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import numpy as np

try:
    import torch
except ImportError:  # pragma: no cover - depends on environment
    torch = None

from data.labels import NUM_CLASSES


def _synthetic_processed(root: Path, per_class: int = 4) -> Path:
    """A tiny processed dataset outside data/phase6 (so the Phase 6 audit gate does not apply)."""
    processed = root / "data" / "processed"
    rng = np.random.default_rng(0)
    tic = 7000
    for label in range(NUM_CLASSES):
        for i in range(per_class):
            star = processed / f"TIC_{tic}"
            star.mkdir(parents=True)
            for name in ("flux_1000.npy", "folded_flux_1000.npy"):
                np.save(star / name, rng.standard_normal(1000).astype(np.float32))
            for name in ("flux_200.npy", "folded_flux_200.npy"):
                np.save(star / name, rng.standard_normal(200).astype(np.float32))
            meta = {"label": label, "period_source": "catalog" if i % 2 else "BLS"}
            (star / "metadata.json").write_text(json.dumps(meta))
            tic += 1
    return processed


@unittest.skipIf(torch is None, "PyTorch not installed")
class TrainTransformerCliTests(unittest.TestCase):
    def test_defaults_come_from_config(self) -> None:
        from training.train_transformer import build_arg_parser

        args = build_arg_parser().parse_args([])
        self.assertEqual((args.seed, args.data_dir, args.out_dir, args.variant), (42, None, None, "shared"))

    def test_one_epoch_run_writes_to_out_dir_and_records_the_seed(self) -> None:
        import training.dataset as dataset_module
        from training.train_transformer import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = _synthetic_processed(root)
            out = root / "run"
            argv = ["--data-dir", str(processed), "--out-dir", str(out), "--seed", "7",
                    "--epochs", "1", "--batch-size", "8", "--tag", "cli"]
            # Other tests may have touched the test split in this process; the run itself must not.
            with patch.object(dataset_module, "TEST_SET_ACCESSED", False), redirect_stdout(io.StringIO()):
                main(argv)
            self.assertTrue((out / "best_star_transformer_cli.pt").is_file())
            history = json.loads((out / "training_history_transformer_cli.json").read_text())
            self.assertEqual(len(history["epochs"]), 1)
            metadata = json.loads((out / "experiment_metadata_cli.json").read_text())
            self.assertEqual(metadata["seed"], 7)
            self.assertEqual(metadata["variant"], "shared")
            self.assertTrue((out / "classification_report_transformer_cli.txt").is_file())

    def test_same_seed_gives_identical_initial_weights(self) -> None:
        from training.models.hybrid_transformer import HybridTransformer
        from training.train_transformer import set_deterministic_seeds

        previous = torch.are_deterministic_algorithms_enabled()
        try:
            set_deterministic_seeds(11)
            a = HybridTransformer(variant="shared", num_classes=NUM_CLASSES).state_dict()
            set_deterministic_seeds(12)
            b = HybridTransformer(variant="shared", num_classes=NUM_CLASSES).state_dict()
        finally:
            torch.use_deterministic_algorithms(previous)
        self.assertFalse(all(torch.equal(a[k], b[k]) for k in a))


@unittest.skipIf(torch is None, "PyTorch not installed")
class TrainCnnCliTests(unittest.TestCase):
    def test_defaults_come_from_config(self) -> None:
        from training.train_cnn import build_arg_parser

        args = build_arg_parser().parse_args([])
        self.assertEqual((args.seed, args.data_dir, args.out_dir), (42, None, None))

    def test_one_epoch_dual_branch_run_writes_to_out_dir_and_records_the_seed(self) -> None:
        import training.dataset as dataset_module
        from training.train_cnn import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = _synthetic_processed(root)
            out = root / "run"
            argv = ["--data-dir", str(processed), "--out-dir", str(out), "--seed", "3",
                    "--epochs", "1", "--batch-size", "8", "--use-folded", "--tag", "cli"]
            with patch.object(dataset_module, "TEST_SET_ACCESSED", False), redirect_stdout(io.StringIO()):
                main(argv)
            metadata = json.loads((out / "experiment_metadata_cli.json").read_text())
            self.assertEqual(metadata["seed"], 3)
            self.assertTrue(list(out.glob("best_star_cnn*.pt")))


@unittest.skipIf(torch is None, "PyTorch not installed")
class CrossValidateCliTests(unittest.TestCase):
    def test_defaults_match_the_documented_protocol(self) -> None:
        from training.cross_validate import build_arg_parser

        args = build_arg_parser().parse_args([])
        self.assertEqual((args.seeds, args.folds, args.epochs), ([42, 100, 2026], 5, 50))

    def test_seeds_folds_and_epochs_are_honoured(self) -> None:
        import csv as csv_module

        from training.cross_validate import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = _synthetic_processed(root)
            out = root / "cv"
            with redirect_stdout(io.StringIO()):
                main(["--data-dir", str(processed), "--out-dir", str(out),
                      "--seeds", "1", "--folds", "2", "--epochs", "1"])
            rows = list(csv_module.DictReader((out / "fold_metrics.csv").open()))
            self.assertEqual([(r["seed"], r["fold"]) for r in rows], [("1", "0"), ("1", "1")])
            self.assertTrue((out / "aggregate_metrics.json").is_file())
            report = (out / "statistical_report.md").read_text(encoding="utf-8")
            self.assertIn("2 folds, 1 seeds, 2 runs total", report)
            self.assertEqual(len(list(out.glob("confusion_matrix_seed1_fold*.png"))), 2)


def _random_checkpoint(path: Path) -> None:
    """A checkpoint in the training script's format, with untrained weights."""
    from training.models.hybrid_transformer import HybridTransformer

    torch.manual_seed(0)
    model = HybridTransformer(variant="shared", num_classes=NUM_CLASSES)
    torch.save({"variant": "shared", "num_classes": NUM_CLASSES, "model_state_dict": model.state_dict()}, path)


@unittest.skipIf(torch is None, "PyTorch not installed")
class CalibrationCliTests(unittest.TestCase):
    def test_all_paths_are_configurable(self) -> None:
        from training.calibration import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = _synthetic_processed(root, per_class=6)  # >= 5 validation samples for 5 bins
            ckpt = root / "model.pt"
            _random_checkpoint(ckpt)
            out = root / "reports"
            temperature_file = root / "models" / "temperature.txt"
            with redirect_stdout(io.StringIO()):
                main(["--checkpoint", str(ckpt), "--data-dir", str(processed),
                      "--out-dir", str(out), "--temperature-out", str(temperature_file)])
            temperature = float(temperature_file.read_text().strip())
            self.assertGreater(temperature, 0.0)
            self.assertTrue((out / "calibration_report.md").is_file())
            self.assertTrue((out / "reliability_before.png").is_file())

    def test_missing_checkpoint_exits_cleanly(self) -> None:
        from training.calibration import main

        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(["--checkpoint", str(Path(tmp) / "nope.pt")])


if __name__ == "__main__":
    unittest.main()
