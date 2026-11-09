---
id: ADR-0060
title: "7-day sprint workflow: per-workstream PRs, single tracker PR, stacked branches, rebase merge on Day 7"
version: 1.0
status: accepted
owner: chief-architect
created: 2026-11-09
modified: 2026-11-09
related_adr: ADR-0057
related_standard: standards/code_quality.md
related_checklist: QG-002
related_workflow: master.md
related_agent: planner
---

# Architecture Decision Record: ADR-0060

## Context

The owner's 7-day sprint brief (2026-11-09) requires:
- one branch and PR per workstream
- 50+ genuine commits from `yeshika-02`
- merging only after a joint review on Day 7
- individual commits preserved through rebase merging
- every PR updating `TASK_CHECKLIST.md` and the other tracker files

With about 15 PRs open at once, two of these requirements collide:
- if each PR edits the same tracker lines, every rebase merge after the first conflicts;
- parallel PRs would also claim the same ADR number.

## Problem Statement

How do we keep per-task tracking current and PRs independently reviewable, while still merging everything cleanly on Day 7?

## Alternatives Considered

- **Option A — Every PR edits the tracker files.** Guaranteed conflicts on Day 7, and the trackers end up hand-merged. Rejected.
- **Option B — Merge PRs as they finish.** Contradicts the brief's "joint review on Day 7". Rejected.
- **Option C — A single tracker PR, PR descriptions as per-task records, stacked branches, pre-allocated ADRs.** Selected.

## Decision Rationale

1. **Tracker files** (`TASK_CHECKLIST.md`, `7_DAY_SPRINT.md`, `PROJECT_STATUS.md`, `UPDATED_ROADMAP.md`, `CHANGELOG.md`) and `context/decisions.md` / `context/state.md` are edited only on `sprint/tracking`. It's updated in the same session as each workstream's work, with PR numbers and commit SHAs, and merged last.
2. **Each workstream PR description** is its per-task record: task IDs, changed files, tests and results, acceptance criteria, parent PR.
3. **Stacked branches** for real dependencies (dossier §6). PR bases stay `main`; children are rebased onto `main` after each parent merges.
4. **ADR numbers pre-allocated:** 0061 weights recovery/retraining, 0062 evaluation protocol, 0063 metrics source of truth, 0064 preprocessing v2, 0065 configuration and path policy.
5. **Rebase merge, in dependency order**, after the joint review. Individual commits and their author (`yeshika-02`) and author dates are preserved. No squash, no backdating, no artificial commits.

## Consequences

- No tracker conflicts on Day 7. Each workstream PR stays small and focused on code, tests and its own docs.
- The tracker branch is long-lived and has to be kept current by the session that lands each task.
- Contribution-graph entries appear when the commits reach `main` on Day 7, with their original author dates.
