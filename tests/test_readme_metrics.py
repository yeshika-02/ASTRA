"""Every number in the README's results sections must trace to the authoritative record (SP-18).

A README number passes if some value from models/published_metrics.json (or computed from it:
confusion-matrix metrics, best validation accuracy, dataset counts) rounds to it at the README's
own precision. Numbers the README quotes as superseded or wrong are in the record too, under
"superseded" or "conflicts", so they still trace; anything else fails.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import numpy as np

from pipeline import build_platform_artifacts as gen
from training.evaluate import metrics_from_confusion

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
SECTIONS = [("## ⚠️ Scientific Integrity Notice", "## 📁 Repository Structure"),
            ("## 📈 Results", "## 🔁 Reproducing Results")]


def _numbers(obj: object) -> list[float]:
    if isinstance(obj, bool) or obj is None:
        return []
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, str):
        return [float(x) for x in re.findall(r"\d+\.\d+", obj)]
    if isinstance(obj, dict):
        return [v for value in obj.values() for v in _numbers(value)]
    if isinstance(obj, list):
        return [v for value in obj for v in _numbers(value)]
    return []


def _traceable_values() -> list[float]:
    record = gen.load_record()
    values = _numbers(record)
    for model in record["models"].values():
        metrics = metrics_from_confusion(np.array(model["test_confusion_matrix"]["matrix"]))
        values += [metrics["accuracy"], metrics["macro_f1"], metrics["weighted_f1"]]
        values += [c["f1"] for c in metrics["per_class"].values()]
        values.append(gen.best_validation(ROOT / model["training_history"])["accuracy"])
    dataset = gen.dataset_counts()
    values += [count / dataset["total_stars"] for count in dataset["class_counts"].values()]
    values += _numbers(json.loads(gen.serialise("calibration.json", gen.build(record)["calibration.json"])))
    return values


def _readme_numbers() -> list[tuple[str, float, int]]:
    """(text, value as a fraction or plain number, decimals at which to compare)."""
    found = []
    for start, end in SECTIONS:
        section = README[README.index(start):README.index(end)]
        section = re.sub(r"\]\([^)]*\)", "]", section)  # drop link targets (file names)
        section = re.sub(r"`[^`]*`", "", section)  # drop code spans (hashes, paths)
        for whole, number, percent in re.findall(r"(?<![\w.])((\d+\.\d+)(%?))", section):
            decimals = len(number.split(".")[1])
            if percent:
                found.append((whole, float(number) / 100, decimals + 2))
            else:
                found.append((whole, float(number), decimals))
    return found


class ReadmeMetricsTests(unittest.TestCase):
    def test_every_results_number_traces_to_the_record(self) -> None:
        values = _traceable_values()
        untraced = sorted({text for text, value, decimals in _readme_numbers()
                           if not any(abs(round(v, decimals) - value) < 10 ** -(decimals + 2) for v in values)})
        self.assertEqual(untraced, [], "README numbers with no source in models/published_metrics.json")

    def test_sections_contain_numbers(self) -> None:
        self.assertGreater(len(_readme_numbers()), 40)

    def test_superseded_and_unsourced_values_are_not_shown_as_results(self) -> None:
        # They may only appear inside a sentence that flags them.
        for value in ("0.7654", "0.0478", "0.5332", "84.68%", "74.47%"):
            for line in README.splitlines():
                if value in line:
                    self.assertRegex(line.lower(), r"earlier|superseded|contradict|before", f"{value}: {line[:80]}")


if __name__ == "__main__":
    unittest.main()
