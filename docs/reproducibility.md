# Reproducibility Guide

How to reproduce ASTRA's pipeline from a clone, and what can and cannot be reproduced today. Every command below runs against the current scripts; `tests/test_readme_commands.py` checks their flags.

> [!IMPORTANT]
> The trained weights behind the published results are **not in this repository**. You can verify the dataset and splits, train, cross-validate and evaluate new models. You can't recompute the published test metrics (78.17% accuracy, macro F1 0.7677) until the published checkpoint is recovered. See [model_recovery.md](model_recovery.md).

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python | 3.11 or 3.12 (CI runs both) |
| PyTorch | Any 2.x. CPU is enough. The published runs used PyTorch 2.12.0 on Python 3.12 with Apple MPS (`models/saved/experiment_metadata_shared.json`); CI uses 2.15.0 CPU |
| OS | Linux, macOS or Windows |

Training is not bitwise reproducible across hardware or library versions: MPS, CUDA and CPU kernels order floating-point operations differently. Seeds make runs repeatable on the same machine and software, not identical across machines. Compare runs statistically (`evaluate.py` gives bootstrap CIs), and identify models by checkpoint hash.

---

## Step 0: Clone and install

```bash
git clone https://github.com/yeshika-02/ASTRA.git
cd ASTRA
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-lock.txt   # pinned versions CI verifies (or requirements.txt for the latest allowed)
```

---

## Step 1: Verify the dataset and build the frozen layout

```bash
python pipeline/prepare_from_repo.py --verify-only   # check only
python pipeline/prepare_from_repo.py                 # build data/phase6/{processed,splits,audits}
```

This checks two things:
- the manifest `scientific_dataset_freeze_v2.csv` against its published SHA256 `f99b4b06…bf58`;
- every one of the 944 stars × 5 files against the per-file SHA256 recorded in that manifest.

It then rebuilds the frozen splits and recomputes the split hash (`ebcdc44c…`), and runs the dataset audit.

`f99b4b06…` is the hash of the manifest file itself. An earlier version of this guide hashed the concatenated arrays and compared the result with it, a check that could never pass.

---

## Step 2: Rebuild the dataset from the archives (optional, historical)

The steps that built the dataset query VizieR and MAST over the network. Preprocessing needs the raw light curves, which aren't shipped. To work with the frozen dataset, Step 1 is enough.

```bash
python pipeline/build_catalog.py
python pipeline/batch_process.py
python pipeline/dataset_audit.py
```

---

## Step 3: Verify split integrity by hand (optional)

`prepare_from_repo.py` already does this.

```bash
python -c "
import hashlib, pathlib
expected = {
    'train': '5a9bf6c6ad40757a52d0f4a044626e82a4876839b175f5070fb28834c815eed0',
    'val':   'c733ab95c4a22ebc29ca123b2e923c8b8069933ccdff2e9f03a3fdc882f761b3',
    'test':  '2b62970d610f66f12711b6d9594305b33961a04d17c48807bd6123562350f4c0',
}
for split, want in expected.items():
    path = pathlib.Path(f'docs/engineering-log/phase6_{split}_ids.json')
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    print('OK  ' if got == want else 'FAIL', split)
"
```

---

## Step 4: Train

```bash
# HybridTransformer (shared), the production configuration
python training/train_transformer.py --variant shared --seed 42 --out-dir outputs/run_shared

# CNN dual-branch baseline
python training/train_cnn.py --use-folded --augment --seed 42 --tag dual_aug --out-dir outputs/run_cnn
```

Without `--out-dir`, runs go to `outputs/runs/`. `models/saved/` holds the published training records and is never written to by default.

Each run writes `experiment_metadata_<tag>.json`, which records:
- the seed, data hashes and checkpoint SHA256;
- a `provenance` block: git commit and dirty flag, Python/platform/package versions, the split files used, and whether they were the frozen ones.

A retrained checkpoint is a new model: its hash won't match the published one.

---

## Step 5: Evaluate

```bash
python training/evaluate.py --checkpoint outputs/run_shared/best_star_transformer_shared.pt \
    --split test --out-dir outputs/evaluation
```

The output includes:
- accuracy, macro and weighted F1, and 95% percentile bootstrap CIs (1,000 resamples of the 142 test stars, seed 42);
- per-class precision, recall and F1, and the confusion matrix;
- NLL, Brier and ECE;
- per-star predictions and provenance, written to JSON and Markdown.

The checkpoint's SHA256 is compared with [`models/published_weights.json`](../models/published_weights.json). Only a verified published checkpoint is compared with the published numbers.

**With the published checkpoint** (once recovered):

```bash
python training/verify_weights.py --require best_star_transformer_shared.pt
python training/evaluate.py --checkpoint models/saved/best_star_transformer_shared.pt \
    --temperature-file models/saved/optimal_temperature_transformer_shared.txt --require-published
```

Expected:
- 111/142 correct (78.17%), macro F1 0.7677, weighted F1 0.7784;
- the confusion matrix in `models/saved/test_confusion_matrix_transformer_shared.png`.

The metric code reproduces these numbers from that matrix (`tests/test_evaluate.py`).

---

## Step 6: Cross-validation

```bash
# 5 folds x 3 seeds = 15 runs of 50 epochs (hours on CPU)
python training/cross_validate.py --seeds 42 100 2026 --folds 5 --epochs 50 --out-dir outputs/cv
```

Writes `fold_metrics.csv`, `aggregate_metrics.json` (with protocol and provenance) and `statistical_report.md`.

> [!NOTE]
> The pool is the 802 frozen train + validation stars; the 142 test stars are excluded (`--test-ids`). Duplicate groups never straddle folds, the epoch is chosen on an inner selection set (`--inner-folds`), and each outer fold is scored once. The report gives the outer-fold mean and a bootstrap CI per seed ([ADR-0062](../artifacts/decisions/ADR-0062-evaluation-protocol.md)). Earlier versions of this script drew folds from all 944 stars and scored each fold with its own best epoch.

---

## Step 7: Calibration

```bash
python training/calibration.py --checkpoint outputs/run_shared/best_star_transformer_shared.pt \
    --temperature-out outputs/run_shared/optimal_temperature.txt --out-dir outputs/calibration
```

This fits a single temperature by minimising validation NLL.

The published temperature (T = 1.257665) is `models/saved/optimal_temperature_transformer_shared.txt`; its hash is in the manifest. The repository holds two other temperatures (1.258631 in `optimal_temperature.txt`, and the 1.2944 fallback in `uncertainty.py`), which sprint task SP-18 reconciles.

---

## Step 8: Uncertainty (MC Dropout)

```bash
python training/uncertainty.py --checkpoint outputs/run_shared/best_star_transformer_shared.pt \
    --temperature-file outputs/run_shared/optimal_temperature.txt --n-passes 30 --out-dir outputs/uncertainty
```

---

## Step 9: Export

```bash
python training/export_model.py --checkpoint outputs/run_shared/best_star_transformer_shared.pt \
    --out-dir outputs/export
```

`export_model.py` exports TorchScript and ONNX, checks both against PyTorch, and benchmarks CPU latency.

`python training/export_explainability_model.py` builds the ONNX model with attention outputs. It reads `best_star_transformer_shared.pt` from the models directory (`models/saved`, or `ASTRA_MODELS_DIR`).

---

## Tests

```bash
python -m pytest tests/
```

This covers the dataset and split checks, the training and evaluation CLIs end to end on small synthetic data and on the real arrays, published-hash consistency, and the README and guide commands.

---

## Records to check

| File | What it pins |
|---|---|
| `astra-platform/data/scientific_dataset_freeze_v2.csv` | SHA256 of every shipped array and metadata file (the manifest itself hashes to `f99b4b06…`) |
| `docs/engineering-log/phase6_*_ids.json` | The frozen split (`ebcdc44c…`) |
| `models/published_weights.json` | SHA256 of every published checkpoint, ONNX file and temperature |
| `models/saved/experiment_metadata_*.json` | Seed, data hashes and checkpoint hash of each published run |
| `outputs/.../experiment_metadata_*.json` (your runs) | The same, plus the `provenance` block |
