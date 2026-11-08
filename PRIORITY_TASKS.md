# ASTRA — Priority Tasks

**Date:** 2026-11-09 · **Basis:** [PROJECT_AUDIT.md](PROJECT_AUDIT.md) · **Full plan:** [UPDATED_ROADMAP.md](UPDATED_ROADMAP.md)

These are the tasks to start with, ordered by **impact ÷ effort**.

**Update 2026-11-09:** T1, T2, T3 and T5 are done on branch `phase0/integrity-security-hotfix` (see ADR-0058 and `artifacts/reviews/phase0-gate-review.md`). They are not merged or deployed. **Next up (Phase 1, awaiting approval): T4 → T7 → T8 → T9, plus T13 below.**

Effort: **S** ≤ 1 day · **M** 2–5 days.

| # | Task | Impact | Effort | Phase | Finding |
|---|---|---|---|---|---|
| T1 | ✅ Remove fabricated predictions, attention and uncertainty | 🔴 Very high | S | 0 | P1 |
| T2 | ✅ Close the command injection in `/api/upload` (and harden predict/explain) | 🔴 Very high | S | 0 | P2 |
| T3 | ✅ Make `/api/health` truthful + add a "known limitations" notice | 🟠 High | S | 0 | P5, E3 |
| T4 | Recover or regenerate the model weights and host them with hashes | 🔴 Very high | S–M | 1 | R1 |
| T5 | ✅ Get CI green (verified locally; first GitHub run on push) | 🟠 High | S | 1 | E1, U2, R5 |
| T6 | Commit the metadata baseline and report it next to the model | 🟠 High | S | 1–2 | S2 |
| T7 | Replace hardcoded paths with one config; make README commands run | 🟠 High | M | 1 | R2, R3 |
| T8 | Artifact + SQLite generator; remove duplicated metrics in `constants.ts` | 🟠 High | M | 1 | R4, S11 |
| T9 | Fix docs: 24 broken links, false claims, one repo URL (validator → 100/100) | 🟡 Medium | S | 1 | E3 |
| T10 | Honest CV: nested, test-free, `duplicate_group_id` groups | 🟠 High | S | 2 | S7 |
| T11 | Uniform period search + time-based detrending experiment | 🔴 Very high (science) | M | 2 | S1, S4, S5 |
| T12 | Media diet: stop shipping 310 MB of video/audio to every visitor | 🟡 Medium | S | 5 | U1, U4 |
| T13 | Fix ESLint errors (46), starting with the `rules-of-hooks` bug in `CosmicBackground.tsx`; then gate lint in CI | 🟡 Medium | S–M | 1 | new (Phase 0) |

---

## T1 — Remove fabricated outputs 🔴
**Files:**
- `astra-platform/src/app/api/predict/[id]/route.ts`
- `astra-platform/src/app/api/explain/[id]/route.ts`
- `astra-platform/src/app/api/upload/route.ts`
- `astra-platform/src/lib/utils.ts` (`generateProbabilities`)
- `astra-platform/src/app/mission-replay/page.tsx`
- `astra-platform/src/app/target/[id]/page.tsx`

**Do:**
- Delete every synthetic branch.
- On failure, return `503 {status: "inference_unavailable", reason}`.
- The UI shows an "inference unavailable" state instead of probabilities, attention or the 0.7 default.

**Done when:**
- No code in `src/` generates class probabilities or attention from labels or `Math.random()`.
- `GET /api/predict/TIC_122784551` on a Python-less deploy returns 503.
- The target page renders the unavailable state.

**Preserves:** all browsing features, light curves, dataset/model pages.

## T2 — Close command injection 🔴
**Files:**
- `astra-platform/src/app/api/upload/route.ts`, plus the predict/explain routes
- `training/upload_inference.py`

**Do:**
- Use `execFile(python, [script, ...args])` (no shell).
- Validate inputs: `tic_id` against `^\d{1,12}$`, `period` finite and > 0, `flux` an array of 50–100k finite numbers, `id` against `^\d+$`.
- Remove the "`--flux` is a file path" branch.
- Cap the request body size.

**Done when:**
- Tests show that payloads with quotes, `;`, `$()` or paths are rejected with 400.
- QG-005 "Sanitized Input" passes.

## T3 — Truthful health and limitations notice 🟠
**Files:**
- `astra-platform/src/app/api/health/route.ts`
- `README.md`
- the site banner (`TopBar.tsx` or the layout)

**Do:**
- Compute the model file hash; report `inference: available | unavailable` from a real check.
- `READY` only when inference works.
- Add a short "Known limitations" section: weights not published, confounds under review, live inference offline.

**Done when:** the live health shows `DEGRADED` / inference unavailable until T4 + Phase 3 land.

## T4 — Model weights 🔴 (needs your decision)
**Question:** do you, or the original author, still have `models/saved/best_star_transformer_shared.pt` (SHA256 `bf374ce4…d388`), `best_star_cnn_dual_aug.pt` and the `*.onnx.data` files?

- **If yes:**
  - Publish them as a GitHub Release asset or with Git LFS (about 5–7 MB each).
  - Add `models/MANIFEST.json` with hashes.
  - Re-export ONNX as a single file.
  - Verify 78.17% from a clean clone.
- **If no:**
  - Retrain the shared model and the CNN on the frozen splits (after T7).
  - Record the result as *v1-retrained* in an ADR; small differences are expected.

**Done when:** `training/evaluate.py --split test` reproduces the published metrics from downloaded weights.

## T5 — Green CI 🟠
**Files:**
- `.github/workflows/ci.yml`
- `astra-platform/package-lock.json`, `postcss.config.mjs`, `eslint.config.mjs` (new)
- `.gitattributes` (new)
- `pyproject.toml`

**Do:**
- Commit the lockfile and missing configs.
- Smoke test: `HybridTransformer(variant="shared")(torch.randn(2, 2, 1000))`, and StarCNN with its real input shape.
- Point the integrity job at `docs/engineering-log/phase6_*_ids.json`.
- Fix the build backend to `setuptools.build_meta`.
- Add `.gitattributes` so hashes match on Windows.

**Done when:** all CI jobs pass on a PR, and a fresh `npm ci && npm run build` produces a styled app.

## T6 — Baseline next to the model 🟠
**Files:**
- `artifacts/experiments/EXP-0001-metadata-baseline.py` (written in this audit), promoted to `training/baselines.py`
- the README results table

**Do:**
- Report RF / logistic regression on metadata features beside the transformer, with CIs.
- State clearly that the variable-class period is a catalog value.

**Done when:** the README and research page show the baseline row; QG-004 "Baseline Mapped" can be evaluated.

## T7 — One config, runnable commands 🟠
**Files:**
- 11 files containing `/Users/soumyadebtripathy` paths
- `training/*.py` argparse blocks
- `README.md`

**Do:**
- Add a config module with env overrides.
- Add `--seed`, `--data-dir`, `--out-dir`.
- Add `training/evaluate.py`.
- Verify every README command in a clean clone.

**Done when:** `grep -r "/Users/" pipeline training` is empty, and every documented command runs.

## T8 — Single source of truth for metrics 🟠
**Do:**
- Write `tools/build_platform_artifacts.py` to produce `data/artifacts/*.json` and `astra.sqlite` from evaluation outputs.
- Fix NLL=ECE.
- Delete the metrics, selective-prediction, per-class-ECE and lineage constants from `constants.ts`; the UI reads only the artifacts.

**Done when:** README, artifacts and UI show identical numbers, all regenerated by one command.

## T9 — Documentation fixes 🟡
**Do:**
- Fix the 24 broken links in `docs/`.
- Correct the detrending description and the Phase 8 verdict items (ONNX inference, dynamic hash check, CSV upload).
- Use one canonical repo URL and author list.

**Done when:** `python tools/scripts/validate_agentos.py` shows 100/100.

## T10 — Honest cross-validation 🟠
**File:** `training/cross_validate.py`

**Do:**
- Exclude test stars.
- Group by `duplicate_group_id`.
- Use an inner validation split for epoch selection; report the outer fold.
- Report bootstrap CIs.

**Done when:** the CV estimate is unbiased and documented. Expect it to move closer to the test accuracy.

## T11 — De-confounded period search experiment 🔴
**Files:** `pipeline/preprocess.py` (new versioned preprocessing; v1 untouched), experiment log

**Do:**
- Run Lomb–Scargle (log grid) + BLS for every star, independent of class.
- Use a time-based detrending window.
- Bin all cadences to 30 min.
- Retrain the shared model + baseline.
- Compare against v1 under T10's protocol.

**Done when:** an experiment log reports v1 vs v2 with CIs, and an ADR records which preprocessing becomes the default.

## T12 — Media diet 🟡
**Files:** `astra-platform/public/*.mp4|mp3`, `CosmicBackground.tsx`, `SpaceHum.ts`

**Do:**
- Keep at most one compressed background (≤ 2 MB) or a static poster.
- No autoplay audio.
- Respect `prefers-reduced-motion`.
- Stop committing large media.
- Rewrite git history only with explicit team approval.

**Done when:** the first load on `/analysis` is under 3 MB.

---

## Recommended next phase (awaiting approval)

**Phase 0 + start of Phase 1: tasks T1, T2, T3 and T5, plus the T4 decision.**
- About 3–5 working days.
- Changes are confined to the API routes, two pages, CI config, build configs and docs notices.
- No scientific results, datasets, splits or model code are modified.

After it:
- The live site no longer shows invented predictions.
- The injection path is closed.
- CI is green.
- The project is ready for reproducibility work (T4, T7, T8).
