"""
ASTRA — baselines to report beside the model (SP-22, ADR-0062).

Every baseline is fit on the frozen train split and evaluated once on the frozen test split
(661 / 142 stars), the same split as the published HybridTransformer result.

Feature sets:
- shortcut_no_source: cadence, number of sectors (pipeline artefacts only)
- shortcut:           + period source (catalog vs BLS)
- physical:           log10 period, log10 amplitude, log10 SNR
- all:                the six above
- lightcurve:         12 statistics of the network's own inputs (z-scored flux_1000 and
                      folded_flux_1000), so no period and no amplitude

The first four are EXP-0001 (artifacts/experiments/EXP-0001-metadata-baseline.md) and are
reproduced exactly: same features, same models, same row order (numeric TIC id) and class
encoding (sorted class names). Caveat: for RR Lyrae, Cepheids and eclipsing binaries the
period is the VSX catalog period, i.e. external information; for Solar-like and Stable it
is a mostly unreliable BLS value (audit S5).

    python training/baselines.py            # all baselines -> outputs/baselines/
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from astra.config import get_paths, resolve_cli_path

SHIPPED_PROCESSED = PROJECT_ROOT / "astra-platform" / "data" / "processed"
SHIPPED_SPLIT_IDS = PROJECT_ROOT / "docs" / "engineering-log"
FEATURE_SETS = ("shortcut_no_source", "shortcut", "physical", "all", "lightcurve")
MODEL_NAMES = ("LogReg", "RandomForest")
LIGHTCURVE_FEATURES = (
    "raw_skew", "raw_kurtosis", "raw_acf_1", "raw_acf_10", "raw_acf_100", "raw_frac_beyond_2sigma",
    "raw_zero_crossing_rate", "folded_skew", "folded_kurtosis", "folded_acf_1", "folded_range", "folded_roughness",
)


@dataclass(frozen=True)
class Star:
    tic_id: str
    split: str
    astra_class: str
    cadence_type: str
    n_sectors: int
    period_source: str
    period: float
    amplitude: float
    snr: float
    directory: Path


def load_split_ids(splits_dir: Path) -> dict[str, set[str]]:
    """Frozen ids from <dir>/{split}_ids.json or the shipped <dir>/phase6_{split}_ids.json."""
    ids = {}
    for split in ("train", "val", "test"):
        for name in (f"{split}_ids.json", f"phase6_{split}_ids.json"):
            path = Path(splits_dir) / name
            if path.is_file():
                ids[split] = set(json.loads(path.read_text(encoding="utf-8")))
                break
        else:
            raise FileNotFoundError(f"No {split} id file in {splits_dir}")
    return ids


def load_stars(data_dir: Path, split_ids: dict[str, set[str]]) -> list[Star]:
    """All split stars, in numeric TIC order (the row order EXP-0001 read from the SQLite table)."""
    split_of = {tic: split for split, tics in split_ids.items() for tic in tics}
    stars = []
    for directory in sorted(Path(data_dir).glob("TIC_*"), key=lambda p: int(p.name.removeprefix("TIC_"))):
        if directory.name not in split_of:
            continue
        meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        stars.append(Star(directory.name, split_of[directory.name], meta["astra_class"], meta["cadence_type"],
                          meta["n_sectors"], meta["period_source"], meta["period"], meta["variability_amplitude"],
                          meta["snr_estimate"], directory))
    return stars


def metadata_features(star: Star, kind: str) -> list[float]:
    """EXP-0001's feature formulas, unchanged."""
    cadence = 1.0 if star.cadence_type == "short" else 0.0
    bls = 1.0 if star.period_source == "BLS" else 0.0
    physical = [np.log10(star.period), np.log10(max(star.amplitude, 1e-6)), np.log10(max(star.snr, 1e-3))]
    if kind == "shortcut_no_source":
        return [cadence, star.n_sectors]
    if kind == "shortcut":
        return [cadence, star.n_sectors, bls]
    if kind == "physical":
        return physical
    if kind == "all":
        return [cadence, star.n_sectors, bls, *physical]
    raise ValueError(f"unknown metadata feature set {kind!r}")


def _autocorrelation(values: np.ndarray, lag: int) -> float:
    a, b = values[:-lag], values[lag:]
    return 0.0 if a.std() == 0 or b.std() == 0 else float(np.corrcoef(a, b)[0, 1])


def lightcurve_features(raw: np.ndarray, folded: np.ndarray) -> list[float]:
    """Shape statistics of the z-scored network inputs; undefined statistics (flat input) become 0."""
    from scipy.stats import kurtosis, skew

    raw, folded = np.asarray(raw, dtype=np.float64), np.asarray(folded, dtype=np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # skew/kurtosis of a flat array
        values = [
            skew(raw), kurtosis(raw), _autocorrelation(raw, 1), _autocorrelation(raw, 10), _autocorrelation(raw, 100),
            float(np.mean(np.abs(raw) > 2)), float(np.mean(np.diff(np.sign(raw)) != 0)),
            skew(folded), kurtosis(folded), _autocorrelation(folded, 1), float(folded.max() - folded.min()),
            float(np.std(np.diff(folded))),
        ]
    return [float(v) for v in np.nan_to_num(np.array(values, dtype=np.float64))]


def feature_matrix(stars: list[Star], kind: str) -> np.ndarray:
    if kind == "lightcurve":
        rows = [lightcurve_features(np.load(s.directory / "flux_1000.npy"), np.load(s.directory / "folded_flux_1000.npy"))
                for s in stars]
    else:
        rows = [metadata_features(s, kind) for s in stars]
    return np.array(rows, dtype=np.float64)


def make_model(name: str):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression

    if name == "LogReg":
        return LogisticRegression(max_iter=5000)
    if name == "RandomForest":
        return RandomForestClassifier(n_estimators=500, random_state=42, min_samples_leaf=2)
    raise ValueError(f"unknown model {name!r}")


def run_baseline(stars: list[Star], kind: str, model_name: str, n_bootstrap: int = 1000, seed: int = 42) -> dict:
    """Fit on train, evaluate once on test; metrics in data.labels class order."""
    from data.labels import CLASS_NAMES
    from training.evaluate import bootstrap_ci, confusion_matrix, metrics_from_confusion

    classes = sorted({s.astra_class for s in stars})  # EXP-0001's encoding
    train = [s for s in stars if s.split == "train"]
    test = [s for s in stars if s.split == "test"]
    model = make_model(model_name)
    model.fit(feature_matrix(train, kind), [classes.index(s.astra_class) for s in train])
    predicted = [classes[i] for i in model.predict(feature_matrix(test, kind))]
    labels = np.array([CLASS_NAMES.index(s.astra_class) for s in test])
    preds = np.array([CLASS_NAMES.index(c) for c in predicted])
    cm = confusion_matrix(labels, preds)
    metrics = metrics_from_confusion(cm)
    return {
        "feature_set": kind,
        "model": model_name,
        "n_train": len(train),
        "n_test": len(test),
        "accuracy": metrics["accuracy"],
        "macro_f1": metrics["macro_f1"],
        "weighted_f1": metrics["weighted_f1"],
        "per_class_f1": {name: values["f1"] for name, values in metrics["per_class"].items()},
        "bootstrap": bootstrap_ci(labels, preds, n_resamples=n_bootstrap, seed=seed),
        "confusion_matrix": cm.tolist(),
    }


def run_all(stars: list[Star], feature_sets=FEATURE_SETS, models=MODEL_NAMES, n_bootstrap: int = 1000) -> list[dict]:
    return [run_baseline(stars, kind, name, n_bootstrap) for kind in feature_sets for name in models]


def render_markdown(results: list[dict]) -> str:
    lines = [
        "# Baselines on the frozen split",
        "",
        "Fit on the 661 frozen train stars, evaluated once on the 142 frozen test stars (`training/baselines.py`). "
        "Period-based features use the VSX catalog period for RR Lyrae, Cepheids and eclipsing binaries (external "
        "information) and a mostly unreliable BLS period for Solar-like and Stable stars.",
        "",
        "| Feature set | Model | Accuracy | 95% CI | Macro F1 | 95% CI |",
        "|---|---|---:|---|---:|---|",
    ]
    for r in results:
        acc, f1 = r["bootstrap"]["ci"]["accuracy"], r["bootstrap"]["ci"]["macro_f1"]
        lines.append(f"| {r['feature_set']} | {r['model']} | {r['accuracy'] * 100:.2f}% | "
                     f"[{acc[0] * 100:.2f}%, {acc[1] * 100:.2f}%] | {r['macro_f1']:.4f} | [{f1[0]:.4f}, {f1[1]:.4f}] |")
    return "\n".join(lines) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Baselines beside the model on the frozen split (SP-22).")
    parser.add_argument("--data-dir", default=None,
                        help=f"Processed stars (default: {SHIPPED_PROCESSED.relative_to(PROJECT_ROOT)})")
    parser.add_argument("--splits-dir", default=None,
                        help=f"Frozen split ids (default: {SHIPPED_SPLIT_IDS.relative_to(PROJECT_ROOT)})")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Bootstrap resamples for CIs (default: 1000)")
    parser.add_argument("--out-dir", default=None, help="Report directory (default: outputs/baselines)")
    return parser


def main(argv: list[str] | None = None) -> int:
    from astra import provenance
    from astra.console import ensure_utf8_stdio

    ensure_utf8_stdio()
    args = build_arg_parser().parse_args(argv)
    paths = get_paths()
    data_dir = resolve_cli_path(args.data_dir, SHIPPED_PROCESSED)
    splits_dir = resolve_cli_path(args.splits_dir, SHIPPED_SPLIT_IDS)
    out_dir = resolve_cli_path(args.out_dir, paths.output_dir / "baselines")
    stars = load_stars(data_dir, load_split_ids(splits_dir))
    results = run_all(stars, n_bootstrap=args.bootstrap)
    report = render_markdown(results)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "baselines.md").write_text(report, encoding="utf-8")
    (out_dir / "baselines.json").write_text(json.dumps({
        "results": results,
        "lightcurve_features": LIGHTCURVE_FEATURES,
        "data": {"data_dir": str(data_dir), "splits_dir": str(splits_dir)},
        "provenance": provenance.collect(seed=42, device="cpu"),
    }, indent=2) + "\n", encoding="utf-8")
    print(report)
    print(f"Reports: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
