---
id: ADR-0063
title: "Published metrics: one authoritative record, generated artifacts, explicit status"
version: 1.0
status: accepted
owner: chief-architect
created: 2026-11-10
modified: 2026-11-10
related_adr: ADR-0061
related_standard: standards/research.md
related_checklist: QG-002
related_workflow: feature_development.md
related_agent: chief-architect
---

# Architecture Decision Record: ADR-0063

## Context

ASTRA's results were copied by hand into the README, five docs pages, the release notes, eight platform JSON artifacts and `constants.ts`. No script produced the artifacts (audit R4).

The SP-18 inventory found that the copies disagree and that several are wrong:
- **Earlier experiment shown as current:** the README's cross-validation table, ECE, NLL, selective prediction and entropy came from an earlier 269-star experiment.
- **Contradicted figures:** a CNN row contradicts its own confusion matrix.
- **Copy error:** the calibration audit copied ECE into NLL, and the copy spread to three artifacts.
- **Unsourced figures:** variant accuracies and lineage counts appear in no report.

The trained weights are missing (ADR-0061), so most numbers can't be recomputed. The committed confusion matrices still reproduce every test-set point metric.

## Problem Statement

How do we make every number ASTRA shows traceable to a source, keep copies from drifting, and say plainly which numbers can be checked?

## Alternatives Considered

- **Option A: Fix the copies by hand.** Quick, but they would drift again, and there would be no record of why a value was chosen. Rejected.
- **Option B: Regenerate everything from predictions.** The right end state, but impossible without the weights. Kept as the `--evaluation` path.
- **Option C: One curated record with sources and status, generated outputs, and tests that tie copies to the record.** Selected.

## Decision Rationale

1. **One record.** `models/published_metrics.json` holds the confusion matrices plus every recorded value, each with:
   - its source report;
   - a status: *computed* (from a committed matrix or training history), *recorded* (from a report; needs the weights to recompute) or *unverified* (the report contradicts committed evidence).
2. **Generated outputs.** `pipeline/build_platform_artifacts.py` writes the platform metric artifacts and `docs/metrics.md` from the record:
   - Point metrics are computed from the matrices, never copied.
   - NLL stays null until it can be computed from per-star logits.
   - `--check` and a test fail on stale outputs.
3. **Explicit exceptions.** Superseded results (another dataset), resolved conflicts and unsourced numbers are listed in the record rather than deleted silently. Engineering-log reports keep their original text.
4. **Tests tie copies to the record.** Each recorded value must appear in its cited report. Every README results number must trace to the record at its printed precision. The UI's constants and page literals must equal the record.
5. **Path to recomputation.** When weights exist, `evaluate.py` output passed with `--evaluation` replaces a model's recorded values, NLL included, and marks them *recomputed*.

## Consequences

- Changing a published number means editing the record and regenerating; the tests catch edits made anywhere else.
- Readers can see what is checked and what is taken on trust (`docs/metrics.md`).
- Some displayed numbers changed: the CNN figures, and NLL is now "not recorded". The README no longer shows the 269-star results as current.
