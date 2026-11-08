---
id: ART-EXP-0001
title: "Metadata-only baseline on the frozen ASTRA split"
version: 1.0
status: completed
owner: science-reviewer
created: 2026-11-09
modified: 2026-11-09
related_adr: ADR-0057
related_standard: standards/research.md
related_checklist: QG-004
related_workflow: research.md
related_agent: science-reviewer
---

# Experiment Log: EXP-0001

## Hypothesis

If the 5-class labels are confounded with pipeline metadata (period source, cadence, sector count), then classifiers that never see a light curve will score far above chance (20%) on the frozen test split. Simple physical scalars (period, amplitude, SNR) may match or beat the reported HybridTransformer result (78.17% accuracy, macro-F1 0.7677).

## Setup

- Data: `astra-platform/data/astra.sqlite` (944 stars, identical to the hash-locked manifest `f99b4b06…dbf58`).
- Split: frozen `split` column (661 train / 141 val / 142 test). Fit on train only; evaluated once on test.
- Models: scikit-learn 1.6.1 LogisticRegression (max_iter 5000) and RandomForest (500 trees, min_samples_leaf 2, random_state 42).
- Script: `artifacts/experiments/EXP-0001-metadata-baseline.py`. Run with `python -I EXP-0001-metadata-baseline.py astra-platform/data/astra.sqlite`.

## Results

| Feature set | Model | Test acc | Macro F1 |
|---|---|---|---|
| cadence, n_sectors | LogReg / RF | 43.7% / 43.7% | 0.310 / 0.353 |
| + period_source | LogReg / RF | 62.0% / 62.7% | 0.558 / 0.572 |
| log period, log amplitude, log SNR | LogReg / RF | 81.7% / 86.6% | 0.792 / 0.854 |
| all six | LogReg / RF | 88.0% / 90.9% | 0.861 / 0.897 |
| HybridTransformer shared (reported) | — | 78.2% | 0.768 |

## Interpretation

- Pipeline artefacts alone reach 3× chance, which confirms the confounds.
- Three scalar features beat the deep model. The network discards both amplitude (per-star z-scoring) and period (phase axis).
- Caveat: for the variable classes, `period` is the VSX catalog period (external information). For Solar-like/Stable it is a noisy BLS value.

## Decision

Report a baseline beside every model result. Feed log period and log amplitude to the network as side inputs. Re-run with a class-independent period search (roadmap Phase 2).
