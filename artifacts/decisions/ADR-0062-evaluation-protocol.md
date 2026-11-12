---
id: ADR-0062
title: "Evaluation protocol: test-free grouped nested CV, bootstrap CIs, baselines beside every model"
version: 1.0
status: accepted
owner: chief-architect
created: 2026-11-12
modified: 2026-11-12
related_adr: ADR-0063
related_standard: standards/research.md
related_checklist: QG-002
related_workflow: feature_development.md
related_agent: chief-architect
---

# Architecture Decision Record: ADR-0062

## Context

Audit finding S7 lists three problems with `training/cross_validate.py`:
- It drew folds from all 944 stars, including the 142 frozen test stars.
- It scored each fold with the best of 50 epochs, chosen on that same fold.
- It reported a 95% CI that treated 15 correlated fold scores as independent.

Its 84.7% sat well above the 78.2% test result. (The README's copy of that number turned out to come from an earlier 269-star experiment; see ADR-0063.)

Audit finding S2 found that a three-feature metadata baseline (86.6%) beats the deep model on the same test split, and that no baseline was reported anywhere.

The frozen split records `grouping_key: duplicate_group_id`, but no shipped metadata carries that field, so every star was its own group. Recomputing duplicate groups with the pipeline's rule (same TIC id, or within 2″; review radius 10″) on the shipped manifest finds no duplicates. Per-star grouping therefore did not leak in this dataset.

## Problem Statement

How should ASTRA estimate generalisation, and against what reference, so that the reported numbers are not optimistic and any gain over trivial features is visible?

## Alternatives Considered

- **Option A: Keep k-fold, but drop the test stars.** Selection on the scored fold still inflates the estimate. Rejected.
- **Option B: Full nested CV with hyper-parameter search in the inner loop.** Correct, but costs 5× more CPU time, and the sprint changes no hyper-parameters. Kept for when tuning starts.
- **Option C: Test-free, grouped outer k-fold, with epoch selection on an inner held-out set and the outer fold scored once. Report bootstrap CIs and a baseline next to every model.** Selected.

## Decision Rationale

1. **No test stars.** The cross-validation pool is the frozen train and validation stars. The frozen test-id file is required, and the frozen test split is used once per published model, never for development.
2. **Groups.** Stars are grouped with `assign_duplicate_groups`, the pipeline's own rule, and no group may straddle train, selection and test. `check_plans()` asserts this, and the outer folds of each seed must cover the pool exactly once.
3. **Selection inside the training data.** An inner stratified group split (20% by default) chooses the epoch. The outer fold is scored once with the chosen weights. Selection-set scores are recorded but labelled as optimistic.
4. **Uncertainty.** Report the mean and spread of the outer-fold scores, plus a percentile bootstrap over each seed's pooled out-of-fold predictions. Never use ±1.96·σ/√n over correlated folds.
5. **Baselines.** Every model result is reported beside the baselines from `training/baselines.py` (sprint task SP-22):
   - the metadata baselines of EXP-0001;
   - features derived from the network's own inputs.
   Each baseline's caveats (catalog periods are external information) stay with the numbers.
6. **Testable protocol.** The protocol is separate from the network: a trainer is injected. Synthetic tests prove no leakage and that the reported score is the outer fold's.

## Consequences

- CV numbers will be lower and wider than before; that is the point. No full run is part of the sprint: 15 outer folds of 50 epochs take hours on CPU.
- The README no longer shows a CV result for the frozen dataset until such a run exists.
- A model only counts as better if it beats the baselines on the same split, with intervals.
