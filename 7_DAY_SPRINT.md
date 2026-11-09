# ASTRA — 7-Day Sprint Dossier

**Sprint window:** Day 1–7 = 2026-11-09 → 2026-11-15 · **Owner:** `yeshika-02` · **Framework:** AgentOS (profile `ml`)
**Tracking branch / PR:** `sprint/tracking` (merged last) · **Task-level status:** [TASK_CHECKLIST.md](TASK_CHECKLIST.md)
**Built from:** the owner's sprint brief (2026-11-09), cross-checked against [PROJECT_AUDIT.md](PROJECT_AUDIT.md), [UPDATED_ROADMAP.md](UPDATED_ROADMAP.md), [PRIORITY_TASKS.md](PRIORITY_TASKS.md) and [PROJECT_STATUS.md](PROJECT_STATUS.md).

---

## 0. Summary

- The brief and the existing roadmap **agree on direction**. The brief's Days 1–6 map onto roadmap Phase 1 (reproducibility), Phase 2 (scientific validation) and Phase 5 (platform quality).
- Five places needed adjusting, mostly about **how** the work is done rather than what:
  1. Merging all PRs on Day 7 means shared tracker files would conflict, so they live in one tracking PR (§3, A1).
  2. Some workstreams depend on others, so those branches are stacked and merged in a fixed order (A2).
  3. Day 3 "find the weights" is already answered: they were never on GitHub (A4).
  4. Day 5 preprocessing fixes can't be validated without raw TESS data and a model, so the sprint characterises and adds an opt-in v2 instead of changing results (A5).
  5. One AgentOS-mandatory task (validator 100/100) was missing from the brief and is added to Day 1 (A6).
- **50+ genuine commits is realistic.** The plan scopes 15 workstreams with an estimated 70–90 meaningful commits, so the target holds even if optional items are dropped (§7).
- **Main risk:** production still serves the pre-Phase-0 code, including fabricated predictions and the command-injection path, until the owner deploys `main`. The sprint doesn't touch deployment, per the brief (§9, R1).

---

## 1. Verified starting state (checked 2026-11-09)

| Check | Result | Evidence |
|---|---|---|
| PR #1 merged | ✅ MERGED 2026-11-08T20:31:10Z UTC (rebase) | `gh pr view 1` |
| `main` contains Phase 0 | ✅ tip `1beca47`; tree identical to reviewed head `31bb98f` | `git rev-parse main^{tree}` |
| Post-merge CI on `main` | ✅ run 42520528644, 5/5 jobs | `gh run list --branch main` |
| Open PRs | none | `gh pr list --state open` |
| Uncommitted work | none (Phase 0 merge record was pending; committed on `sprint/tracking`) | `git status` |
| Unfinished branches | `phase0/integrity-security-hotfix` (local and remote) is fully merged; kept until the owner decides (D3) | `git branch -a` |
| GitHub CLI | `gh api user` → `yeshika-02` (Yeshika Sharma, id 206655782), active account | `gh auth status` |
| Git author | `yeshika-02 <yeshika715@gmail.com>` (repo-local) | `git config` |
| Email belongs to the account | ✅ GitHub links commits by this email to `yeshika-02` (only happens for verified emails) | `GET /repos/.../commits/1beca47` → `author.login = yeshika-02` |
| Model weights anywhere on GitHub | ❌ never committed in history, no LFS, 0 releases. `Rexy-5097/ASTRA` redirects to this same repo | `git log --all`, `gh release list` |
| Tags | `v1.1.0` exists; no matching CHANGELOG entry or release | `git ls-remote --tags` |
| AgentOS validator | 94/100 (only Cross-reference: 24 pre-existing broken links in `docs/`) | `python tools/scripts/validate_agentos.py` |
| ESLint | 86 findings: 46 errors in 20 files (34 `no-explicit-any`, 7 `react-hooks/purity`, 3 `set-state-in-effect`, 1 `rules-of-hooks`, 1 `jsx-no-comment-textnodes`), 40 warnings | `npx eslint .` |
| Hardcoded machine paths | 27 `/Users/...` paths in 11 Python files | `grep -rn /Users/` |
| GitHub Actions versions | repo uses `checkout@v4`, `setup-python@v5`, `setup-node@v4` (Node 20, deprecated); latest are v7 | GitHub releases API |
| Tests | 88 web (Vitest) + 21 Python, all passing; Python coverage was 8% before Phase 0 | CI |

---

## 2. Cross-verification: sprint brief vs previous plan

Verdicts:
- **Aligned:** same task, same intent.
- **Adjusted:** kept, but changed for a stated reason (see §3).
- **Added:** in the roadmap or required by AgentOS, missing from the brief.
- **Deferred:** valid, but outside this sprint.

| Brief item | Roadmap / audit link | Verdict | Notes |
|---|---|---|---|
| D1 Fix ESLint issues | T13 (new in Phase 0) | Aligned | 46 errors / 40 warnings measured; lint becomes a CI gate at the end |
| D1 Fix React bug in `CosmicBackground.tsx` | T13 (`rules-of-hooks`) | Aligned | Plus 7 `react-hooks/purity` errors (`Math.random` during render) in visual components |
| D1 GitHub Actions deprecation notices | TASK_CHECKLIST backlog | Aligned | Upgrade to v7 actions |
| D1 Improve test coverage | Roadmap 1.9, E2 | Aligned | Target the 0%-covered `training/` helpers first |
| — | **T9: fix doc links → validator 100/100; re-enable AgentOS workflows; PR-template casing** | **Added** | Mandatory under AgentOS (`CLAUDE.md`: validator must be 100/100) |
| D2 Resolve hardcoded local paths | T7, R3 | Aligned | 27 paths / 11 files |
| D2 Fix README reproduction commands | T7, R2 | Aligned | Depends on the config work (stacked) |
| D2 Environment configuration | Roadmap 1.5, R5 | Aligned | Python lock file; `onnxruntime` missing from requirements; package namespacing noted |
| D2 Test fresh-clone setup | Roadmap Phase 1 exit criteria | Aligned | Scripted check in a temp clone |
| D3 Investigate missing weights | T4, R1 | **Adjusted** | Already answered: never on GitHub. Remaining actions: ask the original author (D4) and/or a reproduction retrain (D1) |
| D3 Check Git history, releases, artifact storage | T4 | Aligned (done) | Recorded in §1; formal write-up in WS-07 |
| D3 Recovery or retraining plan | T4, roadmap decision | Aligned | ADR plus `docs/` plan |
| D3 Experiment reproducibility | Roadmap 1.3, R5 | Aligned | `training/evaluate.py`, provenance (git SHA, env), seeds |
| D4 Conflicting metrics | T8, R4, S11 | **Adjusted** | Metrics can't be regenerated without weights. Sprint delivers: inventory, authoritative table, generator tested on synthetic outputs, UI reading one source |
| D4 Evaluation methodology | Roadmap 2.6 | Aligned | Bootstrap CIs, paired comparisons |
| D4 Cross-validation and leakage | T10, S7 | Aligned | Exclude test stars, `duplicate_group_id` groups, nested selection |
| D4 Fair baselines | T6, S2, EXP-0001 | Aligned | Promote EXP-0001 into a tested `training/baselines.py` |
| D5 Detrending and cadence | T11, S4–S6 | **Adjusted** | Characterise with tests and add an opt-in v2. No change to v1 data or results (§3, A5) |
| D5 Preprocessing tests | E2 | Aligned | `preprocess.py` is at 14% coverage |
| D5 Dataset validation and error handling | Audit E4 | Aligned | |
| D6 APIs and frontend reliability | P8, U3 | Aligned | Param validation, DB handle reuse, error messages |
| D6 User-facing error states | Phase 0 follow-up | Aligned | |
| D6 Explainability "where supported by real outputs" | S10, roadmap 2.8 | **Adjusted** | No weights means no real outputs. Only methodology code tested on an untrained model; the UI shows explanations only from real inference (optional) |
| D6 Accessibility and UI consistency | U4, T12 | Aligned | Includes stopping 310 MB of autoplay media; **no git history rewrite** |
| D7 Consolidation, review, merge plan | Workflow rule | Aligned | §6 merge order |
| — | P4 Dockerfile / `render.yaml` | **Deferred** | Deployment-adjacent; brief freezes deployment work |
| — | Roadmap Phase 3 (inference service) | **Deferred** | Needs weights and deployment decisions |
| — | Roadmap Phase 4 (dataset expansion) | **Deferred** | Multi-week research |
| — | `v1.1.0` tag without a CHANGELOG entry | **Added** (Day 7) | Reconcile in CHANGELOG; no tag changes without the owner |

---

## 3. Adjustments and why

| ID | Issue found while cross-checking | Resolution |
|---|---|---|
| **A1** | The brief asks every PR to update `TASK_CHECKLIST.md`, `PROJECT_STATUS.md`, `CHANGELOG.md` and so on, **and** to merge everything on Day 7. Fifteen open PRs editing the same lines of the same files would make every rebase merge after the first conflict. | **Tracking-file policy:** the five tracker files are edited only on `sprint/tracking` (one PR, merged last). Each workstream PR records its tasks, acceptance criteria, tests and commit list in its **PR description**, and the tracker is updated (with PR number and commit SHAs) in the same session the work lands. Workstream PRs still update their own docs (README sections, `docs/`, ADRs). The intent of "update the checklist with every task" is kept without guaranteed conflicts. |
| **A2** | Several workstreams change the same files (`training/*.py`, `README.md`, `ci.yml`, `src/lib/hooks`). Branching all of them from `main` would mean overlapping edits. | **Stacked branches** where there's a real dependency (§6). The PR base stays `main`, the description names the parent PR, and the Day 7 merge goes in dependency order, rebasing children onto the updated `main`. |
| **A3** | ADRs are numbered sequentially, and parallel PRs would claim the same number. | **Pre-allocated ADR numbers** (§5). The index `context/decisions.md` is updated only on `sprint/tracking`. |
| **A4** | Day 3 "investigate missing weights": history, LFS, releases and the "upstream" repo were checked during this planning step. The weights were never on GitHub. | Day 3 records the finding and moves to what can actually be done: author recovery (owner action, D4), an `evaluate.py` + provenance toolchain, and an optional CPU reproduction run on the 944 shipped arrays (D1), recorded as an experiment that **never replaces** the published 78.17%. |
| **A5** | The detrending and period-search fixes (S4, S5) change the data, so their effect can only be validated by re-preprocessing from raw TESS light curves (not in the repo; multi-GB download) **and** retraining. That's an unsupported scientific change inside one sprint. | Day 5 adds characterisation tests that document the current behaviour, plus an **opt-in** `phase6_preprocess_v2` (cadence-aware window, Lomb–Scargle) validated on synthetic light curves. The default stays v1; frozen arrays and results are untouched (D2). |
| **A6** | The AgentOS validator at 94/100 violates the project rule in `CLAUDE.md`, and the brief doesn't list it. | Added as WS-03 on Day 1 (cheap, unblocks the AgentOS workflows). |
| **A7** | Contribution graph: commits appear on the profile only once they're **on the default branch**. With Day 7 merging, they appear on Day 7, under the commits' original author dates. | Expected. Rebase merge keeps each commit's author (`yeshika-02`) and author date. Nothing is backdated. |

---

## 4. Sprint rules (brief + AgentOS, combined)

1. **Genuine commits only.** No empty, artificial, duplicate, backdated or formatting-only commits made to raise the count. One commit = one coherent, independently useful unit (implementation, test, or doc change), with conventional messages (`fix:`, `feat:`, `test:`, `refactor:`, `docs:`, `ci:`).
2. **One workstream = one branch = one PR** targeting `main`. No unrelated tasks combined; dependent changes aren't split artificially.
3. **Each PR description** contains: task IDs, summary, changed files, tests run with results, acceptance criteria (checked), parent PR (if stacked), and the risks reviewers should look at.
4. **Every change is tested** before it's marked done. CI (5 jobs; 6 once lint is gated) must pass on the PR head.
5. **No merging before Day 7**, except an urgent security or dependency fix, which is reported when it happens.
6. **Merge policy:** final review of all PRs together, then rebase merge in dependency order (§6). Keep individual commits; no squash. A PR with a critical failure stays open and is reported as a blocker.
7. **Deployment freeze:** no Vercel investigation, configuration, deployment or environment-variable changes, and no claims that production is updated.
8. **Science guardrails:** no change to the frozen dataset, splits, published metrics or model architecture. New methods are opt-in and versioned. Experiments are logged in `artifacts/experiments/` and never overwrite v1 results.
9. **AgentOS:** plan before building, apply `standards/`, record decisions as ADRs, pass the matching checklist gate, keep `context/state.md` current, validator to 100/100 (WS-03).
10. **Session continuity:** start each session by reading this file and `TASK_CHECKLIST.md`. End it by committing and pushing, updating the tracker, and adding a session-log entry (§12). Never claim work happened between sessions.

---

## 5. Workstreams and schedule

Effort: S ≤ ½ day · M ≈ 1 day · L > 1 day. "Commits" is a planning estimate of genuine units, not a quota.

### Day 1 — Repository quality

| WS | Branch | Tasks | Acceptance criteria | Depends | Commits |
|---|---|---|---|---|---|
| WS-01 | `fix/eslint-react-hooks` | SP-01 `rules-of-hooks` bug in `CosmicBackground.tsx` · SP-02 7 `react-hooks/purity` + 3 `set-state-in-effect` · SP-03 34 `no-explicit-any` via typed API responses · SP-04 unused vars, JSX comment, font warning · SP-05 lint as a CI gate | `npx eslint .` → 0 errors (warnings justified or fixed); visual behaviour unchanged (manual check of the affected pages); typecheck, tests and build green; CI lint step required | WS-02 (for the CI edit) | 6–8 |
| WS-02 | `ci/actions-v7` | SP-06 upgrade checkout / setup-python / setup-node to v7; pip and npm caching; coverage summary artifact | No deprecation annotations; 5 jobs green; run time not worse | — | 3 |
| WS-03 | `docs/agentos-validator-100` | SP-07 fix 24 broken links (relative paths; remove `file:///Users/...`; link targets only, no report content changed) · PR-template casing · re-enable AgentOS workflows (ADR-0059 follow-up) | Validator 100/100 on Windows and Linux; AgentOS workflows trigger on push/PR and pass | — | 4 |
| WS-04 | `test/python-coverage` | SP-08 tests for `focal_loss`, calibration metric functions (ECE/NLL/Brier), `dataset.py` split guards, `explainable_wrapper`, preprocess helpers | `training/` coverage ≥ 40%; all tests deterministic and CPU-only | — | 5–7 |

### Day 2 — Project reliability

| WS | Branch | Tasks | Acceptance criteria | Depends | Commits |
|---|---|---|---|---|---|
| WS-05 | `refactor/config-paths` | SP-09 central config (`ASTRA_DATA_ROOT`, `ASTRA_ARTIFACT_DIR`, … with env overrides) replacing all 27 hardcoded paths · SP-10 `--seed`, `--data-dir`, `--out-dir` on training/eval scripts | `grep -rn /Users/ pipeline training` empty; scripts run from a fresh clone against `astra-platform/data/`; tests for config resolution | — | 6–8 |
| WS-06 | `docs/reproduction-and-env` | SP-11 README commands match the CLIs · SP-12 pinned Python lock (incl. `onnxruntime`) · SP-13 fresh-clone verification script (hashes, tests, data-path checks) run in a temp clone on Windows, plus CI | Every documented command runs; fresh-clone script passes | WS-05 (stacked) | 5–6 |

### Day 3 — ML reproducibility

| WS | Branch | Tasks | Acceptance criteria | Depends | Commits |
|---|---|---|---|---|---|
| WS-07 | `feat/evaluation-reproducibility` | SP-14 weights investigation record + recovery/retraining plan (ADR-0061, `docs/model_recovery.md`) · SP-15 `training/evaluate.py` (checkpoint → metrics on a frozen split with bootstrap CIs; reproduces published metrics when given the published checkpoint) · SP-16 provenance (git SHA, env, seed, data hash) in experiment metadata · SP-17 *(optional, D1)* CPU reproduction run on shipped arrays → EXP-0002 | `evaluate.py` tested end-to-end with a randomly initialised model on real arrays; metadata contains a git SHA; plan reviewed; EXP-0002 (if run) logged with CIs and compared with the published result, never replacing it | WS-05 (stacked) | 6–8 |

### Day 4 — Scientific validation

| WS | Branch | Tasks | Acceptance criteria | Depends | Commits |
|---|---|---|---|---|---|
| WS-08 | `fix/metrics-single-source` | SP-18 inventory of every reported number with its source; authoritative table in `docs/` · SP-19 `tools/build_platform_artifacts.py` (NLL computed properly, not copied from ECE), tested on synthetic predictions · SP-20 UI reads only generated artifacts; remove unsourced constants (`SELECTIVE_PREDICTION_DATA`, `PER_CLASS_ECE`, `DATASET_LINEAGE` counts) or mark them clearly | No metric shown in the UI without a source; generator unit-tested; README numbers consistent or explicitly flagged | WS-07 (stacked) | 6–7 |
| WS-09 | `fix/honest-cross-validation` | SP-21 CV excludes test stars, groups by `duplicate_group_id`, inner split for epoch selection, outer score reported, bootstrap CI (ADR-0062) | Unit tests on synthetic data prove no test-star leakage and no group straddling; the full CV run is optional (CPU time) | WS-05 (stacked) | 4–5 |
| WS-10 | `feat/feature-baselines` | SP-22 `training/baselines.py` (metadata RF from EXP-0001 + TESS-derived light-curve features), tests, results doc | Reproduces EXP-0001 numbers exactly; documented beside the model with caveats (catalog period) | WS-05 (stacked) | 4–5 |

### Day 5 — Data pipeline

| WS | Branch | Tasks | Acceptance criteria | Depends | Commits |
|---|---|---|---|---|---|
| WS-11 | `test/preprocessing-validation` | SP-23 characterisation tests: detrend window in days per cadence (documents S4) · SP-24 BLS grid and edge-pile-up behaviour (S5) · SP-25 input validation and clear errors in pipeline entry points | `preprocess.py` coverage ≥ 50%; no change to v1 outputs (golden-hash test on sample arrays) | WS-05 | 5–6 |
| WS-12 | `feat/preprocess-v2-optin` *(optional, D2)* | SP-26 cadence-aware time-based detrending + Lomb–Scargle search behind `--preprocess-version v2` (ADR-0064) | Default stays v1 (golden test); v2 validated on synthetic light curves with known periods/amplitudes | WS-11 (stacked) | 4–5 |

### Day 6 — Platform quality

| WS | Branch | Tasks | Acceptance criteria | Depends | Commits |
|---|---|---|---|---|---|
| WS-13 | `fix/api-reliability` | SP-27 query-param validation for `stars`/`search`, shared read-only DB handle, generic client errors · SP-28 consistent loading / empty / error / unavailable states | New API tests; no `error.message` leakage; Vitest green | WS-01 | 5–6 |
| WS-14 | `feat/accessibility-media` | SP-29 `prefers-reduced-motion`, ARIA on charts and controls, keyboard navigation · SP-30 media diet: no autoplay audio, lazy/poster video, none on data pages (no history rewrite) | Lighthouse a11y ≥ 90 on the main pages (local build); first load on `/analysis` < 5 MB | WS-01 | 4–6 |
| WS-15 | `feat/explainability-methods` *(optional)* | SP-31 occlusion / integrated-gradients utilities + deletion-curve faithfulness test on an untrained model; UI shows them only from real inference | Tests pass; nothing rendered without a real model output | WS-07 | 3–4 |

### Day 7 — Consolidation

| Task | Description | Acceptance criteria |
|---|---|---|
| SP-32 | Review all open PRs together: full diffs, overlaps, security and regression risk, CI, acceptance criteria | Review notes recorded on each PR |
| SP-33 | Resolve conflicts; rebase merge in dependency order (§6); verify `main` after each merge | `main` CI green after the final merge |
| SP-34 | Full validation on `main`: Python + web tests, build, validator, fresh-clone script | All green; results in the tracker |
| SP-35 | Docs: CHANGELOG (incl. the `v1.1.0` tag discrepancy), PROJECT_STATUS, roadmap; merge `sprint/tracking` last | Tracker reflects the final state |

**Pre-allocated ADRs** (A3): ADR-0060 sprint workflow and merge policy (WS-00) · ADR-0061 model weights recovery/retraining (WS-07) · ADR-0062 evaluation protocol: nested CV, bootstrap, baselines (WS-09/WS-10) · ADR-0063 single source of truth for metrics (WS-08) · ADR-0064 preprocessing v2 versioning (WS-12) · ADR-0065 configuration and path policy (WS-05).

---

## 6. Dependencies, overlaps and merge order

```
WS-02 ci ──► WS-01 lint ──► WS-13 api ──► WS-14 a11y
WS-03 docs/validator (independent)
WS-04 tests (independent)
WS-05 config ──► WS-06 repro docs
            ├──► WS-07 evaluate ──► WS-08 metrics
            │                  └──► WS-15 explainability (optional)
            ├──► WS-09 CV
            ├──► WS-10 baselines
            └──► WS-11 preprocessing tests ──► WS-12 v2 (optional)
WS-00 sprint/tracking ── merged last
```

**Merge order on Day 7:** WS-02 → WS-03 → WS-04 → WS-01 → WS-05 → WS-06 → WS-07 → WS-09 → WS-10 → WS-08 → WS-11 → WS-12 → WS-15 → WS-13 → WS-14 → WS-00.

**Overlap hotspots to review:**
- `.github/workflows/ci.yml`: WS-02 owns it; WS-01 adds only the lint gate step, rebased.
- `training/*.py`: WS-05 first, then WS-07/09/10 on top.
- `README.md`: WS-06 owns the commands section; WS-08/10 touch only the results section.
- `src/lib/hooks` and `constants.ts`: WS-01 types first, then WS-08/13.
- `package.json`: WS-01/13/14.

---

## 7. Commit plan (honest estimate)

| Day | Workstreams | Estimated genuine commits |
|---|---|---|
| 0 (planning, today) | WS-00 tracking | 5 |
| 1 | WS-01, WS-02, WS-03, WS-04 | 18–22 |
| 2 | WS-05, WS-06 | 11–14 |
| 3 | WS-07 | 6–8 |
| 4 | WS-08, WS-09, WS-10 | 14–17 |
| 5 | WS-11, (WS-12) | 5–11 |
| 6 | WS-13, WS-14, (WS-15) | 9–16 |
| 7 | review fixes, tracker | 3–6 |
| **Total** | | **≈ 71–99 (≈ 60–75 without the optional items)** |

Phase 0's 7 commits are already on `main` and **aren't counted** toward the sprint target. If scope has to shrink, the optional items (WS-12, WS-15, SP-17) go first, and the 50+ target still holds. Commits are never split or invented to make up a number.

---

## 8. Decisions needed from the owner

| ID | Decision | Default if no answer |
|---|---|---|
| **D1** | Allow a CPU reproduction training run (EXP-0002) on the shipped 944 arrays? It creates new local weights (not committed, not published) to test reproducibility. | Not run; WS-07 still delivers tooling and the plan |
| **D2** | Implement the opt-in preprocessing v2 (WS-12) this sprint, or design only? | Design + characterisation tests only |
| **D3** | Delete the merged `phase0/integrity-security-hotfix` branch (local and remote)? | Keep |
| **D4** | Ask the original author (Soumyadeb Tripathy) for the checkpoints `best_star_transformer_shared.pt` (SHA256 `bf374ce4…d388`) and `*.onnx.data`. Owner action. | Plan assumes they may not arrive |
| **D5** | Acknowledge R1: production stays on vulnerable code until deployed. Consider deploying `main` before the sprint ends. | Deployment after the sprint, per the brief |
| **D6** | AgentOS `lint.yml` lints the framework's own code (52 ruff errors with defaults, 3 yamllint). Fix the framework code, or keep the workflow manual? (SP-36) | Keep manual |

---

## 9. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Live site still serves fabricated predictions and the injection-vulnerable upload route** (pre-Phase-0 code) | Certain until deploy | High | Owner deploys `main` from the separate Vercel account (out of scope here; flagged) |
| R2 | Day 7 merge conflicts across 15 PRs | Medium | Medium | A1 tracking policy, A2 stacking, fixed merge order |
| R3 | Stacked branches need rebasing after rewrites of parent branches | Medium | Low | Rebase children at Day 7 in order; CI rerun per PR |
| R4 | Lint fixes in visual components change rendering | Low | Medium | Move randomness into memoised initialisers or effects; manual page check per change |
| R5 | CPU time for the optional training / full CV | Medium | Low | Optional; tooling is tested on small synthetic data |
| R6 | Scope pressure tempts padding commits | Low | High | Rule 1; optional items drop first |

---

## 10. Out of scope for this sprint

- Vercel: integration, configuration, deployment, environment variables, production verification.
- Retraining that replaces published results; changing the frozen dataset, splits, published metrics or model architecture.
- Re-downloading and re-preprocessing the full TESS dataset.
- Git history rewrites, including removing the 310 MB of media from history.
- Roadmap Phase 3 (inference service) and Phase 4 (dataset expansion).
- Changing or deleting tags or releases.

## 11. Sprint definition of done

- Every planned (non-optional) task is Completed with tests, or Blocked with a stated reason.
- All workstream PRs are reviewed together; approved ones are rebase-merged in order; `main` CI is green.
- Full validation on `main` passes: tests, build, AgentOS validator 100/100, fresh-clone script.
- The tracker files reflect reality, and the final report lists commits, PRs, CI results and blockers.

## 12. Session log

| Session | Date | Work | Commits | Branches / PRs | CI | Notes |
|---|---|---|---|---|---|---|
| Planning | 2026-11-09 | Verified starting state; cross-checked the brief against the roadmap; wrote this dossier, the sprint checklist, ADR-0060, roadmap/status links and the CHANGELOG entry; recorded the Phase 0 merge | 6 (docs) | `sprint/tracking` (tracker PR) | docs-only | Owner approved the dossier; D1–D3 defaults apply |
| Day 1 | 2026-11-09 | WS-02 Actions v7, coverage artifact, release workflow fix · WS-03 validator 100/100 (Windows + Linux), validate workflow re-enabled · WS-04 41 Python tests (training coverage 7% → 22.5%) · WS-01 React #300 crash fixed, ESLint 86 → 0, lint CI gate | 23 in PRs + 2 tracker | #3, #4, #5, #6 (+ #2) | all 4 PRs green (5 jobs each; #4 also AgentOS Health Check) | SP-08 coverage target carried to SP-09; new SP-36 (D6) and SP-37 |
