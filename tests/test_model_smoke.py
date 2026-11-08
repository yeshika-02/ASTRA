"""Forward-pass smoke tests for the model architectures (replaces the broken inline CI snippet).

Skipped automatically when PyTorch is not installed.
"""

from __future__ import annotations

import unittest

try:
    import torch
except ImportError:  # pragma: no cover - depends on environment
    torch = None

from data.labels import NUM_CLASSES


@unittest.skipIf(torch is None, "PyTorch not installed")
class ModelSmokeTests(unittest.TestCase):
    def test_hybrid_transformer_variants_accept_dual_channel_input(self) -> None:
        from training.models.hybrid_transformer import HybridTransformer

        x = torch.randn(2, 2, 1000)
        for variant in ["shared", "separate", "cross", "only", "shared_no_folded", "shared_no_folded_matched"]:
            with self.subTest(variant=variant):
                model = HybridTransformer(variant=variant, num_classes=NUM_CLASSES).eval()
                with torch.no_grad():
                    out = model(x)
                self.assertEqual(tuple(out.shape), (2, NUM_CLASSES))

    def test_shared_variant_parameter_count_matches_published_value(self) -> None:
        from training.models.hybrid_transformer import HybridTransformer

        model = HybridTransformer(variant="shared", num_classes=NUM_CLASSES)
        n_params = sum(p.numel() for p in model.parameters())
        self.assertEqual(n_params, 1_373_701)

    def test_star_cnn_single_and_dual_branch(self) -> None:
        from training.models.star_cnn import StarCNN

        cases = [(False, torch.randn(2, 1, 1000)), (True, torch.randn(2, 2, 1000))]
        for use_folded, x in cases:
            with self.subTest(use_folded=use_folded):
                model = StarCNN(use_folded=use_folded).eval()
                with torch.no_grad():
                    out = model(x)
                self.assertEqual(tuple(out.shape), (2, NUM_CLASSES))


if __name__ == "__main__":
    unittest.main()
