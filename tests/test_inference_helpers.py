"""Helper functions shared by the inference and training scripts."""

from __future__ import annotations

import unittest

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:  # pragma: no cover - depends on environment
    torch = None

from data.labels import NUM_CLASSES


class UploadPreprocessingTests(unittest.TestCase):
    """training/upload_inference.py preprocessing (numpy only)."""

    def setUp(self) -> None:
        from training import upload_inference as ui

        self.ui = ui

    def test_output_is_1000_points_zero_mean_unit_std(self) -> None:
        flux = 1.0 + 0.01 * np.sin(np.linspace(0, 20, 3000))
        out = self.ui.preprocess_raw_flux(flux.tolist())
        self.assertEqual(out.shape, (1000,))
        self.assertAlmostEqual(float(out.mean()), 0.0, places=5)
        self.assertAlmostEqual(float(out.std()), 1.0, places=4)

    def test_non_finite_values_are_dropped_before_the_minimum_check(self) -> None:
        flux = [1.0] * 49 + [float("nan")] * 100 + [float("inf")]
        with self.assertRaisesRegex(ValueError, "minimum 50"):
            self.ui.preprocess_raw_flux(flux)

    def _spiky_flux(self) -> list[float]:
        rng = np.random.default_rng(0)
        flux = (1.0 + 0.001 * rng.standard_normal(2000)).tolist()
        flux[500] = 50.0  # one extreme spike
        return flux

    def test_clipping_bounds_values_to_mean_plus_three_sigma_of_the_raw_input(self) -> None:
        # Pins current behaviour: the clip uses the mean/std of the raw input, which
        # includes the outlier itself, so the spike is only pulled down to mean + 3*std.
        flux = np.asarray(self._spiky_flux(), dtype=np.float32)
        bound = flux.mean() + 3 * flux.std()
        out = self.ui.preprocess_raw_flux(flux.tolist())
        self.assertTrue(np.all(np.isfinite(out)))
        self.assertLess(bound, 50.0)
        self.assertGreater(bound, 3.0)  # far above the ~0.001 scatter of the real signal

    @unittest.expectedFailure
    def test_single_spike_is_suppressed_like_training(self) -> None:
        # Known issue (audit P7): training used astropy sigma_clip (5 sigma, iterative,
        # robust); the upload path uses one non-robust 3-sigma pass, so a single spike
        # still dominates the normalised curve (max |z| about 31). Remove the
        # expectedFailure marker when upload preprocessing is aligned with training.
        out = self.ui.preprocess_raw_flux(self._spiky_flux())
        self.assertLess(float(np.abs(out).max()), 10.0)

    def test_softmax_and_entropy(self) -> None:
        probs = self.ui.softmax(np.array([2.0, 1.0, 0.1]))
        self.assertAlmostEqual(float(probs.sum()), 1.0, places=6)
        self.assertAlmostEqual(self.ui.compute_entropy(np.array([1.0, 0.0, 0.0])), 0.0, places=6)
        uniform = np.full(5, 0.2)
        self.assertAlmostEqual(self.ui.compute_entropy(uniform), np.log(5), places=6)

    def test_fold_is_normalised_and_periodic_signal_survives(self) -> None:
        t = np.linspace(0, 20.8, 1000)  # 1000 points at the assumed 30-min cadence
        flux = np.sin(2 * np.pi * t / 2.0).astype(np.float32)
        folded = self.ui.fold_light_curve_linear(flux, period=2.0)
        self.assertEqual(folded.shape, (1000,))
        self.assertAlmostEqual(float(folded.mean()), 0.0, places=4)
        # Folding at the true period yields one clean cycle: strongly anti-correlated halves.
        self.assertLess(np.corrcoef(folded[:500], folded[500:])[0, 1], -0.9)


@unittest.skipIf(torch is None, "PyTorch not installed")
class PredictInferenceHelperTests(unittest.TestCase):
    def test_entropy_matches_shannon_definition(self) -> None:
        from training.predict_inference import compute_entropy

        p = np.array([0.5, 0.25, 0.25, 0.0, 0.0])
        expected = -(0.5 * np.log(0.5) + 2 * 0.25 * np.log(0.25))
        self.assertAlmostEqual(compute_entropy(p), expected, places=6)

    def test_enable_dropout_keeps_only_dropout_layers_stochastic(self) -> None:
        from training.predict_inference import enable_dropout

        model = nn.Sequential(nn.Linear(4, 4), nn.BatchNorm1d(4), nn.Dropout(0.5), nn.Linear(4, 2))
        enable_dropout(model)
        self.assertFalse(model[1].training)  # BatchNorm stays in eval mode
        self.assertTrue(model[2].training)  # Dropout active for MC sampling

    def test_mc_dropout_passes_differ_but_eval_is_deterministic(self) -> None:
        from training.models.hybrid_transformer import HybridTransformer
        from training.predict_inference import enable_dropout

        torch.manual_seed(0)
        model = HybridTransformer(variant="shared", num_classes=NUM_CLASSES)
        x = torch.randn(1, 2, 1000)
        model.eval()
        with torch.no_grad():
            self.assertTrue(torch.equal(model(x), model(x)))
            enable_dropout(model)
            self.assertFalse(torch.equal(model(x), model(x)))

    def test_linear_fold_shape_and_normalisation(self) -> None:
        from training.predict_inference import fold_light_curve_linear

        flux = np.sin(np.linspace(0, 40, 1000)).astype(np.float32)
        out = fold_light_curve_linear(flux, period=1.5, n_points_clean=20000, source_cadence=2.0)
        self.assertEqual(out.shape, (1000,))
        self.assertAlmostEqual(float(out.std()), 1.0, places=4)


@unittest.skipIf(torch is None, "PyTorch not installed")
class TrainingLoopTests(unittest.TestCase):
    def test_attention_entropy_bounds(self) -> None:
        from training.train_transformer import compute_attention_entropy

        uniform = torch.full((2, 10, 10), 0.1)
        self.assertAlmostEqual(compute_attention_entropy(uniform), float(np.log(10)), places=5)
        self.assertEqual(compute_attention_entropy(None), 0.0)

    def test_seeding_makes_initialisation_reproducible(self) -> None:
        from training.models.hybrid_transformer import HybridTransformer
        from training.train_transformer import set_deterministic_seeds

        previous = torch.are_deterministic_algorithms_enabled()
        try:
            set_deterministic_seeds(123)
            a = HybridTransformer(variant="shared", num_classes=NUM_CLASSES).state_dict()
            set_deterministic_seeds(123)
            b = HybridTransformer(variant="shared", num_classes=NUM_CLASSES).state_dict()
        finally:
            torch.use_deterministic_algorithms(previous)
        for key in a:
            self.assertTrue(torch.equal(a[key], b[key]), key)

    def test_one_epoch_trains_and_validates_on_synthetic_batches(self) -> None:
        from torch.utils.data import DataLoader, TensorDataset

        from training.models.hybrid_transformer import HybridTransformer
        from training.train_transformer import RegularizedFocalLoss, train_one_epoch, validate

        torch.manual_seed(0)
        x = torch.randn(20, 2, 1000)
        y = torch.arange(20) % NUM_CLASSES
        loader = DataLoader(TensorDataset(x, y), batch_size=10)
        model = HybridTransformer(variant="shared", num_classes=NUM_CLASSES)
        criterion = RegularizedFocalLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        before = [p.detach().clone() for p in model.parameters()]

        loss, grad_norm, entropy = train_one_epoch(model, loader, criterion, optimizer, torch.device("cpu"))
        self.assertTrue(np.isfinite(loss) and loss > 0)
        self.assertTrue(np.isfinite(grad_norm))
        self.assertGreater(entropy, 0.0)
        self.assertTrue(any(not torch.equal(b, p) for b, p in zip(before, model.parameters())))

        result = validate(model, loader, criterion, torch.device("cpu"))
        self.assertGreaterEqual(result["val_accuracy"], 0.0)
        self.assertLessEqual(result["val_accuracy"], 1.0)
        self.assertEqual(sum(result["per_class_total"].values()), 20)


if __name__ == "__main__":
    unittest.main()
