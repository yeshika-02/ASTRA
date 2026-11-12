"""The web platform's hardcoded metrics must match the authoritative record (SP-20).

astra-platform/src/lib/data/constants.ts still carries a copy of some published numbers
(SYSTEM_METRICS for /api/metrics, CHECKPOINT_REGISTRY). Each must equal the value built from
models/published_metrics.json, and numbers with no source must not be shown.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from pipeline import build_platform_artifacts as gen

ROOT = Path(__file__).resolve().parent.parent
CONSTANTS = (ROOT / "astra-platform/src/lib/data/constants.ts").read_text(encoding="utf-8")


def _block(start: str) -> str:
    """Text of the {...} or [...] literal that follows ``start``."""
    i = CONSTANTS.index(start) + len(start)
    opening = CONSTANTS[i - 1]
    closing = {"{": "}", "[": "]"}[opening]
    depth, j = 1, i
    while depth:
        depth += {opening: 1, closing: -1}.get(CONSTANTS[j], 0)
        j += 1
    return CONSTANTS[i:j - 1]


def _number(block: str, key: str) -> float:
    return float(re.search(rf"\b{key}: ([\d.]+)", block).group(1))


def _pair(block: str, key: str) -> list[float]:
    return [float(x) for x in re.search(rf"\b{key}: \[([\d.]+), ([\d.]+)\]", block).groups()]


class SystemMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = gen.load_record()
        outputs = gen.build(cls.record)
        cls.shared = outputs["benchmark.json"]["models"]["shared"]
        cls.dataset = outputs["benchmark.json"]["dataset"]
        cls.calibration = outputs["calibration.json"]
        cls.performance = _block("performance: {")
        cls.subgroup = _block("subgroup: {")

    def test_test_metrics(self) -> None:
        for key, expected in (("test_accuracy", self.shared["test_accuracy"]), ("macro_f1", self.shared["macro_f1"]),
                              ("weighted_f1", self.shared["weighted_f1"])):
            self.assertEqual(_number(self.performance, key), expected, key)
        ci = self.record["models"]["shared"]["test_bootstrap_ci95"]
        self.assertEqual(_pair(self.performance, "bootstrap_ci_accuracy"), ci["accuracy"])
        self.assertEqual(_pair(self.performance, "bootstrap_ci_macro_f1"), ci["macro_f1"])
        per_class = _block("per_class_f1: {")
        for cls, f1 in self.shared["per_class_f1"].items():
            self.assertEqual(_number(per_class, cls), f1, cls)

    def test_validation_and_calibration(self) -> None:
        best = gen.best_validation(ROOT / self.record["models"]["shared"]["training_history"])
        self.assertEqual(_number(self.performance, "val_accuracy"), round(best["accuracy"], 4))
        shared_cal = self.calibration["global"]["shared"]
        self.assertEqual(_number(self.performance, "ece_before"), shared_cal["ece_raw"])
        self.assertEqual(_number(self.performance, "ece_after"), shared_cal["ece_calibrated"])
        self.assertEqual(_number(self.performance, "calibration_temperature"), self.calibration["temperatures"]["shared"])

    def test_subgroups(self) -> None:
        groups = self.record["models"]["shared"]["subgroups"]
        for name, key in (("catalog", "catalog"), ("bls", "bls")):
            block = _block(f"{key}: {{")
            self.assertEqual(_number(block, "accuracy"), groups[name]["accuracy"])
            self.assertEqual(int(_number(block, "count")), groups[name]["n"])
            self.assertEqual(_number(block, "macro_f1"), groups[name]["macro_f1"])
            self.assertEqual(_number(block, "ece"), groups[name]["ece"])

    def test_dataset_counts(self) -> None:
        dataset = _block("dataset: {")
        self.assertEqual(int(_number(dataset, "total_stars")), self.dataset["total_stars"])
        for cls, count in self.dataset["class_counts"].items():
            self.assertEqual(int(_number(_block("classes: {"), cls)), count, cls)
        periods = _block("period_sources: {")
        self.assertEqual(int(_number(periods, "catalog")), self.dataset["period_source_counts"]["catalog"])
        self.assertEqual(int(_number(periods, "BLS")), self.dataset["period_source_counts"]["BLS"])


class RegistryAndLineageTests(unittest.TestCase):
    def test_checkpoint_registry_metrics(self) -> None:
        record = gen.load_record()
        models = gen.build(record)["benchmark.json"]["models"]
        rows = {m.group(1): m.group(0) for m in re.finditer(r"\{ filename: '([^']+)'[^}]*\}", _block("CHECKPOINT_REGISTRY: CheckpointRecord[] = ["))}
        for name in ("shared", "cnn_dual"):
            row = rows[record["models"][name]["checkpoint"]]
            self.assertEqual(_number(row, "test_accuracy"), models[name]["test_accuracy"], name)
            self.assertEqual(_number(row, "macro_f1"), models[name]["macro_f1"], name)
            best = gen.best_validation(ROOT / record["models"][name]["training_history"])
            self.assertEqual(_number(row, "val_accuracy"), round(best["accuracy"], 4), name)

    def test_lineage_shows_only_sourced_counts(self) -> None:
        counts = re.findall(r"count: (\w+)", _block("count: number | null }[] = ["))
        self.assertEqual([c for c in counts if c != "null"], ["944"])
        for unsourced in gen.load_record()["unsourced"][0]["values"]:
            self.assertNotIn(f"count: {unsourced}", CONSTANTS)

    def test_unsourced_tables_are_gone(self) -> None:
        self.assertNotIn("SELECTIVE_PREDICTION_DATA", CONSTANTS)
        self.assertNotIn("PER_CLASS_ECE", CONSTANTS)


class PageLiteralTests(unittest.TestCase):
    """Metric values written directly into pages must equal their sourced values."""

    def test_page_literals_match_the_record(self) -> None:
        record = gen.load_record()
        outputs = gen.build(record)
        temperature = outputs["calibration.json"]["temperatures"]["shared"]
        shared_cal = outputs["calibration.json"]["global"]["shared"]
        best = {name: round(gen.best_validation(ROOT / record["models"][name]["training_history"])["accuracy"], 4)
                for name in ("shared", "cnn_dual")}
        expected = {
            "src/app/mission-replay/page.tsx": [f"T={temperature:.4f}", f"from {shared_cal['ece_raw']:.4f} to {shared_cal['ece_calibrated']:.4f}"],
            "src/app/target/[id]/page.tsx": [f"T={temperature}"],
        }
        for path, snippets in expected.items():
            text = (ROOT / "astra-platform" / path).read_text(encoding="utf-8")
            for snippet in snippets:
                self.assertIn(snippet, text, f"{path}: expected {snippet!r}")
        # Validation-accuracy literals in the model and home pages must be the training-history values.
        for path in ("src/app/model/page.tsx", "src/app/page.tsx"):
            source = (ROOT / "astra-platform" / path).read_text(encoding="utf-8")
            literals = re.findall(r"(?<![\d.])0\.8\d{3}(?!\d|rem|em|px)", source)  # skip CSS sizes like 0.8125rem
            self.assertEqual([v for v in literals if float(v) not in best.values()], [], path)
        # PR #6 replaces one literal with a documented constant; it must equal the unrounded history value.
        match = re.search(r"SHARED_BEST_VAL_ACCURACY = ([\d.]+)", CONSTANTS)
        if match:
            exact = gen.best_validation(ROOT / record["models"]["shared"]["training_history"])["accuracy"]
            self.assertEqual(float(match.group(1)), exact)


if __name__ == "__main__":
    unittest.main()
