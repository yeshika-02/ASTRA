# Model weights: investigation record and recovery plan

Sprint task SP-14 · Decision: [ADR-0061](../artifacts/decisions/ADR-0061-model-weights-recovery-and-verification.md) · Hashes: [`models/published_weights.json`](../models/published_weights.json)

## Summary

The trained weights behind every published ASTRA result are not in this repository and never were. The repository does record their SHA256 hashes, consistently in four places, so recovered files can be verified byte for byte.

None of the published metrics (test accuracy 78.17%, macro F1 0.7677, calibration, uncertainty) can be recomputed until the weights are recovered. Retraining produces a new model with new results: it can test whether the method reproduces, but it can never stand in for the published checkpoint.

## What was checked (2026-11-09)

| Where | Result |
|---|---|
| Every commit, branch and tag (`git rev-list --all --objects`) | No `.pt`, `.pth`, `.ckpt`, `.torchscript` or `.onnx.data` blob ever committed |
| Git LFS | Not used (no `filter=lfs` in any `.gitattributes`) |
| GitHub Releases | None. Tag `v1.1.0` exists but has no release or assets |
| The "upstream" repository `Rexy-5097/ASTRA` (cited in `CITATION.cff` and the README) | The same repository: it redirects to `yeshika-02/ASTRA` (same repository id, 1268488502) after a transfer, so it isn't a separate copy |
| `.gitignore` | Excludes `*.onnx.data` and `*_smoke.pt`. The lines that would keep the production checkpoints are commented out, and no `.pt` file was ever added |
| Shipped ONNX files (`astra-platform/data/*.onnx`) | Graphs only (190 KB and 216 KB, opset 18). Each references 46 external tensors in a `.onnx.data` file of at least 5,505,024 bytes, which matches 1.37 M float32 parameters. Neither data file is present |
| `astra-platform/data/artifacts/model_registry.json` (generated 2026-06-13) | Lists every checkpoint with `exists: true` at `models/saved/...`: the files existed on the original author's machine when the registry was generated |

The investigation didn't cover deployment environments; that was out of scope for the sprint.

## What the repository does record

All hashes are collected in `models/published_weights.json`. `tests/test_published_weights.py` checks that they agree with every source below.

| Artifact | SHA256 | Recorded in |
|---|---|---|
| `best_star_transformer_shared.pt` (production, 1,373,701 parameters) | `bf374ce4…d388` | `model_registry.json`, `constants.ts`, `inference.ts`, `experiment_metadata_shared.json`, `ground_truth_checkpoint_audit.md` |
| `best_star_cnn_dual_aug.pt` (CNN baseline) | `65da1034…8af2` | the same, except `inference.ts` |
| 7 other checkpoints (variants and ablations) | see the manifest | `model_registry.json`, `constants.ts`, the audit |
| `best_star_transformer_shared.onnx` | `48e75b77…2dfe` | `model_registry.json`. **The shipped graph matches** |
| `best_star_transformer_shared.onnx.data` | `5a8fcc0d…3e06` | `model_registry.json` |
| `best_star_transformer_shared_explain.onnx` | `07a9d194…3bce` (shipped file) | no published hash |
| `best_star_transformer_shared_explain.onnx.data` | none recorded | — |
| `optimal_temperature_transformer_shared.txt` (T = 1.257665) | `d6e61017…d2ed` | `model_registry.json`. **The shipped file matches** |

The registry also lists four pilot checkpoints (`*_smoke.pt`). They back no reported result and aren't needed.

The published test confusion matrices are kept as images (`models/saved/test_confusion_matrix_transformer_shared.png`, `..._cnn_dual.png`). Transcribed, they reproduce the published accuracy, per-class F1 and macro F1 exactly. `tests/test_evaluate.py` holds them as fixtures.

## Recovery plan

### Path A: recover the original files (preferred)

Owner action, decision D4. Ask the original author for:

1. `best_star_transformer_shared.pt` (required: production model, every headline number)
2. `best_star_transformer_shared.onnx.data` (web-platform inference)
3. `best_star_cnn_dual_aug.pt` (baseline comparison)
4. Optionally the other 6 checkpoints, for the ablation table

Then verify and evaluate:

```bash
# put the files in models/saved/ (or point ASTRA_MODELS_DIR at them)
python training/verify_weights.py --require best_star_transformer_shared.pt
python training/evaluate.py --checkpoint models/saved/best_star_transformer_shared.pt \
    --temperature-file models/saved/optimal_temperature_transformer_shared.txt
```

Acceptance:
- `verify_weights.py` reports `match`.
- `evaluate.py` reproduces 111/142 correct (78.17%) and macro F1 0.7677 on the frozen test split.
- The confusion matrix equals the published one.

A hash mismatch means the file isn't the published artifact, whatever its metrics.

### Path B: reproduction run (only if Path A fails or as an extra check)

Owner decision D1; sprint task SP-17.

- Train the shared transformer on the shipped 944 arrays with the published configuration (`--variant shared --seed 42`, 50 epochs) on CPU.
- Record it as **EXP-0002**, with its own hashes, provenance (git commit, environment, data hashes) and bootstrap CIs from `evaluate.py`.
- Compare it with the published result.

Rules:
- It never replaces the published 78.17%, and it isn't written over `models/saved/`.
- A retrained file will not match the published hash. GPU/MPS kernels, library versions and thread scheduling make training non-bitwise-reproducible across machines, so the comparison is statistical (overlapping CIs, paired test on the same 142 stars), not byte-level.
- Retrained weights aren't committed. Whether to publish them as a separate, clearly labelled artifact is a later decision.

### Storage once recovered

- Publish the weights as **GitHub Release assets**, keyed to a tag, alongside `published_weights.json`. Don't commit them to git, and don't use LFS: the repository's history stays small and the hashes stay the source of truth.
- Export a single-file ONNX (weights embedded, about 5.7 MB) for the web platform, so a missing `.onnx.data` can't silently disable inference. Record its hash in the manifest.
- Download scripts and CI must verify with `verify_weights.py` before use.

## Until then

- The web platform answers inference requests with `503 inference_unavailable` and health reports `DEGRADED`. It never serves placeholder predictions (ADR-0058).
- Published numbers stay labelled as published: the README states they can't be recomputed from a clone.
- `evaluate.py`, `verify_weights.py` and experiment provenance (SP-15, SP-16) are ready, so whichever path delivers weights can be checked the same day.
