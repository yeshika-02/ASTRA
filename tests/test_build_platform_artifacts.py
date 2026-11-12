"""pipeline/build_platform_artifacts.py (SP-19), tested on synthetic predictions.

- NLL is computed from probabilities (never copied from ECE) and the calibration metrics
  agree with training/calibration.py.
- An evaluate.py record with logits replaces a model's recorded values.
- Outputs keep the fields the web platform reads, and the committed outputs are current.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from pipeline import build_platform_artifacts as gen

try:
    import torch
except ImportError:  # pragma: no cover - depends on environment
    torch = None

CLASSES = ["rr_lyrae", "cepheid", "eclipsing_binary", "solar_like", "stable"]


def _synthetic_logits(n: int = 200, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    labels = rng.integers(0, 5, n)
    logits = rng.normal(0, 1, (n, 5))
    logits[np.arange(n), labels] += rng.uniform(0, 3, n)  # mostly right, sometimes wrong
    return logits, labels


def _evaluation_record(path: Path, logits: np.ndarray, labels: np.ndarray, temperature: float = 1.3) -> Path:
    """The parts of an evaluate.py JSON record the generator reads."""
    record = {
        "split": {"name": "test"},
        "checkpoint": {"sha256": "0" * 64},
        "published": None,
        "temperature": {"value": temperature},
        "bootstrap": {"ci": {"accuracy": [0.5, 0.7], "macro_f1": [0.4, 0.6], "weighted_f1": [0.45, 0.65]}},
        "predictions": [{"label": CLASSES[int(y)], "logits": [float(v) for v in row]} for row, y in zip(logits, labels)],
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


class MetricFunctionTests(unittest.TestCase):
    def test_nll_and_brier_by_hand(self) -> None:
        probs = np.array([[0.7, 0.2, 0.1], [0.1, 0.1, 0.8]])
        labels = np.array([0, 1])
        self.assertAlmostEqual(gen.nll(probs, labels), -(np.log(0.7) + np.log(0.1)) / 2)
        self.assertAlmostEqual(gen.brier(probs, labels), ((0.09 + 0.04 + 0.01) + (0.01 + 0.81 + 0.64)) / 2)

    def test_nll_is_not_ece(self) -> None:
        logits, labels = _synthetic_logits()
        cal = gen.calibration_from_logits(logits, labels, temperature=1.3)
        self.assertNotAlmostEqual(cal["nll_raw"], cal["ece_raw"], places=3)
        self.assertNotAlmostEqual(cal["nll_calibrated"], cal["ece_calibrated"], places=3)
        self.assertNotAlmostEqual(cal["nll_raw"], cal["nll_calibrated"], places=4)  # temperature matters

    @unittest.skipIf(torch is None, "PyTorch not installed")
    def test_matches_training_calibration(self) -> None:
        from training.calibration import compute_calibration_metrics
        from training.evaluate import softmax

        logits, labels = _synthetic_logits(143)  # not a multiple of 5: exercises the last, larger bin
        probs = softmax(logits)
        ece, nll, brier, _ = compute_calibration_metrics(torch.tensor(probs, dtype=torch.float64),
                                                         torch.tensor(labels), n_bins=5)
        self.assertAlmostEqual(gen.adaptive_ece(probs, labels), ece, places=6)
        self.assertAlmostEqual(gen.nll(probs, labels), nll, places=6)
        self.assertAlmostEqual(gen.brier(probs, labels), brier, places=6)

    def test_too_few_samples_for_the_bins(self) -> None:
        with self.assertRaises(ValueError):
            gen.adaptive_ece(np.full((3, 5), 0.2), np.zeros(3, dtype=int))


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = gen.load_record()
        cls.outputs = gen.build(cls.record)

    def test_benchmark_has_the_fields_the_platform_reads(self) -> None:
        benchmark = self.outputs["benchmark.json"]
        self.assertEqual(set(benchmark["models"]), {"shared", "cnn_dual", "cross", "separate", "only"})
        for entry in benchmark["models"].values():
            for key in ("label", "test_accuracy", "accuracy_ci", "macro_f1", "macro_f1_ci", "weighted_f1"):
                self.assertIn(key, entry)
            self.assertEqual(set(entry["per_class_f1"]), set(CLASSES))
            self.assertEqual(set(entry["subgroups"]),
                             {"catalog_accuracy", "catalog_macro_f1", "bls_accuracy", "bls_macro_f1"})
        dataset = benchmark["dataset"]
        self.assertEqual(dataset["total_stars"], 944)
        self.assertEqual(dataset["split_counts"], {"test": 142, "train": 661, "val": 141})
        self.assertEqual(sum(dataset["class_counts"].values()), 944)

    def test_published_numbers(self) -> None:
        models = self.outputs["benchmark.json"]["models"]
        self.assertEqual((models["shared"]["test_accuracy"], models["shared"]["macro_f1"]), (0.7817, 0.7677))
        self.assertEqual(models["shared"]["accuracy_ci"], "[71.13%, 85.21%]")
        # The CNN row follows its published confusion matrix (7C), not the Phase 7A report.
        self.assertEqual((models["cnn_dual"]["macro_f1"], models["cnn_dual"]["weighted_f1"]), (0.7635, 0.7756))
        self.assertEqual(models["cnn_dual"]["accuracy_ci"], "[71.83%, 84.51%]")
        self.assertEqual(models["cnn_dual"]["status"]["subgroups"], "unverified")

    def test_calibration_artifact(self) -> None:
        calibration = self.outputs["calibration.json"]
        for summary in calibration["global"].values():
            self.assertIsNone(summary["nll_raw"])  # no valid NLL is recorded
            self.assertIsNone(summary["nll_calibrated"])
            self.assertIn("source", summary)
        self.assertEqual(calibration["temperatures"], {"shared": 1.257665, "cnn_dual": 1.010702})
        self.assertEqual(set(calibration["per_class"]["solar_like"]),
                         {"cnn_raw", "cnn_calibrated", "transformer_raw", "transformer_calibrated"})

    def test_uncertainty_and_research_artifacts(self) -> None:
        sweep = self.outputs["uncertainty.json"]["coverage_sweep"]
        self.assertEqual(len(sweep), 10)
        self.assertEqual(set(sweep[0]), {"accuracy", "confidence_threshold", "coverage", "model"})
        research = self.outputs["research_findings.json"]
        self.assertEqual(research["accuracy_gap_catalog_vs_bls"], 0.3231)
        self.assertEqual(research["findings"][1]["value"], 0.0368)
        self.assertEqual(research["shared_transformer"], self.outputs["benchmark.json"]["models"]["shared"])
        registry = self.outputs["model_registry.json"]
        self.assertEqual(registry["active_model"]["calibration"], self.outputs["calibration.json"]["global"]["shared"])

    def test_docs_page_lists_every_model_and_flag(self) -> None:
        page = self.outputs["metrics.md"]
        for model in self.record["models"].values():
            self.assertIn(model["label"], page)
        for marker in ("Superseded results", "Numbers without a source", "not recorded", "111/142",
                       "Baselines on the same test split", "| 12 statistics of the network's own inputs | RandomForest | 79.58%"):
            self.assertIn(marker, page)

    def test_committed_outputs_are_up_to_date(self) -> None:
        self.assertEqual(gen.stale_outputs(self.outputs), [],
                         "run: python pipeline/build_platform_artifacts.py")


class EvaluationOverrideTests(unittest.TestCase):
    def test_an_evaluation_record_replaces_recorded_values(self) -> None:
        logits, labels = _synthetic_logits()
        with tempfile.TemporaryDirectory() as tmp:
            path = _evaluation_record(Path(tmp) / "eval.json", logits, labels)
            evaluation = gen.load_evaluation(path, CLASSES)
            outputs = gen.build(gen.load_record(), {"shared": evaluation})
        shared = outputs["benchmark.json"]["models"]["shared"]
        self.assertEqual(shared["status"]["point_metrics"], "recomputed")
        self.assertAlmostEqual(shared["test_accuracy"], round(float((logits.argmax(1) == labels).mean()), 4))
        self.assertEqual(shared["accuracy_ci"], "[50.00%, 70.00%]")
        cal = outputs["calibration.json"]["global"]["shared"]
        self.assertEqual(cal["status"], "recomputed")
        self.assertIsNotNone(cal["nll_calibrated"])
        self.assertNotEqual(cal["nll_calibrated"], cal["ece_calibrated"])
        # Other models keep their recorded values.
        self.assertEqual(outputs["benchmark.json"]["models"]["cross"]["test_accuracy"], 0.8099)

    def test_records_without_logits_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.json"
            path.write_text(json.dumps({"predictions": [{"label": "stable", "probabilities": {}}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                gen.load_evaluation(path, CLASSES)

    def test_check_mode_reports_a_stale_file(self) -> None:
        outputs = {"benchmark.json": {"a": 1}}
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp)
            (artifacts / "benchmark.json").write_text('{"a": 2}\n', encoding="utf-8")
            self.assertEqual(len(gen.stale_outputs(outputs, artifacts, artifacts / "metrics.md")), 1)
            gen.write_outputs(outputs, artifacts, artifacts / "metrics.md")
            self.assertEqual(gen.stale_outputs(outputs, artifacts, artifacts / "metrics.md"), [])


if __name__ == "__main__":
    unittest.main()
