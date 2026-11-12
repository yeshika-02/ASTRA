---
id: ART-EXP-0003
title: "Light-curve feature baseline: the network's own inputs, no period or amplitude"
version: 1.0
status: completed
owner: science-reviewer
created: 2026-11-12
modified: 2026-11-12
related_adr: ADR-0062
related_standard: standards/research.md
related_checklist: QG-004
related_workflow: research.md
related_agent: science-reviewer
---

# Experiment Log: EXP-0003

EXP-0002 is reserved for the CPU reproduction run, which waits on owner decision D1.

## Hypothesis

EXP-0001 showed that period, amplitude and SNR beat the HybridTransformer. Those features are not in the network's input, which is z-scored per star (audit S3), so that comparison is unfair to the network.

If simple shape statistics of the **same** inputs the network sees reach the network's accuracy, the 1.37M-parameter model is not shown to extract more than those statistics.

## Setup

- **Data:** the shipped `flux_1000.npy` (detrended, z-scored, time order) and `folded_flux_1000.npy` (phase-folded, z-scored) of the 944 frozen stars. Both are hash-locked by the manifest `f99b4b06…dbf58`.
- **Split:** frozen train (661 stars) for fitting; frozen test (142 stars) evaluated once.
- **Features:** 12 per star, from `training/baselines.py` (`LIGHTCURVE_FEATURES`):
  - raw channel: skewness, excess kurtosis, autocorrelation at lags 1, 10 and 100, fraction beyond 2σ, zero-crossing rate;
  - folded channel: skewness, excess kurtosis, lag-1 autocorrelation, range, roughness (std of first differences).
  - Undefined statistics of flat inputs are set to 0.
- **Models:** the same as EXP-0001, logistic regression (max_iter 5000) and a random forest (500 trees, min_samples_leaf 2, random_state 42), with scikit-learn 1.9.1.
- **Uncertainty:** percentile-bootstrap CIs over the 142 test stars (1,000 resamples, seed 42).
- **Command:** `python training/baselines.py`

## Results

| Model | Test accuracy | 95% CI | Macro F1 | 95% CI |
|---|---:|---|---:|---|
| Logistic regression | 73.24% | [65.49%, 80.28%] | 0.7347 | [0.6519, 0.8006] |
| Random forest | 79.58% (113/142) | [72.54%, 85.92%] | 0.7867 | [0.7137, 0.8560] |
| HybridTransformer shared (published) | 78.17% (111/142) | [71.13%, 85.21%] | 0.7677 | [0.6944, 0.8320] |

## Interpretation

- **The network is not shown to beat the statistics:** 12 statistics of its own inputs match it. The difference (2 stars) is well inside both intervals.
- **Not a paired test:** the comparison is not a paired test on the same stars. The published model's per-star predictions are not available (ADR-0061). A paired test (McNemar) becomes possible once the checkpoint is recovered and `training/evaluate.py` produces per-star predictions.
- **Platform sensitivity:** the statistics can differ in the last bits between platforms, which can move one test star. On Linux CI the logistic regression gets 103/142 instead of 104/142, and the random forest stays within the tests' one-star tolerance.
- **The folded channel still carries the period choice:** the folded statistics depend on the selected period, which is the catalog period for the variable classes, so the period is still indirectly present.

## Decision

- Report this baseline, with EXP-0001's, beside every model result (ADR-0062): `docs/metrics.md` and the README.
- A model change counts as an improvement only if it beats the light-curve random forest on the same split.
