---
id: ADR-0057
title: "ASTRA audit baseline: integrity-first roadmap (Phase 0 before features)"
version: 1.0
status: accepted
owner: chief-architect
created: 2026-11-09
modified: 2026-11-09
related_adr: None
related_standard: standards/ai_ml.md
related_checklist: QG-004
related_workflow: master.md
related_agent: chief-architect
---

# Architecture Decision Record: ADR-0057

## Context

The 2026-11-09 audit (`PROJECT_AUDIT.md`) found three problems:
- The deployed platform returns fabricated predictions derived from ground-truth labels whenever Python inference is unavailable, which is always the case on Vercel, Render and Docker.
- `/api/upload` has a command-injection path.
- No model weights are in the repository.

On the science side, labels are perfectly confounded with period source and source catalog, and a 3-feature baseline (86.6%) beats the reported model (78.2%).

## Problem Statement

In what order should work proceed, so that existing valid assets (frozen dataset, splits, model code, browsing UI) are preserved while integrity and security problems are removed before any new features?

## Alternatives Considered

- **Option A — Features first** (upload UI, new visualisations): keeps momentum but keeps fabricated output live. Rejected.
- **Option B — Full rebuild:** discards working, verified assets. Rejected.
- **Option C — Integrity-first phased plan:** Phase 0 (remove fabrication, fix injection, truthful health) → Phase 1 (reproducibility: weights, config, CI) → Phase 2 (de-confounded science vs baselines) → Phase 3 (real inference) → later phases.

## Decision Rationale

Option C. It follows the "Architecture First" principle and `standards/ai_ml.md` (baseline comparison, reproducibility, no deployment without a gate). It changes no scientific results until they can be reproduced and re-evaluated.

## Consequences

- No new platform features until the Phase 0 and Phase 1 exit criteria pass.
- The current 78.17% stays on record as the v1 baseline with documented caveats.
- Accepted 2026-11-09: the project owner approved Phase 0 (T1, T2, T3, T5). Implementation decisions are in ADR-0058 and ADR-0059. Follow-up ADRs will record the weights decision (recover vs retrain) and the inference architecture.
