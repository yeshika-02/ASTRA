"""training/evaluate.py end to end: untrained models on the real shipped arrays (SP-15).

Uses the 944 shipped stars (astra-platform/data/processed) and the frozen split files
rebuilt by prepare_from_repo.build_splits, so the evaluation runs on exactly the
published 142-star test split.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

try:
    import torch
except ImportError:  # pragma: no cover - depends on environment
    torch = None

ROOT = Path(__file__).resolve().parent.parent
SHIPPED_PROCESSED = ROOT / "astra-platform" / "data" / "processed"
TEST_SUPPORT = {"rr_lyrae": 32, "cepheid": 35, "eclipsing_binary": 23, "solar_like": 22, "stable": 30}


def _save_untrained(path: Path, kind: str) -> Path:
    from training.models.hybrid_transformer import HybridTransformer
    from training.models.star_cnn import StarCNN

    torch.manual_seed(0)
    if kind == "transformer":
        model = HybridTransformer(variant="shared", num_classes=5)
        torch.save({"variant": "shared", "num_classes": 5, "use_folded": True, "model_state_dict": model.state_dict()},
                   path)
    else:
        model = StarCNN(num_classes=5, use_folded=True)
        torch.save({"num_classes": 5, "use_folded": True, "model_state_dict": model.state_dict()}, path)
    return path


@unittest.skipIf(torch is None, "PyTorch not installed")
class EvaluateEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from pipeline.prepare_from_repo import build_splits
        from training.evaluate import evaluate

        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.splits = cls.root / "splits"
        errors = build_splits(cls.splits)
        assert not errors, errors
        cls.checkpoint = _save_untrained(cls.root / "untrained_shared.pt", "transformer")
        cls.result = evaluate(cls.checkpoint, split="test", data_dir=SHIPPED_PROCESSED, splits_dir=cls.splits,
                              temperature=1.257665, n_bootstrap=200, seed=1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_runs_on_the_published_test_split(self) -> None:
        result = self.result
        self.assertEqual(result["split"]["n"], 142)
        self.assertEqual({k: v["support"] for k, v in result["metrics"]["per_class"].items()}, TEST_SUPPORT)
        frozen = json.loads((ROOT / "docs/engineering-log/phase6_test_ids.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(p["tic_id"] for p in result["predictions"]), sorted(frozen))
        self.assertEqual(result["provenance"]["data"]["split_hash"],
                         "ebcdc44c3dba849579675369b1559c77e50b6fead06abd40d3fc187425a7d4e4")

    def test_metrics_are_consistent(self) -> None:
        metrics, ci = self.result["metrics"], self.result["bootstrap"]["ci"]
        cm = metrics["confusion_matrix"]
        self.assertEqual(sum(map(sum, cm)), 142)
        self.assertAlmostEqual(metrics["accuracy"], sum(cm[i][i] for i in range(5)) / 142)
        self.assertLessEqual(ci["accuracy"][0], metrics["accuracy"])
        self.assertGreaterEqual(ci["accuracy"][1], metrics["accuracy"])
        correct = sum(p["label"] == p["predicted"] for p in self.result["predictions"])
        self.assertEqual(correct, metrics["correct"])
        # Logits are recorded and reproduce the probabilities at the recorded temperature.
        from training.evaluate import softmax

        first = self.result["predictions"][0]
        probs = softmax([first["logits"]], self.result["temperature"]["value"])[0]
        self.assertAlmostEqual(float(probs.max()), max(first["probabilities"].values()), places=5)
        self.assertIn("calibration_uncalibrated", metrics)  # T != 1 reports both

    def test_records_provenance_and_status(self) -> None:
        self.assertIsNone(self.result["published"])  # an untrained model is not a published artifact
        self.assertEqual(self.result["temperature"]["value"], 1.257665)
        self.assertEqual(len(self.result["checkpoint"]["sha256"]), 64)
        self.assertIn("commit", self.result["provenance"]["git"])
        json.dumps(self.result)

    def test_refuses_to_run_without_frozen_split_files(self) -> None:
        from training.evaluate import evaluate

        empty = self.root / "no_splits"
        empty.mkdir(exist_ok=True)
        with self.assertRaises(FileNotFoundError):
            evaluate(self.checkpoint, split="val", data_dir=SHIPPED_PROCESSED, splits_dir=empty, n_bootstrap=10)

    def test_cnn_checkpoints_are_supported(self) -> None:
        from training.evaluate import evaluate

        cnn = _save_untrained(self.root / "untrained_cnn.pt", "cnn")
        result = evaluate(cnn, split="val", data_dir=SHIPPED_PROCESSED, splits_dir=self.splits, n_bootstrap=20)
        self.assertEqual(result["checkpoint"]["architecture"], "StarCNN (dual branch)")
        self.assertEqual(result["split"]["n"], 141)


@unittest.skipIf(torch is None, "PyTorch not installed")
class PublishedCheckTests(unittest.TestCase):
    def test_verified_checkpoint_is_compared_with_published_numbers(self) -> None:
        from training.evaluate import compare_with_published

        metrics = {"accuracy": 111 / 142, "macro_f1": 0.76766, "weighted_f1": 0.77835}
        published = {"accuracy": 0.7817, "macro_f1": 0.7677, "weighted_f1": 0.7784}
        self.assertTrue(compare_with_published(metrics, published)["reproduced"])
        worse = dict(metrics, accuracy=110 / 142)
        comparison = compare_with_published(worse, published)
        self.assertFalse(comparison["reproduced"])
        self.assertFalse(comparison["accuracy"]["match"])

    def test_confusion_matrix_must_match_exactly(self) -> None:
        from training.evaluate import compare_with_published
        from training.verify_weights import find_published

        published = find_published("best_star_transformer_shared.pt")["published_test"]
        cm = [row[:] for row in published["confusion_matrix"]]
        metrics = {"accuracy": 111 / 142, "macro_f1": 0.76766, "weighted_f1": 0.77836, "confusion_matrix": cm}
        self.assertTrue(compare_with_published(metrics, published)["reproduced"])
        # Same accuracy, different errors: two misclassifications swapped between classes.
        cm[3][4], cm[3][1] = cm[3][4] + 1, cm[3][1] - 1
        comparison = compare_with_published(metrics, published)
        self.assertFalse(comparison["confusion_matrix"]["match"])
        self.assertFalse(comparison["reproduced"])

    def test_published_status_by_name_and_hash(self) -> None:
        from training.evaluate import published_status

        name = Path("best_star_transformer_shared.pt")
        good = published_status(name, "bf374ce492825916f2f97a4e29673a1eca35f76cc08f603b384d103fbe95d388")
        self.assertTrue(good["verified"])
        self.assertEqual(good["published_test"]["accuracy"], 0.7817)
        self.assertFalse(published_status(name, "0" * 64)["verified"])
        self.assertIsNone(published_status(Path("my_run.pt"), "0" * 64))


@unittest.skipIf(torch is None, "PyTorch not installed")
class EvaluateCliTests(unittest.TestCase):
    def test_writes_reports_and_gates_on_published(self) -> None:
        from pipeline.prepare_from_repo import build_splits
        from training.evaluate import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(build_splits(root / "splits"), [])
            # Named like the production checkpoint but with different bytes: must be flagged.
            checkpoint = _save_untrained(root / "best_star_transformer_shared.pt", "transformer")
            out = root / "reports"
            temperature = root / "t.txt"
            temperature.write_text("1.257665\n", encoding="utf-8")
            argv = ["--checkpoint", str(checkpoint), "--split", "val", "--data-dir", str(SHIPPED_PROCESSED),
                    "--splits-dir", str(root / "splits"), "--temperature-file", str(temperature),
                    "--bootstrap", "20", "--out-dir", str(out)]
            with redirect_stdout(io.StringIO()) as log:
                self.assertEqual(main(argv), 0)
                self.assertEqual(main(argv + ["--require-published"]), 1)
            record = json.loads((out / "evaluation_best_star_transformer_shared_val.json").read_text(encoding="utf-8"))
            self.assertFalse(record["published"]["verified"])
            self.assertEqual(record["temperature"]["value"], 1.257665)
            report = (out / "evaluation_best_star_transformer_shared_val.md").read_text(encoding="utf-8")
            self.assertIn("HASH MISMATCH", report)
            self.assertIn("FAILED: --require-published", log.getvalue())

    def test_missing_checkpoint(self) -> None:
        from training.evaluate import main

        with redirect_stdout(io.StringIO()) as log:
            self.assertEqual(main(["--checkpoint", "does/not/exist.pt"]), 1)
        self.assertIn("Checkpoint not found", log.getvalue())

    def test_invalid_numbers_are_rejected_by_the_parser(self) -> None:
        from training.evaluate import build_arg_parser

        parser = build_arg_parser()
        for bad in (["--temperature", "0"], ["--bootstrap", "0"], ["--confidence", "1.5"], ["--batch-size", "-1"]):
            with self.subTest(bad=bad), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parser.parse_args(["--checkpoint", "x.pt", *bad])

    def test_missing_frozen_test_split_is_a_clean_error(self) -> None:
        from training.evaluate import main

        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = _save_untrained(Path(tmp) / "m.pt", "transformer")
            empty = Path(tmp) / "no_splits"
            empty.mkdir()
            with redirect_stdout(io.StringIO()) as log:
                code = main(["--checkpoint", str(checkpoint), "--data-dir", str(SHIPPED_PROCESSED),
                             "--splits-dir", str(empty), "--out-dir", tmp])
        self.assertEqual(code, 1)
        self.assertIn("ERROR:", log.getvalue())

    def test_require_published_fails_when_a_verified_checkpoint_does_not_reproduce(self) -> None:
        from pipeline.prepare_from_repo import build_splits
        from training.evaluate import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(build_splits(root / "splits"), [])
            checkpoint = _save_untrained(root / "m.pt", "transformer")
            # Pretend the hash verified; the untrained model cannot reproduce the published numbers.
            fake = {"filename": "m.pt", "expected_sha256": "x", "verified": True,
                    "published_test": {"accuracy": 0.7817, "macro_f1": 0.7677, "weighted_f1": 0.7784}}
            argv = ["--checkpoint", str(checkpoint), "--data-dir", str(SHIPPED_PROCESSED),
                    "--splits-dir", str(root / "splits"), "--bootstrap", "10", "--out-dir", str(root / "r"),
                    "--require-published"]
            with patch("training.evaluate.published_status", return_value=fake), \
                    redirect_stdout(io.StringIO()) as log:
                self.assertEqual(main(argv), 1)
        self.assertIn("NOT reproduced", log.getvalue())


if __name__ == "__main__":
    unittest.main()
