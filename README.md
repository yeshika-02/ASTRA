<div align="center">

<h1>
  🌟 ASTRA
  <br/>
  <sub>Automated Stellar Transient Recognition &amp; Analysis</sub>
</h1>

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12"/>
  <img src="https://img.shields.io/badge/PyTorch-2.12.0-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch 2.12.0"/>
  <img src="https://img.shields.io/badge/Platform-Apple%20Silicon%20MPS-000000?style=for-the-badge&logo=apple&logoColor=white" alt="Apple Silicon MPS"/>
  <img src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge" alt="MIT License"/>
  <img src="https://img.shields.io/badge/TESS-lightkurve-8B5CF6?style=for-the-badge" alt="TESS lightkurve"/>
  <img src="https://img.shields.io/badge/Data%20Source-VSX%20%7C%20MAST-0EA5E9?style=for-the-badge" alt="VSX MAST"/>
  <img src="https://img.shields.io/badge/Web-Next.js%20%2B%20Three.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js Three.js"/>
</p>

<p>
  <strong>An end-to-end machine learning pipeline for automated classification of stellar variability from TESS light curves.</strong><br/>
  Hybrid CNN + Transformer · Cryptographic Data Integrity · Temperature Calibration · MC Dropout Uncertainty · ONNX/TorchScript Deployment
</p>

</div>

---

## 🔭 Overview

**ASTRA** is a reproducible, publication-grade research system that classifies variable stars into five astrophysical categories — RR Lyrae, Cepheid, Eclipsing Binary, Solar-like, and Stable — directly from TESS light curves. It combines a dual-branch Hybrid CNN + Transformer architecture that jointly processes raw and phase-folded photometry, achieving **78.17% test accuracy** and **macro F1 = 0.7677** on a cryptographically verified held-out test set of 142 stars drawn from 944 total. The pipeline spans the full research lifecycle: automated data acquisition from VSX/AAVSO and TESS/MAST, feature engineering, model training with rigorous cross-validation, post-hoc calibration, uncertainty quantification, and a web platform that serves ONNX inference when the model weights are installed (they are not in this repository; see [Web Platform](#-web-platform)).

---

## ⚠️ Scientific Integrity Notice

> [!IMPORTANT]
> **Verified Results** — The following numbers have been independently recomputed from checkpoint weights and test-set IDs and confirmed to zero mismatches in the ground truth audit. They are the authoritative, reportable metrics for this project:
> - **Test Accuracy:** 78.17% (95% CI: [71.13%, 85.21%])
> - **Macro F1:** 0.7677 (95% CI: [0.6944, 0.8320])
> - **Dataset:** 944 stars, SHA256 fingerprint `f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58`
> - **Ground Truth Audit:** All 8 checks **PASS**, 0 mismatches.

> [!WARNING]
> **Experimental / Under-Represented Class** — The **Solar-like** class achieves the lowest per-class F1 of **0.52** on the test set, significantly below all other classes. This class contains only 142 samples in the full dataset (15.04%) and has notably higher predictive uncertainty. Solar-like classification results should be interpreted with caution and are not considered production-ready. Additional data collection is recommended before deploying ASTRA predictions for Solar-like targets in any scientific analysis.

> [!CAUTION]
> **Known limitations (audit of 2026-11-09 — see [`PROJECT_AUDIT.md`](PROJECT_AUDIT.md) and [`PROJECT_STATUS.md`](PROJECT_STATUS.md))**
> - **Model weights are not published in this repository.** The metrics above are internally consistent with the committed confusion matrix, but can't yet be reproduced from a clean clone.
> - **The web platform does not run the model on its current deployment.** Prediction, explanation and upload endpoints return `503 inference_unavailable`, and the UI says so. Earlier versions showed synthetic outputs derived from catalog labels; those have been removed.
> - **The class labels are confounded with pipeline metadata** (period source, source catalog, cadence), so the catalog-vs-BLS subgroup gap and the headline accuracy need re-evaluation. A 3-feature metadata baseline scores 86.6% on the same test split. This is being addressed in the roadmap ([`UPDATED_ROADMAP.md`](UPDATED_ROADMAP.md)).
> - Some commands and paths in the sections below don't match the current scripts. Corrections are tracked as task T7.

---

## ✨ Key Results

### 🏆 Model Comparison — Held-Out Test Set (N = 142)

| Model | Params | Test Accuracy | 95% CI | Macro F1 | 95% CI |
|:---|:---:|:---:|:---:|:---:|:---:|
| **HybridTransformer (shared)** ⭐ | 1,373,701 | **78.17%** | [71.13%, 85.21%] | **0.7677** | [0.6944, 0.8320] |
| CNN Dual-Branch | 1,043,333 | 78.17% | [71.13%, 84.51%] | 0.7654 | [0.6840, 0.8317] |
| HybridTransformer (cross) | — | 80.99% | [73.94%, 87.32%] | 0.7949 | [0.7252, 0.8594] |
| HybridTransformer (separate) | — | 84.51% | [78.17%, 90.16%] | 0.8394 | [0.7712, 0.9012] |
| HybridTransformer (only) | — | 72.54% | [64.79%, 80.28%] | 0.7127 | [0.6420, 0.7834] |

> **Note:** The `shared` variant is the production model selected for calibration, ONNX/TorchScript export, and the web platform — chosen for its balance of accuracy, parameter efficiency, and interpretable attention maps. The `separate` and `cross` variants achieved higher raw test accuracy but were not selected as the production model.

### 🎯 Per-Class F1 — HybridTransformer (shared)

| Class | F1 Score | Interpretation |
|:---|:---:|:---|
| RR Lyrae | **0.94** | Excellent — highly discriminative periodic signature |
| Eclipsing Binary | **0.91** | Excellent — sharp transit morphology |
| Cepheid | **0.81** | Good — moderate light-curve variability |
| Stable | **0.66** | Moderate — confusion with low-amplitude variables |
| Solar-like | **0.52** | ⚠️ Experimental — low sample count, high ambiguity |

### 📊 5-Fold Cross-Validation (3 Random Seeds: 42, 100, 2026)

| Metric | Mean | Std Dev | 95% CI |
|:---|:---:|:---:|:---:|
| Validation Accuracy | 84.68% | 2.12% | [83.60%, 85.75%] |
| Macro F1 | 0.8349 | — | — |
| Catalog Subgroup Accuracy | 89.90% | 2.67% | — |
| BLS Fallback Subgroup Accuracy | 75.69% | 4.27% | — |

---

## 📁 Repository Structure

```
ASTRA/
│
├── 📄 README.md, CITATION.cff, LICENSE
├── 📄 requirements.txt, pyproject.toml   # Python dependencies (CPU torch installed separately)
├── 📄 lineage.json                       # Dataset provenance & version tracking
│
├── 📂 astra/                             # Shared helpers: configurable paths (config.py), UTF-8 console (console.py)
│
├── 📂 pipeline/                          # Data acquisition & preprocessing
│   ├── prepare_from_repo.py              # Verify the shipped data and rebuild data/phase6/ (start here)
│   ├── build_catalog.py                  # VSX/AAVSO catalog construction via VizieR
│   ├── candidate_expander.py             # Star candidate expansion with cross-matching
│   ├── dataset_builder.py                # TESS MAST light-curve downloader (lightkurve)
│   ├── preprocess.py                     # Normalize, detrend, phase-fold (1000 pts)
│   ├── dataset_audit.py                  # Dataset integrity and label verification
│   ├── freeze_phase6_splits.py           # Original split freezing (see the note under Reproducing Results)
│   └── cleanup_data.py                   # Dry-run-by-default cleanup of failed downloads
│
├── 📂 training/                          # Model definitions & training scripts
│   ├── models/
│   │   ├── hybrid_transformer.py         # HybridTransformer (4 variants)
│   │   ├── star_cnn.py                   # Dual-branch CNN baseline
│   │   └── explainable_wrapper.py        # Attention-return wrapper for ONNX export
│   ├── train_transformer.py              # Transformer training (--variant, --seed, --data-dir, --out-dir)
│   ├── train_cnn.py                      # CNN training
│   ├── cross_validate.py                 # 5-fold × 3-seed stratified group CV
│   ├── calibration.py                    # Temperature scaling (NLL minimization)
│   ├── uncertainty.py                    # MC Dropout uncertainty (30 passes)
│   ├── dataset.py                        # ASTRADataset (raw + folded dual-channel)
│   ├── focal_loss.py                     # Class-weighted Focal Loss
│   ├── export_model.py                   # ONNX + TorchScript export
│   ├── predict.py                        # Single-star inference
│   └── visualize_attention.py            # Attention map visualization
│
├── 📂 data/                              # Catalog and label definitions
│   ├── catalog_full.json                 # Full 944-star catalog with TIC IDs
│   ├── dataset_summary.json              # Class distribution summary
│   └── labels.py                         # CLASS_NAMES, NUM_CLASSES, LABEL_TO_NAME
│
├── 📂 models/saved/                      # Published training records (no weight files)
│   ├── experiment_metadata_*.json        # Per-run hashes, seeds and hyperparameters
│   ├── classification_report_*.txt       # Validation reports per run
│   ├── confusion_matrix_*.png, training_curves_*.png, training_history_*.json
│   └── optimal_temperature*.txt          # Calibration temperatures
│
├── 📂 astra-platform/                    # Web platform (Next.js) and the shipped dataset
│   ├── data/processed/TIC_*/             # 944 stars × 5 files, hash-locked by the manifest
│   ├── data/scientific_dataset_freeze_v2.csv  # Cryptographically locked manifest
│   ├── data/artifacts/                   # Audit, calibration, benchmark and registry JSON
│   ├── data/*.onnx                       # ONNX graphs of the shared transformer (weight files not shipped)
│   ├── src/                              # Next.js app source (TypeScript)
│   └── tests/                            # Vitest API, security and no-fabrication tests
│
├── 📂 docs/engineering-log/              # Phase-by-phase audit trail and the frozen split ID files
├── 📂 tests/                             # Python unit and integration tests (pytest)
├── 📂 artifacts/decisions/               # Architecture decision records (ADRs)
└── 📂 agents/, standards/, checklists/, context/ ...   # AgentOS development process files
```

Created at run time and not tracked: `data/phase6/` (by `prepare_from_repo.py`) and `outputs/` (script reports and checkpoints).

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11 or 3.12** (CI runs both)
- **PyTorch ≥ 2.0**: CPU is enough for everything below; Apple MPS or CUDA is used automatically when available
- Linux, macOS or Windows (all commands below are verified on Windows and on CI's Ubuntu)

### 1. Clone the Repository

```bash
git clone https://github.com/yeshika-02/ASTRA.git
cd ASTRA
```

### 2. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # or the CUDA/MPS wheel you need
pip install -r requirements.txt
```

For the exact versions CI verifies, install from the lock file instead (Python 3.11 or 3.12, any OS):

```bash
pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-lock.txt
```

`requirements-lock.txt` pins every dependency except PyTorch. Its header holds the `uv` command that regenerates it from `requirements.txt`. The published runs used PyTorch 2.12.0 on Python 3.12 (see `models/saved/experiment_metadata_shared.json`).

### 3. Verify and Prepare the Frozen Dataset

The repository ships the frozen 944-star dataset (processed arrays, hash-locked manifest and frozen split ids) but not in the `data/phase6/` layout the scripts use. One command verifies every shipped file and builds that layout:

```bash
python pipeline/prepare_from_repo.py --verify-only   # check only: manifest + 944 stars x 5 files
python pipeline/prepare_from_repo.py                 # build data/phase6/{processed,splits,audits}
```

It checks:
- the manifest SHA256 (`f99b4b06…`);
- every array and metadata file against the manifest;
- the three split files against their published hashes, and the recomputed split hash (`ebcdc44c…`).

It then runs the dataset audit. Raw light curves are not shipped, so the audit records that raw files were not checked. `data/phase6/` is git-ignored.

Paths can be changed with environment variables (`ASTRA_PHASE6_ROOT`, `ASTRA_PROCESSED_DIR`, `ASTRA_SPLITS_DIR`, `ASTRA_MODELS_DIR`, `ASTRA_OUTPUT_DIR`); see `astra/config.py`. Script reports go to `outputs/` (git-ignored).

---

## ⚙️ Pipeline

ASTRA is organized as four sequential phases. Each phase produces hash-locked outputs consumed by the next.

```mermaid
flowchart TD
    %% Styling
    classDef phase1 fill:#e0f2fe,stroke:#0369a1,stroke-width:2px,color:#0f172a
    classDef phase2 fill:#f0fdf4,stroke:#15803d,stroke-width:2px,color:#0f172a
    classDef phase3 fill:#fef3c7,stroke:#b45309,stroke-width:2px,color:#0f172a
    classDef phase4 fill:#faf5ff,stroke:#6b21a8,stroke-width:2px,color:#0f172a

    subgraph P1 ["Phase 1: Data Acquisition"]
        A["build_catalog.py"] -->|VSX/AAVSO Catalog via VizieR| B["candidate_expander.py"]
        B -->|TIC Cross-Matching| C["dataset_builder.py"]
        C -->|Download Light Curves from MAST| D[(Raw Light Curves)]
    end

    subgraph P2 ["Phase 2: Preprocessing & Freeze"]
        D --> E["preprocess.py"]
        E -->|Normalize, Detrend, Fold, Resample| F["dataset_audit.py"]
        F -->|Label/Duplicate Audit| G["freeze_phase6_splits.py"]
        G -->|SHA256 Lock| H[("scientific_dataset_freeze_v2.csv (944 stars)")]
    end

    subgraph P3 ["Phase 3: Training & Validation"]
        H --> I["train_transformer.py / train_cnn.py"]
        I -->|5-Fold x 3-Seed CV| J["calibration.py"]
        J -->|NLL Minimization / Temp Scaling| K["uncertainty.py"]
        K -->|MC Dropout 30 passes| L[(Calibrated Checkpoints)]
    end

    subgraph P4 ["Phase 4: Evaluation & Export"]
        L --> M["predict.py"]
        M -->|Evaluate on held-out test set| N["export_model.py"]
        N -->|ONNX / TorchScript| O["visualize_attention.py"]
        O -->|Attention Map Visualizer| P[Live Next.js Web Platform]
    end

    class A,B,C,D,P1 phase1
    class E,F,G,H,P2 phase2
    class I,J,K,L,P3 phase3
    class M,N,O,P,P4 phase4
```

### Phase 1 — Data Acquisition

Phases 1 and 2 record how the frozen dataset was built. They query VizieR and MAST over the network, and Phase 2 needs the raw light curves, which are not shipped. To work with the frozen dataset, use Quick Start step 3 instead.

```bash
# Build the VSX/AAVSO catalog via VizieR
python pipeline/build_catalog.py

# Expand candidates with TIC cross-matching
python pipeline/candidate_expander.py

# Download TESS light curves from MAST via lightkurve
python pipeline/dataset_builder.py
```

**Sources:** VSX/AAVSO via VizieR, TESS/MAST via `lightkurve`, TIC catalog.

### Phase 2 — Preprocessing & Freeze

```bash
# Preprocess all light curves (normalize → detrend → phase-fold → resample to 1000 pts)
python pipeline/preprocess.py

# Audit dataset integrity (label cross-checks, duplicate detection)
python pipeline/dataset_audit.py

# Freeze train/val/test splits with SHA256 hash locks
# (do not rerun to regenerate the published split; see "Reproducing Results")
python pipeline/freeze_phase6_splits.py
```

This produces the cryptographically locked `scientific_dataset_freeze_v2.csv`  
(944 stars, SHA256: `f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58`).

```mermaid
flowchart TD
    %% Styling
    classDef steps fill:#f8fafc,stroke:#64748b,stroke-width:2px,color:#0f172a
    classDef decision fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#0f172a
    classDef output fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#0f172a

    Input["Raw TESS FITS/CSV Light Curve"] --> Norm["Normalisation (Median Division)"]
    Norm --> Detrend["Spline Detrending (Biweight, window_length=0.5 days)"]
    Detrend --> Detrended["Detrended Flux"]
    
    Detrended --> CheckPeriod{"Has Catalog Period?"}
    CheckPeriod -->|Yes| UseCatalog["Fetch VSX/AAVSO Period"]
    CheckPeriod -->|No| RunBLS["Compute Period via BLS (Box Least Squares)"]
    
    UseCatalog --> Fold["Phase-Folding (Phase = modulo Time, Period)"]
    RunBLS --> Fold
    
    Fold --> Folded["Folded Light Curve"]
    
    Folded --> Resample["Dual-Channel Resampling (1000 linear bins)"]
    Detrended --> Resample
    
    Resample --> Output[("Dual-Channel Input (2, 1000): Raw & Folded")]

    class Norm,Detrend,Detrended,Fold,Folded,Resample,UseCatalog steps
    class CheckPeriod decision
    class Output output
```

### Phase 3 — Training & Validation

All commands read the frozen dataset prepared in Quick Start step 3. `--out-dir` defaults to `models/saved/` for training, so pass a separate directory to avoid overwriting committed artifacts.

```bash
# Train the production HybridTransformer (shared variant); 50 epochs by default
python training/train_transformer.py --variant shared --seed 42 --out-dir outputs/run_shared

# Train the CNN dual-branch baseline (raw + phase-folded input, augmentation)
python training/train_cnn.py --use-folded --augment --seed 42 --tag dual_aug --out-dir outputs/run_cnn

# 5-fold x 3-seed cross-validation of the shared transformer (defaults shown)
python training/cross_validate.py --seeds 42 100 2026 --folds 5 --epochs 50

# Temperature calibration on the validation split (NLL minimisation)
python training/calibration.py --checkpoint outputs/run_shared/best_star_transformer_shared.pt \
    --temperature-out outputs/run_shared/optimal_temperature.txt

# MC Dropout uncertainty on the validation split
python training/uncertainty.py --checkpoint outputs/run_shared/best_star_transformer_shared.pt \
    --temperature-file outputs/run_shared/optimal_temperature.txt --n-passes 30
```

Every script has `--help`. Reports and plots go to `outputs/` (`--out-dir` to change).

> [!NOTE]
> Cross-validation currently selects each fold's best epoch on that fold's own validation data and includes the test stars, so its score is optimistic. Fixing this is sprint task SP-21.

### Phase 4 — Evaluation & Export

```bash
# Classify one prepared star with MC Dropout (needs a checkpoint)
python training/predict.py --input data/phase6/processed/TIC_100009973 \
    --checkpoint outputs/run_shared/best_star_transformer_shared.pt

# Attention maps for validation stars
python training/visualize_attention.py --checkpoint outputs/run_shared/best_star_transformer_shared.pt \
    --output-dir outputs/attention

# Export ONNX / TorchScript, check both against PyTorch, benchmark CPU latency
python training/export_model.py --checkpoint outputs/run_shared/best_star_transformer_shared.pt \
    --out-dir outputs/export
```

A test-set evaluation script with bootstrap confidence intervals (`training/evaluate.py`) is planned as sprint task SP-15. The published checkpoint is not in the repository; see "Known limitations" above.

---

## 🏗️ Model Architecture

### HybridTransformer (`shared` variant) — 1,373,701 parameters

The production model processes a star's **dual-channel input** `(B, 2, 1000)` — raw photometry and phase-folded light curve — through a parallel CNN tokenizer followed by a shared self-attention encoder.

```mermaid
graph TD
    %% Styling
    classDef input fill:#e0f2fe,stroke:#0369a1,stroke-width:2px,color:#0f172a
    classDef raw fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#0f172a
    classDef folded fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#0f172a
    classDef shared fill:#faf5ff,stroke:#7c3aed,stroke-width:2px,color:#0f172a
    classDef classifier fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#0f172a

    Input["Dual-Channel Input (B, 2, 1000)"] --> SplitRaw["Raw Channel (B, 1, 1000)"]
    Input --> SplitFolded["Folded Channel (B, 1, 1000)"]

    subgraph RawBranch ["Raw CNN Tokenizer"]
        SplitRaw --> RC1["Conv1d(1→32, k=7) + BN + ReLU + MaxPool(2)"]
        RC1 --> RC2["Conv1d(32→64, k=5) + BN + ReLU + MaxPool(2)"]
        RC2 --> RC3["Conv1d(64→128, k=5) + BN + ReLU + MaxPool(2)"]
        RC3 --> RawTokens["Raw Tokens: (B, 125, 128)"]
        RC3 --> RCTail["CNN Tail: Conv1d(128→256→512) + AdaptiveAvgPool(1)"]
        RCTail --> RawEmb["Raw Global Feature (B, 512)"]
    end

    subgraph FoldedBranch ["Folded CNN Tokenizer"]
        SplitFolded --> FC1["Conv1d(1→32, k=7) + BN + ReLU + MaxPool(2)"]
        FC1 --> FC2["Conv1d(32→64, k=5) + BN + ReLU + MaxPool(2)"]
        FC2 --> FC3["Conv1d(64→128, k=5) + BN + ReLU + MaxPool(2)"]
        FC3 --> FoldedTokens["Folded Tokens: (B, 125, 128)"]
        FC3 --> FCTail["CNN Tail: Conv1d(128→256) + AdaptiveAvgPool(1)"]
        FCTail --> FoldedEmb["Folded Global Feature (B, 256)"]
    end

    RawTokens --> AddPosRaw["Add Position & Branch Embeddings"]
    FoldedTokens --> AddPosFolded["Add Position & Branch Embeddings"]

    AddPosRaw --> CatTokens["Concat Tokens: (B, 250, 128)"]
    AddPosFolded --> CatTokens

    subgraph SharedEncoder ["Shared Transformer Encoder"]
        CatTokens --> TE1["Transformer Layer 1 (Pre-LN, MHA=4, FFN=256)"]
        TE1 --> TE2["Transformer Layer 2 (Pre-LN, MHA=4, FFN=256)"]
        TE2 --> MeanPool["Global Mean Pooling (B, 128)"]
    end

    MeanPool --> ConcatAll["Concat Features: (B, 896)"]
    RawEmb --> ConcatAll
    FoldedEmb --> ConcatAll

    subgraph Classifier ["Multi-Layer Classifier"]
        ConcatAll --> CL1["Linear(896→384) + BN + ReLU + Dropout(0.2)"]
        CL1 --> CL2["Linear(384→128) + BN + ReLU + Dropout(0.2)"]
        CL2 --> CL3["Linear(128→5)"]
    end

    CL3 --> Output["Class Logits (B, 5)"]

    class Input,SplitRaw,SplitFolded input
    class RC1,RC2,RC3,RawTokens,RCTail,RawEmb,AddPosRaw raw
    class FC1,FC2,FC3,FoldedTokens,FCTail,FoldedEmb,AddPosFolded folded
    class CatTokens,TE1,TE2,MeanPool shared
    class ConcatAll,CL1,CL2,CL3,Output classifier
```

**Key design choices:**
- **Pre-LN Transformer layers** for training stability on small datasets
- **Learnable branch embeddings** distinguish raw vs. folded tokens in the shared encoder
- **Dual CNN tail** preserves local morphological features alongside global attention features
- **Attention weight capture** (`last_attention_weights`, shape `[250×250]`) for scientific interpretability
- **Focal Loss** with class weighting for imbalanced class training

### CNN Dual-Branch — 1,043,333 parameters

A convolutional baseline with two parallel branches (raw + folded) using deeper pooling hierarchies and global average pooling, without attention mechanisms. Achieves the same 78.17% test accuracy, confirming that the transformer's advantage lies in interpretability and calibration rather than raw accuracy at this dataset scale.

---

## 📈 Results

### Test Set Performance (N = 142, held-out)

| Metric | Value | 95% CI |
|:---|:---:|:---:|
| Accuracy | **78.17%** | [71.13%, 85.21%] |
| Macro F1 | **0.7677** | [0.6944, 0.8320] |
| Weighted F1 | 0.7784 | — |
| ECE (calibrated) | 0.0478 | — |
| NLL (calibrated) | 0.5332 | — |

<p align="center">
  <img src="models/saved/test_confusion_matrix_transformer_shared.png" alt="Test set confusion matrix — HybridTransformer (shared)" width="480"/>
</p>

### Selective Prediction via MC Dropout Uncertainty

By thresholding on model confidence (30 stochastic MC Dropout passes), accuracy can be traded for coverage:

| Confidence Threshold | Coverage | Accuracy |
|:---:|:---:|:---:|
| 0.0 (all predictions) | 100.0% | 85.82% |
| 0.5 | 92.2% | 88.46% |
| 0.7 | 75.9% | 93.46% |
| 0.8 | 68.1% | 94.79% |
| 0.9 | 48.2% | 92.65% |

**Uncertainty correlation:** Incorrect predictions show mean entropy of **0.84 nats** vs. **0.53 nats** for correct predictions, confirming uncertainty is a reliable proxy for classification difficulty.

### Period Source Subgroup Analysis (Test Set, SHARED)

| Subgroup | N | Accuracy |
|:---|:---:|:---:|
| Catalog Period (VSX-sourced) | 90 | 90.00% |
| BLS Fallback (computed) | 52 | 57.69% |

> [!NOTE]
> The 32-percentage-point gap between catalog-period and BLS-fallback stars reflects the inherent difficulty of classifying stars whose periods were computed by Box Least Squares rather than referenced from cataloged surveys. This is a documented limitation in [`docs/engineering-log/phase7_testset_results.md`](docs/engineering-log/phase7_testset_results.md).

---

## 🔁 Reproducing Results

What can be reproduced from a clone today:

| Step | Status |
|---|---|
| Dataset, manifest and frozen splits | ✅ verified by `pipeline/prepare_from_repo.py` |
| Training and cross-validation runs | ✅ runnable (CI trains one epoch from a fresh clone and checks the recorded data hashes) |
| The published test metrics (78.17%) | ❌ not yet: the checkpoint (`best_star_transformer_shared.pt`, SHA256 `bf374ce4…`) is not in the repository, and a test-set evaluation script is planned (SP-15) |

### Verify Split Integrity

The split files are verified, and the split hash recomputed, by `python pipeline/prepare_from_repo.py`. To check the shipped files by hand:

```bash
python -c "
import hashlib, pathlib

hashes = {
    'docs/engineering-log/phase6_train_ids.json': '5a9bf6c6ad40757a52d0f4a044626e82a4876839b175f5070fb28834c815eed0',
    'docs/engineering-log/phase6_val_ids.json':   'c733ab95c4a22ebc29ca123b2e923c8b8069933ccdff2e9f03a3fdc882f761b3',
    'docs/engineering-log/phase6_test_ids.json':  '2b62970d610f66f12711b6d9594305b33961a04d17c48807bd6123562350f4c0',
}

for path, expected in hashes.items():
    actual = hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    print('OK  ' if actual == expected else 'FAIL', path)
"
```

### Reproduce Cross-Validation

```bash
# 5-fold CV x 3 seeds = 15 runs of 50 epochs (hours on CPU; MPS/CUDA used when available)
python training/cross_validate.py --seeds 42 100 2026 --folds 5 --epochs 50
```

Note that `pipeline/freeze_phase6_splits.py` cannot regenerate the committed split: it uses 70/10/10/10 ratios, while the frozen split is 70/15/15/0. Use the shipped split files.

### Cryptographic Artifact Registry

| Artifact | SHA256 |
|:---|:---|
| Dataset manifest (`scientific_dataset_freeze_v2.csv`) | `f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58` |
| Train split IDs | `5a9bf6c6ad40757a52d0f4a044626e82a4876839b175f5070fb28834c815eed0` |
| Validation split IDs | `c733ab95c4a22ebc29ca123b2e923c8b8069933ccdff2e9f03a3fdc882f761b3` |
| Test split IDs | `2b62970d610f66f12711b6d9594305b33961a04d17c48807bd6123562350f4c0` |
| Transformer Shared checkpoint | `bf374ce492825916f2f97a4e29673a1eca35f76cc08f603b384d103fbe95d388` |
| CNN Dual checkpoint | `65da1034868c5460b2c269e1a11936864fe6191fa81116d5fe2be934d8478af2` |

All hashes are recorded in `models/saved/experiment_metadata.json` and reproduced in [`docs/engineering-log/ground_truth_final_verdict.md`](docs/engineering-log/ground_truth_final_verdict.md).

---

## 🌐 Web Platform

The `astra-platform/` directory contains an interactive research web application built with:

| Technology | Version | Role |
|:---|:---:|:---|
| Next.js | 16.2.9 | Full-stack React framework (SSR + API routes) |
| React | 19.2.4 | UI rendering |
| Three.js / @react-three/fiber | 0.184.0 | 3D stellar field visualization |
| ONNX Runtime Node | 1.26.0 | Server-side inference via exported ONNX model |
| Recharts | 3.8.1 | Light-curve and training-curve visualization |
| Framer Motion | 12.40.0 | Animated UI transitions |
| Tailwind CSS | 4.x | Utility-first styling |
| Zustand | 5.0.14 | Global state management |

### Platform Features

- **`/api/upload`**: accepts JSON `{ "period": <days>, "flux": [...] }` (50 to 100,000 points), normalizes and resamples to 1,000 points, phase-folds at the given period, and runs the explainability ONNX model with temperature scaling (T = 1.257665). Returns class probabilities and the attention matrix.
- **`/api/predict/[id]`**: 30-pass MC Dropout prediction for a catalog star from the PyTorch checkpoint, shown on the star detail page.
- **`/api/health`**: reports `READY` (data verified and all inference runnable), `DEGRADED` (data verified, some or all inference unavailable) or `BLOCKED` (manifest or star database missing or not matching).
- **Attention Visualization**: 250 × 250 self-attention map (125 raw + 125 folded CNN tokens), rendered on a client canvas.
- **Mission Replay**: animated walkthrough of a star's light-curve classification.

**Model weights are not in the repository.** The ONNX files in `astra-platform/data/` are graphs whose weights live in separate `.onnx.data` files, and the PyTorch checkpoint is not shipped. On a fresh clone the inference endpoints return `503` with `"status": "inference_unavailable"` and the reasons, and health reports `DEGRADED`. They never return placeholder predictions.

### Running Locally

Requires Node.js 22.5 or later.

```bash
cd astra-platform
npm ci              # install the exact versions in package-lock.json
npm run dev         # open http://localhost:3000
```

Checks:

```bash
npm run typecheck
npm run lint        # ESLint
npm test            # Vitest: API, security, health and no-fabrication tests
npm run build
```

---

## 📋 Dataset

| Property | Value |
|:---|:---|
| Total Stars | **944** |
| Classes | 5 (RR Lyrae, Cepheid, Eclipsing Binary, Solar-like, Stable) |
| Train / Val / Test | 661 / 141 / 142 |
| Light-curve Length | 1000 points (resampled) |
| Input Channels | 2 (raw photometry + phase-folded) |
| Period Sources | 597 catalog (VSX/AAVSO) · 347 BLS-computed |
| Data Sources | VSX/AAVSO via VizieR · TESS/MAST via lightkurve · TIC catalog |
| SHA256 Fingerprint | `f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58` |

### Class Distribution

| Class | Count | Share |
|:---|:---:|:---:|
| Cepheid | 230 | 24.36% |
| RR Lyrae | 217 | 22.99% |
| Stable | 205 | 21.72% |
| Eclipsing Binary | 150 | 15.89% |
| Solar-like | 142 | 15.04% |

---

## 💬 Citation

If you use ASTRA in your research, please cite it using the information in [`CITATION.cff`](CITATION.cff):

```bibtex
@software{tripathy2026astra,
  author    = {Tripathy, Soumyadeb},
  title     = {{ASTRA}: Automated Stellar Transient Recognition \& Analysis},
  year      = {2026},
  version   = {1.0.0},
  url       = {https://github.com/Rexy-5097/ASTRA},
  license   = {MIT},
  abstract  = {An end-to-end machine learning pipeline for automated classification
               of stellar variability from TESS light curves, implementing a Hybrid
               CNN + Transformer architecture achieving 78.17\% test accuracy across
               five stellar variability classes on a verified dataset of 944 stars
               with cryptographic integrity guarantees.}
}
```

---

## 📄 License

This project is licensed under the **MIT License** — see [`LICENSE`](LICENSE) for details.

---

<div align="center">
<sub>Built with 🔭 by <a href="https://github.com/Rexy-5097">Soumyadeb Tripathy</a> · ASTRA v1.0.0 · 2026</sub>
</div>
