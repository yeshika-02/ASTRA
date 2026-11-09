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

## Backlog — Phase 1 (not started; needs owner approval)

- [ ] T4 Model weights: recover the original `.pt` / `.onnx.data` or retrain (**owner decision needed**)
- [ ] T7 One config for paths (remove 27 hardcoded `/Users/...` paths); README commands that run
- [ ] T8 Artifact + SQLite generator; single source of truth for metrics
- [ ] T9 Fix 24 broken doc links → AgentOS validator 100/100; re-enable AgentOS workflows; PR-template casing
- [ ] T13 ESLint debt (46 errors, incl. a `rules-of-hooks` bug in `CosmicBackground.tsx`); then gate lint in CI
- [ ] Bump GitHub Actions versions (checkout/setup-python/setup-node use deprecated Node 20)
