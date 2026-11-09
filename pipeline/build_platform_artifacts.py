"""
ASTRA — build the web platform's metric artifacts and docs/metrics.md from one source.

Input: models/published_metrics.json, the authoritative record of every published result
(sprint task SP-18). Outputs:

    astra-platform/data/artifacts/benchmark.json
    astra-platform/data/artifacts/calibration.json
    astra-platform/data/artifacts/uncertainty.json
    astra-platform/data/artifacts/research_findings.json
    astra-platform/data/artifacts/model_registry.json   (active_model benchmark and calibration only)
    docs/metrics.md

Test-set point metrics are computed from the published confusion matrices. Values that need
per-star predictions (CIs, calibration, uncertainty) are copied from the record with their
source, and NLL stays null because no valid NLL was ever recorded. When evaluate.py output
for a model is passed with --evaluation, that model's metrics are recomputed from its
per-star logits instead, NLL included.

    python pipeline/build_platform_artifacts.py            # write
    python pipeline/build_platform_artifacts.py --check    # exit 1 if any output is stale
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from training.evaluate import confusion_matrix, metrics_from_confusion, softmax

RECORD_PATH = PROJECT_ROOT / "models" / "published_metrics.json"
ARTIFACT_DIR = PROJECT_ROOT / "astra-platform" / "data" / "artifacts"
DOCS_PATH = PROJECT_ROOT / "docs" / "metrics.md"
MANIFEST_PATH = PROJECT_ROOT / "astra-platform" / "data" / "scientific_dataset_freeze_v2.csv"
SPLIT_IDS = {split: PROJECT_ROOT / "docs" / "engineering-log" / f"phase6_{split}_ids.json"
             for split in ("train", "val", "test")}
GENERATOR = "pipeline/build_platform_artifacts.py"


# ─── Metrics from per-star probabilities ────────────────────────────────────────


def nll(probs: np.ndarray, labels: np.ndarray, eps: float = 1e-15) -> float:
    """Mean negative log-likelihood of the true class."""
    p_true = np.clip(np.asarray(probs, dtype=np.float64)[np.arange(len(labels)), labels], eps, 1.0)
    return float(-np.log(p_true).mean())


def brier(probs: np.ndarray, labels: np.ndarray) -> float:
    """Multi-class Brier score: mean squared distance to the one-hot label."""
    probs = np.asarray(probs, dtype=np.float64)
    onehot = np.eye(probs.shape[1])[labels]
    return float(((probs - onehot) ** 2).sum(axis=1).mean())


def adaptive_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 5) -> float:
    """ECE over equal-frequency confidence bins, as training/calibration.py computes it."""
    probs = np.asarray(probs, dtype=np.float64)
    confidence = probs.max(axis=1)
    correct = (probs.argmax(axis=1) == labels).astype(np.float64)
    order = np.argsort(confidence, kind="stable")
    confidence, correct = confidence[order], correct[order]
    n = len(labels)
    size = n // n_bins
    if size == 0:
        raise ValueError(f"need at least {n_bins} samples for {n_bins} bins, got {n}")
    ece = 0.0
    for i in range(n_bins):
        end = (i + 1) * size if i < n_bins - 1 else n
        sl = slice(i * size, end)
        ece += (end - i * size) / n * abs(correct[sl].mean() - confidence[sl].mean())
    return float(ece)


def calibration_from_logits(logits: np.ndarray, labels: np.ndarray, temperature: float) -> dict:
    raw, calibrated = softmax(logits), softmax(logits, temperature)
    return {
        "ece_raw": adaptive_ece(raw, labels), "ece_calibrated": adaptive_ece(calibrated, labels),
        "brier_raw": brier(raw, labels), "brier_calibrated": brier(calibrated, labels),
        "nll_raw": nll(raw, labels), "nll_calibrated": nll(calibrated, labels),
    }


# ─── Record and evaluation inputs ───────────────────────────────────────────────


def load_record(path: Path = RECORD_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_temperature(path: Path) -> float:
    return float(path.read_text(encoding="utf-8").strip())


def best_validation(history_path: Path) -> dict:
    history = json.loads(history_path.read_text(encoding="utf-8"))
    accuracies = history["val_accuracy"]
    best = max(range(len(accuracies)), key=lambda i: accuracies[i])
    return {"accuracy": round(accuracies[best], 6), "epoch": best + 1, "epochs": len(accuracies)}


def load_evaluation(path: Path, classes: list[str]) -> dict:
    """Metrics recomputed from an evaluate.py record (needs per-star logits)."""
    record = json.loads(path.read_text(encoding="utf-8"))
    predictions = record["predictions"]
    if not predictions or "logits" not in predictions[0]:
        raise ValueError(f"{path}: evaluation records need per-star logits (re-run training/evaluate.py)")
    logits = np.array([p["logits"] for p in predictions], dtype=np.float64)
    labels = np.array([classes.index(p["label"]) for p in predictions])
    cm = confusion_matrix(labels, logits.argmax(axis=1), len(classes))
    return {
        "source": str(path),
        "split": record["split"]["name"],
        "checkpoint_sha256": record["checkpoint"]["sha256"],
        "published_verified": bool((record.get("published") or {}).get("verified")),
        "confusion_matrix": cm.tolist(),
        "ci": record["bootstrap"]["ci"],
        "temperature": record["temperature"]["value"],
        "calibration": calibration_from_logits(logits, labels, record["temperature"]["value"]),
    }


# ─── Builders ───────────────────────────────────────────────────────────────────


def _r(value: float | None, places: int = 4) -> float | None:
    return None if value is None else round(float(value), places)


def _pct_interval(pair: list[float]) -> str:
    return f"[{pair[0] * 100:.2f}%, {pair[1] * 100:.2f}%]"


def _interval(pair: list[float]) -> str:
    return f"[{pair[0]:.4f}, {pair[1]:.4f}]"


def model_results(name: str, model: dict, evaluation: dict | None, classes: list[str]) -> dict:
    """Point metrics, CIs and their provenance for one model."""
    if evaluation is not None:
        matrix, ci = evaluation["confusion_matrix"], evaluation["ci"]
        point_source = ci_source = evaluation["source"]
        point_status = ci_status = "recomputed"
    else:
        matrix = model["test_confusion_matrix"]["matrix"]
        ci = model["test_bootstrap_ci95"]
        point_source, ci_source = model["test_confusion_matrix"]["source"], ci["source"]
        point_status, ci_status = "computed from the published confusion matrix", "recorded"
    metrics = metrics_from_confusion(np.array(matrix), classes)
    return {
        "metrics": metrics,
        "ci": {key: ci[key] for key in ("accuracy", "macro_f1", "weighted_f1") if key in ci},
        "sources": {"point_metrics": point_source, "ci": ci_source, "subgroups": model["subgroups"]["source"]},
        "status": {"point_metrics": point_status, "ci": ci_status, "subgroups": model["subgroups"]["status"]},
    }


def benchmark_entry(name: str, model: dict, results: dict) -> dict:
    metrics, ci, groups = results["metrics"], results["ci"], model["subgroups"]
    entry = {
        "label": name.replace("_", " ").title(),
        "test_accuracy": _r(metrics["accuracy"]),
        "accuracy_ci": _pct_interval(ci["accuracy"]),
        "macro_f1": _r(metrics["macro_f1"]),
        "macro_f1_ci": _interval(ci["macro_f1"]),
        "weighted_f1": _r(metrics["weighted_f1"]),
        "per_class_f1": {cls: _r(values["f1"]) for cls, values in metrics["per_class"].items()},
        "subgroups": {
            "catalog_accuracy": groups["catalog"]["accuracy"], "catalog_macro_f1": groups["catalog"]["macro_f1"],
            "bls_accuracy": groups["bls"]["accuracy"], "bls_macro_f1": groups["bls"]["macro_f1"],
        },
        "sources": results["sources"],
        "status": results["status"],
    }
    if "weighted_f1" in ci:
        entry["weighted_f1_ci"] = _interval(ci["weighted_f1"])
    return entry


def dataset_counts() -> dict:
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    splits = {split: len(json.loads(path.read_text(encoding="utf-8"))) for split, path in SPLIT_IDS.items()}
    return {
        "total_stars": len(rows),
        "class_counts": dict(sorted(Counter(row["astra_class"] for row in rows).items())),
        "period_source_counts": dict(sorted(Counter(row["period_source"] for row in rows).items())),
        "split_counts": dict(sorted(splits.items())),
        "source": "astra-platform/data/scientific_dataset_freeze_v2.csv; docs/engineering-log/phase6_*_ids.json",
    }


def calibration_summary(model: dict, evaluation: dict | None) -> dict:
    if evaluation is not None:
        summary = {key: _r(value) for key, value in evaluation["calibration"].items()}
        summary.update(source=evaluation["source"], status="recomputed", split=evaluation["split"])
        return summary
    cal = model["calibration"]
    summary = {key: cal[key] for key in ("ece_raw", "ece_calibrated", "brier_raw", "brier_calibrated",
                                         "nll_raw", "nll_calibrated")}
    summary.update(source=cal["source"], status=cal["status"], split=cal["split"])
    if cal.get("note"):
        summary["note"] = cal["note"]
    return summary


def build(record: dict, evaluations: dict[str, dict] | None = None) -> dict[str, object]:
    """All outputs, keyed by name; JSON artifacts as objects, the docs page as text."""
    evaluations = evaluations or {}
    classes = record["classes"]
    models = record["models"]
    generated = record["updated"]
    results = {name: model_results(name, model, evaluations.get(name), classes) for name, model in models.items()}
    benchmark_models = {name: benchmark_entry(name, models[name], results[name]) for name in models}

    calibrated = [name for name in models if "calibration" in models[name]]
    calibration = {
        "generated_at": generated,
        "generator": GENERATOR,
        "global": {name: calibration_summary(models[name], evaluations.get(name)) for name in calibrated},
        "per_class": {
            cls: {f"{'transformer' if name == 'shared' else 'cnn'}_{kind}": models[name]["calibration"]["per_class_ece"][cls][kind]
                  for name in ("cnn_dual", "shared") for kind in ("raw", "calibrated")}
            for cls in classes
        },
        "per_class_source": models["shared"]["calibration"]["source"],
        "temperatures": {name: read_temperature(PROJECT_ROOT / models[name]["calibration"]["temperature_file"])
                         for name in calibrated},
    }

    uncertainty = {
        "generated_at": generated,
        "generator": GENERATOR,
        "coverage_sweep": [dict(point, model=name) for name in ("cnn_dual", "shared")
                           for point in models[name]["uncertainty"]["coverage_sweep"]],
        "entropy": {name: {
            "correct_mean_entropy": models[name]["uncertainty"]["entropy"]["correct_mean"],
            "correct_entropy_var": models[name]["uncertainty"]["entropy"]["correct_var"],
            "incorrect_mean_entropy": models[name]["uncertainty"]["entropy"]["incorrect_mean"],
            "incorrect_entropy_var": models[name]["uncertainty"]["entropy"]["incorrect_var"],
        } for name in ("cnn_dual", "shared")},
        "error_detection_auroc": {name: models[name]["uncertainty"]["error_detection_auroc"]
                                  for name in ("cnn_dual", "shared")},
        "source": models["shared"]["uncertainty"]["source"],
        "note": models["shared"]["uncertainty"]["note"],
    }

    shared = benchmark_models["shared"]
    shared_cal = calibration["global"]["shared"]
    gap = _r(shared["subgroups"]["catalog_accuracy"] - shared["subgroups"]["bls_accuracy"])
    research = {
        "generated_at": generated,
        "generator": GENERATOR,
        "headline": "Period source quality remains the dominant performance bottleneck.",
        "accuracy_gap_catalog_vs_bls": gap,
        "calibration": shared_cal,
        "findings": [
            {"id": "bls_gap", "statement": "Catalog-period stars classify more reliably than BLS-period stars.",
             "unit": "accuracy_delta", "value": gap},
            {"id": "calibration_gain",
             "statement": "Temperature scaling improves transformer calibration on the test split.",
             "unit": "ece_delta", "value": _r(shared_cal["ece_raw"] - shared_cal["ece_calibrated"])},
        ],
        "selective_prediction": [dict(point, model="shared") for point in models["shared"]["uncertainty"]["coverage_sweep"]],
        "shared_transformer": shared,
    }

    registry = json.loads((ARTIFACT_DIR / "model_registry.json").read_text(encoding="utf-8"))
    registry["active_model"]["benchmark"] = shared
    registry["active_model"]["calibration"] = shared_cal

    validation = {name: best_validation(PROJECT_ROOT / model["training_history"]) for name, model in models.items()}
    return {
        "benchmark.json": {"generated_at": generated, "generator": GENERATOR, "dataset": dataset_counts(),
                           "models": benchmark_models},
        "calibration.json": calibration,
        "uncertainty.json": uncertainty,
        "research_findings.json": research,
        "model_registry.json": registry,
        "metrics.md": render_markdown(record, results, calibration, validation),
    }


# ─── docs/metrics.md ────────────────────────────────────────────────────────────


def render_markdown(record: dict, results: dict, calibration: dict, validation: dict) -> str:
    models, classes = record["models"], record["classes"]
    lines = [
        "# Published metrics",
        "",
        f"<!-- Generated by {GENERATOR} from models/published_metrics.json. Do not edit by hand. -->",
        "",
        "The single authoritative table of ASTRA's published results (sprint task SP-18). Every number "
        "comes from [`models/published_metrics.json`](../models/published_metrics.json), which cites its source. "
        "The trained weights are not in the repository ([model_recovery.md](model_recovery.md)), so only the "
        "test-set point metrics can be recomputed here, from the committed confusion matrices.",
        "",
        "**Status:** *computed*: recomputed from a committed confusion matrix or training history. "
        "*recorded*: copied from the cited report; needs the weights to recompute. "
        "*unverified*: the cited report contradicts committed evidence.",
        "",
        f"## Test set (N = {record['test_split']['n']}, frozen split)",
        "",
        "| Model | Parameters | Accuracy | 95% CI | Macro F1 | 95% CI | Weighted F1 |",
        "|---|---:|---:|---|---:|---|---:|",
    ]
    for name, model in models.items():
        m, ci = results[name]["metrics"], results[name]["ci"]
        star = " (production)" if model.get("production") else ""
        lines.append(f"| {model['label']}{star} | {model['parameters']:,} | {m['accuracy'] * 100:.2f}% "
                     f"({m['correct']}/{m['n']}) | {_pct_interval(ci['accuracy'])} | {m['macro_f1']:.4f} | "
                     f"{_interval(ci['macro_f1'])} | {m['weighted_f1']:.4f} |")
    lines += ["", "Point metrics: *computed* from each model's published test confusion matrix. "
              "CIs: *recorded* (percentile bootstrap) from `ground_truth_metrics.md` (shared, CNN) and "
              "`phase7_testset_results.md` (others).", "",
              "### Per-class F1 (test)", "",
              "| Model | " + " | ".join(classes) + " |", "|---|" + "---:|" * len(classes)]
    for name, model in models.items():
        f1 = results[name]["metrics"]["per_class"]
        lines.append(f"| {model['label']} | " + " | ".join(f"{f1[c]['f1']:.4f}" for c in classes) + " |")
    lines += ["", "## Validation (best epoch, 141 stars) — *computed*", "",
              "| Model | Best validation accuracy | Epoch | Source |", "|---|---:|---:|---|"]
    for name, model in models.items():
        v = validation[name]
        lines.append(f"| {model['label']} | {v['accuracy'] * 100:.2f}% | {v['epoch']} of {v['epochs']} | "
                     f"`{model['training_history']}` |")
    lines += ["", "## Calibration (test split) — *recorded*", "",
              "| Model | Temperature | ECE raw | ECE calibrated | Brier raw | Brier calibrated | NLL |",
              "|---|---:|---:|---:|---:|---:|---|"]
    for name, summary in calibration["global"].items():
        nll_text = (f"{summary['nll_raw']:.4f} / {summary['nll_calibrated']:.4f}"
                    if summary["nll_raw"] is not None else "not recorded")
        lines.append(f"| {models[name]['label']} | {calibration['temperatures'][name]} | {summary['ece_raw']:.4f} | "
                     f"{summary['ece_calibrated']:.4f} | {summary['brier_raw']:.4f} | "
                     f"{summary['brier_calibrated']:.4f} | {nll_text} |")
    lines += ["", f"Source: `{models['shared']['calibration']['source']}`. "
              "ECE uses 5 equal-frequency bins. The audit reports NLL equal to ECE (a copy error), so no valid NLL "
              "is recorded; `build_platform_artifacts.py --evaluation` recomputes it from per-star logits.", "",
              "## Uncertainty (MC Dropout) — *recorded*", "",
              "| Model | Error-detection AUROC | Mean entropy, correct | Mean entropy, incorrect |",
              "|---|---:|---:|---:|"]
    for name in ("shared", "cnn_dual"):
        u = models[name]["uncertainty"]
        lines.append(f"| {models[name]['label']} | {u['error_detection_auroc']:.4f} | "
                     f"{u['entropy']['correct_mean']:.4f} nats | {u['entropy']['incorrect_mean']:.4f} nats |")
    lines += ["", "| Confidence threshold | " + " | ".join(f"{models[n]['label']} coverage / accuracy"
                                                       for n in ("shared", "cnn_dual")) + " |",
              "|---:|---|---|"]
    for i, point in enumerate(models["shared"]["uncertainty"]["coverage_sweep"]):
        cnn = models["cnn_dual"]["uncertainty"]["coverage_sweep"][i]
        lines.append(f"| {point['confidence_threshold']} | {point['coverage'] * 100:.1f}% / {point['accuracy'] * 100:.1f}% "
                     f"| {cnn['coverage'] * 100:.1f}% / {cnn['accuracy'] * 100:.1f}% |")
    lines += ["", f"Source: `{models['shared']['uncertainty']['source']}`. {models['shared']['uncertainty']['note']}",
              "", "## Period-source subgroups (test)", "",
              "| Model | Catalog accuracy (N=90) | BLS accuracy (N=52) | Catalog macro F1 | BLS macro F1 | Status |",
              "|---|---:|---:|---:|---:|---|"]
    for name, model in models.items():
        g = model["subgroups"]
        lines.append(f"| {model['label']} | {g['catalog']['accuracy'] * 100:.2f}% | {g['bls']['accuracy'] * 100:.2f}% | "
                     f"{g['catalog']['macro_f1']:.4f} | {g['bls']['macro_f1']:.4f} | {g['status']} |")
    lines += ["", "Source: `phase7_testset_results.md`. The CNN row is *unverified*: that report's CNN headline "
              "numbers do not match the published CNN confusion matrix.", "",
              "## Superseded results", "",
              record["superseded"]["reason"] + f" Source: `{record['superseded']['source']}`. They include the "
              "cross-validation summary (mean validation accuracy 84.68%), calibrated ECE 0.0478, NLL 0.5332, "
              "entropy 0.5250 / 0.8407 nats and a selective-prediction table that the README used to show as "
              "current results.", "",
              "## Conflicts and how they were resolved", ""]
    for conflict in record["conflicts"]:
        values = "; ".join(f"{where}: {value}" for where, value in conflict["values"].items())
        lines.append(f"- **{conflict['metric']}.** {values}. Resolution: {conflict['resolution']}")
    lines += ["", "## Numbers without a source", ""]
    for item in record["unsourced"]:
        values = f" ({', '.join(str(v) for v in item['values'])})" if item.get("values") else ""
        lines.append(f"- `{item['where']}`{values}: {item['note']}")
    return "\n".join(lines) + "\n"


# ─── Output ─────────────────────────────────────────────────────────────────────


def serialise(name: str, content: object) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, indent=2, sort_keys=True) + "\n"


def output_path(name: str, artifact_dir: Path, docs_path: Path) -> Path:
    return docs_path if name == "metrics.md" else artifact_dir / name


def stale_outputs(outputs: dict[str, object], artifact_dir: Path = ARTIFACT_DIR, docs_path: Path = DOCS_PATH) -> list[str]:
    stale = []
    for name, content in outputs.items():
        path = output_path(name, artifact_dir, docs_path)
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.is_file() else None
        if current != serialise(name, content):
            stale.append(str(path.relative_to(PROJECT_ROOT) if path.is_relative_to(PROJECT_ROOT) else path))
    return stale


def write_outputs(outputs: dict[str, object], artifact_dir: Path = ARTIFACT_DIR, docs_path: Path = DOCS_PATH) -> None:
    for name, content in outputs.items():
        path = output_path(name, artifact_dir, docs_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialise(name, content), encoding="utf-8", newline="\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build platform metric artifacts and docs/metrics.md.")
    parser.add_argument("--check", action="store_true", help="Exit 1 if any committed output differs from a rebuild")
    parser.add_argument("--evaluation", action="append", default=[], metavar="MODEL=PATH",
                        help="Recompute MODEL from an evaluate.py JSON with per-star logits (repeatable)")
    return parser


def main(argv: list[str] | None = None) -> int:
    from astra.console import ensure_utf8_stdio
    ensure_utf8_stdio()
    args = build_arg_parser().parse_args(argv)
    record = load_record()
    evaluations = {}
    for item in args.evaluation:
        name, _, path = item.partition("=")
        if name not in record["models"] or not path:
            print(f"--evaluation expects MODEL=PATH with MODEL in {sorted(record['models'])}, got {item!r}")
            return 1
        evaluations[name] = load_evaluation(Path(path), record["classes"])
    outputs = build(record, evaluations)
    if args.check:
        stale = stale_outputs(outputs)
        if stale:
            print("Stale outputs (run python pipeline/build_platform_artifacts.py):\n  " + "\n  ".join(stale))
            return 1
        print(f"All {len(outputs)} outputs are up to date.")
        return 0
    write_outputs(outputs)
    print(f"Wrote {len(outputs)} outputs from {RECORD_PATH.relative_to(PROJECT_ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
