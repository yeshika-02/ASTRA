"""training/baselines.py (SP-22): reproduces EXP-0001 exactly and documents the light-curve baseline."""

from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

from training import baselines

ROOT = Path(__file__).resolve().parent.parent

# Output of artifacts/experiments/EXP-0001-metadata-baseline.py (accuracy, macro F1), as recorded in
# artifacts/experiments/EXP-0001-metadata-baseline.md (rounded there to 3 decimals).
EXP_0001 = {
    ("shortcut_no_source", "LogReg"): (0.4366, 0.3100), ("shortcut_no_source", "RandomForest"): (0.4366, 0.3528),
    ("shortcut", "LogReg"): (0.6197, 0.5578), ("shortcut", "RandomForest"): (0.6268, 0.5722),
    ("physical", "LogReg"): (0.8169, 0.7920), ("physical", "RandomForest"): (0.8662, 0.8537),
    ("all", "LogReg"): (0.8803, 0.8605), ("all", "RandomForest"): (0.9085, 0.8972),
}


class Exp0001ReproductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stars = baselines.load_stars(baselines.SHIPPED_PROCESSED, baselines.load_split_ids(baselines.SHIPPED_SPLIT_IDS))
        cls.all_results = baselines.run_all(cls.stars, n_bootstrap=1000)  # the settings the record uses
        cls.results = [r for r in cls.all_results if r["feature_set"] != "lightcurve"]

    def test_the_authoritative_record_holds_these_numbers(self) -> None:
        record = json.loads((ROOT / "models/published_metrics.json").read_text(encoding="utf-8"))["baselines"]
        recorded = {(r["feature_set"], r["model"]): r for r in record["results"]}
        self.assertEqual(set(recorded), {(r["feature_set"], r["model"]) for r in self.all_results})
        for result in self.all_results:
            entry = recorded[(result["feature_set"], result["model"])]
            with self.subTest(feature_set=result["feature_set"], model=result["model"]):
                if result["feature_set"] == "lightcurve":
                    # Light-curve statistics can differ in the last bits across platforms, which moved one test
                    # star for the logistic regression on Linux CI; compare whole stars, allowing one.
                    n = result["n_test"]
                    self.assertLessEqual(abs(round(result["accuracy"] * n) - round(entry["accuracy"] * n)), 1)
                else:
                    self.assertLessEqual(abs(result["accuracy"] - entry["accuracy"]), 5e-5)
                    self.assertEqual(round(result["macro_f1"], 4), entry["macro_f1"])
                    self.assertEqual([round(x, 4) for x in result["bootstrap"]["ci"]["accuracy"]], entry["accuracy_ci95"])
                    self.assertEqual([round(x, 4) for x in result["bootstrap"]["ci"]["macro_f1"]], entry["macro_f1_ci95"])

    def test_split_sizes(self) -> None:
        self.assertEqual({s: sum(star.split == s for star in self.stars) for s in ("train", "val", "test")},
                         {"train": 661, "val": 141, "test": 142})

    def test_every_exp_0001_number_is_reproduced_exactly(self) -> None:
        for result in self.results:
            expected = EXP_0001[(result["feature_set"], result["model"])]
            with self.subTest(feature_set=result["feature_set"], model=result["model"]):
                self.assertEqual((round(result["accuracy"], 4), round(result["macro_f1"], 4)), expected)

    def test_features_equal_the_sqlite_table_exp_0001_read(self) -> None:
        connection = sqlite3.connect(ROOT / "astra-platform/data/astra.sqlite")
        rows = connection.execute("select tic_id, split, astra_class, cadence_type, n_sectors, period_source, period, "
                                  "variability_amplitude, snr_estimate from stars").fetchall()
        connection.close()
        self.assertEqual([f"TIC_{r[0]}" for r in rows], [s.tic_id for s in self.stars])  # same row order
        for row, star in zip(rows, self.stars):
            self.assertEqual(row[1:], (star.split, star.astra_class, star.cadence_type, star.n_sectors,
                                       star.period_source, star.period, star.amplitude, star.snr))

    def test_physical_features_use_exp_0001_formulas(self) -> None:
        star = baselines.Star("TIC_1", "train", "stable", "short", 3, "BLS", 2.0, 0.0, 0.0, Path("."))
        self.assertEqual(baselines.metadata_features(star, "shortcut"), [1.0, 3, 1.0])
        np.testing.assert_allclose(baselines.metadata_features(star, "physical"), [np.log10(2.0), -6.0, -3.0])
        with self.assertRaises(ValueError):
            baselines.metadata_features(star, "lightcurve")


class LightcurveFeatureTests(unittest.TestCase):
    def test_twelve_finite_features_even_for_flat_input(self) -> None:
        flat = baselines.lightcurve_features(np.zeros(1000), np.zeros(1000))
        self.assertEqual(len(flat), len(baselines.LIGHTCURVE_FEATURES))
        self.assertTrue(np.all(np.isfinite(flat)))
        wave = np.sin(np.linspace(0, 20 * np.pi, 1000))
        features = dict(zip(baselines.LIGHTCURVE_FEATURES, baselines.lightcurve_features(wave, wave)))
        self.assertGreater(features["raw_acf_1"], 0.9)          # smooth signal
        self.assertAlmostEqual(features["raw_skew"], 0.0, places=6)

    def test_lightcurve_baseline_result(self) -> None:
        stars = baselines.load_stars(baselines.SHIPPED_PROCESSED, baselines.load_split_ids(baselines.SHIPPED_SPLIT_IDS))
        result = baselines.run_baseline(stars, "lightcurve", "RandomForest", n_bootstrap=50)
        # 113/142 correct; one star of tolerance for last-bit platform differences in the statistics.
        self.assertLessEqual(abs(result["accuracy"] - 113 / 142), 1 / 142 + 1e-9)
        self.assertAlmostEqual(result["macro_f1"], 0.7867, delta=0.01)


class CliTests(unittest.TestCase):
    def test_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()) as log:
            self.assertEqual(baselines.main(["--out-dir", tmp, "--bootstrap", "20"]), 0)
            record = json.loads((Path(tmp) / "baselines.json").read_text(encoding="utf-8"))
            self.assertEqual(len(record["results"]), len(baselines.FEATURE_SETS) * len(baselines.MODEL_NAMES))
            self.assertIn("commit", record["provenance"]["git"])
            self.assertIn("| physical | RandomForest | 86.62%", (Path(tmp) / "baselines.md").read_text(encoding="utf-8"))
        self.assertIn("lightcurve", log.getvalue())

    def test_missing_split_ids_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(FileNotFoundError, "No train id file"):
            baselines.load_split_ids(Path(tmp))


if __name__ == "__main__":
    unittest.main()
