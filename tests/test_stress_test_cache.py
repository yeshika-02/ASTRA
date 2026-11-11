"""stress_test.load_raw_timeseries finds light curves in the configured lightkurve cache."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

try:
    import torch  # noqa: F401  (stress_test imports torch)
    from astropy.io import fits
except ImportError:  # pragma: no cover - depends on environment
    torch = None


def _write_tess_lc(path: Path, n: int = 200) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    time = np.linspace(1000.0, 1027.0, n)
    flux = 500.0 + 5.0 * np.sin(time)
    quality = np.zeros(n, dtype=np.int32)
    quality[:5] = 1  # flagged cadences must be dropped
    cols = fits.ColDefs([
        fits.Column(name="TIME", format="D", array=time),
        fits.Column(name="PDCSAP_FLUX", format="E", array=flux),
        fits.Column(name="QUALITY", format="J", array=quality),
    ])
    fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU.from_columns(cols)]).writeto(path)


@unittest.skipIf(torch is None, "PyTorch/astropy not installed")
class LightkurveCacheTests(unittest.TestCase):
    def test_reads_tess_files_from_the_configured_cache(self) -> None:
        import training.stress_test as st
        from astra.config import get_paths

        tic = 123456789
        with tempfile.TemporaryDirectory() as cache:
            fits_path = Path(cache) / "mastDownload" / "TESS" / "s0001" / f"tess-s0001-{tic:016d}-lc.fits"
            _write_tess_lc(fits_path)
            with patch.object(st, "PATHS", get_paths(env={"ASTRA_LIGHTKURVE_CACHE": cache})):
                time, flux = st.load_raw_timeseries(tic)
        self.assertIsNotNone(time)
        self.assertEqual(len(time), 195)  # 200 cadences minus 5 quality-flagged
        self.assertAlmostEqual(float(np.median(flux)), 1.0, places=6)  # median-normalised

    def test_returns_nothing_when_the_cache_has_no_match(self) -> None:
        import training.stress_test as st
        from astra.config import get_paths

        with tempfile.TemporaryDirectory() as cache:
            with patch.object(st, "PATHS", get_paths(env={"ASTRA_LIGHTKURVE_CACHE": cache})):
                time, flux = st.load_raw_timeseries(42)
        self.assertIsNone(time)
        self.assertIsNone(flux)


if __name__ == "__main__":
    unittest.main()
