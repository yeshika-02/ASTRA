"""A minimal stand-in for the parts of lightkurve that pipeline/preprocess.py uses.

It lets process_star() run end to end on synthetic light curves, offline and fast:
search_lightcurve() -> search result -> download_all() -> light curves with time/flux,
boolean masking, normalize(), and LightCurveCollection.stitch().
"""

from __future__ import annotations

import contextlib
import sys
import types
from dataclasses import dataclass

import numpy as np


@dataclass
class _Quantity:
    value: np.ndarray

    def __len__(self) -> int:
        return len(self.value)


class FakeLightCurve:
    def __init__(self, time: np.ndarray, flux: np.ndarray, meta: dict | None = None) -> None:
        self.time = _Quantity(np.asarray(time, dtype=np.float64))
        self.flux = _Quantity(np.asarray(flux, dtype=np.float64))
        self.flux_err = None
        self.meta = meta or {}
        self.colnames: list[str] = []

    def __len__(self) -> int:
        return len(self.flux.value)

    def __getitem__(self, mask: np.ndarray) -> FakeLightCurve:
        return FakeLightCurve(self.time.value[mask], self.flux.value[mask], self.meta)

    def normalize(self) -> FakeLightCurve:
        return FakeLightCurve(self.time.value, self.flux.value / np.nanmedian(self.flux.value), self.meta)


class FakeCollection(list):
    def stitch(self, corrector_func=None) -> FakeLightCurve:
        parts = [corrector_func(lc) if corrector_func else lc for lc in self]
        return FakeLightCurve(np.concatenate([p.time.value for p in parts]),
                              np.concatenate([p.flux.value for p in parts]))


class _Table:
    def __init__(self, n: int) -> None:
        self.colnames = ["mission", "author", "exptime"]
        self._rows = [{"mission": f"TESS Sector {i + 1}", "author": "SPOC", "exptime": 120.0} for i in range(n)]

    def __getitem__(self, key: str) -> list:
        return [row[key] for row in self._rows]

    def __iter__(self):
        return iter(self._rows)


class FakeSearch:
    def __init__(self, light_curves: list[FakeLightCurve]) -> None:
        self._light_curves = light_curves
        self.table = _Table(len(light_curves))

    def __len__(self) -> int:
        return len(self._light_curves)

    def __getitem__(self, item: slice) -> FakeSearch:
        return FakeSearch(self._light_curves[item])

    def download_all(self, quality_bitmask: str = "default") -> FakeCollection:
        return FakeCollection(self._light_curves)


def module_serving(light_curves: list[FakeLightCurve]) -> types.ModuleType:
    """A fake ``lightkurve`` module whose searches return these light curves."""
    module = types.ModuleType("lightkurve")
    module.search_lightcurve = lambda target, mission=None, author=None: FakeSearch(light_curves)
    module.LightCurveCollection = FakeCollection
    return module


@contextlib.contextmanager
def serving(light_curves: list[FakeLightCurve]):
    """Install the fake ``lightkurve`` for the duration of the block.

    Only the ``lightkurve`` entry of sys.modules is swapped: restoring the whole table
    (unittest.mock.patch.dict) would unload scipy/astropy extensions imported inside the
    block, and numpy 2 extensions cannot be loaded twice in one process.
    """
    missing = object()
    previous = sys.modules.get("lightkurve", missing)
    sys.modules["lightkurve"] = module_serving(light_curves)
    try:
        yield
    finally:
        if previous is missing:
            sys.modules.pop("lightkurve", None)
        else:
            sys.modules["lightkurve"] = previous


# ─── Synthetic stars ────────────────────────────────────────────────────────────


def sector(start: float, days: float, cadence_minutes: float) -> np.ndarray:
    step = cadence_minutes / (24 * 60)
    return start + np.arange(0, days, step)


def eclipsing_binary(seed: int = 1) -> list[FakeLightCurve]:
    """Two 27-day sectors at 30-min cadence; 2% box eclipses every 2.5 d, 0.1% noise."""
    rng = np.random.default_rng(seed)
    curves = []
    for k, start in enumerate((2000.0, 2030.0)):
        time = sector(start, 27.0, 30.0)
        flux = 1000.0 * (1.0 - 0.02 * (((time - 2000.3) % 2.5) < 0.12)) + rng.normal(0, 1.0, time.size)
        curves.append(FakeLightCurve(time, flux, {"SECTOR": k + 1, "TARGETID": 1}))
    return curves


def cepheid_like(seed: int = 2) -> list[FakeLightCurve]:
    """One 10-day sector at 2-min cadence; 5% sinusoid with a 5-day period."""
    rng = np.random.default_rng(seed)
    time = sector(2100.0, 10.0, 2.0)
    flux = 500.0 * (1.0 + 0.05 * np.sin(2 * np.pi * time / 5.0)) + rng.normal(0, 0.5, time.size)
    return [FakeLightCurve(time, flux, {"SECTOR": 3, "TARGETID": 2})]


def rr_lyrae_like(seed: int = 3) -> list[FakeLightCurve]:
    """One 20-day sector at 10-min cadence; 30% sawtooth-like pulsation with a 0.55-day period."""
    rng = np.random.default_rng(seed)
    time = sector(2200.0, 20.0, 10.0)
    phase = (time / 0.55) % 1.0
    flux = 800.0 * (1.0 + 0.3 * (phase - 0.5) * (phase < 0.85) - 0.3 * 0.35 * (phase >= 0.85))
    flux += rng.normal(0, 1.0, time.size)
    return [FakeLightCurve(time, flux, {"SECTOR": 4, "TARGETID": 3})]


STARS = {
    # name: (tic_id, astra_class, light curves, catalog_period)
    "eclipsing_binary": (9000001, "eclipsing_binary", eclipsing_binary, None),
    "cepheid_like": (9000002, "cepheid", cepheid_like, 5.0),
    "rr_lyrae_like": (9000003, "rr_lyrae", rr_lyrae_like, None),
}
