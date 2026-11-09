"""training/export_model.py: --checkpoint / --out-dir, and a full export of an untrained model.

The script used to read only models/saved/best_star_transformer_shared.pt (not shipped)
and crashed at torch.onnx.export without onnxscript, which torch's default ONNX
exporter requires.
"""

from __future__ import annotations

import gc
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

try:
    import torch
except ImportError:  # pragma: no cover - depends on environment
    torch = None


def _untrained_checkpoint(path: Path) -> Path:
    from training.models.hybrid_transformer import HybridTransformer

    torch.manual_seed(0)
    model = HybridTransformer(variant="shared", num_classes=5)
    torch.save({"variant": "shared", "num_classes": 5, "use_folded": True,
                "model_state_dict": model.state_dict()}, path)
    return path


@unittest.skipIf(torch is None, "PyTorch not installed")
class ExportCliTests(unittest.TestCase):
    def test_flags_default_to_the_configured_checkpoint(self) -> None:
        from training.export_model import build_arg_parser

        args = build_arg_parser().parse_args([])
        self.assertEqual((args.checkpoint, args.out_dir), (None, None))

    def test_missing_checkpoint_exits_with_an_error(self) -> None:
        from training.export_model import main

        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit) as raised:
                main(["--checkpoint", str(Path(tmp) / "missing.pt"), "--out-dir", tmp])
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("Checkpoint not found", out.getvalue())

    @unittest.skipUnless(importlib.util.find_spec("onnxscript") and importlib.util.find_spec("onnxruntime"),
                         "onnxscript / onnxruntime not installed")
    def test_exports_torchscript_and_onnx_into_out_dir(self) -> None:
        from training.export_model import main

        # ONNX Runtime memory-maps the .onnx.data weights; on Windows the file can stay
        # locked until the session is garbage-collected, so cleanup must not fail the test.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tmp_path = Path(tmp)
            checkpoint = _untrained_checkpoint(tmp_path / "untrained.pt")
            out = tmp_path / "export"
            with redirect_stdout(io.StringIO()) as log:
                main(["--checkpoint", str(checkpoint), "--out-dir", str(out)])

            for name in ("best_star_transformer_shared.torchscript", "best_star_transformer_shared.onnx",
                         "deployment_report.md"):
                self.assertTrue((out / name).is_file(), name)
            self.assertIn("PyTorch vs ONNX", log.getvalue())
            report = (out / "deployment_report.md").read_text(encoding="utf-8")
            self.assertNotIn("file://", report)
            self.assertNotIn(tmp, report)
            gc.collect()


if __name__ == "__main__":
    unittest.main()
