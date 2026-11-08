---
id: ADR-0058
title: "Inference contract: real model output or explicit 503, executed without a shell"
version: 1.0
status: accepted
owner: chief-architect
created: 2026-11-09
modified: 2026-11-09
related_adr: ADR-0057
related_standard: standards/security.md
related_checklist: QG-005
related_workflow: bug_fix.md
related_agent: security-reviewer
---

# Architecture Decision Record: ADR-0058

## Context

The audit (PROJECT_AUDIT.md, findings P1, P2, P5) found that the inference API routes did three things wrong:
- When Python was unavailable, they returned predictions, uncertainty and attention maps generated from the star's ground-truth label or `Math.random()`. This happened on every deployment, including the live site.
- `/api/upload` built a shell command string from request JSON, which allowed command injection; `--flux` could also name a server file to read.
- `/api/health` reported `READY` with a hardcoded model hash.

## Problem Statement

How should the platform behave when the trained model cannot run, and how should it start the Python inference processes safely?

## Alternatives Considered

- **Option A — Keep a "demo mode", but label it.** Rejected. Synthetic class probabilities derived from labels have no scientific meaning, and labels get lost in screenshots and API consumers.
- **Option B — Port inference to ONNX Runtime in Node now.** Rejected for Phase 0. The model weights aren't in the repository (R1), so there's nothing to run. That's a Phase 3 decision.
- **Option C — Explicit unavailability plus hardened process execution.** Selected.

## Decision Rationale

1. **No fabricated output.** If the model cannot run, the route returns HTTP 503 `{status: "inference_unavailable", capability, reasons[], message}`. Reasons are short codes without server paths. The UI renders an "inference unavailable" state and a site-wide notice; catalog labels are always shown as ground truth.
2. **Readiness gating before spawning.** A process starts only if the interpreter, the inference script and the model files exist. For `predict`, the checkpoint's SHA256 must also match the published hash. ONNX models must have their external weights present.
3. **No shell.** `child_process.spawn(cmd, args, { shell: false })` with an argument array; bulk data (flux) goes over stdin. All inputs are validated first (`tic_id` `^(TIC_)?[1-9]\d{0,11}$`; `period` a finite number in (0, 1000]; `flux` an array of 50–100,000 finite numbers; body ≤ 4 MB). `upload_inference.py` no longer reads a file path from `--flux`.
4. **Output validation.** Model output must contain a known class and five probabilities in [0, 1]; otherwise 503 `invalid_model_output`. Successful responses carry `source: "model"`.
5. **Truthful health.** `/api/health` recomputes dataset and checkpoint hashes, queries the star database, checks ONNX weights, and probes Python for `numpy`/`torch`/`onnxruntime` (cached for 5 minutes). `READY` only when every inference capability is runnable; `DEGRADED` when the data is verified but inference isn't; `BLOCKED` when the dataset or database fails.

Implementation:
- `astra-platform/src/lib/server/validation.ts`, `inference.ts` and `health.ts`.
- Routes `api/predict`, `api/explain`, `api/upload`, `api/health`.

Enforced by `astra-platform/tests/*.test.ts`, including a static test that forbids `Math.random` outside visual effects, label-derived probability generators, and process spawning outside `lib/server/inference.ts`.

## Consequences

- On Vercel today (no Python, no weights), the target, mission-replay and upload features show "unavailable". This is the honest state until Phase 1 (weights) and Phase 3 (an inference service).
- New inference paths must go through `lib/server/inference.ts`; the static test fails otherwise.
- Paths outside the app are marked `turbopackIgnore` so they aren't traced into serverless bundles.
