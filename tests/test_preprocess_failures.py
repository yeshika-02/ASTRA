"""How process_star() fails, and its cache (SP-25).

Each failure must name its stage, explain itself, and leave no partial star directory
behind; a star that was already processed is loaded from disk without downloading.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import fake_lightkurve as fl
import numpy as np

from pipeline import preprocess


def curve(n: int, flux: float | np.ndarray = 1000.0, cadence: float = 30.0) -> fl.FakeLightCurve:
    time = fl.sector(3000.0, n * cadence / (24 * 60), cadence)[:n]
    values = np.full(time.size, flux, dtype=float) if np.isscalar(flux) else np.asarray(flux, dtype=float)
    values = values + np.random.default_rng(0).normal(0, 1.0, time.size)
    return fl.FakeLightCurve(time, values, {"SECTOR": 9, "TARGETID": 7})


def process(curves: list[fl.FakeLightCurve], output_dir: Path, **kwargs) -> dict:
    kwargs = {"astra_class": "rr_lyrae", "source_catalogs": ["synthetic"], "ra": 1.0, "dec": 2.0, **kwargs}
    with fl.serving(curves):
        return preprocess.process_star(8000001, output_dir=output_dir, force=True, **kwargs)


class FailureStageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def assert_failed(self, result: dict, stage: str, message: str) -> None:
        self.assertEqual(result.get("stage"), stage, result)
        self.assertIn(message, result["error"])
        self.assertFalse((self.out / "TIC_8000001").exists(), "partial output left behind")

    def test_no_tess_data(self) -> None:
        with self.assertLogs("preprocess", level="WARNING"):
            self.assert_failed(process([], self.out), "download", "No TESS light-curve data found")

    def test_nothing_usable_after_quality_filtering(self) -> None:
        unusable = curve(200, flux=np.where(np.arange(200) % 2, np.nan, -5.0))  # NaN or non-positive only
        with self.assertLogs("preprocess", level="WARNING"):
            self.assert_failed(process([unusable], self.out), "quality", "No usable data after quality filtering")

    def test_too_few_points_after_stitching(self) -> None:
        with self.assertLogs("preprocess", level="WARNING"):
            self.assert_failed(process([curve(40)], self.out), "stitch", "Only 40 points after stitching")

    def test_short_curve_without_catalog_period_has_no_period(self) -> None:
        # 60 points: enough to stitch (>= 50) but too few for BLS (< 100).
        with self.assertLogs("preprocess", level="WARNING"):
            self.assert_failed(process([curve(60)], self.out), "period",
                               "required for folded periodic classes")


class ShortCurveTests(unittest.TestCase):
    def test_short_curve_with_catalog_period_is_processed_without_bls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            meta = process([curve(60, flux=1000 + 50 * np.sin(np.arange(60) / 3.0))], Path(tmp), catalog_period=0.6)
            self.assertNotIn("error", meta)
            self.assertEqual((meta["bls_period"], meta["period_source"], meta["selected_period"]), (None, "catalog", 0.6))
            self.assertEqual(np.load(Path(tmp) / "TIC_8000001" / "flux_1000.npy").shape, (1000,))


class CacheTests(unittest.TestCase):
    def test_processed_stars_are_loaded_without_downloading(self) -> None:
        tic, astra_class, make, _ = fl.STARS["eclipsing_binary"]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with fl.serving(make()):
                first = preprocess.process_star(tic, astra_class, output_dir=out, force=True,
                                                source_catalogs=["synthetic"], ra=1.0, dec=2.0)

            def no_download(*args, **kwargs):
                raise AssertionError("downloaded although the star was cached")

            with fl.serving([]):
                sys.modules["lightkurve"].search_lightcurve = no_download
                cached = preprocess.process_star(tic, astra_class, output_dir=out, source_catalogs=["synthetic"],
                                                 ra=1.0, dec=2.0)
        self.assertEqual(cached["processing_timestamp"], first["processing_timestamp"])
        self.assertEqual(cached["selected_period"], first["selected_period"])


if __name__ == "__main__":
    unittest.main()
