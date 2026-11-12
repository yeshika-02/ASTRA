"""
ASTRA — evaluate a checkpoint on a frozen split, with bootstrap confidence intervals.

Metrics come from the confusion matrix, so the same code reproduces the published test
results from the published confusion matrices (tests/test_evaluate.py). Confidence
intervals resample stars with replacement (percentile bootstrap, fixed seed).

The checkpoint's SHA256 is compared with models/published_weights.json: only a verified
published checkpoint is compared with the published numbers. Anything else (a retrained
or recovered-but-different file) is reported as a new model.

    python training/evaluate.py --checkpoint models/saved/best_star_transformer_shared.pt \\
        --temperature-file models/saved/optimal_temperature_transformer_shared.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES, NUM_CLASSES

BOOTSTRAP_METRICS = ("accuracy", "macro_f1", "weighted_f1")
PUBLISHED_TOLERANCE = 5e-5  # published numbers are rounded to 4 decimals


def confusion_matrix(labels: np.ndarray, predictions: np.ndarray, num_classes: int = NUM_CLASSES) -> np.ndarray:
    """Rows are true classes, columns predicted classes."""
    labels = np.asarray(labels, dtype=np.int64)
    predictions = np.asarray(predictions, dtype=np.int64)
    if labels.shape != predictions.shape:
        raise ValueError(f"labels {labels.shape} and predictions {predictions.shape} differ in shape")
    flat = np.bincount(labels * num_classes + predictions, minlength=num_classes * num_classes)
    return flat.reshape(num_classes, num_classes)


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Element-wise division that gives 0 where the denominator is 0 (sklearn's zero_division=0)."""
    numerator = np.asarray(numerator, dtype=np.float64)
    denominator = np.asarray(denominator, dtype=np.float64)
    out = np.zeros(np.broadcast(numerator, denominator).shape)
    np.divide(numerator, denominator, out=out, where=denominator != 0)
    return out


def metrics_from_confusion(cm: np.ndarray, class_names: tuple[str, ...] | list[str] = CLASS_NAMES) -> dict:
    """Accuracy, macro / weighted F1 and per-class precision, recall, F1 and support."""
    cm = np.asarray(cm, dtype=np.int64)
    true_positive = np.diag(cm)
    support = cm.sum(axis=1)
    predicted = cm.sum(axis=0)
    precision = _safe_divide(true_positive, predicted)
    recall = _safe_divide(true_positive, support)
    f1 = _safe_divide(2 * true_positive, support + predicted)
    total = int(cm.sum())
    return {
        "n": total,
        "correct": int(true_positive.sum()),
        "accuracy": float(true_positive.sum() / total) if total else 0.0,
        "macro_f1": float(f1.mean()),
        "weighted_f1": float((f1 * support).sum() / total) if total else 0.0,
        "per_class": {
            name: {"precision": float(precision[i]), "recall": float(recall[i]), "f1": float(f1[i]),
                   "support": int(support[i])}
            for i, name in enumerate(class_names)
        },
    }


def bootstrap_ci(
    labels: np.ndarray,
    predictions: np.ndarray,
    num_classes: int = NUM_CLASSES,
    n_resamples: int = 1000,
    seed: int = 42,
    confidence: float = 0.95,
) -> dict:
    """Percentile bootstrap CIs for accuracy, macro F1 and weighted F1, resampling stars."""
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if n_resamples < 1:
        raise ValueError("n_resamples must be at least 1")
    labels = np.asarray(labels, dtype=np.int64)
    predictions = np.asarray(predictions, dtype=np.int64)
    n = len(labels)
    rng = np.random.default_rng(seed)
    samples = {name: np.empty(n_resamples) for name in BOOTSTRAP_METRICS}
    for b in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        resampled = metrics_from_confusion(confusion_matrix(labels[idx], predictions[idx], num_classes),
                                           class_names=[str(i) for i in range(num_classes)])
        for name in BOOTSTRAP_METRICS:
            samples[name][b] = resampled[name]
    alpha = (1 - confidence) / 2
    return {
        "method": "percentile bootstrap over stars",
        "n_resamples": n_resamples,
        "seed": seed,
        "confidence": confidence,
        "ci": {name: [float(np.quantile(values, alpha)), float(np.quantile(values, 1 - alpha))]
               for name, values in samples.items()},
    }


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """Row-wise softmax of logits / temperature."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    scaled = np.asarray(logits, dtype=np.float64) / temperature
    scaled -= scaled.max(axis=1, keepdims=True)
    exp = np.exp(scaled)
    return exp / exp.sum(axis=1, keepdims=True)


# ─── Model and data ─────────────────────────────────────────────────────────────


def load_checkpoint(path: Path):
    """Rebuild the model a training script saved; returns (model in eval mode, description)."""
    import torch

    from training.models.hybrid_transformer import HybridTransformer
    from training.models.star_cnn import StarCNN

    ckpt = torch.load(path, map_location="cpu", weights_only=True)
    num_classes = ckpt.get("num_classes", NUM_CLASSES)
    if "variant" in ckpt:  # train_transformer.py checkpoints
        variant = ckpt["variant"]
        use_folded = ckpt.get("use_folded", variant not in ("only", "shared_no_folded", "shared_no_folded_matched"))
        model = HybridTransformer(variant=variant, num_classes=num_classes)
        architecture = f"HybridTransformer ({variant})"
    else:  # train_cnn.py checkpoints
        variant = None
        use_folded = bool(ckpt.get("use_folded", False))
        model = StarCNN(num_classes=num_classes, use_folded=use_folded)
        architecture = "StarCNN (dual branch)" if use_folded else "StarCNN (raw)"
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model, {
        "architecture": architecture,
        "variant": variant,
        "use_folded": use_folded,
        "num_classes": num_classes,
        "epoch": ckpt.get("epoch"),
        "val_accuracy": ckpt.get("val_accuracy"),
    }


def predict_logits(model, dataset, batch_size: int = 64) -> tuple[np.ndarray, np.ndarray]:
    """Logits and labels for every sample, in dataset order, without augmentation."""
    import torch
    from torch.utils.data import DataLoader

    logits, labels = [], []
    with torch.no_grad():
        for inputs, targets in DataLoader(dataset, batch_size=batch_size, shuffle=False):
            logits.append(model(inputs).numpy())
            labels.append(targets.numpy())
    return np.concatenate(logits), np.concatenate(labels)


def load_split(data_dir: Path, split: str, use_folded: bool, splits_dir: Path | None):
    """The frozen split as an ASTRADataset; refuses to fall back to a random split."""
    from training.dataset import ASTRADataset

    dataset = ASTRADataset(data_dir=data_dir, split=split, use_folded=use_folded, augment=False,
                           splits_dir=splits_dir)
    if not dataset.frozen_split:
        raise FileNotFoundError(f"Frozen split files for '{split}' not found (data dir {data_dir}). "
                                "Run python pipeline/prepare_from_repo.py, or pass --splits-dir.")
    return dataset, dataset.splits_dir


def read_temperature(path: Path) -> float:
    value = float(Path(path).read_text(encoding="utf-8").strip())
    if value <= 0:
        raise ValueError(f"{path}: temperature must be positive, got {value}")
    return value


def calibration(probs: np.ndarray, labels: np.ndarray) -> dict:
    """NLL, Brier and ECE with the method calibration.py uses (5 equal-frequency bins)."""
    import torch

    from training.calibration import compute_calibration_metrics

    ece, nll, brier, _ = compute_calibration_metrics(torch.as_tensor(probs, dtype=torch.float32),
                                                     torch.as_tensor(labels, dtype=torch.long), n_bins=5)
    return {"nll": nll, "brier": brier, "ece": ece, "ece_method": "adaptive, 5 equal-frequency bins"}


# ─── Published-checkpoint check ─────────────────────────────────────────────────


def published_status(checkpoint: Path, sha256: str) -> dict | None:
    """Whether this file is a published artifact (by name and hash)."""
    from training.verify_weights import find_published

    entry = find_published(checkpoint.name)
    if entry is None:
        return None
    return {"filename": entry["filename"], "expected_sha256": entry["sha256"], "verified": sha256 == entry["sha256"],
            "published_test": entry.get("published_test")}


def compare_with_published(metrics: dict, published_test: dict) -> dict:
    """Headline metrics within rounding, and the confusion matrix exactly, when published."""
    comparison = {}
    for name in BOOTSTRAP_METRICS:
        if name in published_test:
            comparison[name] = {"published": published_test[name], "evaluated": round(metrics[name], 4),
                                "match": abs(metrics[name] - published_test[name]) <= PUBLISHED_TOLERANCE}
    if "confusion_matrix" in published_test and "confusion_matrix" in metrics:
        comparison["confusion_matrix"] = {"match": metrics["confusion_matrix"] == published_test["confusion_matrix"]}
    comparison["reproduced"] = all(item["match"] for item in comparison.values())
    return comparison


# ─── Evaluation ─────────────────────────────────────────────────────────────────


def evaluate(
    checkpoint: Path,
    split: str = "test",
    data_dir: Path | None = None,
    splits_dir: Path | None = None,
    temperature: float = 1.0,
    temperature_source: str | None = None,
    n_bootstrap: int = 1000,
    seed: int = 42,
    confidence: float = 0.95,
    batch_size: int = 64,
) -> dict:
    from astra import provenance
    from astra.config import get_paths
    from training.verify_weights import sha256_file

    paths = get_paths()
    data_dir = Path(data_dir) if data_dir else paths.processed_dir
    checkpoint = Path(checkpoint)
    sha256 = sha256_file(checkpoint)
    model, model_info = load_checkpoint(checkpoint)
    dataset, resolved_splits = load_split(data_dir, split, model_info["use_folded"], splits_dir)

    logits, labels = predict_logits(model, dataset, batch_size)
    raw_probs = softmax(logits)
    probs = softmax(logits, temperature)
    predictions = probs.argmax(axis=1)
    cm = confusion_matrix(labels, predictions, model_info["num_classes"])
    metrics = metrics_from_confusion(cm)
    metrics["confusion_matrix"] = cm.tolist()
    metrics["calibration"] = {"temperature": temperature, **calibration(probs, labels)}
    if temperature != 1.0:
        metrics["calibration_uncalibrated"] = calibration(raw_probs, labels)

    published = published_status(checkpoint, sha256)
    if published and published["verified"] and split == "test" and published["published_test"]:
        published["comparison"] = compare_with_published(metrics, published["published_test"])

    tic_ids = [sample["tic_id"] for sample in dataset._samples]
    return {
        "checkpoint": {"path": str(checkpoint), "sha256": sha256, **model_info},
        "published": published,
        "split": {"name": split, "n": len(labels), "data_dir": str(data_dir), "splits_dir": str(resolved_splits)},
        "temperature": {"value": temperature, "source": temperature_source},
        "metrics": metrics,
        "bootstrap": bootstrap_ci(labels, predictions, model_info["num_classes"], n_bootstrap, seed, confidence),
        # Logits are kept so calibration metrics (NLL, ECE, Brier) can be recomputed at any temperature,
        # e.g. by pipeline/build_platform_artifacts.py --evaluation.
        "predictions": [
            {"tic_id": tic, "label": CLASS_NAMES[int(y)], "predicted": CLASS_NAMES[int(p)],
             "probabilities": {name: round(float(v), 6) for name, v in zip(CLASS_NAMES, row)},
             "logits": [round(float(v), 6) for v in logit_row]}
            for tic, y, p, row, logit_row in zip(tic_ids, labels, predictions, probs, logits)
        ],
        "provenance": provenance.collect(
            seed=seed, device="cpu",
            data=provenance.data_fingerprint(paths.phase6_root / "scientific_dataset_freeze_v2.csv", resolved_splits),
        ),
    }


def _status_line(result: dict) -> str:
    published = result["published"]
    if published is None:
        return "not a published artifact (new model): results describe this checkpoint only"
    if not published["verified"]:
        return ("HASH MISMATCH: same name as a published checkpoint but different bytes; "
                "this is not the published model")
    comparison = published.get("comparison")
    if comparison is None:
        return "verified published checkpoint"
    return ("verified published checkpoint; published test metrics "
            + ("REPRODUCED" if comparison["reproduced"] else "NOT reproduced"))


def render_markdown(result: dict) -> str:
    metrics, ci = result["metrics"], result["bootstrap"]["ci"]
    level = int(round(result["bootstrap"]["confidence"] * 100))
    resamples, seed = result["bootstrap"]["n_resamples"], result["bootstrap"]["seed"]
    cal = metrics["calibration"]
    git = result["provenance"]["git"]
    temperature = result["temperature"]
    lines = [
        f"# Evaluation: `{Path(result['checkpoint']['path']).name}` on the {result['split']['name']} split",
        "",
        f"- **Model:** {result['checkpoint']['architecture']}",
        f"- **Checkpoint SHA256:** `{result['checkpoint']['sha256']}`",
        f"- **Status:** {_status_line(result)}",
        f"- **Stars:** {result['split']['n']} · split hash `{result['provenance']['data']['split_hash']}`",
        f"- **Temperature:** {temperature['value']}" + (f" (from `{temperature['source']}`)" if temperature["source"] else ""),
        f"- **Code:** `{git['commit']}`" + (" (uncommitted changes)" if git["dirty"] else ""),
        "",
        f"| Metric | Value | {level}% CI ({resamples} bootstrap resamples, seed {seed}) |",
        "|---|---:|---|",
    ]
    for name, label in (("accuracy", "Accuracy"), ("macro_f1", "Macro F1"), ("weighted_f1", "Weighted F1")):
        lines.append(f"| {label} | {metrics[name]:.4f} | [{ci[name][0]:.4f}, {ci[name][1]:.4f}] |")
    lines += [
        f"| NLL | {cal['nll']:.4f} | |",
        f"| Brier | {cal['brier']:.4f} | |",
        f"| ECE ({cal['ece_method']}) | {cal['ece']:.4f} | |",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, v in metrics["per_class"].items():
        lines.append(f"| {name} | {v['precision']:.4f} | {v['recall']:.4f} | {v['f1']:.4f} | {v['support']} |")
    lines += ["", "Confusion matrix (rows: true, columns: predicted, order as above):", "", "```"]
    lines += [" ".join(f"{value:4d}" for value in row) for row in metrics["confusion_matrix"]]
    lines.append("```")
    comparison = (result["published"] or {}).get("comparison")
    if comparison:
        lines += ["", "| Published metric | Published | Evaluated | Match |", "|---|---:|---:|:---:|"]
        for name, item in comparison.items():
            if name in ("reproduced", "confusion_matrix"):
                continue
            match = "yes" if item["match"] else "NO"
            lines.append(f"| {name} | {item['published']:.4f} | {item['evaluated']:.4f} | {match} |")
        if "confusion_matrix" in comparison:
            match = "yes" if comparison["confusion_matrix"]["match"] else "NO"
            lines.append(f"| confusion matrix | published figure | above | {match} |")
    return "\n".join(lines) + "\n"


def _positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be positive, got {text}")
    return value


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {text}")
    return value


def _probability(text: str) -> float:
    value = float(text)
    if not 0 < value < 1:
        raise argparse.ArgumentTypeError(f"must be between 0 and 1, got {text}")
    return value


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a checkpoint on a frozen split with bootstrap CIs.")
    parser.add_argument("--checkpoint", required=True,
                        help="PyTorch checkpoint from train_transformer.py or train_cnn.py")
    parser.add_argument("--split", choices=("test", "val", "train"), default="test",
                        help="Frozen split (default: test)")
    parser.add_argument("--data-dir", default=None, help="Processed arrays (default: configured processed dir)")
    parser.add_argument("--splits-dir", default=None, help="Frozen split files (default: configured splits dir)")
    temperature = parser.add_mutually_exclusive_group()
    temperature.add_argument("--temperature", type=_positive_float, default=None,
                             help="Temperature for scaling logits (default: 1.0, no scaling)")
    temperature.add_argument("--temperature-file", default=None,
                             help="File holding the temperature, e.g. optimal_temperature_transformer_shared.txt")
    parser.add_argument("--bootstrap", type=_positive_int, default=1000, help="Bootstrap resamples (default: 1000)")
    parser.add_argument("--seed", type=int, default=42, help="Bootstrap seed (default: 42)")
    parser.add_argument("--confidence", type=_probability, default=0.95, help="CI level (default: 0.95)")
    parser.add_argument("--batch-size", type=_positive_int, default=64)
    parser.add_argument("--out-dir", default=None, help="Report directory (default: outputs/evaluation)")
    parser.add_argument("--require-published", action="store_true",
                        help="Exit 1 unless the checkpoint is a verified published artifact and, on the "
                             "test split, reproduces the published metrics and confusion matrix")
    return parser


def main(argv: list[str] | None = None) -> int:
    from astra.config import get_paths, resolve_cli_path
    from astra.console import ensure_utf8_stdio

    ensure_utf8_stdio()
    args = build_arg_parser().parse_args(argv)
    paths = get_paths()
    checkpoint = resolve_cli_path(args.checkpoint, paths.models_dir)
    if not checkpoint.is_file():
        print(f"Checkpoint not found: {checkpoint}")
        return 1
    temperature, source = 1.0, None
    try:
        if args.temperature is not None:
            temperature, source = args.temperature, "--temperature"
        elif args.temperature_file:
            temperature_path = resolve_cli_path(args.temperature_file, paths.models_dir)
            temperature, source = read_temperature(temperature_path), str(temperature_path)

        result = evaluate(
            checkpoint,
            split=args.split,
            data_dir=resolve_cli_path(args.data_dir, paths.processed_dir),
            splits_dir=resolve_cli_path(args.splits_dir, paths.splits_dir) if args.splits_dir else None,
            temperature=temperature,
            temperature_source=source,
            n_bootstrap=args.bootstrap,
            seed=args.seed,
            confidence=args.confidence,
            batch_size=args.batch_size,
        )
    except (FileNotFoundError, ValueError) as error:
        # Missing frozen split files, an unreadable temperature file, or a malformed split.
        print(f"ERROR: {error}")
        return 1

    out_dir = resolve_cli_path(args.out_dir, paths.output_dir / "evaluation")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"evaluation_{checkpoint.stem}_{args.split}"
    (out_dir / f"{stem}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report = render_markdown(result)
    (out_dir / f"{stem}.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"Reports: {out_dir / stem}.json and .md")

    if args.require_published:
        published = result["published"] or {}
        if not published.get("verified"):
            print("FAILED: --require-published, but this is not a verified published checkpoint.")
            return 1
        comparison = published.get("comparison")
        if comparison is not None and not comparison["reproduced"]:
            print("FAILED: --require-published: verified checkpoint, but the published test results "
                  "were NOT reproduced.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
