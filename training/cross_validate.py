"""
ASTRA — honest cross-validation of the shared transformer (SP-21, ADR-0062).

Protocol:
- The pool is the frozen train + validation stars. The frozen test stars are excluded and
  the script refuses to run without the test-id file.
- Stars are grouped with the pipeline's duplicate rule (same TIC id, or within 2 arcsec;
  pipeline.phase6_utils.assign_duplicate_groups), so no group is ever split.
- Outer loop: stratified group k-fold. Inside each outer training set an inner stratified
  group split holds out a selection set; the best epoch is chosen on that selection set
  only, and the selected model is scored once on the outer fold.
- Reported: outer-fold metrics, their mean and spread over folds and seeds, and a
  percentile-bootstrap CI over each seed's pooled out-of-fold predictions.

The old script scored each fold with the best of 50 epochs chosen on that same fold and
drew folds from all 944 stars, test stars included (audit S7).

Outputs fold_metrics.csv, aggregate_metrics.json, statistical_report.md and one confusion
matrix per outer fold.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import logging
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from astra.config import get_paths, resolve_cli_path
from data.labels import CLASS_NAMES, NUM_CLASSES
from training.dataset import ASTRADataset
from training.models.hybrid_transformer import HybridTransformer
from training.train_transformer import RegularizedFocalLoss

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# Output Paths
PATHS = get_paths()
ARTIFACT_DIR = PATHS.output_dir  # reports, plots, metrics
DATA_DIR = PATHS.processed_dir


def set_deterministic_seeds(seed: int) -> None:
    """Enforce seed determinism."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass


class CrossValDataset(ASTRADataset):
    """Custom dataset wrapper for cross-validation subsets."""
    def __init__(
        self, samples: list[dict], use_folded: bool = True, augment: bool = False, data_dir: Path = DATA_DIR
    ) -> None:
        self.data_dir = data_dir
        self.split = "custom"
        self.use_folded = use_folded
        self.augment = augment
        self.augment_prob = 0.5
        self.splits_dir = None
        self.frozen_split = False
        self._samples = samples
        self._label_list = [s["label"] for s in samples]


def scan_all_samples(data_dir: Path = DATA_DIR) -> list[dict]:
    """Scan all processed TIC directories to build list of valid samples."""
    tic_dirs = sorted(Path(data_dir).glob("TIC_*"))
    required_files = ("flux_1000.npy", "flux_200.npy", "folded_flux_1000.npy", "folded_flux_200.npy", "metadata.json")

    samples = []
    for tic_dir in tic_dirs:
        if not tic_dir.is_dir():
            continue
        if all((tic_dir / f).exists() for f in required_files):
            try:
                with open(tic_dir / "metadata.json", "r") as f:
                    meta = json.load(f)
                label = meta.get("label")
                if label is not None and isinstance(label, int) and (0 <= label < NUM_CLASSES):
                    samples.append({
                        "flux_path": tic_dir / "flux_1000.npy",
                        "folded_flux_path": tic_dir / "folded_flux_1000.npy",
                        "label": label,
                        "tic_id": tic_dir.name,
                        "ra": meta.get("ra"),
                        "dec": meta.get("dec"),
                        "period_source": meta.get("period_source", "unknown"),
                    })
            except Exception:
                pass
    return samples


# ─── Protocol: pool, groups, folds (no model involved) ──────────────────────────


@dataclass(frozen=True)
class FoldPlan:
    """One outer fold: train on train_idx, pick the epoch on select_idx, score on test_idx."""
    seed: int
    fold: int
    train_idx: np.ndarray
    select_idx: np.ndarray
    test_idx: np.ndarray


def read_test_ids(path: Path) -> set[str]:
    if not Path(path).is_file():
        raise FileNotFoundError(
            f"Frozen test-id file not found: {path}. Cross-validation must exclude the test stars; "
            "run python pipeline/prepare_from_repo.py or pass --test-ids."
        )
    return set(json.loads(Path(path).read_text(encoding="utf-8")))


def cv_pool(samples: list[dict], test_ids: set[str]) -> list[dict]:
    """Every sample except the frozen test stars."""
    return [s for s in samples if s["tic_id"] not in test_ids]


def duplicate_groups(samples: list[dict]) -> np.ndarray:
    """Group ids from the pipeline's duplicate rule (same TIC id, or within 2 arcsec)."""
    from pipeline.phase6_utils import assign_duplicate_groups

    rows = [{"tic_id": s["tic_id"].removeprefix("TIC_"), "ra": s.get("ra"), "dec": s.get("dec")} for s in samples]
    return np.array([row["duplicate_group_id"] for row in assign_duplicate_groups(rows)])


def plan_folds(labels: np.ndarray, groups: np.ndarray, seeds: list[int], n_folds: int,
               inner_folds: int) -> list[FoldPlan]:
    """Outer stratified group k-fold; one inner stratified group split per outer training set."""
    from sklearn.model_selection import StratifiedGroupKFold

    plans = []
    index = np.arange(len(labels))
    for seed in seeds:
        outer = StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=seed)
        for fold, (outer_train, outer_test) in enumerate(outer.split(index, labels, groups=groups)):
            inner = StratifiedGroupKFold(n_splits=inner_folds, shuffle=True, random_state=seed + 1000 + fold)
            inner_train, inner_select = next(inner.split(outer_train, labels[outer_train], groups=groups[outer_train]))
            plans.append(FoldPlan(seed, fold, outer_train[inner_train], outer_train[inner_select], outer_test))
    return plans


def check_plans(plans: list[FoldPlan], groups: np.ndarray, n_pool: int) -> None:
    """Raise if any group straddles train / select / test, or a seed's test folds miss or repeat a star."""
    for plan in plans:
        parts = {"train": plan.train_idx, "select": plan.select_idx, "test": plan.test_idx}
        for a, b in (("train", "select"), ("train", "test"), ("select", "test")):
            if set(parts[a]) & set(parts[b]):
                raise AssertionError(f"seed {plan.seed} fold {plan.fold}: {a} and {b} share stars")
            if set(groups[parts[a]]) & set(groups[parts[b]]):
                raise AssertionError(f"seed {plan.seed} fold {plan.fold}: a duplicate group straddles {a}/{b}")
    for seed in {plan.seed for plan in plans}:
        tested = np.concatenate([plan.test_idx for plan in plans if plan.seed == seed])
        if len(tested) != n_pool or len(set(tested)) != n_pool:
            raise AssertionError(f"seed {seed}: outer test folds do not cover every pool star exactly once")


# ─── Running the protocol ───────────────────────────────────────────────────────

# train_fn(train_samples, select_samples) -> (predict_fn, selection_info). It may look at the
# selection samples to choose an epoch, and must never see the outer test fold.
TrainFn = Callable[[list[dict], list[dict]], tuple[Callable[[list[dict]], list[int]], dict]]


def run_plans(samples: list[dict], plans: list[FoldPlan], train_fn: TrainFn) -> list[dict]:
    """Train and select on each plan, then score once on its outer fold."""
    from sklearn.metrics import f1_score

    results = []
    for plan in plans:
        t0 = time.time()
        test_samples = [samples[i] for i in plan.test_idx]
        predict, selection = train_fn([samples[i] for i in plan.train_idx], [samples[i] for i in plan.select_idx])
        preds = list(predict(test_samples))
        labels = [s["label"] for s in test_samples]
        f1s = f1_score(labels, preds, average=None, labels=list(range(NUM_CLASSES)), zero_division=0)
        results.append({
            "seed": plan.seed,
            "fold": plan.fold,
            "n_train": len(plan.train_idx),
            "n_select": len(plan.select_idx),
            "n_test": len(plan.test_idx),
            "accuracy": float(np.mean(np.array(preds) == np.array(labels))),
            "macro_f1": float(np.mean(f1s)),
            **{f"f1_{name}": float(f1s[i]) for i, name in enumerate(CLASS_NAMES)},
            **evaluate_subgroups({"preds": preds, "labels": labels}, test_samples),
            "selection_accuracy": selection.get("selection_accuracy"),
            "best_epoch": selection.get("best_epoch"),
            "runtime_sec": time.time() - t0,
            "test_tic_ids": [s["tic_id"] for s in test_samples],
            "preds": preds,
            "labels": labels,
        })
    return results


def summarise(results: list[dict], n_resamples: int = 1000) -> dict:
    """Mean and spread of outer-fold scores, and a bootstrap CI per seed over out-of-fold predictions."""
    from training.evaluate import bootstrap_ci

    accuracies = [r["accuracy"] for r in results]
    per_seed = {}
    for seed in sorted({r["seed"] for r in results}):
        labels = np.concatenate([r["labels"] for r in results if r["seed"] == seed])
        preds = np.concatenate([r["preds"] for r in results if r["seed"] == seed])
        ci = bootstrap_ci(labels, preds, NUM_CLASSES, n_resamples=n_resamples, seed=seed)["ci"]
        per_seed[str(seed)] = {"out_of_fold_accuracy": float(np.mean(labels == preds)),
                               "accuracy_ci95": ci["accuracy"], "macro_f1_ci95": ci["macro_f1"]}
    return {
        "mean_fold_accuracy": float(np.mean(accuracies)),
        "std_fold_accuracy": float(np.std(accuracies)),
        "mean_fold_macro_f1": float(np.mean([r["macro_f1"] for r in results])),
        "mean_catalog_accuracy": float(np.mean([r["catalog_accuracy"] for r in results])),
        "mean_bls_accuracy": float(np.mean([r["bls_accuracy"] for r in results])),
        "mean_f1_per_class": {name: float(np.mean([r[f"f1_{name}"] for r in results])) for name in CLASS_NAMES},
        "mean_selection_accuracy": float(np.mean([r["selection_accuracy"] for r in results
                                                  if r["selection_accuracy"] is not None] or [np.nan])),
        "per_seed": per_seed,
    }


# ─── The transformer trainer ────────────────────────────────────────────────────


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    model.train()
    total_loss = 0.0
    for flux, labels in loader:
        flux = flux.to(device)
        labels = labels.to(device)
        optimizer.zero_grad()
        logits = model(flux)
        loss = criterion(logits, labels)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        total_loss += loss.item()
    return total_loss / max(len(loader), 1)


@torch.no_grad()
def validate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> dict:
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []

    for flux, labels in loader:
        flux = flux.to(device)
        labels = labels.to(device)
        logits = model(flux)
        loss = criterion(logits, labels)
        total_loss += loss.item()

        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

        all_preds.extend(preds.cpu().tolist())
        all_labels.extend(labels.cpu().tolist())

    return {
        "loss": total_loss / max(len(loader), 1),
        "accuracy": correct / max(total, 1),
        "preds": all_preds,
        "labels": all_labels,
    }


def transformer_trainer(n_epochs: int, device: torch.device, data_dir: Path) -> TrainFn:
    """Train the shared transformer; keep the weights of the epoch that scores best on the selection set."""
    def train(train_samples: list[dict], select_samples: list[dict]):
        train_dataset = CrossValDataset(train_samples, use_folded=True, augment=True, data_dir=data_dir)
        select_dataset = CrossValDataset(select_samples, use_folded=True, augment=False, data_dir=data_dir)
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, num_workers=0)
        select_loader = DataLoader(select_dataset, batch_size=32, shuffle=False, num_workers=0)

        model = HybridTransformer(variant="shared", num_classes=NUM_CLASSES).to(device)
        criterion = RegularizedFocalLoss(alpha=train_dataset.class_weights.to(device), gamma=2.0, label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-3)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=n_epochs)

        best = {"selection_accuracy": -1.0, "best_epoch": None, "state": None}
        for epoch in range(1, n_epochs + 1):
            train_one_epoch(model, train_loader, criterion, optimizer, device)
            selection = validate(model, select_loader, criterion, device)
            scheduler.step()
            if selection["accuracy"] > best["selection_accuracy"]:
                best = {"selection_accuracy": selection["accuracy"], "best_epoch": epoch,
                        "state": copy.deepcopy(model.state_dict())}
        model.load_state_dict(best["state"])

        def predict(samples: list[dict]) -> list[int]:
            loader = DataLoader(CrossValDataset(samples, use_folded=True, augment=False, data_dir=data_dir),
                                batch_size=32, shuffle=False, num_workers=0)
            return validate(model, loader, criterion, device)["preds"]

        return predict, {"selection_accuracy": best["selection_accuracy"], "best_epoch": best["best_epoch"]}

    return train


def evaluate_subgroups(val_results: dict, val_samples: list[dict]) -> dict:
    """Evaluate accuracy on catalog-period stars vs BLS-fallback stars."""
    preds = val_results["preds"]
    labels = val_results["labels"]

    catalog_correct = 0
    catalog_total = 0
    bls_correct = 0
    bls_total = 0

    for pred, label, sample in zip(preds, labels, val_samples):
        source = sample["period_source"]
        if source == "catalog":
            catalog_total += 1
            if pred == label:
                catalog_correct += 1
        elif source == "BLS":
            bls_total += 1
            if pred == label:
                bls_correct += 1

    cat_acc = catalog_correct / catalog_total if catalog_total > 0 else 0.0
    bls_acc = bls_correct / bls_total if bls_total > 0 else 0.0

    return {
        "catalog_accuracy": cat_acc,
        "catalog_count": catalog_total,
        "bls_accuracy": bls_acc,
        "bls_count": bls_total,
    }


def save_confusion_matrix(
    labels: list[int], preds: list[int], seed: int, fold: int, out_dir: Path | None = None
) -> None:
    """Generate and save confusion matrix plot for this fold."""
    out_dir = ARTIFACT_DIR if out_dir is None else out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import confusion_matrix

    cm = confusion_matrix(labels, preds, labels=list(range(NUM_CLASSES)))
    fig, ax = plt.subplots(figsize=(6, 5.5))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=CLASS_NAMES,
        yticklabels=CLASS_NAMES,
        ax=ax,
        square=True,
        linewidths=0.5,
    )
    ax.set_xlabel("Predicted", fontsize=11)
    ax.set_ylabel("True", fontsize=11)
    ax.set_title(f"Outer-fold Confusion Matrix (Seed {seed}, Fold {fold})", fontsize=12, fontweight="bold")
    plt.tight_layout()

    save_path = out_dir / f"confusion_matrix_seed{seed}_fold{fold}.png"
    fig.savefig(save_path, dpi=120)
    plt.close(fig)


# ─── Reports ────────────────────────────────────────────────────────────────────


def render_report(summary: dict, protocol: dict) -> str:
    lines = [
        "# ASTRA — Cross-Validation Report",
        "",
        f"Shared transformer, {protocol['folds']}-fold outer cross-validation over {len(protocol['seeds'])} seed(s) "
        f"({protocol['folds'] * len(protocol['seeds'])} outer folds), {protocol['epochs']} epochs per fold.",
        "",
        "## Protocol",
        "",
        f"- Pool: {protocol['pool_stars']} frozen train + validation stars; {protocol['excluded_test_stars']} frozen "
        "test stars excluded.",
        f"- Groups: {protocol['groups']} duplicate groups ({protocol['grouping']}); no group is split.",
        f"- Epoch selection: best epoch on an inner selection set (1/{protocol['inner_folds']} of each outer "
        "training set); the selected model is scored once on the outer fold.",
        "",
        "## Outer-fold results",
        "",
        f"- Mean outer-fold accuracy: `{summary['mean_fold_accuracy'] * 100:.2f}%` "
        f"(standard deviation over folds and seeds `{summary['std_fold_accuracy'] * 100:.2f}%`)",
        f"- Mean outer-fold macro F1: `{summary['mean_fold_macro_f1']:.4f}`",
        f"- Catalog-period / BLS-period accuracy: `{summary['mean_catalog_accuracy'] * 100:.2f}%` / "
        f"`{summary['mean_bls_accuracy'] * 100:.2f}%`",
        "",
        "| Seed | Out-of-fold accuracy | 95% CI (bootstrap over stars) | Macro F1 95% CI |",
        "|---|---:|---|---|",
    ]
    for seed, entry in summary["per_seed"].items():
        lo, hi = entry["accuracy_ci95"]
        flo, fhi = entry["macro_f1_ci95"]
        lines.append(f"| {seed} | {entry['out_of_fold_accuracy'] * 100:.2f}% | [{lo * 100:.2f}%, {hi * 100:.2f}%] "
                     f"| [{flo:.4f}, {fhi:.4f}] |")
    lines += [
        "",
        "| Class | Mean outer-fold F1 |",
        "|---|---:|",
    ]
    lines += [f"| {name} | {f1:.4f} |" for name, f1 in summary["mean_f1_per_class"].items()]
    lines += [
        "",
        f"Mean selection-set accuracy of the chosen epochs: `{summary['mean_selection_accuracy'] * 100:.2f}%`. "
        "It is the maximum over epochs on the set used for selection, so it is optimistic and is not an estimate "
        "of performance; the outer-fold numbers above are.",
        "",
        "Details: [fold_metrics.csv](fold_metrics.csv), [aggregate_metrics.json](aggregate_metrics.json).",
    ]
    return "\n".join(lines) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Test-free, grouped, nested cross-validation of the shared transformer (ADR-0062)."
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 100, 2026],
                        help="Repeat seeds (default: 42 100 2026)")
    parser.add_argument("--folds", type=int, default=5, help="Outer folds (default: 5)")
    parser.add_argument("--inner-folds", type=int, default=5,
                        help="One inner fold of each outer training set selects the epoch (default: 5, i.e. 20%%)")
    parser.add_argument("--epochs", type=int, default=50, help="Epochs per fold (default: 50)")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Bootstrap resamples for the CIs (default: 1000)")
    parser.add_argument("--data-dir", type=str, default=None,
                        help="Processed arrays (default: configured processed dir)")
    parser.add_argument("--test-ids", type=str, default=None,
                        help="Frozen test-id file to exclude (default: <configured splits dir>/test_ids.json)")
    parser.add_argument("--out-dir", type=str, default=None,
                        help="Reports and plots (default: configured output dir)")
    return parser


def main(argv: list[str] | None = None) -> None:
    from astra.console import ensure_utf8_stdio
    ensure_utf8_stdio()
    args = build_arg_parser().parse_args(argv)
    data_dir = resolve_cli_path(args.data_dir, DATA_DIR)
    out_dir = resolve_cli_path(args.out_dir, ARTIFACT_DIR)
    test_ids_path = resolve_cli_path(args.test_ids, PATHS.splits_dir / "test_ids.json")
    seeds = list(args.seeds)
    print("=" * 70)
    print(f"  ASTRA cross-validation: {args.folds} outer folds x {len(seeds)} seed(s), test stars excluded")
    print("=" * 70)

    device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
    print(f"Device: {device}")

    all_samples = scan_all_samples(data_dir)
    test_ids = read_test_ids(test_ids_path)
    samples = cv_pool(all_samples, test_ids)
    labels = np.array([s["label"] for s in samples])
    groups = duplicate_groups(samples)
    plans = plan_folds(labels, groups, seeds, args.folds, args.inner_folds)
    check_plans(plans, groups, len(samples))
    print(f"Pool: {len(samples)} stars ({len(all_samples) - len(samples)} test stars excluded), "
          f"{len(set(groups))} duplicate groups.")

    results = []
    for plan in plans:
        set_deterministic_seeds(plan.seed * 100 + plan.fold)
        (result,) = run_plans(samples, [plan], transformer_trainer(args.epochs, device, data_dir))
        save_confusion_matrix(result["labels"], result["preds"], plan.seed, plan.fold, out_dir=out_dir)
        print(f"  Seed {plan.seed} fold {plan.fold}: outer accuracy {result['accuracy']:.4f} "
              f"(epoch {result['best_epoch']} chosen on the selection set) in {result['runtime_sec']:.1f}s")
        results.append(result)

    out_dir.mkdir(parents=True, exist_ok=True)
    columns = [k for k in results[0] if k not in ("test_tic_ids", "preds", "labels")]
    with open(out_dir / "fold_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    summary = summarise(results, args.bootstrap)
    from astra import provenance

    protocol = {
        "seeds": seeds, "folds": args.folds, "inner_folds": args.inner_folds, "epochs": args.epochs,
        "pool_stars": len(samples), "excluded_test_stars": len(all_samples) - len(samples),
        "test_ids_file": str(test_ids_path), "groups": len(set(groups)),
        "grouping": "duplicate_group_id: same TIC id or within 2 arcsec (pipeline.phase6_utils)",
        "score": "outer fold, once, with the epoch chosen on the inner selection set",
        "data_dir": str(data_dir),
    }
    aggregate = {
        **summary,
        "protocol": protocol,
        "out_of_fold_predictions": [{"seed": r["seed"], "fold": r["fold"], "tic_ids": r["test_tic_ids"],
                                     "preds": r["preds"], "labels": r["labels"]} for r in results],
        "provenance": provenance.collect(
            device=str(device),
            data={"manifest_sha256": provenance.file_sha256(PATHS.phase6_root / "scientific_dataset_freeze_v2.csv"),
                  "test_ids_sha256": provenance.file_sha256(test_ids_path)},
        ),
    }
    (out_dir / "aggregate_metrics.json").write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")
    (out_dir / "statistical_report.md").write_text(render_report(summary, protocol), encoding="utf-8")
    print(f"\nMean outer-fold accuracy {summary['mean_fold_accuracy'] * 100:.2f}% -> {out_dir}")


if __name__ == "__main__":
    main()
