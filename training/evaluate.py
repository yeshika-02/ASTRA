"""
ASTRA — evaluate a checkpoint on a frozen split, with bootstrap confidence intervals.

Metrics come from the confusion matrix, so the same code reproduces the published test
results from the published confusion matrices (tests/test_evaluate.py). Confidence
intervals resample stars with replacement (percentile bootstrap, fixed seed).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES, NUM_CLASSES

BOOTSTRAP_METRICS = ("accuracy", "macro_f1", "weighted_f1")


def confusion_matrix(labels: np.ndarray, predictions: np.ndarray, num_classes: int = NUM_CLASSES) -> np.ndarray:
    """Rows are true classes, columns predicted classes."""
    labels = np.asarray(labels, dtype=np.int64)
    predictions = np.asarray(predictions, dtype=np.int64)
    if labels.shape != predictions.shape:
        raise ValueError(f"labels {labels.shape} and predictions {predictions.shape} differ in shape")
    flat = np.bincount(labels * num_classes + predictions, minlength=num_classes * num_classes)
    return flat.reshape(num_classes, num_classes)


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Element-wise division that gives 0 where the denominator is 0 (sklearn's zero_division=0)."""
    numerator = np.asarray(numerator, dtype=np.float64)
    denominator = np.asarray(denominator, dtype=np.float64)
    out = np.zeros(np.broadcast(numerator, denominator).shape)
    np.divide(numerator, denominator, out=out, where=denominator != 0)
    return out


def metrics_from_confusion(cm: np.ndarray, class_names: tuple[str, ...] | list[str] = CLASS_NAMES) -> dict:
    """Accuracy, macro / weighted F1 and per-class precision, recall, F1 and support."""
    cm = np.asarray(cm, dtype=np.int64)
    true_positive = np.diag(cm)
    support = cm.sum(axis=1)
    predicted = cm.sum(axis=0)
    precision = _safe_divide(true_positive, predicted)
    recall = _safe_divide(true_positive, support)
    f1 = _safe_divide(2 * true_positive, support + predicted)
    total = int(cm.sum())
    return {
        "n": total,
        "correct": int(true_positive.sum()),
        "accuracy": float(true_positive.sum() / total) if total else 0.0,
        "macro_f1": float(f1.mean()),
        "weighted_f1": float((f1 * support).sum() / total) if total else 0.0,
        "per_class": {
            name: {"precision": float(precision[i]), "recall": float(recall[i]), "f1": float(f1[i]),
                   "support": int(support[i])}
            for i, name in enumerate(class_names)
        },
    }


def bootstrap_ci(
    labels: np.ndarray,
    predictions: np.ndarray,
    num_classes: int = NUM_CLASSES,
    n_resamples: int = 1000,
    seed: int = 42,
    confidence: float = 0.95,
) -> dict:
    """Percentile bootstrap CIs for accuracy, macro F1 and weighted F1, resampling stars."""
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if n_resamples < 1:
        raise ValueError("n_resamples must be at least 1")
    labels = np.asarray(labels, dtype=np.int64)
    predictions = np.asarray(predictions, dtype=np.int64)
    n = len(labels)
    rng = np.random.default_rng(seed)
    samples = {name: np.empty(n_resamples) for name in BOOTSTRAP_METRICS}
    for b in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        resampled = metrics_from_confusion(confusion_matrix(labels[idx], predictions[idx], num_classes),
                                           class_names=[str(i) for i in range(num_classes)])
        for name in BOOTSTRAP_METRICS:
            samples[name][b] = resampled[name]
    alpha = (1 - confidence) / 2
    return {
        "method": "percentile bootstrap over stars",
        "n_resamples": n_resamples,
        "seed": seed,
        "confidence": confidence,
        "ci": {name: [float(np.quantile(values, alpha)), float(np.quantile(values, 1 - alpha))]
               for name, values in samples.items()},
    }


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """Row-wise softmax of logits / temperature."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    scaled = np.asarray(logits, dtype=np.float64) / temperature
    scaled -= scaled.max(axis=1, keepdims=True)
    exp = np.exp(scaled)
    return exp / exp.sum(axis=1, keepdims=True)
