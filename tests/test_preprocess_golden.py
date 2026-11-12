"""Preprocessing v1 must keep producing the same outputs (golden test, SP-23/24/25).

tests/fixtures/preprocess_v1_golden.{npz,json} hold the outputs of process_star() for the
three synthetic stars in tests/fake_lightkurve.py, captured from pipeline/preprocess.py
before any refactoring. Every published array was made with v1, so v1 must not drift.

Arrays are compared with a 1e-5 tolerance (normalised float32, std 1) because last-bit
floating-point results can differ across platforms; the fixture's own SHA256 values are
checked exactly.
"""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

import fake_lightkurve as fl
import numpy as np

from pipeline import preprocess

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
GOLDEN = json.loads((FIXTURES / "preprocess_v1_golden.json").read_text(encoding="utf-8"))["stars"]
ARRAYS = ("flux_1000", "flux_200", "folded_flux_1000", "folded_flux_200")


def run_star(name: str, output_dir: Path) -> tuple[dict, dict[str, np.ndarray]]:
    tic, astra_class, make, catalog_period = fl.STARS[name]
    with fl.serving(make()):
        meta = preprocess.process_star(tic, astra_class, output_dir=output_dir, force=True,
                                       catalog_period=catalog_period, source_catalogs=["synthetic"],
                                       ra=10.0, dec=-20.0)
    star = output_dir / f"TIC_{tic}"
    arrays = {arr: np.load(star / f"{arr}.npy") for arr in ARRAYS} if "error" not in meta else {}
    return meta, arrays


class GoldenFixtureTests(unittest.TestCase):
    def test_fixture_arrays_match_their_recorded_hashes(self) -> None:
        with np.load(FIXTURES / "preprocess_v1_golden.npz") as golden:
            for name, entry in GOLDEN.items():
                for arr in ARRAYS:
                    values = golden[f"{name}__{arr}"]
                    self.assertEqual(hashlib.sha256(values.tobytes()).hexdigest(), entry[f"{arr}_sha256"], f"{name} {arr}")


class PreprocessV1GoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.results = {name: run_star(name, Path(cls.tmp.name)) for name in GOLDEN}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_every_star_processes(self) -> None:
        for name, (meta, _) in self.results.items():
            self.assertNotIn("error", meta, f"{name}: {meta.get('error')}")

    def test_arrays_are_unchanged(self) -> None:
        with np.load(FIXTURES / "preprocess_v1_golden.npz") as golden:
            for name, (_, arrays) in self.results.items():
                for arr in ARRAYS:
                    with self.subTest(star=name, array=arr):
                        expected = golden[f"{name}__{arr}"]
                        self.assertEqual(arrays[arr].dtype, expected.dtype)
                        self.assertEqual(arrays[arr].shape, expected.shape)
                        np.testing.assert_allclose(arrays[arr], expected, rtol=0, atol=1e-5)

    def test_metadata_is_unchanged(self) -> None:
        for name, (meta, _) in self.results.items():
            expected = GOLDEN[name]
            with self.subTest(star=name):
                for key in ("selected_period", "period_source", "source_cadence", "cadence_type",
                            "n_points_raw", "n_points_clean", "n_sectors"):
                    self.assertEqual(meta[key], expected[key], key)
                self.assertTrue(math.isclose(meta["bls_period"], expected["bls_period"], rel_tol=1e-9))
                for key in ("bls_power", "variability_amplitude", "estimated_snr"):
                    self.assertTrue(math.isclose(meta[key], expected[key], rel_tol=1e-6), key)


if __name__ == "__main__":
    unittest.main()
