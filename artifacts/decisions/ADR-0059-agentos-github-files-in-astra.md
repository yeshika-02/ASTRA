---
id: ADR-0059
title: "AgentOS GitHub files in the ASTRA repository"
version: 1.0
status: accepted
owner: chief-architect
created: 2026-11-09
modified: 2026-11-09
related_adr: ADR-0057
related_standard: standards/code_quality.md
related_checklist: QG-002
related_workflow: master.md
related_agent: chief-architect
---

# Architecture Decision Record: ADR-0059

## Context

The AgentOS installer added these files to ASTRA's `.github/`:
- `workflows/lint.yml`, `workflows/validate.yml`
- `CODEOWNERS`
- `ISSUE_TEMPLATE/question.md`
- `LABELS.md`

The AgentOS validator requires all of these except `LABELS.md` to exist (Distribution category). As shipped, though:
- `CODEOWNERS` names a placeholder user (`@lead-engineer`).
- `lint.yml` contains a link check that fails on ASTRA's 24 pre-existing broken doc links.
- `validate.yml` fails while the validator is below 100/100.
- `question.md` asks about "AgentOS usage".

## Problem Statement

Which of these files should be committed to ASTRA, and in what form, without breaking ASTRA's CI or GitHub review flow?

## Alternatives Considered

- **Option A — Commit as-is.** Every push goes red, and CODEOWNERS references a non-existent user. Rejected.
- **Option B — Don't commit them.** Breaks the AgentOS Distribution check for every fresh clone. Rejected.
- **Option C — Commit adapted versions.** Selected.

## Decision Rationale

| File | Decision |
|---|---|
| `CODEOWNERS` | Committed, with the real owner `@yeshika-02`, including explicit ownership of the security-sensitive inference paths |
| `workflows/validate.yml`, `workflows/lint.yml` | Committed with `on: workflow_dispatch` only, until task T9 fixes the doc links and the validator reaches 100/100; then switch back to push/PR triggers |
| `ISSUE_TEMPLATE/question.md` | Committed, reworded for ASTRA |
| `LABELS.md` | Not committed (framework-specific, not required) |
| ASTRA `workflows/ci.yml` | Remains the gating CI (lint, Python tests incl. model smoke tests, dataset integrity, web typecheck/tests/build) |

## Consequences

- ASTRA CI stays meaningful and green; the AgentOS checks can be run manually from the Actions tab.
- Task T9 (Phase 1) must re-enable the two AgentOS workflows once the validator reaches 100/100.
- On Linux, the validator also expects `.github/PULL_REQUEST_TEMPLATE.md` (ASTRA uses the lowercase `pull_request_template.md`). Windows hides this because its filesystem is case-insensitive; address it in T9.
