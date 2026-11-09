"""models/published_metrics.json: every published number has a source that says so (SP-18).

- Confusion matrices reproduce the headline test metrics printed in the cited reports.
- Every recorded value appears, in some printed form, in the report it cites.
- The record agrees with published_weights.json and with the shipped test split.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import numpy as np

from training.evaluate import metrics_from_confusion
from training.verify_weights import find_published

ROOT = Path(__file__).resolve().parent.parent
RECORD = json.loads((ROOT / "models" / "published_metrics.json").read_text(encoding="utf-8"))
REPORT_7A = ROOT / "docs/engineering-log/phase7_testset_results.md"
REPORT_7C = ROOT / "docs/engineering-log/ground_truth_metrics.md"


def _printed_forms(value: float) -> set[str]:
    return {f"{value:.4f}", f"{value * 100:.2f}%", f"{value * 100:.1f}%", f"{value:.3f}", f"{value}"}


def _is_printed(value: float, text: str) -> bool:
    """True if the value appears as a whole number (so 0.044 does not match inside 0.0442)."""
    return any(re.search(rf"(?<![\d.]){re.escape(form)}(?!\d)", text) for form in _printed_forms(value))


def _source_text(source: str) -> str:
    files = re.findall(r"docs/engineering-log/[\w.]+\.md", source)
    assert files, f"no report cited in {source!r}"
    return "".join((ROOT / f).read_text(encoding="utf-8") for f in files)


def _assert_printed(test: unittest.TestCase, values: list, source: str, label: str) -> None:
    text = _source_text(source)
    missing = [v for v in values if v is not None and not _is_printed(v, text)]
    test.assertEqual(missing, [], f"{label}: not found in {source}")


class ConfusionMatrixTests(unittest.TestCase):
    def test_matrices_cover_the_shipped_test_split(self) -> None:
        ids = json.loads((ROOT / RECORD["test_split"]["file"]).read_text(encoding="utf-8"))
        counts = np.zeros(len(RECORD["classes"]), dtype=int)
        for tic in ids:
            meta = json.loads((ROOT / "astra-platform/data/processed" / tic / "metadata.json").read_text(encoding="utf-8"))
            counts[meta["label"]] += 1
        for name, model in RECORD["models"].items():
            matrix = np.array(model["test_confusion_matrix"]["matrix"])
            self.assertEqual(matrix.sum(axis=1).tolist(), counts.tolist(), name)

    def test_matrices_reproduce_the_reported_metrics(self) -> None:
        # The shared transformer and CNN are checked against the 7C audit, the others against 7A.
        for name, model in RECORD["models"].items():
            report = REPORT_7C if name in ("shared", "cnn_dual") else REPORT_7A
            text = report.read_text(encoding="utf-8")
            metrics = metrics_from_confusion(np.array(model["test_confusion_matrix"]["matrix"]))
            printed = [f"{metrics['accuracy'] * 100:.2f}%", f"{metrics['macro_f1']:.4f}", f"{metrics['weighted_f1']:.4f}"]
            printed += [f"{c['f1']:.4f}" for c in metrics["per_class"].values()]
            self.assertEqual([p for p in printed if p not in text], [], f"{name} vs {report.name}")

    def test_phase7a_cnn_row_does_not_match_the_published_matrix(self) -> None:
        # Recorded conflict: 7A's CNN macro F1 (0.7654) cannot come from the published CNN matrix.
        metrics = metrics_from_confusion(np.array(RECORD["models"]["cnn_dual"]["test_confusion_matrix"]["matrix"]))
        self.assertEqual(round(metrics["macro_f1"], 4), 0.7635)
        self.assertIn("0.7654", REPORT_7A.read_text(encoding="utf-8"))

    def test_matrices_agree_with_published_weights(self) -> None:
        for name in ("shared", "cnn_dual"):
            model = RECORD["models"][name]
            weights = find_published(model["checkpoint"])["published_test"]
            self.assertEqual(model["test_confusion_matrix"]["matrix"], weights["confusion_matrix"], name)
            self.assertEqual(model["test_bootstrap_ci95"]["accuracy"], weights["accuracy_ci95"], name)


class ProvenanceTests(unittest.TestCase):
    def test_recorded_values_appear_in_their_sources(self) -> None:
        for name, model in RECORD["models"].items():
            ci = model["test_bootstrap_ci95"]
            _assert_printed(self, [v for key in ("accuracy", "macro_f1", "weighted_f1") for v in ci.get(key, [])],
                            ci["source"], f"{name} CIs")
            groups = model["subgroups"]
            _assert_printed(self, [groups[g][k] for g in ("catalog", "bls") for k in groups[g] if k != "n"],
                            groups["source"], f"{name} subgroups")
            if "calibration" in model:
                cal = model["calibration"]
                values = [cal[k] for k in ("ece_raw", "ece_calibrated", "brier_raw", "brier_calibrated")]
                values += [v for pair in cal["per_class_ece"].values() for v in pair.values()]
                _assert_printed(self, values, cal["source"], f"{name} calibration")
                unc = model["uncertainty"]
                values = [unc["error_detection_auroc"], *unc["entropy"].values()]
                values += [p[k] for p in unc["coverage_sweep"] for k in ("coverage", "accuracy")]
                _assert_printed(self, values, unc["source"], f"{name} uncertainty")

    def test_no_nll_is_claimed(self) -> None:
        # The only recorded NLL values are copies of ECE (audit copy error).
        for model in RECORD["models"].values():
            if "calibration" in model:
                self.assertIsNone(model["calibration"]["nll_raw"])
                self.assertIsNone(model["calibration"]["nll_calibrated"])

    def test_temperatures_come_from_their_files(self) -> None:
        for model in RECORD["models"].values():
            if "calibration" in model:
                self.assertTrue((ROOT / model["calibration"]["temperature_file"]).is_file())
        shared = (ROOT / RECORD["models"]["shared"]["calibration"]["temperature_file"]).read_text().strip()
        self.assertEqual(float(shared), find_published("optimal_temperature_transformer_shared.txt")["value"])

    def test_superseded_results_are_from_the_earlier_dataset(self) -> None:
        superseded = RECORD["superseded"]
        text = _source_text(superseded["source"])
        self.assertIn("269 stars", text)
        scalars = [v for v in superseded["values"].values() if isinstance(v, float)]
        _assert_printed(self, scalars, superseded["source"], "superseded")


if __name__ == "__main__":
    unittest.main()
