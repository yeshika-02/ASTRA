---
id: ADR-0061
title: "Model weights: recovery first, hash-verified, retraining recorded as a separate experiment"
version: 1.0
status: accepted
owner: chief-architect
created: 2026-11-10
modified: 2026-11-10
related_adr: ADR-0058
related_standard: standards/ai_ml.md
related_checklist: QG-002
related_workflow: feature_development.md
related_agent: chief-architect
---

# Architecture Decision Record: ADR-0061

## Context

The audit (R1) found no trained weights in the repository. The SP-14 investigation ([docs/model_recovery.md](../../docs/model_recovery.md)) confirmed:
- No weight file was ever committed, in any branch or tag.
- No LFS, and no release assets.
- The cited "upstream" repository is this one before a transfer.

The repository does record the SHA256 of all 9 published checkpoints, of the production ONNX weights file, and of the calibration temperature, and the four records agree. The shipped ONNX graph and temperature file match their recorded hashes.

Every headline number depends on `best_star_transformer_shared.pt` (`bf374ce4…`): test accuracy 78.17%, macro F1 0.7677, calibration and uncertainty.

## Problem Statement

How do we get usable weights back without weakening the published results, and how do we make sure any weights we use are the ones those results came from?

## Alternatives Considered

- **Option A: Retrain and publish the new model as "the" ASTRA model.** Fast, but the new weights can't match the published hashes, and the published numbers would silently come to describe a different model. Rejected.
- **Option B: Recover the original files only; no retraining.** Correct, but it depends entirely on the original author. Kept as the preferred path, not the only one.
- **Option C: Recover first. Verify everything by hash. Allow a retraining run only as a separately recorded experiment.** Selected.

## Decision Rationale

1. **Hashes are the identity of a model.** `models/published_weights.json` is the single list of published artifacts. `training/verify_weights.py` checks files against it. `training/evaluate.py` records whether the evaluated checkpoint is a verified published artifact. A file that doesn't match isn't treated as published, whatever its metrics.
2. **Recovery is preferred.** Ask the original author for the production checkpoint, its `.onnx.data` and the CNN baseline (owner decision D4). Acceptance:
   - the hash matches;
   - `evaluate.py` reproduces 111/142 correct and the published confusion matrix on the frozen test split.
3. **Retraining is an experiment, not a replacement.** A reproduction run (owner decision D1, SP-17):
   - is logged as EXP-0002 with full provenance and bootstrap CIs, and is compared statistically with the published result;
   - never overwrites `models/saved/` or the published numbers;
   - is not committed.
4. **Storage:** GitHub Release assets with the manifest, not git or LFS. The web platform gets a single-file ONNX, so missing external data can't silently disable inference.
5. **Until weights exist:** inference keeps returning `503 inference_unavailable` (ADR-0058), and the documentation states that the published metrics can't be recomputed from a clone.

## Consequences

- Recovered weights can be verified and evaluated the same day.
- Publishing weights later requires updating the manifest and `tests/test_published_weights.py`, which asserts they're absent. That keeps the documentation honest.
- If recovery fails, the project's published results remain unverifiable. A reproduction experiment can show whether the method reproduces; it can't show that the published checkpoint performed as reported.
