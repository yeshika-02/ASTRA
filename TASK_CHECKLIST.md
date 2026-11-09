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
- CI must pass all 5 jobs: Lint, Python 3.11, Python 3.12, Dataset integrity, Web platform.
- During the sprint: one branch and PR per workstream, merged together on Day 7 in dependency order (7_DAY_SPRINT.md §6).

---

## 7-day sprint (2026-11-09 → 2026-11-15) — see [7_DAY_SPRINT.md](7_DAY_SPRINT.md)

Status values: **Pending** · **In Progress** · **Blocked** · **Completed**.

**Tracker policy (dossier §3, A1):** this file is edited only on `sprint/tracking`. Each workstream PR also lists its tasks, tests and commits in its description.

Priority: P0 = must land this sprint · P1 = planned · P2 = optional.

| ID | Task (old ID) | Pri | Status | Branch | PR | Commits | Tests |
|---|---|---|---|---|---|---|---|
| SP-00 | Sprint dossier, tracker, Phase 0 merge record | P0 | In Progress | `sprint/tracking` | (tracker PR) | 6 planning commits (0457af5…) | validator: no new broken links (24 pre-existing) |
| SP-01 | Fix `rules-of-hooks` bug in `CosmicBackground.tsx` (T13) | P0 | Completed (in review) | `fix/eslint-react-hooks` | #6 | 1843001 | crash reproduced on prod build, fixed: GFX LOW/MED/HIGH + reload with saved low, no React #300 |
| SP-02 | Fix 7 `react-hooks/purity` + 3 `set-state-in-effect` errors (T13) | P0 | Completed (in review) | `fix/eslint-react-hooks` | #6 | f092e45, 1fcd973 | 0 react-hooks errors; counters, palette checked in browser; scroll highlight not verifiable (hidden pane) |
| SP-03 | Replace 34 `any` with typed API responses (T13, U5) | P1 | Completed (in review) | `fix/eslint-react-hooks` | #6 | c588b85, 506b85c, f704e04 | tsc clean; Vitest 88/88; found val_accuracy + parseFloat bugs |
| SP-04 | Unused vars, JSX comment, font warning (T13) | P1 | Completed (in review) | `fix/eslint-react-hooks` | #6 | f704e04, fc47b7d, 98f105e | ESLint 0 errors / 0 warnings; font self-hosted, verified in browser |
| SP-05 | Make ESLint a CI gate (roadmap 1.7) | P0 | Completed (in review) | `fix/eslint-react-hooks` | #6 | 308bf5b | CI web job with `--max-warnings=0` passes (PR #6) |
| SP-06 | GitHub Actions → v7; caching; coverage artifact | P0 | Completed (in review) | `ci/actions-v7` | #3 | f3778c1, 7166f53, ebed6f0, 07311e7, 9a345aa | actionlint clean (was 1 error); no Node 20 annotations; `python-coverage` artifact uploaded; release archive dry run 5,351/5,351 files |
| SP-07 | Fix 24 doc links → validator 100/100; PR-template casing; re-enable AgentOS workflows (T9) | P0 | Completed with exception (in review) | `docs/agentos-validator-100` | #4 | 5c9bdc6, 04015a5, 4fc95e4, 7ee7a95 | validator 100/100 on Windows and Linux (CI); suite 21/21; `lint.yml` stays manual, see SP-36 |
| SP-08 | Python tests for `training/` helpers (roadmap 1.9, E2) | P1 | Completed (in review) | `test/python-coverage` | #5 | a205ca4, 7ace8cd, 3a87533, 7267531, 40a6592 | 62 passed + 1 xfail; `training/` coverage 7% → 22.5% on #5; the ≥ 40% target is met by #7 (56%), so both land together on Day 7 |
| SP-09 | Central config replacing 27 hardcoded paths (T7, R3) | P0 | Completed (in review) | `refactor/config-paths` | #7 | f8e2f9b, d43fb37, 7721ea6, 18d6ab2, a6da543, d78dda3, 820cb34, 11c0a4f, c72bb07, 94f59b6 | machine paths 27 → 0 (`test_no_machine_paths`); config resolution tested; 60 passed; CI 5/5 green |
| SP-10 | `--seed` / `--data-dir` / `--out-dir` CLI flags (T7, R2) | P0 | Completed (in review) | `refactor/config-paths` | #7 | 015600c, 8f297db, 74ba11d, 98fcd3b, 5079fe5, 58b502a, 625f452 | end-to-end CLI runs on temp dirs (`test_train_cli`, `test_script_outputs`); `training/` coverage 56% |
| SP-11 | README reproduction commands that run (T7, R2) | P0 | Completed (in review) | `docs/reproduction-and-env` | #8 | 513bc56, 6eb79a3, 7f29101, b35e6da, eea4aa8, 432b870, 8c235a6, fb170dc, eb56087, e07dbe9, 490176c, e63299a | all 8 Phase 3/4 commands exit 0 in the locked env (training/CV with fewer epochs/folds); `test_readme_commands` checks every documented flag; Phase 1–2 marked network-bound and historical |
| SP-12 | Pinned Python lock incl. `onnxruntime` (R5) | P1 | Completed (in review) | `docs/reproduction-and-env` | #8 | 62cdc22, ba8273a, 807e0c6, 1d61e00, fb170dc | `requirements-lock.txt` (uv, universal, `--exclude-newer 2026-10-27`, 87 packages, torch excluded); clean venv: `pip check` OK, 92 passed; `test_dependency_lock` mutation-checked |
| SP-13 | Fresh-clone verification script | P1 | Completed (in review) | `docs/reproduction-and-env` | #8 | 778f7a1, b69430e, f106d3f, c08536c, 5dee4d6, 82ce6d2, 4760f93 | `pipeline/prepare_from_repo.py`: 944 stars × 5 files verified, split hash matches, audit PASS; Windows fresh clone trains 1 epoch in 64 s with matching provenance; CI on e63299a: all 6 jobs passed (fresh-clone job verified 944 stars, split hash ebcdc44c…, audit PASS, provenance match), but each run is marked failed because a GitHub Actions incident (2026-11-09 18:12 UTC) skipped creating some jobs; needs one clean run before Day 7 |
| SP-14 | Weights investigation record + recovery/retraining plan, ADR-0061 (T4) | P0 | Pending | `feat/evaluation-reproducibility` | — | — | — |
| SP-15 | `training/evaluate.py` with bootstrap CIs (roadmap 1.3) | P0 | Pending | `feat/evaluation-reproducibility` | — | — | — |
| SP-16 | Experiment provenance: git SHA, env, seed, data hash (R5) | P1 | Pending | `feat/evaluation-reproducibility` | — | — | — |
| SP-17 | CPU reproduction run → EXP-0002 (needs D1) | P2 | Blocked (D1) | `feat/evaluation-reproducibility` | — | — | — |
| SP-18 | Metric inventory + authoritative table (T8, R4, S11) | P0 | Pending | `fix/metrics-single-source` | — | — | — |
| SP-19 | Artifact generator, NLL fixed, tested on synthetic outputs (T8) | P1 | Pending | `fix/metrics-single-source` | — | — | — |
| SP-20 | UI reads only generated artifacts; unsourced constants removed (T8, U3) | P1 | Pending | `fix/metrics-single-source` | — | — | — |
| SP-21 | Honest CV: no test stars, `duplicate_group_id`, nested selection, ADR-0062 (T10, S7) | P0 | Pending | `fix/honest-cross-validation` | — | — | — |
| SP-22 | `training/baselines.py` (T6, S2) | P1 | Pending | `feat/feature-baselines` | — | — | — |
| SP-23 | Detrend/cadence characterisation tests (S4) | P1 | Pending | `test/preprocessing-validation` | — | — | — |
| SP-24 | Period-search characterisation tests (S5) | P1 | Pending | `test/preprocessing-validation` | — | — | — |
| SP-25 | Pipeline input validation and clear errors (E4) | P1 | Pending | `test/preprocessing-validation` | — | — | — |
| SP-26 | Opt-in preprocessing v2, ADR-0064 (needs D2) | P2 | Blocked (D2) | `feat/preprocess-v2-optin` | — | — | — |
| SP-27 | API param validation, shared DB handle, generic errors (P8) | P1 | Pending | `fix/api-reliability` | — | — | — |
| SP-28 | Consistent loading / empty / error / unavailable states | P1 | Pending | `fix/api-reliability` | — | — | — |
| SP-29 | Reduced motion, ARIA, keyboard navigation (U4) | P1 | Pending | `feat/accessibility-media` | — | — | — |
| SP-30 | Media diet without history rewrite (U1, T12) | P1 | Pending | `feat/accessibility-media` | — | — | — |
| SP-31 | Explainability methods + faithfulness test (S10) | P2 | Pending | `feat/explainability-methods` | — | — | — |
| SP-32 | Day 7: review all PRs together | P0 | Pending | — | — | — | — |
| SP-33 | Day 7: rebase merge in dependency order; verify `main` | P0 | Pending | — | — | — | — |
| SP-34 | Day 7: full validation on `main` | P0 | Pending | — | — | — | — |
| SP-35 | Day 7: CHANGELOG (incl. `v1.1.0` tag), status, roadmap; merge tracker last | P0 | Pending | `sprint/tracking` | — | — | — |
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
