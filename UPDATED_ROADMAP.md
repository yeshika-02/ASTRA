# ASTRA — Updated Development Roadmap

**Date:** 2026-11-09 · **Basis:** [PROJECT_AUDIT.md](PROJECT_AUDIT.md) · **Status snapshot:** [PROJECT_STATUS.md](PROJECT_STATUS.md) · **First tasks:** [PRIORITY_TASKS.md](PRIORITY_TASKS.md)

## Guiding rules

1. **Honesty before features.** Nothing shown on the platform may be fabricated. Unknown means "unavailable", never a guess.
2. **Preserve what works.** The frozen dataset, splits, processed arrays, model code and browsing UI are kept. The current 78.17% result stays on record as the *v1 baseline*, with its caveats documented. It is not deleted or overwritten.
3. **Every new number gets a baseline next to it.** Any model result is reported alongside the metadata-only baseline and with confidence intervals.
4. **AgentOS flow per phase:** plan → apply standards → implement → gate checklist → ADR for significant decisions → update `context/state.md` → validator at 100/100.

Effort scale: **S** ≤ 1 day · **M** 2–5 days · **L** 1–3 weeks · **XL** > 3 weeks. Estimates assume one engineer familiar with Python and Next.js.

---

## Phase overview

```
Phase 0  Integrity & security hotfix ─────┐  (days)
                                          ▼
Phase 1  Reproducibility foundation ──────┬──────────────┐  (1–2 wks)
                                          ▼              ▼
Phase 2  Scientific re-baseline      Phase 5  Platform hardening & UX  (parallel)
         (de-confound, baselines)         │
                                          ▼
Phase 3  Real inference service  ◄── needs Phase 1 weights + Phase 2 preprocessing decision
                                          ▼
Phase 4  Dataset expansion & class redesign  (long-running, research)
                                          ▼
Phase 6  Research publication readiness (model card, external validation)
```

| Phase | Goal | Priority | Effort | Depends on | Gate |
|---|---|---|---|---|---|
| 0 | No fabricated output, no RCE | ✅ Done 2026-11-09 (in review) | — | — | QG-005, QG-007 passed |
| 1 | Anyone can reproduce v1 from a clean clone; CI green | P0 | M–L (1–2 wks) | 0 | QG-002, QG-003 |
| 2 | Credible, de-confounded scientific numbers vs baselines | P1 | L (2–3 wks) | 1 | QG-004 |
| 3 | Real model inference on the platform, with one shared preprocessing implementation | P1 | L (2–3 wks) | 1, 2 (preprocessing frozen) | QG-001, QG-006 |
| 4 | Larger, broader, balanced dataset | P2 | XL (4–8 wks) | 2 | QG-004 |
| 5 | Fast, accessible, tested, hardened web app | P2 | M–L (1–2 wks, parallel) | 0 | QG-003, QG-005, QG-006 |
| 6 | Publication-grade documentation and external validation | P3 | L | 2–4 | QG-004, QG-008 |

---

## Phase 0 — Integrity and security hotfix ✅ COMPLETE (2026-11-09, branch `phase0/integrity-security-hotfix`, awaiting review)

**Done:**
- 0.1 and 0.2: fabricated outputs removed; unavailable UI state and site-wide notice added.
- 0.3: injection closed.
- 0.4: truthful health.
- 0.5: README limitations notice.
- 0.6: OSINT fields.
- T5 (CI) pulled forward from Phase 1: lockfile, PostCSS/ESLint configs, `.gitattributes`, `pyproject` backend, rewritten CI.

Details: ADR-0058, ADR-0059, `artifacts/reviews/phase0-gate-review.md`.

**Not deployed.** The live site keeps the old behaviour until this branch is merged and deployed by the owner.

**Original plan (kept for reference):**

**Why first:** the public site currently presents fabricated scientific output [P1] and has a command-injection path [P2]. These are reputational and security risks today.

| Task | Detail | Effort |
|---|---|---|
| 0.1 Remove fabricated fallbacks | Delete the synthetic branches in `api/predict`, `api/explain`, `api/upload`; return `503 {status:"inference_unavailable", reason}`. Remove `generateProbabilities` from `lib/utils.ts` and the `0.7` confidence defaults in `target/[id]` and `mission-replay`. | S |
| 0.2 UI unavailable state | Target, Analysis and Mission Replay pages show "Model inference unavailable on this deployment" instead of probabilities and attention. A site-wide banner while inference is offline. | S |
| 0.3 Close injection | Switch `exec` to `execFile(python, [script, ...args])` with no shell. Validate: `tic_id` `^\d{1,12}$`, `period` finite and > 0, `flux` an array of 50–100,000 finite numbers. Remove the file-path branch of `--flux` in `upload_inference.py`. Same treatment for predict/explain (`id` `^\d+$`). | S |
| 0.4 Truthful health | Compute the model hash from the actual file; report `inference: available/unavailable` from a real test call. `READY` only when inference truly works. | S |
| 0.5 Honesty notices | Add a short "Known limitations" note to the README and the site: weights not published, confounds under investigation, live inference unavailable. Don't rewrite the scientific numbers yet. | S |
| 0.6 Fix OSINT invented fields | Return `null`/"not available" for match distance, observation dates and otype unless backed by data; fix the null-period crash. | S |

**Exit criteria:**
- `grep` finds no synthetic probability or attention generation in `src/`.
- The upload route rejects malicious payloads (add tests).
- The live site shows "unavailable" rather than fake predictions.
- QG-005 input-sanitisation item passes.

**Outcome:** the platform is honest and safe, and still useful for browsing data.

---

## Phase 1 — Reproducibility foundation (P0, 1–2 weeks)

**Key decision (needs your input):** can the original checkpoints (`models/saved/*.pt` and `*.onnx.data`) be recovered from the original author's machine?
- **Yes** → publish them (GitHub Release asset or Git LFS, or Hugging Face Hub) with SHA256 in a manifest, and re-verify 78.17% from a clean clone.
- **No** → retrain from the frozen splits with the fixed scripts. Record the result as *v1-retrained*; it will differ somewhat, which is expected. Record this in an ADR.

| Task | Detail | Effort | Depends |
|---|---|---|---|
| 1.1 Weights | Recover or retrain (see decision); single-file ONNX export (`external_data=False`, about 5.5 MB); hash manifest | S–M | — |
| 1.2 One config for paths | `astra/config.py` (or a YAML file) defining `DATA_ROOT`, `SPLITS_DIR`, `MODELS_DIR`, `ARTIFACT_DIR`, env-overridable. Remove all 27 `/Users/soumyadebtripathy` paths. Point at the shipped `astra-platform/data/` or a documented download. | M | — |
| 1.3 CLIs match docs | Add `--seed`, `--data-dir`, `--out-dir` everywhere; add `training/evaluate.py --checkpoint --split test --temperature`. Update README commands and verify each one runs. | M | 1.2 |
| 1.4 Artifact generator | `tools/build_platform_artifacts.py`: from evaluation outputs → `data/artifacts/*.json` + `astra.sqlite`. Fix the NLL=ECE bug. Delete the metric duplicates in `constants.ts`; the UI reads only the generated artifacts. | M | 1.1, 1.3 |
| 1.5 Pin environments | `requirements.lock` (pip-tools or uv) including `onnxruntime`. *(Lockfile, PostCSS/ESLint configs and build backend done in Phase 0.)* Namespace the Python packages (`data`/`training` are generic top-level names). | S | — |
| 1.6 `.gitattributes` | ✅ Done in Phase 0 | — | — |
| 1.7 CI extensions | *(Base CI fixed in Phase 0.)* Add the "evaluate checkpoint on test = expected metrics ± ε" job once weights are hosted; make ESLint a gate after 1.10 | S | 1.1, 1.10 |
| 1.8 Docs clean-up | Fix 24 broken links (AgentOS validator back to 100/100); add `.github/PULL_REQUEST_TEMPLATE.md` casing for Linux; re-enable the AgentOS `lint.yml`/`validate.yml` triggers (ADR-0059); one canonical repo URL; mark Phase 8 verdict items that were not true; correct the detrending description | S | — |
| 1.9 Tests for the core | *(Model forward shapes per variant done in Phase 0.)* Preprocessing determinism; train-vs-inference preprocessing parity; metric functions (ECE, NLL, Brier) | M | 1.2 |
| 1.10 ESLint debt | 46 errors / 40 warnings app-wide, incl. a real `rules-of-hooks` bug (conditional `useMemo` in `CosmicBackground.tsx`) and 34 `any` | S–M | — |

**Exit criteria:**
- A fresh clone on Linux and on Windows can verify hashes, evaluate the published checkpoint, and regenerate platform artifacts with documented commands.
- CI is fully green.
- Coverage of `training/` is ≥ 40%.
- AgentOS validator is at 100/100.

**Outcome:** v1 is reproducible, or honestly retrained, and every later change can be measured.

---

## Phase 2 — Scientific re-baseline (P1, 2–3 weeks)

**Why:** the current accuracy can't be interpreted because of the confounds [S1, S6], and a trivial baseline beats it [S2]. This phase decides whether the deep model adds value, and on what representation.

| Task | Detail | Effort | Depends |
|---|---|---|---|
| 2.1 Baseline suite | Commit EXP-0001 (metadata RF) and add a light-curve feature baseline (period, amplitude, skewness, kurtosis, Stetson-like indices, LS power, fold residuals) with LightGBM or RF. Report every model against it. | M | 1.2 |
| 2.2 Shortcut audit | Train on cadence/sector/period-source only; shuffle the folded channel; evaluate per cadence group; report within-class performance by subgroup instead of the confounded "catalog vs BLS" split | S–M | 1.1 |
| 2.3 Uniform period search | Run the **same** search on every star regardless of class: Lomb–Scargle (log-spaced grid, 0.05–30 d) with BLS as a secondary search for eclipsing systems. Catalog period becomes an optional feature, not a per-class pipeline switch. Use Santos2021 rotation periods for validation. | M | 1.2 |
| 2.4 Fix detrending | A time-based window (days) that scales with the detected period, or detrend only for sector-level systematics (e.g. a ≥ 10 d window); bin all cadences to a common 30-min grid before features | M | 2.3 |
| 2.5 Restore lost information | Add scalar inputs to the network: log period, log amplitude (pre-normalisation), period-search power. Keep z-scored shape channels. | S–M | 2.3, 2.4 |
| 2.6 Honest evaluation protocol | Nested CV on train+val only (inner split for early stopping, outer fold reported); `duplicate_group_id` groups; test touched once per final model; bootstrap CIs; McNemar or paired bootstrap for model comparisons | S | 1.3 |
| 2.7 Re-run variants | Shared / separate / cross / CNN / feature baseline under 2.3–2.6. Select on CV only; evaluate on test once. | M | 2.1–2.6 |
| 2.8 Explainability check | Replace raw attention with integrated gradients or occlusion on the light curve; add a deletion-curve faithfulness metric | M | 2.7 |
| 2.9 Write-up | Experiment logs in `artifacts/experiments/`; ADR on the chosen representation; update the README results with v1 and v2 side by side | S | 2.7 |

**Exit criteria:**
- QG-004 passes: baseline mapped, reproducibility run, test held out, hypothesis logged.
- The reported model either beats the feature baseline with a significant difference, or the project switches its production model to the better approach. Either outcome is acceptable and documented.

**Expected outcome:** a defensible number. It may be lower than 78% once shortcuts are removed. A ≥ 85% de-confounded result is realistic, given that the feature baseline already reaches about 87% with partial shortcuts.

---

## Phase 3 — Real inference service (P1, 2–3 weeks)

**Decision to record as an ADR — inference architecture:**

| Option | Pros | Cons |
|---|---|---|
| A. Precomputed predictions for catalogued stars + ONNX Runtime (Node) for uploads, preprocessing ported to TypeScript | Serverless-friendly (Vercel), no Python at runtime | Two preprocessing implementations; needs parity tests |
| B. Small Python FastAPI inference service (Docker on Render/Fly) called by Next.js | One preprocessing implementation, reuses `pipeline/` code | Extra service and cold starts; free tiers sleep |
| C. Precomputed only, no upload | Simplest, zero runtime risk | Loses the upload feature |

**Recommendation:** B for uploads plus precomputed batch predictions for the 944 stars, so the main pages never depend on a live service. Fall back to C if hosting budget is zero.

| Task | Detail | Effort |
|---|---|---|
| 3.1 Batch predictions | Offline job writes per-star probabilities, MC-dropout stats and explanations into the generated artifacts / SQLite (with model hash) | M |
| 3.2 Inference service | FastAPI `/predict` that accepts a CSV upload (time, flux, flux_err) and runs the **same** `pipeline/preprocess.py` functions; size limits, timeouts, rate limit | M–L |
| 3.3 Upload UI | CSV drag-and-drop, validation feedback, preview chart, results with uncertainty and an explicit "out-of-distribution" warning when inputs differ from training (cadence, length, amplitude range) | M |
| 3.4 Parity tests | The same light curve through the training pipeline and the service gives identical tensors (CI test) | S |
| 3.5 Remove dead code | Drop the unused `onnxruntime-node` dependency if option B; remove `exec` shell-outs | S |

**Exit criteria:** predictions on the site match offline evaluation on the test set exactly; upload works end-to-end; QG-006 (deployment) passes.

---

## Phase 4 — Dataset expansion and class redesign (P2, 4–8 weeks, research)

| Task | Detail |
|---|---|
| 4.1 Class scope decision (ADR) | Either keep 5 classes with explicit, documented scope (DCEP, RRAB, EA only), or broaden: RRc, overtone Cepheids, EW/EB binaries, δ Scuti, rotational variables |
| 4.2 Independent labels | Variable classes from VSX + Gaia DR3 variability + ASAS-SN; "Stable" from criteria **independent** of the TESS light curve used for training (e.g. Gaia non-variability + long-baseline survey photometry) |
| 4.3 Balance confounders | Each class drawn across both cadences and similar sector counts and magnitudes; report the joint distributions in the datasheet |
| 4.4 Crowding control | Use TIC contamination ratio; exclude or flag targets with bright neighbours within 2 pixels; group spatial neighbours in splits |
| 4.5 Scale | Target 3,000–5,000 stars; keep the hash-locked freeze process (it's good) |
| 4.6 External test set | Hold out a different sky region or a later TESS cycle as an out-of-distribution test |

**Outcome:** results that generalise beyond the specific catalogs used.

---

## Phase 5 — Platform hardening and UX (P2, 1–2 weeks, can run in parallel after Phase 0)

| Task | Detail | Effort |
|---|---|---|
| 5.1 Media diet | Move videos out of git (CDN or compressed WebM ≤ 2 MB each, or a static poster). One background at most; lazy-loaded; never on data-heavy pages; no autoplay audio. Purge 310 MB from history only with explicit approval (history rewrite). | S–M |
| 5.2 Accessibility | `prefers-reduced-motion`, ARIA labels on charts and controls, keyboard navigation, contrast check (WCAG AA) | M |
| 5.3 API hardening | Shared SQLite connection; zod schemas for query params; generic error messages; rate limiting on heavy routes; security headers (CSP, frame-ancestors) | M |
| 5.4 Typed client | Remove 38 `any` usages; shared response types generated from artifact schemas | S–M |
| 5.5 Tests | Vitest for utilities and API handlers; Playwright smoke test for key pages; run in CI | M |
| 5.6 Deploy configs | Fix the Dockerfile (copy `data/`, standalone output), align `render.yaml`, document env vars | S |

**Exit criteria:** Lighthouse performance ≥ 80 and accessibility ≥ 90 on the main pages; QG-003 and QG-006 pass.

---

## Phase 6 — Research publication readiness (P3)

- Model card (intended use, out-of-scope uses, per-class and per-subgroup performance, known shortcuts) and dataset datasheet.
- External validation (Phase 4.6) and comparison against published TESS/Kepler variability classifiers.
- Reproducibility package: one command reproduces every table from the hosted data and weights.
- `CITATION.cff` and authorship aligned with the actual repository.

---

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Original weights can't be recovered | Medium | Medium | Retrain from frozen splits; v1-retrained recorded via ADR |
| De-confounded accuracy drops well below 78% | Medium | Medium | Expected and acceptable; report honestly; features + model hybrid usually recovers |
| Free-tier hosting can't run inference | High | Low | Precomputed predictions (Phase 3.1) keep the site useful |
| History rewrite to drop 310 MB of media disrupts collaborators | Medium | Medium | Do it only with team agreement; otherwise just stop adding media |
| Scope creep into new features before integrity fixes | Medium | High | Phase 0 and 1 are gates; no new features until they pass |

## Milestones

| Milestone | Definition of done | Target |
|---|---|---|
| M0 Honest platform | Phase 0 exit criteria | ✅ Code complete 2026-11-09; live after merge + deploy |
| M1 Reproducible v1 | Phase 1 exit criteria; CI green; validator 100/100 | Week 2–3 |
| M2 Credible science | Phase 2 exit criteria; baseline table published | Week 5–6 |
| M3 Real inference | Phase 3 exit criteria | Week 7–9 |
| M4 Dataset v3 | Phase 4 freeze + datasheet | Week 10–16 |
