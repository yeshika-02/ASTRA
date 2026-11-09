"""training/evaluate.py metric core (SP-15).

The published test confusion matrices exist only as images
(models/saved/test_confusion_matrix_transformer_shared.png and ..._cnn_dual.png).
They are transcribed below. The metric code must reproduce every published number
from them (docs/engineering-log/ground_truth_metrics.md), and their row sums must equal
the class counts of the shipped frozen test split.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from data.labels import NUM_CLASSES
from training.evaluate import bootstrap_ci, confusion_matrix, metrics_from_confusion, softmax

ROOT = Path(__file__).resolve().parent.parent

# Rows: true rr_lyrae, cepheid, eclipsing_binary, solar_like, stable; columns: predicted, same order.
PUBLISHED_CONFUSION = {
    "transformer_shared": np.array([
        [31, 0, 1, 0, 0],
        [0, 30, 0, 1, 4],
        [1, 0, 20, 2, 0],
        [1, 5, 0, 11, 5],
        [1, 4, 0, 6, 19],
    ]),
    "cnn_dual": np.array([
        [31, 0, 1, 0, 0],
        [1, 29, 0, 1, 4],
        [0, 1, 20, 1, 1],
        [1, 7, 1, 10, 3],
        [1, 2, 1, 5, 21],
    ]),
}

# docs/engineering-log/ground_truth_metrics.md
PUBLISHED_METRICS = {
    "transformer_shared": {
        "accuracy": 0.7817, "macro_f1": 0.7677, "weighted_f1": 0.7784,
        "per_class_f1": [0.9394, 0.8108, 0.9091, 0.5238, 0.6552],
        "accuracy_ci": [0.7113, 0.8521], "macro_f1_ci": [0.6944, 0.8320], "weighted_f1_ci": [0.7076, 0.8485],
    },
    "cnn_dual": {
        "accuracy": 0.7817, "macro_f1": 0.7635, "weighted_f1": 0.7756,
        "per_class_f1": [0.9394, 0.7838, 0.8696, 0.5128, 0.7119],
        "accuracy_ci": [0.7183, 0.8451], "macro_f1_ci": [0.6923, 0.8301], "weighted_f1_ci": [0.7052, 0.8435],
    },
}


def _pairs(cm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """One (label, prediction) pair per star, in confusion-matrix order."""
    labels = np.repeat(np.arange(len(cm)), cm.sum(axis=1))
    predictions = np.concatenate([np.repeat(np.arange(len(cm)), row) for row in cm])
    return labels, predictions


class PublishedResultsTests(unittest.TestCase):
    def test_metrics_reproduce_the_published_numbers(self) -> None:
        for model, cm in PUBLISHED_CONFUSION.items():
            with self.subTest(model=model):
                metrics = metrics_from_confusion(cm)
                published = PUBLISHED_METRICS[model]
                self.assertEqual((metrics["correct"], metrics["n"]), (111, 142))
                for name in ("accuracy", "macro_f1", "weighted_f1"):
                    self.assertAlmostEqual(metrics[name], published[name], places=4)
                f1 = [round(c["f1"], 4) for c in metrics["per_class"].values()]
                self.assertEqual(f1, published["per_class_f1"])

    def test_published_matrices_cover_the_shipped_test_split(self) -> None:
        ids = json.loads((ROOT / "docs/engineering-log/phase6_test_ids.json").read_text(encoding="utf-8"))
        counts = np.zeros(NUM_CLASSES, dtype=int)
        for tic in ids:
            meta = json.loads((ROOT / "astra-platform/data/processed" / tic / "metadata.json").read_text(encoding="utf-8"))
            counts[meta["label"]] += 1
        for model, cm in PUBLISHED_CONFUSION.items():
            self.assertEqual(cm.sum(axis=1).tolist(), counts.tolist(), model)

    def test_bootstrap_agrees_with_the_published_intervals(self) -> None:
        # The published CIs used an unrecorded RNG stream, so only agreement within 0.01 is expected.
        for model, cm in PUBLISHED_CONFUSION.items():
            ci = bootstrap_ci(*_pairs(cm), n_resamples=1000, seed=42)["ci"]
            for name in ("accuracy", "macro_f1", "weighted_f1"):
                for got, want in zip(ci[name], PUBLISHED_METRICS[model][f"{name}_ci"]):
                    self.assertAlmostEqual(got, want, delta=0.01, msg=f"{model} {name}")


class MetricCoreTests(unittest.TestCase):
    def test_matches_scikit_learn(self) -> None:
        from sklearn.metrics import confusion_matrix as sk_confusion
        from sklearn.metrics import f1_score, precision_score, recall_score

        rng = np.random.default_rng(0)
        labels = rng.integers(0, NUM_CLASSES, 300)
        predictions = np.where(rng.random(300) < 0.6, labels, rng.integers(0, NUM_CLASSES, 300))
        predictions[predictions == 3] = 2  # class 3 never predicted: exercises zero division
        cm = confusion_matrix(labels, predictions)
        np.testing.assert_array_equal(cm, sk_confusion(labels, predictions, labels=range(NUM_CLASSES)))
        metrics = metrics_from_confusion(cm)
        kwargs = {"labels": list(range(NUM_CLASSES)), "zero_division": 0}
        self.assertAlmostEqual(metrics["macro_f1"], f1_score(labels, predictions, average="macro", **kwargs))
        self.assertAlmostEqual(metrics["weighted_f1"], f1_score(labels, predictions, average="weighted", **kwargs))
        precision = precision_score(labels, predictions, average=None, **kwargs)
        recall = recall_score(labels, predictions, average=None, **kwargs)
        for i, values in enumerate(metrics["per_class"].values()):
            self.assertAlmostEqual(values["precision"], precision[i])
            self.assertAlmostEqual(values["recall"], recall[i])

    def test_bootstrap_is_deterministic_and_brackets_the_estimate(self) -> None:
        labels, predictions = _pairs(PUBLISHED_CONFUSION["transformer_shared"])
        first = bootstrap_ci(labels, predictions, n_resamples=200, seed=3)
        self.assertEqual(first, bootstrap_ci(labels, predictions, n_resamples=200, seed=3))
        self.assertNotEqual(first["ci"], bootstrap_ci(labels, predictions, n_resamples=200, seed=4)["ci"])
        low, high = first["ci"]["accuracy"]
        self.assertLess(low, 111 / 142)
        self.assertGreater(high, 111 / 142)

    def test_perfect_predictions_have_a_degenerate_interval(self) -> None:
        labels = np.arange(50) % NUM_CLASSES
        ci = bootstrap_ci(labels, labels, n_resamples=100)["ci"]
        self.assertEqual(ci["accuracy"], [1.0, 1.0])

    def test_invalid_arguments(self) -> None:
        with self.assertRaises(ValueError):
            confusion_matrix(np.zeros(3), np.zeros(4))
        with self.assertRaises(ValueError):
            bootstrap_ci(np.zeros(3), np.zeros(3), confidence=1.5)
        with self.assertRaises(ValueError):
            softmax(np.zeros((2, 5)), temperature=0)

    def test_temperature_softens_but_keeps_the_argmax(self) -> None:
        logits = np.array([[4.0, 1.0, 0.0, 0.0, -1.0], [0.0, 0.0, 9.0, 1.0, 0.0]])
        sharp, soft = softmax(logits), softmax(logits, temperature=1.257665)
        np.testing.assert_allclose(sharp.sum(axis=1), 1.0)
        np.testing.assert_array_equal(sharp.argmax(axis=1), soft.argmax(axis=1))
        self.assertTrue((soft.max(axis=1) < sharp.max(axis=1)).all())


if __name__ == "__main__":
    unittest.main()
