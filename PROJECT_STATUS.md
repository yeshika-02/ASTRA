# ASTRA — Project Status

**As of:** 2026-11-09 (Phase 0 merged) · **`main`:** `1beca47` · **Phase 0:** [PR #1](https://github.com/yeshika-02/ASTRA/pull/1), merged by rebase · **Source:** [PROJECT_AUDIT.md](PROJECT_AUDIT.md) (finding IDs in brackets)

Status is based on what the code, data and runs show, not on README or engineering-log claims.

| Symbol | Meaning |
|---|---|
| ✅ | Done and verified |
| 🟨 | Exists but partial, or claims overstated |
| ❌ | Broken, missing, or claimed but not implemented |
| ⬜ | Not started |

---

## At a glance

| Area | Status | One-line reason |
|---|---|---|
| Data acquisition pipeline | 🟨 | Code complete, but scripts write to another machine's paths [R3]; raw data must be re-downloaded |
| Preprocessing | 🟨 | Works, but detrending and period search are scientifically flawed [S4, S5] |
| Frozen dataset and splits | ✅ | Hashes and split integrity verified |
| Model code | ✅ | 6 transformer variants + CNN baseline; clean code |
| Trained models | ❌ | No weights in repo [R1] |
| Evaluation | 🟨 | Numbers internally consistent but not reproducible; CV biased [S7]; no baseline [S2] |
| Calibration and uncertainty | 🟨 | Correct protocol; reported numbers conflict [S11, R4] |
| Explainability | 🟨 | Attention extraction exists; ONNX export self-reported BLOCKED; no faithfulness check [S10] |
| Web platform: browsing and data | ✅ | Real data, parameterised SQL |
| Web platform: inference | 🟨 | Phase 0: fabricated output removed; honest 503 + "unavailable" UI [P1 ✅]. Still no real inference: no weights [R1], no runtime [P3, P4] |
| Security | 🟨 | Command injection fixed (no shell, strict validation) [P2 ✅]; no rate limiting or dependency audit yet |
| Tests | 🟨 | 21 Python + 88 web tests pass (API, security, health, no-fabrication, model smoke); `training/` coverage still low [E2] |
| CI | ✅ | All 5 jobs green on `main` after the merge (run 42520528644) [E1 ✅] |
| Deployment | ⚠️ | Phase 0 is on `main`, but the live Vercel site (separate account) still serves the pre-Phase-0 code, including the fabricated predictions and the injection path. Deployment is out of scope until after the sprint. Docker image broken [P4] |
| Documentation | 🟨 | Extensive, but contains false claims and broken links [E3] |

---

## 🟦 Current: 7-day sprint (2026-11-09 → 2026-11-15)

- **Status:** planned; Day 1 not started.
- **Plan:** [7_DAY_SPRINT.md](7_DAY_SPRINT.md). **Tasks:** SP-00…SP-35 in [TASK_CHECKLIST.md](TASK_CHECKLIST.md).
- **Open owner decisions:** D1 (CPU reproduction run), D2 (preprocessing v2), D3 (delete merged branch), D4 (ask the original author for weights), D5 (production risk).

## ✅ Phase 0 — completed and merged to `main` 2026-11-09 (not deployed to production)

| Task | Result | Evidence |
|---|---|---|
| T1 Remove fabricated output | ✅ | Synthetic branches deleted from `api/predict`, `api/explain`, `api/upload`; client generator and 0.7 defaults removed; Mission Replay shows the model class only when the model ran; OSINT invented fields nulled; static guard test |
| T2 Close command injection | ✅ | `lib/server/inference.ts` (spawn, `shell: false`, stdin for flux), `lib/server/validation.ts`; `upload_inference.py` file-path read removed; tests fail on the old code, pass on the new |
| T3 Truthful health + notices | ✅ | `lib/server/health.ts` (recomputed hashes, DB query, ONNX weight check, Python module probe); TopBar INFERENCE indicator + site-wide notice; README "Known limitations" |
| T5 CI | ✅ | `package-lock.json`, `postcss.config.mjs`, `eslint.config.mjs`, `.gitattributes`, fixed `pyproject.toml`; rewritten `ci.yml` (lint, Python tests incl. smoke, dataset integrity with hashes, web typecheck/tests/build) |
| AgentOS GitHub files | ✅ | Adapted and committed per ADR-0059 |

## ✅ Completed and verified

| Item | Evidence |
|---|---|
| 944-star scientific freeze (`scientific_dataset_freeze_v2.csv`), SHA256 `f99b4b06…dbf58` | Hash recomputed |
| Train/val/test split 661/141/142, zero overlap, class-stratified, matches SQLite `split` column | Recomputed from `docs/engineering-log/phase6_*_ids.json` |
| Processed arrays (`flux_1000`, `flux_200`, `folded_flux_1000`, `folded_flux_200`, `metadata.json`) for all 944 stars | Present in `astra-platform/data/processed/` |
| Per-star content hashes in the manifest | Present |
| Phase 6 pipeline utilities: duplicate grouping, hashing, audit, split freezing, training guard | 10/10 unit tests pass |
| HybridTransformer (separate / shared / cross / only / shared_no_folded / shared_no_folded_matched) and StarCNN definitions | Code review |
| Focal loss with class weights and label smoothing, AdamW, cosine schedule, augmentation | Code review |
| Temperature scaling fitted on validation, not test | Code review |
| Reported shared-model test metrics: 78.17% acc, macro-F1 0.7677, per-class F1s | Recomputed from the committed confusion matrix |
| SQLite star registry with FTS index; read-only APIs: `stars`, `stars/[id]`, `search`, `lightcurve/[id]`, `dataset`, `model`, `checkpoints`, `benchmark`, `calibration`, `research` | Code review; live site |
| UI: dashboard, search, target dossier, dataset, model, research, visualization pages; command palette; light-curve charts | Live site |
| Vercel deployment serving the data-browsing features | Live `/api/health` |
| Ruff lint clean | Run |

## 🟨 Implemented, but partial or overstated

| Item | What's missing or wrong |
|---|---|
| Catalog construction and candidate expansion (`build_catalog.py`, `candidate_expander.py`, `stable_screen.py`, `variability_crosscheck.py`) | Hardcoded `/Users/soumyadebtripathy/...` output paths [R3]; one VSX subtype per class [S9]; "Stable" is defined by thresholds on the same data [S9] |
| Preprocessing (`preprocess.py`) | Savitzky–Golay window of 301 *points* (cadence-dependent; flattens long periods) [S4]; BLS with a fixed duration on a coarse linear grid [S5]; per-star z-scoring discards amplitude [S3]; README describes different detrending |
| Period handling | Catalog-vs-BLS choice is perfectly confounded with class [S1]; Santos2021 rotation periods discarded [S5] |
| Training scripts | Seed hardcoded (no `--seed`); default data path doesn't exist in a fresh clone [R2] |
| Cross-validation (`cross_validate.py`) | Reports best-epoch validation score, includes test stars, groups by `tic_id` [S7] |
| Calibration (`calibration.py`) | Works; outputs go to a foreign path; report text is stale (mentions 269 stars / N=54) [S8] |
| MC Dropout uncertainty (`uncertainty.py`, `predict_inference.py`) | Implemented (30 passes); three conflicting selective-prediction tables [S11] |
| Attention explainability (`explain_inference.py`, `explainable_wrapper.py`) | Extraction works in PyTorch; ONNX export status BLOCKED per own artifact; no faithfulness test [S10] |
| Export (`export_model.py`) | Produces ONNX with external weights that are gitignored [R1] |
| Platform metric artifacts (`data/artifacts/*.json`, `astra.sqlite`) | No generator script; NLL=ECE copy bug; disagree with `constants.ts` and README [R4] |
| Dataset page lineage funnel | Counts (3,200 → … → 944) have no source [R4] |
| Documentation (`README.md`, `docs/`, 47 engineering-log reports) | Extensive but contradicts code in several places; 24 broken links; three different repo URLs [E3] |
| Unit tests | Cover pipeline utilities only; 8% total coverage [E2] |

## ❌ Broken, missing, or claimed but not implemented

| Item | Detail |
|---|---|
| **Model weights** (`.pt`, `.onnx.data`, `.torchscript`) | None in repo; nothing can be reproduced or served [R1] |
| **Live model inference on the platform** | Not possible yet: no weights [R1] and no Python runtime on Vercel [P4]. Since Phase 0 the endpoints return 503 and the UI says inference is unavailable (fabrication removed) |
| **ONNX Runtime inference** | `onnxruntime-node` installed but never imported [P3] |
| **Upload feature** | API only (JSON, not CSV); no UI; preprocessing differs from training [P7]. Injection fixed in Phase 0 |
| **Python inference in deployment** | `.venv/bin/python` path is Unix-only and absent on Vercel/Render/Docker [P4] |
| **Docker image** | Doesn't copy `data/`, so health is BLOCKED and data routes fail [P4] |
| **README reproduction commands** | `--seed`, `--model`, `--split`, `--temperature` flags don't exist; `splits/` and `data/phase6/` dirs don't exist [R2] |

## ⬜ Not started

| Item | Why it matters |
|---|---|
| Baseline comparison (feature-based classifier) | Required by `standards/ai_ml.md`; a 3-feature RF currently beats the model (86.6% vs 78.2%) [S2] |
| De-confounded evaluation (period source, cadence, catalog balanced or controlled) | Without it the reported accuracy isn't interpretable [S1, S6] |
| Shortcut / ablation tests (metadata-only, cadence-only, shuffled-fold) | Show what the model actually uses |
| Independent external test set (other sectors or other labels) | Generalisation evidence |
| Model card and datasheet | Required for any scientific use |
| Frontend component and e2e tests | API tests exist since Phase 0; no component/e2e tests |
| Rate limiting, security headers, input schemas | Production readiness |
| Accessibility (reduced motion, ARIA, keyboard) | Currently minimal [U4] |
| Media optimisation | 310 MB of video/audio in `public/` [U1] |
| Experiment tracking (MLflow/W&B or structured run logs) | Reproducibility |
| Monitoring / drift detection | Production readiness |

---

## Key numbers

| Metric | Value | Status |
|---|---|---|
| Stars / classes | 944 / 5 | ✅ verified |
| Test accuracy (shared transformer) | 78.17% [71.1, 85.2] | 🟨 consistent, not reproducible |
| Test macro-F1 | 0.7677 | 🟨 same |
| Metadata-only RF (3 features) | 86.6% / 0.854 | ✅ reproduced in this audit |
| CV accuracy (claimed) | 84.68% | ❌ biased estimate |
| Tests | 21 Python + 88 web pass | ✅ |
| Python coverage | 8% before Phase 0; `training/` still mostly untested | ❌ |
| CI status | All 5 jobs green on the Phase 0 branch (GitHub run 42519045208) | ✅ |
| Hardcoded foreign paths | 27 in 11 files | ❌ |
| Committed media | ~310 MB | ❌ |
| AgentOS validator | 94/100 (Cross-reference 0/100 from ASTRA's broken doc links) | 🟨 |
| ESLint | 86 problems (46 errors) app-wide, all pre-existing; not a CI gate yet | 🟨 |
