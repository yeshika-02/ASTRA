# Project Heartbeat & Task State

> **Last Heartbeat:** 2026-11-10
> **Project State:** PHASE 0 MERGED (`main` = `1beca47`) — sprint Days 1–3 complete, PRs #3–#9 in review (see 7_DAY_SPRINT.md)

---

## Session 2026-11-10 — Sprint Day 3

- WS-07 [#9](https://github.com/yeshika-02/ASTRA/pull/9) (stacked on #8): weights investigation (`docs/model_recovery.md`), `models/published_weights.json`, `verify_weights.py`, ADR-0061; `evaluate.py` with bootstrap CIs and hash gate; `astra.provenance`; CI provenance and evaluation checks; reproducibility guide rewritten. 22 commits, 132 tests in a clean locked venv.
- Key facts: weights never on GitHub; upstream repo = this repo; `.onnx.data` hash recorded; published confusion matrices reproduce all published metrics.
- SP-17 blocked (D1). Next: Day 4 (WS-08 metrics single source, SP-18–SP-20).

## Session 2026-11-09 (e) — Sprint Day 2

- WS-05 [#7](https://github.com/yeshika-02/ASTRA/pull/7): `astra.config` + `resolve_cli_path`, 27 machine paths → 0, real CLIs (train, CV, calibration, uncertainty), 5 fresh-clone crashes fixed, ADR-0065. 17 commits, 60 tests, `training/` coverage 56%. CI green.
- WS-06 [#8](https://github.com/yeshika-02/ASTRA/pull/8) (stacked on #7): `prepare_from_repo.py`, CI fresh-clone job, `requirements-lock.txt`, `onnx`/`onnxscript` declared, export/attention CLIs fixed, README rewritten to match the code. 23 commits, 92 tests in a clean locked venv.
- Findings: three calibration temperatures (SP-18), split-script ratio mismatch (SP-21), weights absent incl. ONNX `.onnx.data` (SP-14).
- Nothing merged (ADR-0060). Next: Day 3 (WS-07 weights plan ADR-0061, `evaluate.py`, provenance).

## Session 2026-11-09 (d) — Sprint Day 1

- WS-02 [#3](https://github.com/yeshika-02/ASTRA/pull/3): Actions v7, pip cache, coverage artifact, release workflow (gh-release v3, `git archive`). 5 commits.
- WS-03 [#4](https://github.com/yeshika-02/ASTRA/pull/4): 24 doc links fixed → validator 100/100 (Windows + Linux CI), PR-template casing, `validate.yml` re-enabled; `lint.yml` manual (SP-36 / D6). 4 commits.
- WS-04 [#5](https://github.com/yeshika-02/ASTRA/pull/5): 41 Python tests; `training/` coverage 7% → 22.5%; upload clipping issue pinned as xfail (SP-37). 5 commits.
- WS-01 [#6](https://github.com/yeshika-02/ASTRA/pull/6) (stacked on #3): React #300 crash fixed (reproduced, then verified fixed in a production build); ESLint 86 → 0; lint CI gate. 9 commits.
- All four PRs green. Nothing merged (per ADR-0060). Next: Day 2 (WS-05 config/paths, WS-06 reproduction docs).

## Session 2026-11-09 (c) — Sprint planning

- Verified the starting state: PR #1 merged, `main` = `1beca47`, post-merge CI green, no open PRs, `gh` user `yeshika-02`, author email linked to the account.
- Weights search: never on GitHub (no history, LFS or releases; `Rexy-5097/ASTRA` redirects here).
- Cross-checked the owner's 7-day sprint brief against the roadmap. Wrote `7_DAY_SPRINT.md` (final dossier) and the sprint task table SP-00..SP-35 in `TASK_CHECKLIST.md`; ADR-0060 (sprint workflow).
- Day 1 not started. Open owner decisions: D1–D5 (see dossier §8).

## Session 2026-11-09 (b) — Phase 0: integrity and security hotfix

PR #1 rebase-merged to `main` (`1beca47`); post-merge CI run 42520528644 green. Commits authored as yeshika-02. Production not updated: deployed from a separate Vercel account, out of scope until after the sprint.

**Done (all RESOLVED):**
- T1: fabricated predictions, probabilities, attention maps and OSINT fields removed. Explicit 503 `inference_unavailable` contract plus UI state and site-wide notice (ADR-0058).
- T2: command injection closed. `spawn(..., { shell: false })`, flux over stdin, strict validation; `upload_inference.py` no longer reads file paths.
- T3: `/api/health` measures dataset hash, DB rows, checkpoint hash, ONNX weights and Python modules. README "Known limitations".
- T5: CI rewritten. Lockfile, PostCSS/ESLint configs, `.gitattributes` and `pyproject` backend added or fixed.
- AgentOS GitHub files adapted and committed (ADR-0059). ADR-0057 accepted.

**Verification:**
- Vitest 88/88; pytest 21/21 (incl. model smoke tests with CPU torch); tsc clean; ruff clean; `next build` clean.
- Tests fail against the original route code and pass against the fix.
- End-to-end checks on a local production server.
- Gate record: `artifacts/reviews/phase0-gate-review.md` (QG-005, QG-007 PASS; one documented lint exception).

**Open / next (Phase 1, needs approval):**
- `[ ]` T4: weights — owner to say whether `.pt` / `.onnx.data` are recoverable
- `[ ]` T7: config-driven paths, runnable README commands
- `[ ]` T8: artifact generator, single source of metrics
- `[ ]` T9: fix 24 doc links → validator 100/100; re-enable AgentOS workflows; PR template casing
- `[ ]` T13: ESLint debt (46 errors, incl. a rules-of-hooks bug in CosmicBackground.tsx)

## Session 2026-11-09 (a) — Audit

Full audit; deliverables `PROJECT_AUDIT.md`, `PROJECT_STATUS.md`, `UPDATED_ROADMAP.md`, `PRIORITY_TASKS.md`; EXP-0001 metadata baseline.

## Validator

94/100. Only Cross-reference fails, because of the 24 pre-existing broken links in ASTRA `docs/` (task T9). No new broken links were added.
