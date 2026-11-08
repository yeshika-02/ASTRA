---
id: ART-REV-0001
title: "Phase 0 gate review: integrity and security hotfix"
version: 1.0
status: completed
owner: security-reviewer
created: 2026-11-09
modified: 2026-11-09
related_adr: ADR-0058
related_standard: standards/security.md
related_checklist: QG-005
related_workflow: bug_fix.md
related_agent: security-reviewer
---

# Phase 0 Gate Review

Scope: tasks T1 (remove fabricated output), T2 (command injection), T3 (truthful health and notices), T5 (CI). Branch `phase0/integrity-security-hotfix`.

## QG-007 Bug Fix

| Requirement | Evidence | Result |
|---|---|---|
| Regression test | `astra-platform/tests/api-routes.test.ts`, `validation.test.ts`, `inference-runner.test.ts`, `health.test.ts`, `no-fabrication.test.ts`; `tests/test_upload_inference.py` | ✅ |
| Defect resolved | Tests run against the **original** route files fail (predict: 10 failures; upload: 8 of 10, incl. both injection cases; health: hardcoded READY; static guards: 2), and pass against the fixed files | ✅ |
| No regression | Vitest 88/88; pytest 21/21 (incl. 3 model smoke tests with CPU PyTorch); `tsc --noEmit` clean; `next build` clean | ✅ |
| Clean linting | 0 ESLint findings in new files. The 14 ESLint errors in modified files are all on unchanged, pre-existing lines (checked line-by-line against the diff); ruff clean | ⚠️ PASS with documented exception |
| State updated | `context/state.md` updated | ✅ |

## QG-005 Security Review

| Requirement | Evidence | Result |
|---|---|---|
| No secrets in code | No credentials found in the diff or the audited source | ✅ |
| Dependency CVEs | `npm audit` / `pip-audit` not run in Phase 0 | ⏭ deferred to Phase 5 (T5.3) |
| Auth implemented | Public read-only research site; no auth by design. Abuse controls (rate limiting) deferred to Phase 5 | ⏭ N/A |
| Sanitized input | All process arguments are validated; `spawn(..., { shell: false })`; flux over stdin; SQL already parameterised; `upload_inference.py` no longer opens a path from `--flux` | ✅ |
| CORS policy | Next.js defaults (same-origin); no wildcard configured | ✅ |

## Verified end to end

On a local `next start` production server:
- `GET /api/health` → `DEGRADED` (dataset hash ✓, 944 stars ✓, inference unavailable with reasons)
- `GET /api/predict/TIC_122784551` and `/api/explain/122784551` → 503 `inference_unavailable`, no probabilities
- injection id → 400; upload with injected `tic_id` → 400; valid upload without a model → 503
- the target page shows "Model confidence: UNAVAILABLE", the unavailable panel and the site-wide notice

## Exit decision

**PASS (with one documented lint exception).** Phase 0 is complete. Phase 1 starts only after owner review.
