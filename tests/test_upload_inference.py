"""Input handling of training/upload_inference.py (security hardening, Phase 0)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from training.upload_inference import (
    MAX_FLUX_POINTS,
    parse_flux_json,
    parse_flux_text,
    validate_period,
)

SCRIPT = Path(__file__).resolve().parent.parent / "training" / "upload_inference.py"


class ParseFluxTests(unittest.TestCase):
    def test_parses_comma_and_space_separated_values(self) -> None:
        self.assertEqual(parse_flux_text("1, 2.5,3"), [1.0, 2.5, 3.0])
        self.assertEqual(parse_flux_text("1 2\n3"), [1.0, 2.0, 3.0])

    def test_never_reads_a_file_path(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("1,2,3")
            path = f.name
        try:
            with self.assertRaises(ValueError):
                parse_flux_text(path)
        finally:
            Path(path).unlink()

    def test_parses_json_array(self) -> None:
        self.assertEqual(parse_flux_json("[1, 2.5, 3]"), [1.0, 2.5, 3.0])

    def test_rejects_non_numeric_json(self) -> None:
        for bad in ['"1,2,3"', '{"a": 1}', '[1, "2"]', "[1, true]", "[1, null]"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_flux_json(bad)

    def test_rejects_oversized_input(self) -> None:
        with self.assertRaises(ValueError):
            parse_flux_json(json.dumps([1.0] * (MAX_FLUX_POINTS + 1)))

    def test_period_validation(self) -> None:
        self.assertEqual(validate_period(0.5), 0.5)
        for bad in [0.0, -1.0, float("nan"), float("inf")]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_period(bad)


class CommandLineTests(unittest.TestCase):
    def test_requires_exactly_one_flux_source(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--period", "1"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_missing_model_reports_json_error_without_paths(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--flux-stdin", "--period", "1", "--onnx", "does/not/exist.onnx"],
            input="[1, 2, 3]",
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertIn("error", payload)
        self.assertNotIn("exist.onnx", payload["error"])


if __name__ == "__main__":
    unittest.main()
