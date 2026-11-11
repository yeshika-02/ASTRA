"""Characterisation of the preprocessing v1 period search (SP-24, audit S5).

v1 runs Box Least Squares with a single 0.05-day duration on a linear grid of 5000 periods
from 0.1 to 50 days. These tests document where that works (box-shaped eclipses), where
it does not (slow sinusoids, short periods on a coarse grid), why bls_power is not a
usable feature, and the edge pile-up visible in the shipped data.
"""

from __future__ import annotations

import json
import statistics
import unittest
from pathlib import Path

import numpy as np

from pipeline import preprocess as pp

ROOT = Path(__file__).resolve().parent.parent
TIME = np.arange(0, 27, 30 / (24 * 60))  # one TESS sector at 30-min cadence


def box_eclipses(period: float, depth: float = 0.01, seed: int = 0) -> np.ndarray:
    noise = np.random.default_rng(seed).normal(0, 0.001, TIME.size)
    return 1.0 - depth * (((TIME - 0.2) % period) < 0.1) + noise


def sinusoid(period: float, amplitude: float = 0.02, seed: int = 0) -> np.ndarray:
    noise = np.random.default_rng(seed).normal(0, 0.001, TIME.size)
    return 1.0 + amplitude * np.sin(2 * np.pi * TIME / period) + noise


def search(flux: np.ndarray) -> tuple[float | None, float | None]:
    return pp.bls_search(TIME, pp.detrend(flux))


class GridTests(unittest.TestCase):
    def test_linear_grid_of_5000_periods(self) -> None:
        grid = pp.bls_period_grid()
        self.assertEqual((grid[0], grid[-1], grid.size), (0.1, 50.0, 5000))
        self.assertTrue(np.allclose(np.diff(grid), 49.9 / 4999))
        self.assertEqual(pp.BLS_DURATION, 0.05)

    def test_the_grid_is_coarse_for_short_periods(self) -> None:
        step = pp.bls_period_grid()[1] - pp.bls_period_grid()[0]
        self.assertAlmostEqual(step, 0.00998, places=5)
        self.assertGreater(step / 0.1, 0.09)     # ~10% of the period at 0.1 d
        self.assertLess(step / 10.0, 0.001)      # ~0.1% at 10 d

    def test_too_few_points_skip_the_search(self) -> None:
        self.assertEqual(pp.bls_search(TIME[:99], np.ones(99)), (None, None))
        self.assertIsNotNone(pp.bls_search(TIME[:100], box_eclipses(2.5)[:100])[0])


class SearchBehaviourTests(unittest.TestCase):
    def test_box_eclipses_are_recovered_within_one_grid_step(self) -> None:
        step = 49.9 / 4999
        for period in (1.3, 2.5, 7.0):
            with self.subTest(period=period):
                found, _ = search(box_eclipses(period))
                self.assertLessEqual(abs(found - period), step)

    def test_fast_sinusoids_are_found_but_a_slow_one_is_not(self) -> None:
        for period in (0.3, 1.0):
            with self.subTest(period=period):
                self.assertLess(abs(search(sinusoid(period))[0] - period), 0.01)
        # A 5-day pulsation at 30-min cadence: the detrend weakens it and BLS returns ~27 d.
        found, _ = search(sinusoid(5.0))
        self.assertGreater(abs(found - 5.0), 10)

    def test_power_scales_with_the_square_of_the_flux_scale(self) -> None:
        detrended = pp.detrend(box_eclipses(2.5))
        _, power = pp.bls_search(TIME, detrended)
        _, scaled = pp.bls_search(TIME, detrended * 1000)
        self.assertAlmostEqual(scaled / power, 1e6, delta=1.0)  # not comparable across stars


class ShippedDataEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.periods: dict[str, list[float]] = {}
        cls.powers: list[float] = []
        for path in (ROOT / "astra-platform/data/processed").glob("TIC_*/metadata.json"):
            meta = json.loads(path.read_text(encoding="utf-8"))
            if meta["period_source"] == "BLS":
                cls.periods.setdefault(meta["astra_class"], []).append(meta["selected_period"])
            if meta.get("bls_power") is not None:
                cls.powers.append(meta["bls_power"])

    def test_only_solar_like_and_stable_stars_use_bls_periods(self) -> None:
        self.assertEqual({cls: len(v) for cls, v in self.periods.items()}, {"solar_like": 142, "stable": 205})

    def test_bls_periods_pile_up_at_the_grid_edges(self) -> None:
        def edge_share(values: list[float]) -> float:
            return sum(p < 0.2 or p > 40 for p in values) / len(values)

        self.assertAlmostEqual(edge_share(self.periods["solar_like"]), 0.57, places=2)
        self.assertAlmostEqual(edge_share(self.periods["stable"]), 0.28, places=2)
        # Median Solar-like "period" is longer than one 27-day sector, so the fold covers less than a cycle.
        self.assertGreater(statistics.median(self.periods["solar_like"]), 27)

    def test_shipped_bls_power_spans_tens_of_orders_of_magnitude(self) -> None:
        self.assertGreater(max(self.powers), 1e32)
        self.assertLess(min(self.powers), 1e-5)


if __name__ == "__main__":
    unittest.main()
