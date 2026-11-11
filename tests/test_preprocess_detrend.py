"""Characterisation of preprocessing v1 detrending (SP-23, audit S4).

These tests document what v1 does, so the published arrays stay explainable and any future
change (preprocessing v2, SP-26) is a visible decision. They are not endorsements: S4
records that a fixed-point window removes slow variability by an amount that depends on
the cadence, which is what the numbers below show.
"""

from __future__ import annotations

import json
import statistics
import unittest
from pathlib import Path

import numpy as np

from pipeline import preprocess as pp

ROOT = Path(__file__).resolve().parent.parent


def retained_fraction(period: float, cadence: float, days: float = 27.0, amplitude: float = 0.05) -> float:
    """Share of a noise-free sinusoid's spread that survives v1 detrending."""
    time = np.arange(0, days, cadence / (24 * 60))
    signal = amplitude * np.sin(2 * np.pi * time / period)
    return float(np.std(pp.detrend(1.0 + signal)) / np.std(signal))


class WindowTests(unittest.TestCase):
    def test_window_is_points_not_time(self) -> None:
        self.assertEqual((pp.SAVGOL_WINDOW, pp.SAVGOL_POLY), (301, 2))
        self.assertAlmostEqual(pp.detrend_window_days(2.0), 0.418, places=3)    # about 10 hours
        self.assertAlmostEqual(pp.detrend_window_days(10.0), 2.090, places=3)
        self.assertAlmostEqual(pp.detrend_window_days(30.0), 6.271, places=3)

    def test_short_light_curves_shrink_the_window(self) -> None:
        self.assertEqual(pp.savgol_window(10_000), 301)
        self.assertEqual(pp.savgol_window(100), 99)    # largest odd below the length
        self.assertEqual(pp.savgol_window(302), 301)
        self.assertEqual(pp.savgol_window(10_000, window=300), 299)  # forced odd
        self.assertEqual(pp.savgol_window(4), 5)       # floor of 5 points...
        with self.assertRaises(ValueError):            # ...which the filter then rejects
            pp.detrend(np.ones(4))

    def test_cadence_is_the_median_interval_in_minutes(self) -> None:
        time = np.arange(0, 1, 2 / (24 * 60))
        self.assertEqual(pp.cadence_minutes(time), 2.0)
        with_gap = np.concatenate([time, time[-1] + 1 + np.arange(0, 1, 2 / (24 * 60))])
        self.assertEqual(pp.cadence_minutes(with_gap), 2.0)  # a data gap does not change it
        self.assertEqual(pp.cadence_minutes(np.arange(0, 1, 30 / (24 * 60))), 30.0)


class DetrendBehaviourTests(unittest.TestCase):
    def test_polynomial_trends_up_to_order_two_are_removed(self) -> None:
        time = np.linspace(0, 27, 2000)
        trend = 1.0 + 0.01 * time - 0.0004 * time ** 2
        np.testing.assert_allclose(pp.detrend(trend), 0.0, atol=1e-10)

    def test_slow_signals_are_removed_and_how_much_depends_on_cadence(self) -> None:
        # Retained share of a sinusoid's spread (27-day baseline). The median Cepheid period is 6.2 d.
        expected = {  # (period days, cadence minutes): (lower, upper)
            (0.5, 2): (0.05, 0.30), (2.0, 2): (0.0, 0.01), (6.2, 2): (0.0, 0.01),
            (0.5, 10): (0.90, 1.20), (2.0, 10): (0.20, 0.45), (6.2, 10): (0.0, 0.02),
            (0.5, 30): (0.90, 1.10), (2.0, 30): (0.80, 0.95), (6.2, 30): (0.25, 0.45), (15.0, 30): (0.0, 0.05),
        }
        for (period, cadence), (low, high) in expected.items():
            with self.subTest(period=period, cadence=cadence):
                self.assertTrue(low <= retained_fraction(period, cadence) <= high)

    def test_the_same_cepheid_looks_different_at_different_cadences(self) -> None:
        fast, slow = retained_fraction(6.2, 2), retained_fraction(6.2, 30)
        self.assertGreater(slow / max(fast, 1e-12), 100)


class ShippedDataEvidenceTests(unittest.TestCase):
    def test_cepheid_amplitudes_are_smaller_than_rr_lyrae_amplitudes(self) -> None:
        # Classical Cepheids are not physically 20x quieter than RR Lyrae; the detrend makes them look so.
        amplitudes: dict[str, list[float]] = {}
        for path in (ROOT / "astra-platform/data/processed").glob("TIC_*/metadata.json"):
            meta = json.loads(path.read_text(encoding="utf-8"))
            amplitudes.setdefault(meta["astra_class"], []).append(meta["variability_amplitude"])
        cepheid = statistics.median(amplitudes["cepheid"])
        rr_lyrae = statistics.median(amplitudes["rr_lyrae"])
        self.assertAlmostEqual(cepheid, 0.0227, places=3)
        self.assertAlmostEqual(rr_lyrae, 0.5202, places=3)
        self.assertLess(cepheid * 20, rr_lyrae)


if __name__ == "__main__":
    unittest.main()
