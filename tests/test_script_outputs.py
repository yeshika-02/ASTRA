"""Scripts write their reports under the configured output dir, even in a fresh clone.

Before astra.config, report writers targeted the original author's local folders and
only worked because those folders already existed. They must now create the output
directory themselves.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import torch  # noqa: F401  (training modules import torch)
except ImportError:  # pragma: no cover - depends on environment
    torch = None


@unittest.skipIf(torch is None, "PyTorch not installed")
class ScriptOutputTests(unittest.TestCase):
    def test_every_script_output_dir_comes_from_config(self) -> None:
        import importlib

        from astra.config import get_paths

        expected = get_paths().output_dir
        for module in [
            "training.calibration",
            "training.cross_validate",
            "training.export_model",
            "training.export_explainability_model",
            "training.inference_consistency",
            "training.stress_test",
            "training.uncertainty",
            "pipeline.run_phase6a_expansion",
            "pipeline.stable_screen",
            "pipeline.variability_crosscheck",
        ]:
            with self.subTest(module=module):
                self.assertEqual(importlib.import_module(module).ARTIFACT_DIR, expected)

    def test_confusion_matrix_is_written_into_a_missing_output_dir(self) -> None:
        import training.cross_validate as cv

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fresh" / "outputs"  # does not exist yet
            with patch.object(cv, "ARTIFACT_DIR", out):
                cv.save_confusion_matrix([0, 1, 2, 3, 4, 0], [0, 1, 2, 3, 4, 1], seed=7, fold=2)
            written = list(out.glob("*.png"))
            self.assertEqual(len(written), 1)
            self.assertIn("7", written[0].name)


if __name__ == "__main__":
    unittest.main()
