# ASTRA — Task Checklist

The working checklist for every task. Read it before starting, update it while working, and never skip an item silently. If an item can't be done, mark it ⚠️ and say why.

Legend: `[x]` done and verified · `[ ]` open · `[~]` in progress · `[!]` blocked or failed (with reason)

## Workflow rule (permanent, set 2026-11-09)

1. Read this file before starting.
2. Update task status as work progresses.
3. Test and verify every change.
4. Create or update the relevant PR.
5. Review CI and the complete diff.
6. Merge only when all acceptance criteria pass.
7. Update project documentation and this checklist.
8. Report completed tasks and remaining blockers.

Never stop after creating a PR when the task includes merging it. Never deploy manually or claim production is fixed unless verified.

**Repository conventions**
- Default branch `main`, no branch protection.
- Merge strategy: **rebase merge**. History is linear, with no merge commits, and this keeps logical commits intact.
- Commits authored as `yeshika-02`.
- CI must pass all 5 jobs on `main` today: Lint, Python 3.11, Python 3.12, Dataset integrity, Web platform. After #8 there are 6 (plus Fresh-clone reproduction), and after #4 the AgentOS Health Check runs on every push and PR.
- During the sprint: one branch and PR per workstream, merged together on Day 7 in dependency order (7_DAY_SPRINT.md §6).

---

## 7-day sprint (2026-11-09 → 2026-11-15) — see [7_DAY_SPRINT.md](7_DAY_SPRINT.md)

Status values: **Pending** · **In Progress** · **Blocked** · **Completed**.

**Tracker policy (dossier §3, A1):** this file is edited only on `sprint/tracking`. Each workstream PR also lists its tasks, tests and commits in its description.

Priority: P0 = must land this sprint · P1 = planned · P2 = optional.

| ID | Task (old ID) | Pri | Status | Branch | PR | Commits | Tests |
|---|---|---|---|---|---|---|---|
| SP-00 | Sprint dossier, tracker, Phase 0 merge record | P0 | Completed (merged last, 2026-11-16) | `sprint/tracking` | #2 | planning 0457af5… + one tracker update per session | tracker files kept current each session; validator 100/100 on the final `main` |
| SP-01 | Fix `rules-of-hooks` bug in `CosmicBackground.tsx` (T13) | P0 | Completed (merged 2026-11-16) | `fix/eslint-react-hooks` | #6 | 1843001 | crash reproduced on prod build, fixed: GFX LOW/MED/HIGH + reload with saved low, no React #300 |
| SP-02 | Fix 7 `react-hooks/purity` + 3 `set-state-in-effect` errors (T13) | P0 | Completed (merged 2026-11-16) | `fix/eslint-react-hooks` | #6 | f092e45, 1fcd973 | 0 react-hooks errors; counters, palette checked in browser; scroll highlight not verifiable (hidden pane) |
| SP-03 | Replace 34 `any` with typed API responses (T13, U5) | P1 | Completed (merged 2026-11-16) | `fix/eslint-react-hooks` | #6 | c588b85, 506b85c, f704e04 | tsc clean; Vitest 88/88; found val_accuracy + parseFloat bugs |
| SP-04 | Unused vars, JSX comment, font warning (T13) | P1 | Completed (merged 2026-11-16) | `fix/eslint-react-hooks` | #6 | f704e04, fc47b7d, 98f105e | ESLint 0 errors / 0 warnings; font self-hosted, verified in browser |
| SP-05 | Make ESLint a CI gate (roadmap 1.7) | P0 | Completed (merged 2026-11-16) | `fix/eslint-react-hooks` | #6 | 308bf5b | CI web job with `--max-warnings=0` passes (PR #6) |
| SP-06 | GitHub Actions → v7; caching; coverage artifact | P0 | Completed (merged 2026-11-16) | `ci/actions-v7` | #3 | f3778c1, 7166f53, ebed6f0, 07311e7, 9a345aa | actionlint clean (was 1 error); no Node 20 annotations; `python-coverage` artifact uploaded; release archive dry run 5,351/5,351 files |
| SP-07 | Fix 24 doc links → validator 100/100; PR-template casing; re-enable AgentOS workflows (T9) | P0 | Completed with exception (merged 2026-11-16) | `docs/agentos-validator-100` | #4 | 5c9bdc6, 04015a5, 4fc95e4, 7ee7a95 | validator 100/100 on Windows and Linux (CI); suite 21/21; `lint.yml` stays manual, see SP-36 |
| SP-08 | Python tests for `training/` helpers (roadmap 1.9, E2) | P1 | Completed (merged 2026-11-16) | `test/python-coverage` | #5 | a205ca4, 7ace8cd, 3a87533, 7267531, 40a6592 | 62 passed + 1 xfail; `training/` coverage 7% → 22.5% on #5; the ≥ 40% target is met by #7 (56%), so both land together on Day 7 |
| SP-09 | Central config replacing 27 hardcoded paths (T7, R3) | P0 | Completed (merged 2026-11-16) | `refactor/config-paths` | #7 | f8e2f9b, d43fb37, 7721ea6, 18d6ab2, a6da543, d78dda3, 820cb34, 11c0a4f, c72bb07, 94f59b6 | machine paths 27 → 0 (`test_no_machine_paths`); config resolution tested; 60 passed; CI 5/5 green |
| SP-10 | `--seed` / `--data-dir` / `--out-dir` CLI flags (T7, R2) | P0 | Completed (merged 2026-11-16) | `refactor/config-paths` | #7 | 015600c, 8f297db, 74ba11d, 98fcd3b, 5079fe5, 58b502a, 625f452 | end-to-end CLI runs on temp dirs (`test_train_cli`, `test_script_outputs`); `training/` coverage 56% |
| SP-11 | README reproduction commands that run (T7, R2) | P0 | Completed (merged 2026-11-16) | `docs/reproduction-and-env` | #8 | 513bc56, 6eb79a3, 7f29101, b35e6da, eea4aa8, 432b870, 8c235a6, fb170dc, eb56087, e07dbe9, 490176c, e63299a | all 8 Phase 3/4 commands exit 0 in the locked env (training/CV with fewer epochs/folds); `test_readme_commands` checks every documented flag; Phase 1–2 marked network-bound and historical |
| SP-12 | Pinned Python lock incl. `onnxruntime` (R5) | P1 | Completed (merged 2026-11-16) | `docs/reproduction-and-env` | #8 | 62cdc22, ba8273a, 807e0c6, 1d61e00, fb170dc | `requirements-lock.txt` (uv, universal, `--exclude-newer 2026-10-27`, 87 packages, torch excluded); clean venv: `pip check` OK, 92 passed; `test_dependency_lock` mutation-checked |
| SP-13 | Fresh-clone verification script | P1 | Completed (merged 2026-11-16) | `docs/reproduction-and-env` | #8 | 778f7a1, b69430e, f106d3f, c08536c, 5dee4d6, 82ce6d2, 4760f93 | `pipeline/prepare_from_repo.py`: 944 stars × 5 files verified, split hash matches, audit PASS; Windows fresh clone trains 1 epoch in 64 s with matching provenance; clean CI run on e63299a after the GitHub Actions incident (run 42681469860): all 6 jobs green, including the fresh-clone job |
| SP-14 | Weights investigation record + recovery/retraining plan, ADR-0061 (T4) | P0 | Completed (merged 2026-11-16) | `feat/evaluation-reproducibility` | #9 | 7808e08, 83ec32a, 6cf87c6, 83fbd37, d840e3f, 114b395 | `docs/model_recovery.md` + ADR-0061; `models/published_weights.json` (14 artifacts) agrees with all 4 hash sources (`test_published_weights`, 12 tests); `verify_weights.py`: shipped ONNX graphs + temperature match, all weights missing |
| SP-15 | `training/evaluate.py` with bootstrap CIs (roadmap 1.3) | P0 | Completed (merged 2026-11-16) | `feat/evaluation-reproducibility` | #9 | 8d0035d, 068a73d, 29cedae, 4f555f7, a9a1c0f, bd36f81, 7780876, 364dcca | untrained model on the real 142-star test split (20.4%, chance level); metric code reproduces every published number from the transcribed published confusion matrices; bootstrap CIs within 0.01 of published; hash gate (`HASH MISMATCH`, `--require-published`) tested and run in CI |
| SP-16 | Experiment provenance: git SHA, env, seed, data hash (R5) | P1 | Completed (merged 2026-11-16) | `feat/evaluation-reproducibility` | #9 | 4620903, aa1ef5f, db5ddb1, 370be8a, e0c4c61, 06e533a, 3cabc21, 103c2f8 | `astra.provenance` in training, CV and evaluation records; CI requires the record to name `GITHUB_SHA`, a clean tree and the frozen split; CI on #9: all 6 jobs green in both runs (fresh-clone job: provenance names GITHUB_SHA, shipped artifacts match, evaluation checks pass) |
| SP-17 | CPU reproduction run → EXP-0002 (needs D1) | P2 | Blocked (D1) | `feat/evaluation-reproducibility` | — | — | — |
| SP-18 | Metric inventory + authoritative table (T8, R4, S11) | P0 | Completed (merged 2026-11-16) | `fix/metrics-single-source` | #10 | 7f1ca5e, 7d36566, 26cf257, 8011143, b85aab2, 6ee02e0, c03b8d4, afe337d, b9c913f, 4bd1c55 | `models/published_metrics.json` + generated `docs/metrics.md`; every recorded value found in its cited report, matrices reproduce 7A/7C; README numbers all trace to the record (`test_readme_metrics`, mutation-checked); ADR-0063 |
| SP-19 | Artifact generator, NLL fixed, tested on synthetic outputs (T8) | P1 | Completed (merged 2026-11-16) | `fix/metrics-single-source` | #10 | f39b12b, 47fe53f, 12b1140, bac7b77, 0c3df6f | `pipeline/build_platform_artifacts.py`; NLL/ECE/Brier agree with `calibration.py` on synthetic logits; `--evaluation` recomputes NLL from logits; `--check` + test keep outputs current; artifact values changed only for the CNN row and the copied NLL |
| SP-20 | UI reads only generated artifacts; unsourced constants removed (T8, U3) | P1 | Completed (merged 2026-11-16) | `fix/metrics-single-source` | #10 | d7d5019, 9478b00, ebcec24, 5d66c57 | lineage counts without source → "count not recorded"; `SELECTIVE_PREDICTION_DATA`/`PER_CLASS_ECE` removed; constants and page literals pinned to the record; typecheck + 88 Vitest pass; CI on #10: all 6 jobs green in both runs (head 4bd1c55) |
| SP-21 | Honest CV: no test stars, `duplicate_group_id`, nested selection, ADR-0062 (T10, S7) | P0 | Completed (merged 2026-11-16; carried over from Day 4) | `fix/honest-cross-validation` | #12 | 7985af6, 0c6dc42, 0e6ee75, 898fd6a, 41cdbd9 | synthetic tests: no test-star leakage, no group straddling, reported score is the outer fold's (mutation-checked); real-data smoke run (802-star pool, 142 excluded); CI green |
| SP-22 | `training/baselines.py` (T6, S2) | P1 | Completed (merged 2026-11-16; carried over from Day 4) | `feat/feature-baselines` | #13 | 506d457, 32d05d3, 1b6b9fa, 29ad07a, 810cfa9, 128d886, 1af4be8, 2b46966, d9f0177, c677bde, 406cd40 | all 8 EXP-0001 numbers reproduced exactly; light-curve statistics baseline 79.58% (EXP-0003); recorded and shown beside the model (README, docs/metrics.md); CI on #12 and #13: all 6 jobs green in both runs (#13 after a one-star tolerance fix found by Linux CI) |
| SP-23 | Detrend/cadence characterisation tests (S4) | P1 | Completed (merged 2026-11-16) | `test/preprocessing-validation` | #11 | fad7711, 1e828a9, 59e5ae5, 9d34533 | golden test (fixture from unmodified v1; outputs byte-identical after refactor); retained sinusoid share by period × cadence pinned; shipped Cepheid/RR Lyrae amplitude evidence |
| SP-24 | Period-search characterisation tests (S5) | P1 | Completed (merged 2026-11-16) | `test/preprocessing-validation` | #11 | bbc9ee3 | grid resolution, box vs sinusoid recovery, power ∝ flux², shipped edge pile-up (57% Solar-like / 28% Stable) |
| SP-25 | Pipeline input validation and clear errors (E4) | P1 | Completed (merged 2026-11-16) | `test/preprocessing-validation` | #11 | 147c9f8, 76d7e63, bbb49e0, 260d5dc, c0baf3d | `cli_validation` types in 6 entry points (10 subprocess cases); `process_star` stage "input"; failure stages leave no partial output; `preprocess.py` coverage 57%; CI on #11: all 6 jobs green in both runs (head c0baf3d) |
| SP-26 | Opt-in preprocessing v2, ADR-0064 (needs D2) | P2 | Blocked (D2) | `feat/preprocess-v2-optin` | — | — | — |
| SP-27 | API param validation, shared DB handle, generic errors (P8) | P1 | Completed (merged 2026-11-16) | `fix/api-reliability` | #14 | d8b99e0, bf473ff, 67926ef, ee77882, 57d6408, 8ba404a, 00688a4, 94d0759, 77da73f, cfc021f, c69bd9c | one read-only `immutable` handle (`getDatabase()`); query parsing with 400s that name the parameter (limit ≤ 1000 for the sky map); LIKE wildcards literal; `parseTicId` on star detail and light curve; `serverError()` in all 10 routes; route hygiene guard; ADR-0066; CI green |
| SP-28 | Consistent loading / empty / error / unavailable states | P1 | Completed (merged 2026-11-16) | `fix/api-reliability` | #14 | 4bf8bbd, 35bdeea, 732b0aa, c03f1ef, 58b70fb, 9d706ae, 774a57d, 9fb52c4, c9452e2, 782e32e, 5b9260a, ba8c9a9, 88d4eb2, a0f2084 | `PageLoading` / `LoadError` / `PageError`, `combineQueries`, `ApiError` with no retry on 4xx, on all 10 data pages; OSINT crash and replay "unavailable" mislabel fixed; checked by hand against a server with the database missing; page-state guard; Vitest 286 |
| SP-29 | Reduced motion, ARIA, keyboard navigation (U4) | P1 | Completed (merged 2026-11-16) | `feat/accessibility-media` | #15 | d7ef412, a0b76e1, 29d84d3, 92483cc, 0a09c68, bd24121, 3f45f3d, 231133f, 29dd428, bb57654, 16b37d0, ca7e2c1 | axe-core 4.14 (WCAG 2.1 A/AA + best-practice): 0 violations on the 10 main pages, down from 3–4 each; reduced motion in CSS, framer-motion and canvas code; skip link; chart text alternatives; keyboard-operable replay stages and command palette; `tests/accessibility.test.ts`; ADR-0067. Lighthouse 12.6.1 accessibility 100 on all 10 pages (Day 7) |
| SP-30 | Media diet without history rewrite (U1, T12) | P1 | Completed (merged 2026-11-16) | `feat/accessibility-media` | #15 | a92e389, d0a6f05, 26df0a3 | no autoplay audio (state not persisted); video on `/` only, mounted after load, skipped for reduced motion / Save-Data / low graphics; `/analysis` loads 0.91 MB with no media requests (was a 90 MB stream); 12 media files (~277 MB) unreferenced and kept until D7; no history rewrite |
| SP-31 | Explainability methods + faithfulness test (S10) | P2 | Not started (optional; deferred) | `feat/explainability-methods` | — | — | optional WS-15; no real model outputs exist without the weights (D4) |
| SP-32 | Day 7: review all PRs together | P0 | Completed | — | #2–#15 | review comment on each PR | full own diffs, cross-PR overlaps (6 cross-stack files checked in the merged state), protected paths (only EXP-0003 added), CI on every head, acceptance criteria; Lighthouse 12.6.1 run for SP-29: 100 on all 10 pages |
| SP-33 | Day 7: rebase merge in dependency order; verify `main` | P0 | Completed | — | #3–#15, #16 | #3 → #4 → #5 → #6 → #7 → #8 → #9 → #10 → #11 → #12 → #13 → #14 → #15 → #16 → #2 | stacked children rebased onto `main` before merging (ADR-0060); after every merge `main`'s tree matched the tested simulation byte for byte; authors and author dates preserved; `main` CI green on 3aab237 (all jobs, both stacks combined); AgentOS Validate green on every merge |
| SP-34 | Day 7: full validation on `main` | P0 | Completed | `ci/coverage-astra` | #16 | d3ef6c9 | fresh GitHub clone of `main` at `3aab237`, pinned lock venv: Python suite 264 passed + 1 expected failure; `prepare_from_repo.py` OK (944 stars × 5 files verified, split hash ebcdc44c…, audit PASS); one-epoch training OK; provenance checks all match (dataset and split hashes, 1 373 701 parameters, seed 42, commit, clean tree); `verify_weights.py` OK (shipped ONNX graphs and temperature file match the published hashes); evaluation checks pass (141 val stars, unverified checkpoint correctly flagged); web: `tsc` and `eslint --max-warnings=0` clean, 351 Vitest passed; build OK; AgentOS validator 100/100 on the final tree (66 ADRs, 0 broken references); `--cov=astra` added to CI coverage (all 13 checks green; `astra/` now in the report: config 100%, provenance 97%, console 86%) |
| SP-35 | Day 7: CHANGELOG (incl. `v1.1.0` tag), status, roadmap; merge tracker last | P0 | Completed | `sprint/tracking` | #2 | Day 7 tracker commits | CHANGELOG: sprint entries moved under `main`, `v1.1.0` reconciled (lightweight tag on 98b1508, failed release run, no entry); next version is owner decision D8; status, roadmap and state updated; tracker merged last |
| SP-36 | AgentOS `lint.yml`: framework code fails its own lint (52 ruff errors with defaults, 3 yamllint) | P2 | Blocked (D6) | — | — | — | found in SP-07 |
| SP-37 | Upload preprocessing: robust outlier clipping aligned with training (audit P7) | P2 | Pending (Phase 3) | — | — | — | pinned by an expectedFailure test in #5 |

### Findings log (sprint)

| Date | Source | Finding | Routed to |
|---|---|---|---|
| 2026-11-09 | SP-06 | `v1.1.0` release run failed at "Create release archive"; logs expired, cause unconfirmed; step replaced with `git archive` | #3 |
| 2026-11-09 | SP-06 | `release.yml` body advertises "Verified Metrics (Zero-Hallucination)" and "8/8 audits PASS" | SP-18 |
| 2026-11-09 | SP-07 | `docs/index.md` states "All scientific results have been independently verified" | SP-18 |
| 2026-11-09 | SP-08 | Upload clipping uses non-robust mean/std (spike survives at abs(z) ~ 31) | SP-37 |
| 2026-11-09 | SP-08 | `ASTRADataset` silently falls back to a random split without frozen files; test-split leakage check ignores `val` | SP-09, SP-21 |
| 2026-11-09 | SP-03 | UI showed a hidden hardcoded val accuracy (field missing from `/api/model`) | fixed in #6; source in SP-20 |
| 2026-11-09 | SP-09 | Three calibration temperatures in the repo: 1.257665 (published, UI, upload), 1.258631 (`models/saved/optimal_temperature.txt`), 1.2944 (uncertainty fallback) | SP-18 |
| 2026-11-09 | SP-09 | 9 report writers crashed (missing output dir), reports written in cp1252, seaborn/pandas/onnxruntime undeclared, `cleanup_data.py` deleted files by default | fixed in #7 |
| 2026-11-09 | SP-11 | `freeze_phase6_splits.py` uses 70/10/10/10 ratios but the committed split is 70/15/15/0, so the script cannot regenerate the published split | SP-21 (documented in README) |
| 2026-11-09 | SP-11 | Model weights not shipped: both ONNX files reference absent `.onnx.data` weight files and no `.pt` is tracked, so inference returns 503 on every clone | SP-14 |
| 2026-11-09 | SP-11 | `onnx`/`onnxscript` undeclared: `export_model.py` crashed under torch ≥ 2.9 (dynamo exporter) | fixed in #8 |
| 2026-11-09 | SP-11 | README documented flags and paths that do not exist (`--variant`, `--model`, `--split`, `splits/`, `.pt` files, CSV upload) | fixed in #8 |
| 2026-11-09 | SP-13 | Scripts crashed with `UnicodeEncodeError` when stdout was redirected on Windows (cp1252) | fixed in #8 |
| 2026-11-10 | SP-14 | `model_registry.json` records the hash of the missing `best_star_transformer_shared.onnx.data` (`5a8fcc0d…`) and the shipped ONNX graph matches its recorded hash, so recovered files can be verified byte for byte | SP-14 (manifest) |
| 2026-11-10 | SP-14 | `Rexy-5097/ASTRA` (cited in CITATION.cff/README) is this repository before a transfer: not a second source of weights | recorded |
| 2026-11-10 | SP-14 | Temperature file CRLF-converted on Windows, so its registry hash failed | fixed in #9 |
| 2026-11-10 | SP-15 | Published test confusion matrices exist only as PNGs; transcribed, they reproduce all published test metrics and match the shipped test split | test fixtures in #9 |
| 2026-11-10 | SP-15 | `docs/reproducibility.md`: every step had a failing command, and its dataset check compared an array hash with the manifest hash (could never pass) | fixed in #9 |
| 2026-11-10 | SP-16 | `git_commit` was taken from the caller's working directory ("unknown" or a wrong repository when run elsewhere) | fixed in #9 |
| 2026-11-10 | Review | Without `--out-dir`, `train_transformer.py`/`train_cnn.py` overwrote the published records in `models/saved/` (experiment metadata, history, confusion matrix, report), and `calibration.py` overwrote `optimal_temperature.txt`; pre-sprint behaviour kept by #7 | fixed in #9 (defaults now `outputs/`) |
| 2026-11-10 | Review | Random-split training runs recorded the frozen split's hashes next to `frozen_split: false` | fixed in #9 |
| 2026-11-10 | Review | `--require-published` passed a hash-verified checkpoint that did not reproduce the published numbers; no tool compared the confusion matrix | fixed in #9 |
| 2026-11-10 | Review | `evaluate.py` crashed with tracebacks on invalid numbers or a missing frozen split | fixed in #9 |
| 2026-11-10 | Review | Existing Windows clones keep a CRLF temperature file after the `.gitattributes` change, failing its hash check | #9 prints the refresh command; refresh once after merge |
| 2026-11-10 | Review | `release.yml` release notes still claim "Verified Metrics (Zero-Hallucination)" and "8/8 PASS"; a tag on Day 7 (SP-35) would publish them | fixed in #10 (SP-35 blocker cleared) |
| 2026-11-10 | Review | Coverage step (#3) measures `pipeline`, `training`, `data` but not `astra` (#7) | SP-34 (add `--cov=astra` after merge) |
| 2026-11-10 | Review | #7–#9 alone score below 100/100 on the validator (ADR-0060 keeps the ADR index and ADR-0060 on this branch); the gate (>= 85, no broken links) still passes, and the simulated final `main` scores 100/100 | Day 7 note |
| 2026-11-10 | Review | Day 7 simulation: all 8 PRs rebase onto `main` in the planned order without conflicts; merged Python suite 173 passed + 1 expected failure (after the CRLF refresh); merged `ci.yml`/`validate.yml` coherent | SP-33 input |
| 2026-11-10 | SP-18 | README's CV table, ECE 0.0478, NLL 0.5332, selective-prediction table and entropy came from `phase7_benchmark_report.md`, an earlier 269-star experiment | fixed in #10 (marked superseded) |
| 2026-11-10 | SP-18 | Phase 7A CNN row (macro F1 0.7654) contradicts the published CNN confusion matrix; 7C (0.7635) matches it | fixed in #10 (7C used) |
| 2026-11-10 | SP-18 | `docs/experiments.md` variant accuracies 74.47% / 75.18% / 73.05% have no source; matrices give 80.99% / 84.51% / 72.54% | fixed in #10 |
| 2026-11-10 | SP-19 | The calibration audit itself lists NLL equal to ECE; the copy spread to three artifacts | fixed in #10 (NLL null until logits exist) |
| 2026-11-10 | SP-20 | Lineage funnel counts (3200, 2847, 1621, 1102, 978) have no source; two unused UI tables contradicted the reports | fixed in #10 |
| 2026-11-11 | SP-23 | Detrend retention measured: a 6.2-d signal keeps ~0% / 0.7% / 35% of its spread at 2 / 10 / 30-min cadence | pinned in #11; input for SP-26 (D2) |
| 2026-11-11 | SP-24 | BLS: 5-d sinusoid at 30-min cadence returns ~27 d; grid step is 10% of the period at 0.1 d; edge pile-up is in the shipped data, not in synthetic noise | pinned in #11; input for SP-26 (D2) |
| 2026-11-11 | SP-25 | `process_star` accepted an unknown class and wrote label -1; 0 workers / 0 sectors surfaced as unrelated errors | fixed in #11 |
| 2026-11-11 | Process | Day 4 was reported as done, but WS-09 (SP-21) and WS-10 (SP-22) were never started | done on 2026-11-12 in #12 and #13 |
| 2026-11-12 | SP-21 | No shipped metadata has `duplicate_group_id`, so the frozen split grouped each star alone; the pipeline's rule (same TIC or within 2") finds no duplicates in the 944 stars, so this did not leak | recorded in ADR-0062; CV now groups with the rule |
| 2026-11-12 | SP-21 | Old CV report text claimed a "previously achieved 81.48%" and "N=9 per validation fold" | removed in #12 |
| 2026-11-12 | SP-22 | 12 statistics of the network's own inputs give a random forest 79.58% / 0.7867 vs the transformer's 78.17% / 0.7677 (not a paired test) | EXP-0003; reported beside the model in #13 |
| 2026-11-12 | SP-22 | EXP-0001 reproduces exactly with scikit-learn 1.9.1 (recorded with 1.6.1) | pinned in #13 |
| 2026-11-12 | SP-27 | `/api/lightcurve/<id>` put the raw id into a file path and returned the exception, with the server path, in its 404; 10 routes returned `error.message`; `q=%` matched every star; `/api/stars/12abc` served TIC 12 | fixed in #14 |
| 2026-11-12 | SP-28 | OSINT rendered an error body as a report and crashed (`fetch().then(r => r.json())` without `r.ok`); Mission Replay showed "inference unavailable" for failed requests; target pages said "not found" for server errors | fixed in #14 |
| 2026-11-12 | SP-30 | Every route streamed its own background video: 90 MB on `/analysis` (11 MB buffered in 25 s); a saved audio state restarted sound without a click | fixed in #15; 12 unreferenced files kept (D7) |
| 2026-11-12 | SP-29 | axe: unlabelled volume slider, unfocusable scroll region, missing or skipped headings on every page; no chart text alternatives; replay stages mouse-only; no reduced-motion support | fixed in #15 |
| 2026-11-12 | Process | A commit with a failing test was made on #15 (the chain checked `grep`'s exit code, not Vitest's) | caught before push and amended; commits now gated on Vitest's own exit code |
| 2026-11-16 | Process | Day 7 simulation: a failed `node_modules` junction made the frontend checks run from the repo root; npx fetched `eslint@10.15.0` into its cache and Vitest left a cache folder at the root | folder removed; checks rerun inside the simulation |
| 2026-11-16 | AgentOS | `validate_agentos.py` looks for `artifacts/decisions` with a forward slash, so its unindexed-ADR check never fires on Windows | noted; framework fix out of sprint scope |
| 2026-11-16 | SP-32 | Lighthouse 12.6.1 (desktop, local production build of the merged state): accessibility 100 on all 10 main pages, no failing audits | SP-29 criterion met |
| 2026-11-16 | SP-33 | Each merge cancelled the previous `main` CI run (`cancel-in-progress`); AgentOS Validate passed on every intermediate `main` | expected; final run checked |
| 2026-11-16 | SP-35 | `v1.1.0` is a lightweight tag on 98b1508 (2026-06-13, background-video styling); its release run failed at the archive step (fixed in #3), so no GitHub release exists; CHANGELOG has `[1.0.0]` but no `[1.1.0]` and no `v1.0.0` tag | reconciled in CHANGELOG; next version is D8; no tag changes |
| 2026-11-16 | SP-33 | Rebase merging gives every commit a new SHA on `main` (same content, author and author date); the SHAs in the task table are the PR-branch commits | use each PR's commit list to map them |
| 2026-11-10 | Review | Process slip: 14 review-fix commits on #9 were authored as `day7-sim` (simulation script wrote the shared git config); identity restored | owner then chose to re-author them: rewritten to `yeshika-02` (content, messages and author dates unchanged; same tree) and #9 force-pushed with lease, head `e969753` |

### Acceptance criteria

- **SP-00:**
  - Dossier and tracker reflect the verified state.
  - Phase 0 merge recorded.
  - No new broken links.
- **SP-01/02:**
  - 0 `react-hooks` errors.
  - Affected pages render the same (manual check).
  - Typecheck, tests and build green.
- **SP-03/04:**
  - `npx eslint .` reports 0 errors.
  - Each remaining warning is justified in the PR.
- **SP-05:** the CI lint step is required and passes.
- **SP-06:**
  - No Node 20 deprecation annotations.
  - 5 jobs green.
- **SP-07:**
  - Validator 100/100 on Windows and Linux.
  - AgentOS workflows run on push/PR and pass.
  - Report content unchanged (link targets only).
- **SP-08:**
  - `training/` coverage ≥ 40%.
  - Tests deterministic and CPU-only.
- **SP-09/10:**
  - `grep -rn /Users/ pipeline training` is empty.
  - Scripts run from a fresh clone with the documented flags.
  - Config resolution tested.
- **SP-11/12/13:**
  - Every README command runs.
  - The lock installs cleanly.
  - The fresh-clone script passes locally and in CI.
- **SP-14:** plan and ADR-0061 cover recovery, retraining, storage and verification-by-hash.
- **SP-15:**
  - Tested end-to-end with an untrained model on real arrays.
  - Reports metrics with bootstrap CIs.
- **SP-16:** experiment metadata contains the git SHA, environment, seed and dataset hash.
- **SP-17:**
  - Only if D1 = yes.
  - EXP-0002 logged with CIs.
  - Compared with the published 78.17%, never replacing it.
  - Weights not committed.
- **SP-18:** every number shown in README or UI has a documented source, or is flagged unverifiable.
- **SP-19:**
  - Generator unit-tested.
  - NLL computed from probabilities, not copied.
- **SP-20:** no UI metric without a source.
- **SP-21:** synthetic-data tests prove no test-star leakage and no duplicate-group straddling, and that the reported score is the outer fold's.
- **SP-22:**
  - Reproduces the EXP-0001 numbers exactly.
  - Documented beside the model with caveats.
- **SP-23/24/25:**
  - `preprocess.py` coverage ≥ 50%.
  - A golden-hash test proves v1 outputs are unchanged.
  - Bad inputs give clear errors.
- **SP-26:**
  - Only if D2 = yes.
  - v1 stays the default (golden test).
  - v2 validated on synthetic curves with known periods.
- **SP-27/28:**
  - New API tests pass.
  - No internal error text reaches clients.
  - Every data view has loading, empty, error and unavailable states.
- **SP-29/30:**
  - Lighthouse accessibility ≥ 90 on the main pages (local build).
  - No autoplay audio.
  - `/analysis` first load < 5 MB.
- **SP-31:**
  - Faithfulness test passes on an untrained model.
  - Nothing is rendered without real model output.
- **SP-32–35:** see [7_DAY_SPRINT.md](7_DAY_SPRINT.md) §5 (Day 7) and §11.
- **SP-36:** owner decides (D6) whether to fix framework lint debt or keep `lint.yml` manual.
- **SP-37:** upload path uses robust clipping consistent with training; the expectedFailure test then passes.

---

## Completed: Phase 0 merge (2026-11-09)

[PR #1](https://github.com/yeshika-02/ASTRA/pull/1), branch `phase0/integrity-security-hotfix` → `main`.

- [x] Checked for an existing PR (none existed)
- [x] Created PR #1 targeting `main` with a summary of all Phase 0 changes and test results
- [x] Reviewed the complete diff: 376 files, 0 deletions, research paths untouched except `training/upload_inference.py`, no secrets. **Found and fixed:** 44 files committed with CRLF; fixed in `31bb98f` by scoping `.gitattributes` to hash-locked artifacts
- [x] All 5 GitHub Actions jobs passed on head `31bb98f` (10/10 checks: push + pull_request)
- [x] No merge conflicts, no failing checks, 0 review comments or threads
- [x] Security fixes and their tests confirmed in the PR head
- [x] Merged by rebase merge at 2026-11-08T20:31:10Z UTC; `main` tip `1beca47`
- [x] `main`'s tree is identical to the reviewed head; post-merge CI on `main` passed (run 42520528644, 5/5 jobs)
- [x] Deployment status checked, no manual deploy. **Production was not updated:** the live site still served the pre-Phase-0 code after the merge, and GitHub has no deployment integration for this repo. Production is deployed from a separate Vercel account and is out of scope until after the sprint (owner decision, 2026-11-09)
- [x] Checklist, `PROJECT_STATUS.md` and AgentOS records updated (this commit)

## Completed

### Phase 0 — integrity and security hotfix (2026-11-09)
- [x] T1 Remove fabricated predictions, probabilities, explanations and attention maps (ADR-0058)
- [x] T2 Close command injection: no shell, strict validation, flux via stdin
- [x] T3 Truthful `/api/health` + limitations notices
- [x] T5 CI fixed; build configs committed
- [x] AgentOS GitHub files reviewed and adapted (ADR-0059)
- [x] Tests: 88 web + 21 Python; verified to fail on the original code
- [x] Docs: PROJECT_AUDIT.md §11, PROJECT_STATUS.md, UPDATED_ROADMAP.md, PRIORITY_TASKS.md, context/state.md

## Backlog

The former Phase 1 backlog (T4, T7, T8, T9, T13, Actions upgrade) is now scheduled in the sprint table above (SP-01…SP-35).
