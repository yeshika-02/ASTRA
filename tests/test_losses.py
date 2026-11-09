"""Loss functions used for training: FocalLoss and RegularizedFocalLoss."""

from __future__ import annotations

import unittest

try:
    import torch
    import torch.nn.functional as F
except ImportError:  # pragma: no cover - depends on environment
    torch = None


@unittest.skipIf(torch is None, "PyTorch not installed")
class FocalLossTests(unittest.TestCase):
    def setUp(self) -> None:
        from training.focal_loss import FocalLoss

        self.FocalLoss = FocalLoss
        g = torch.Generator().manual_seed(0)
        self.logits = torch.randn(16, 5, generator=g)
        self.targets = torch.randint(0, 5, (16,), generator=g)

    def test_gamma_zero_equals_cross_entropy(self) -> None:
        loss = self.FocalLoss(gamma=0.0)(self.logits, self.targets)
        expected = F.cross_entropy(self.logits, self.targets)
        self.assertTrue(torch.allclose(loss, expected, atol=1e-6))

    def test_focusing_reduces_loss_on_easy_examples(self) -> None:
        # With gamma > 0, every per-sample loss is scaled by (1 - p_t)^gamma <= 1.
        ce = F.cross_entropy(self.logits, self.targets, reduction="none")
        fl = self.FocalLoss(gamma=2.0, reduction="none")(self.logits, self.targets)
        self.assertTrue(torch.all(fl <= ce + 1e-7))

    def test_alpha_weights_scale_per_class(self) -> None:
        alpha = [1.0, 2.0, 3.0, 4.0, 5.0]
        weighted = self.FocalLoss(alpha=alpha, gamma=0.0, reduction="none")(self.logits, self.targets)
        plain = F.cross_entropy(self.logits, self.targets, reduction="none")
        expected = torch.tensor(alpha)[self.targets] * plain
        self.assertTrue(torch.allclose(weighted, expected, atol=1e-6))

    def test_reductions(self) -> None:
        none = self.FocalLoss(reduction="none")(self.logits, self.targets)
        self.assertEqual(tuple(none.shape), (16,))
        self.assertTrue(torch.allclose(self.FocalLoss(reduction="sum")(self.logits, self.targets), none.sum()))
        self.assertTrue(torch.allclose(self.FocalLoss(reduction="mean")(self.logits, self.targets), none.mean()))

    def test_gradients_are_finite(self) -> None:
        logits = self.logits.clone().requires_grad_(True)
        self.FocalLoss()(logits, self.targets).backward()
        self.assertTrue(torch.isfinite(logits.grad).all())


@unittest.skipIf(torch is None, "PyTorch not installed")
class RegularizedFocalLossTests(unittest.TestCase):
    def setUp(self) -> None:
        from training.train_transformer import RegularizedFocalLoss

        self.Loss = RegularizedFocalLoss
        g = torch.Generator().manual_seed(1)
        self.logits = torch.randn(32, 5, generator=g)
        self.targets = torch.randint(0, 5, (32,), generator=g)

    def test_no_smoothing_no_focus_equals_cross_entropy(self) -> None:
        loss = self.Loss(gamma=0.0, label_smoothing=0.0)(self.logits, self.targets)
        self.assertTrue(torch.allclose(loss, F.cross_entropy(self.logits, self.targets), atol=1e-6))

    def test_smoothing_spreads_mass_over_other_classes(self) -> None:
        # Smoothing eps puts (1 - eps) on the true class and eps / (C - 1) on each other
        # class, which differs from PyTorch's built-in smoothing (eps / C on every class).
        eps = 0.1
        loss = self.Loss(gamma=0.0, label_smoothing=eps)(self.logits, self.targets)
        log_p = torch.log_softmax(self.logits, dim=-1)
        soft = torch.full_like(log_p, eps / 4)
        soft.scatter_(1, self.targets.unsqueeze(1), 1.0 - eps)
        expected = -(soft * log_p).sum(dim=-1).mean()
        self.assertTrue(torch.allclose(loss, expected, atol=1e-6))

    def test_class_weights_change_the_loss(self) -> None:
        alpha = torch.tensor([1.0, 1.0, 1.0, 1.0, 10.0])
        weighted = self.Loss(alpha=alpha)(self.logits, self.targets)
        unweighted = self.Loss()(self.logits, self.targets)
        self.assertFalse(torch.allclose(weighted, unweighted))

    def test_perfect_confident_prediction_has_near_zero_loss(self) -> None:
        targets = torch.arange(5)
        logits = torch.full((5, 5), -20.0)
        logits[targets, targets] = 20.0
        loss = self.Loss(gamma=2.0, label_smoothing=0.0)(logits, targets)
        self.assertLess(loss.item(), 1e-6)


if __name__ == "__main__":
    unittest.main()
