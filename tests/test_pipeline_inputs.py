"""Bad inputs to the pipeline give clear errors (SP-25, audit E4).

Entry-point scripts reject invalid arguments at once (exit 2 with a message naming the
argument); process_star() rejects invalid arguments before any download, with stage
"input"; the array helpers raise ValueError with a readable message.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fake_lightkurve as fl
import numpy as np

from pipeline import cli_validation as cv
from pipeline import preprocess

ROOT = Path(__file__).resolve().parent.parent


def run_script(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, f"pipeline/{script}", *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=300)


class ValidatorTests(unittest.TestCase):
    def test_positive_and_non_negative_ints(self) -> None:
        self.assertEqual(cv.positive_int("3"), 3)
        self.assertEqual(cv.non_negative_int("0"), 0)
        for bad, func in (("0", cv.positive_int), ("-2", cv.positive_int), ("x", cv.positive_int),
                          ("-1", cv.non_negative_int), ("1.5", cv.non_negative_int)):
            with self.subTest(value=bad), self.assertRaises(argparse.ArgumentTypeError):
                func(bad)

    def test_class_and_paths(self) -> None:
        self.assertEqual(cv.astra_class("cepheid"), "cepheid")
        with self.assertRaisesRegex(argparse.ArgumentTypeError, "unknown class 'comet'; choose from rr_lyrae"):
            cv.astra_class("comet")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(cv.existing_dir(tmp), Path(tmp))
            with self.assertRaisesRegex(argparse.ArgumentTypeError, "directory not found"):
                cv.existing_dir(str(Path(tmp) / "missing"))
            with self.assertRaisesRegex(argparse.ArgumentTypeError, "file not found"):
                cv.existing_file(str(Path(tmp) / "missing.csv"))


class ScriptArgumentTests(unittest.TestCase):
    CASES = [
        ("preprocess.py", ["0", "cepheid"], "must be at least 1, got 0"),
        ("preprocess.py", ["123", "comet"], "unknown class 'comet'"),
        ("preprocess.py", ["123", "cepheid", "--max-sectors", "0"], "must be at least 1, got 0"),
        ("batch_process.py", ["--workers", "0"], "must be at least 1, got 0"),
        ("batch_process.py", ["--max-stars", "ten"], "must be a whole number"),
        ("phase6_batch_process.py", ["--checkpoint-interval", "-5"], "must be at least 1, got -5"),
        ("dataset_builder.py", ["--gaia-csv", "no/such/gaia.csv"], "file not found"),
        ("freeze_phase6_splits.py", ["--data-root", "no/such/dir"], "directory not found"),
        ("dataset_audit.py", ["--stage", "-1"], "must be 0 or more, got -1"),
        ("dataset_audit.py", ["--data-root", "no/such/dir"], "directory not found"),
    ]

    def test_bad_arguments_stop_with_a_clear_message(self) -> None:
        for script, args, message in self.CASES:
            with self.subTest(script=script, args=args):
                result = run_script(script, *args)
                self.assertEqual(result.returncode, 2, result.stderr[-500:])
                self.assertIn(message, result.stderr)


class ProcessStarInputTests(unittest.TestCase):
    def test_invalid_arguments_fail_before_any_download(self) -> None:
        cases = [
            (dict(tic_id=1, astra_class="comet"), "unknown class 'comet'"),
            (dict(tic_id=0, astra_class="cepheid"), "tic_id must be a positive integer"),
            (dict(tic_id=True, astra_class="cepheid"), "tic_id must be a positive integer"),
            (dict(tic_id=5, astra_class="cepheid", max_sectors=0), "max_sectors must be at least 1"),
            (dict(tic_id=5, astra_class="cepheid", ra=400.0), "ra must be in [0, 360)"),
            (dict(tic_id=5, astra_class="cepheid", dec=-95.0), "dec must be in [-90, 90]"),
            (dict(tic_id=5, astra_class="cepheid", ra=float("nan")), "ra must be in [0, 360)"),
        ]
        with tempfile.TemporaryDirectory() as tmp, self.assertLogs("preprocess", level="ERROR"):
            for kwargs, message in cases:
                with self.subTest(**{k: str(v) for k, v in kwargs.items()}):
                    result = preprocess.process_star(output_dir=Path(tmp), **kwargs)
                    self.assertEqual(result["stage"], "input")
                    self.assertIn(message, result["error"])
            self.assertEqual(list(Path(tmp).iterdir()), [])  # nothing was created

    def test_invalid_catalog_period_is_reported_and_bls_is_used(self) -> None:
        tic, astra_class, make, _ = fl.STARS["eclipsing_binary"]
        with tempfile.TemporaryDirectory() as tmp, fl.serving(make()), \
                self.assertLogs("preprocess", level="WARNING") as logs:
            meta = preprocess.process_star(tic, astra_class, output_dir=Path(tmp), force=True, catalog_period=-3.0,
                                           source_catalogs=["synthetic"], ra=10.0, dec=-20.0)
        self.assertEqual(meta["period_source"], "BLS")
        self.assertEqual(meta["selected_period"], meta["bls_period"])
        self.assertTrue(any("Ignoring invalid catalog period -3.0" in line for line in logs.output))


class HelperInputTests(unittest.TestCase):
    def test_resample_needs_two_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 2 flux values"):
            preprocess._resample_normalized(np.array([1.0]), 10)
        with self.assertRaisesRegex(ValueError, "output length"):
            preprocess._resample_normalized(np.array([1.0, 2.0]), 0)

    def test_phase_binning_needs_a_positive_period_and_matching_arrays(self) -> None:
        time, flux = np.linspace(0, 10, 100), np.ones(100)
        for period in (0.0, -1.0, float("nan")):
            with self.subTest(period=period), self.assertRaisesRegex(ValueError, "period must be a positive"):
                preprocess._phase_bin_normalized(time, flux, period, 50)
        with self.assertRaisesRegex(ValueError, "same length"):
            preprocess._phase_bin_normalized(time, flux[:50], 2.0, 50)


if __name__ == "__main__":
    unittest.main()
