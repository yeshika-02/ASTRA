# Changelog

All notable changes to ASTRA are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

> On `main` since 2026-11-09 ([PR #1](https://github.com/yeshika-02/ASTRA/pull/1)); not yet released or deployed. The repository also carries a `v1.1.0` tag that has no matching entry in this file; to be reconciled in sprint task SP-35.

### Pending in open sprint PRs (not yet on `main`)
- Fixed a page crash (React error #300) when switching graphics quality to low; ESLint findings 86 → 0 and lint gated in CI ([#6](https://github.com/yeshika-02/ASTRA/pull/6)).
- GitHub Actions upgraded to v7; Python coverage report in CI; release workflow fixed (`softprops/action-gh-release` v3, `git archive`) ([#3](https://github.com/yeshika-02/ASTRA/pull/3)).
- 24 broken documentation links fixed; AgentOS validator 100/100; `validate` workflow re-enabled ([#4](https://github.com/yeshika-02/ASTRA/pull/4)).
- 41 Python tests for losses, calibration metrics, dataset splits, explainability parity and inference helpers ([#5](https://github.com/yeshika-02/ASTRA/pull/5)).
- Central path configuration (`astra.config`, `ASTRA_*` environment overrides) replacing 27 machine-specific paths; `--seed`/`--data-dir`/`--out-dir` and other real CLI flags on training, cross-validation, calibration and uncertainty scripts; fixed report-writer crashes, UTF-8 reports, undeclared dependencies and a cleanup script that deleted by default ([#7](https://github.com/yeshika-02/ASTRA/pull/7)).
- `pipeline/prepare_from_repo.py` verifies the shipped dataset and rebuilds `data/phase6` from a clone; CI fresh-clone reproduction job; `requirements-lock.txt`; `onnx`/`onnxscript` declared; `export_model.py` and `visualize_attention.py` fixed; README commands now match the code ([#8](https://github.com/yeshika-02/ASTRA/pull/8)).
- `training/evaluate.py` (frozen-split evaluation with bootstrap CIs and published-checkpoint hash verification), `models/published_weights.json` and `training/verify_weights.py`, `astra.provenance` in training/CV/evaluation records, the weights investigation and recovery plan (ADR-0061), and a rewritten reproducibility guide ([#9](https://github.com/yeshika-02/ASTRA/pull/9)).
- One authoritative record of published metrics (`models/published_metrics.json`, generated `docs/metrics.md`) and a generator for the platform artifacts; README results that came from an earlier 269-star experiment are marked superseded, the CNN figures follow their confusion matrix, NLL copied from ECE is removed, and unsourced UI numbers are gone ([#10](https://github.com/yeshika-02/ASTRA/pull/10)).
- Golden test pinning preprocessing v1, characterisation tests for its detrending and BLS period search, and clear input errors in the pipeline scripts and `process_star` ([#11](https://github.com/yeshika-02/ASTRA/pull/11)).
- Test-free, grouped, nested cross-validation with bootstrap CIs (ADR-0062) ([#12](https://github.com/yeshika-02/ASTRA/pull/12)).
- `training/baselines.py`: EXP-0001 metadata baselines reproduced exactly and a light-curve-statistics baseline, reported beside the model ([#13](https://github.com/yeshika-02/ASTRA/pull/13)).

### Security
- **Command injection in `POST /api/upload` fixed.** Request fields were interpolated into a shell command; inference now spawns Python with an argument array (`shell: false`), sends flux over stdin, and validates every input. `upload_inference.py` no longer reads a server file when `--flux` is a path.

### Fixed
- Prediction, explanation and upload endpoints no longer return probabilities, uncertainty or attention maps derived from ground-truth labels or random numbers when the model can't run. They return `503 inference_unavailable`, and the UI shows that no inference ran.
- `/api/health` now measures readiness (dataset and checkpoint hashes, database row count, ONNX weights, Python modules) instead of reporting a hardcoded model hash.
- OSINT endpoint no longer reports invented match distances or observation dates; null-period crash fixed.
- Tailwind CSS v4 build: the missing `postcss.config.mjs` meant no utility classes were generated from a fresh clone.
- CI: every job had failed since creation (missing lockfile, wrong split-file paths, wrong model API in the smoke test); all 5 jobs now pass.
- Hash-locked research files keep their bytes on Windows checkouts (`.gitattributes`).
- `pyproject.toml` build backend corrected; a wheel now builds.

### Added
- API, security, health and no-fabrication test suites for the web platform (88 Vitest tests); Python tests for upload input parsing and model forward passes (21 total).
- AgentOS (Raptors Way) development framework, `ml` profile; ADR-0057–ADR-0060.
- Project audit and planning documents: `PROJECT_AUDIT.md`, `PROJECT_STATUS.md`, `UPDATED_ROADMAP.md`, `PRIORITY_TASKS.md`, `TASK_CHECKLIST.md`, `7_DAY_SPRINT.md`.
- README "Known limitations" notice (no published weights, no live inference, confounded labels).

---

## [1.0.0] — 2026-06-13

### Added

#### Models & Architecture
- **HybridTransformer (shared variant)** — primary production model; 1,373,701 parameters; 78.17 % test accuracy on the 944-star TESS benchmark
- **CNN Dual-Branch** — secondary production model; 1,043,333 parameters; 78.17 % test accuracy
- Temperature calibration via MC (Maximum Calibration) scaling for both HybridTransformer and CNN Dual-Branch architectures
- MC Dropout uncertainty quantification layer, enabling per-prediction epistemic uncertainty estimates

#### Deployment & Export
- ONNX export pipeline for hardware-agnostic inference
- TorchScript export for PyTorch-native deployment without Python runtime
- Explainability wrapper with attention-map visualization for HybridTransformer attention heads

#### Web Platform
- Full-stack web platform at `astra-platform/` built with Next.js and Three.js
- Interactive 3-D sky visualization and light-curve inspection UI

#### Validation & Reproducibility
- 5-fold cross-validation with 3 independent random seeds (42, 100, 2026)
- Dataset fingerprint lock — SHA-256 hash integrity verification for the canonical TESS dataset split
- Zero-trust ground truth audit — all 8 audit checks **PASS**
- Full experiment reproducibility artefacts: deterministic split hashes and experiment metadata JSON files

#### Dataset
- 944-star verified TESS dataset spanning 5 transient classes, frozen at Phase 6 dataset fingerprint v2.0

---

## [0.9.0] — 2026-06-12

### Added
- Four Transformer architectural variants: **separate**, **shared**, **cross**, and **only** attention strategies
- Phase 7 full benchmark suite comparing all model variants on the frozen test split
- Phase 8 explainability audit — attention-head attribution analysis across all five stellar classes
- Calibration strategy report documenting reliability diagrams and Expected Calibration Error (ECE) before/after temperature scaling

---

## [0.8.0] — 2026-06-12

### Added
- Phase 6 dataset freeze: canonical train / validation / test split with deterministic seed and persisted indices
- Metadata repair pipeline — corrected missing and malformed class labels in the TESS catalogue
- Integrity verification step: row-count and class-distribution checks gate all downstream experiments
- Dataset fingerprint v2.0 — SHA-256 hash of the frozen split stored in `data/fingerprint.json`

---

## [0.1.0] — 2026-05-25

### Added
- Initial 1D-CNN baseline implementation for single-branch light-curve classification
- VSX + MAST catalogue ingestion pipeline for source cross-matching and label assignment
- `lightkurve`-based preprocessing pipeline: gap filling, normalisation, and sigma-clipping
- Focal loss function with inverse-frequency class weighting to handle severe class imbalance across transient types

---

## Version Summary

| Version | Date       | Milestone                              |
|---------|------------|----------------------------------------|
| 1.0.0   | 2026-06-13 | Production release — dual-model v1     |
| 0.9.0   | 2026-06-12 | Transformer variants + benchmark suite |
| 0.8.0   | 2026-06-12 | Dataset freeze + integrity audit       |
| 0.1.0   | 2026-05-25 | Initial 1D-CNN + data pipeline         |

[Unreleased]: https://github.com/soumyadebtripathy/ASTRA/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/soumyadebtripathy/ASTRA/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/soumyadebtripathy/ASTRA/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/soumyadebtripathy/ASTRA/compare/v0.1.0...v0.8.0
[0.1.0]: https://github.com/soumyadebtripathy/ASTRA/releases/tag/v0.1.0
