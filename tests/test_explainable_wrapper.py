"""ExplainableHybridTransformerWrapper must reproduce the base model exactly.

The wrapper re-implements HybridTransformer's 'shared' forward pass by hand so it can
also return attention maps and intermediate features for the explainability export.
If the two ever diverge, every exported explanation describes a different model.
"""

from __future__ import annotations

import unittest

try:
    import torch
except ImportError:  # pragma: no cover - depends on environment
    torch = None

from data.labels import NUM_CLASSES


@unittest.skipIf(torch is None, "PyTorch not installed")
class ExplainableWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        from training.models.explainable_wrapper import ExplainableHybridTransformerWrapper
        from training.models.hybrid_transformer import HybridTransformer

        torch.manual_seed(0)
        self.base = HybridTransformer(variant="shared", num_classes=NUM_CLASSES).eval()
        self.wrapper = ExplainableHybridTransformerWrapper(self.base).eval()
        self.x = torch.randn(3, 2, 1000)

    def test_logits_match_the_base_model(self) -> None:
        with torch.no_grad():
            expected = self.base(self.x)
            logits, _, _, _ = self.wrapper(self.x)
        self.assertTrue(torch.allclose(logits, expected, atol=1e-5))

    def test_output_shapes(self) -> None:
        with torch.no_grad():
            logits, attn, cnn_features, pooled = self.wrapper(self.x)
        self.assertEqual(tuple(logits.shape), (3, NUM_CLASSES))
        self.assertEqual(tuple(attn.shape), (3, 250, 250))
        self.assertEqual(tuple(cnn_features.shape), (3, 128, 250))
        self.assertEqual(tuple(pooled.shape), (3, 128))

    def test_attention_rows_are_probability_distributions(self) -> None:
        with torch.no_grad():
            _, attn, _, _ = self.wrapper(self.x)
        self.assertTrue(torch.all(attn >= 0))
        self.assertTrue(torch.allclose(attn.sum(dim=-1), torch.ones(3, 250), atol=1e-4))

    def test_attention_matches_the_base_model_capture(self) -> None:
        with torch.no_grad():
            self.base(self.x)
            _, attn, _, _ = self.wrapper(self.x)
        self.assertTrue(torch.allclose(attn, self.base.last_attention_weights, atol=1e-5))

    def test_rejects_unsupported_variants(self) -> None:
        from training.models.explainable_wrapper import ExplainableHybridTransformerWrapper
        from training.models.hybrid_transformer import HybridTransformer

        wrapper = ExplainableHybridTransformerWrapper(HybridTransformer(variant="cross", num_classes=NUM_CLASSES))
        with self.assertRaises(ValueError):
            wrapper(self.x)


if __name__ == "__main__":
    unittest.main()
