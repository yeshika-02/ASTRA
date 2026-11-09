"""training.calibration.compute_calibration_metrics: ECE, NLL and Brier score.

These tests also pin the return order (ece, nll, brier, bins). The published
astra-platform/data/artifacts/calibration.json reports NLL equal to ECE for both
models (audit finding R4), which is impossible for real predictions; this function
returns them separately and with different values.
"""

from __future__ import annotations

import math
import unittest

try:
    import torch
except ImportError:  # pragma: no cover - depends on environment
    torch = None


@unittest.skipIf(torch is None, "PyTorch not installed")
class CalibrationMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        from training.calibration import compute_calibration_metrics

        self.metrics = compute_calibration_metrics

    def test_perfectly_calibrated_one_hot_predictions(self) -> None:
        labels = torch.tensor([0, 1, 2, 3, 4] * 4)
        probs = torch.nn.functional.one_hot(labels, 5).float()
        ece, nll, brier, bins = self.metrics(probs, labels, n_bins=4)
        self.assertAlmostEqual(ece, 0.0, places=6)
        self.assertAlmostEqual(brier, 0.0, places=6)
        self.assertLess(nll, 1e-6)
        self.assertEqual(len(bins), 4)

    def test_nll_matches_manual_value_and_differs_from_ece(self) -> None:
        g = torch.Generator().manual_seed(3)
        probs = torch.softmax(torch.randn(50, 5, generator=g), dim=-1)
        labels = torch.randint(0, 5, (50,), generator=g)
        ece, nll, brier, _ = self.metrics(probs, labels, n_bins=5)
        manual_nll = -torch.log(probs[torch.arange(50), labels]).mean().item()
        self.assertAlmostEqual(nll, manual_nll, places=5)
        self.assertNotAlmostEqual(nll, ece, places=3)

    def test_brier_score_manual(self) -> None:
        probs = torch.tensor([[0.7, 0.3], [0.4, 0.6]])
        labels = torch.tensor([0, 0])
        _, _, brier, _ = self.metrics(probs, labels, n_bins=2)
        expected = ((0.3**2 + 0.3**2) + (0.6**2 + 0.6**2)) / 2
        self.assertAlmostEqual(brier, expected, places=6)

    def test_overconfident_wrong_predictions_have_high_ece(self) -> None:
        labels = torch.zeros(20, dtype=torch.long)
        probs = torch.full((20, 5), 0.01)
        probs[:, 1] = 0.96  # always predicts class 1 with 96% confidence, always wrong
        ece, _, _, _ = self.metrics(probs, labels, n_bins=4)
        self.assertAlmostEqual(ece, 0.96, places=5)

    def test_equal_frequency_bins_cover_every_sample_once(self) -> None:
        g = torch.Generator().manual_seed(4)
        probs = torch.softmax(torch.randn(23, 5, generator=g), dim=-1)
        labels = torch.randint(0, 5, (23,), generator=g)
        _, _, _, bins = self.metrics(probs, labels, n_bins=5)
        self.assertEqual(sum(b["size"] for b in bins), 23)
        # Bins are ordered by confidence.
        confs = [b["conf"] for b in bins]
        self.assertEqual(confs, sorted(confs))
        for b in bins:
            self.assertFalse(math.isnan(b["acc"]))


if __name__ == "__main__":
    unittest.main()
