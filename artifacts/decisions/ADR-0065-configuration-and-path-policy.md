---
id: ADR-0065
title: "Configuration and path policy: astra.config with environment overrides"
version: 1.0
status: accepted
owner: chief-architect
created: 2026-11-09
modified: 2026-11-09
related_adr: ADR-0060
related_standard: standards/code_quality.md
related_checklist: QG-002
related_workflow: feature_development.md
related_agent: chief-architect
---

# Architecture Decision Record: ADR-0065

## Context

The audit (R2, R3) found 27 absolute paths into the original author's home directory. Ten scripts wrote reports to local agent folders, reports linked `file:///Users/...`, one script searched the author's lightkurve cache, and one read a log file from there.

Scripts also disagreed on where data lives (`data/processed` vs `data/phase6/processed`). A fresh clone has the arrays in `astra-platform/data/processed` and the split ids in `docs/engineering-log/`.

Nine report writers only worked because the author's folders already existed. One cleanup script deleted almost all processed data when its log path was missing.

## Problem Statement

How should scripts find data, models and output locations so they work from any clone, on any OS, without editing code?

## Alternatives Considered

- **Option A — Keep paths in each script, made relative.** Still scattered; no override mechanism; layouts differ between scripts. Rejected.
- **Option B — A YAML config file.** Adds a file format and a parser, and is easy to commit by accident with personal paths. Rejected for now.
- **Option C — One module, `astra.config.get_paths()`, with repository-relative defaults and environment-variable overrides.** Selected.

## Decision Rationale

| Path | Variable | Default |
|---|---|---|
| Phase 6 root | `ASTRA_PHASE6_ROOT` | `data/phase6` |
| Processed arrays | `ASTRA_PROCESSED_DIR` | `<phase6>/processed` |
| Frozen splits | `ASTRA_SPLITS_DIR` | `<phase6>/splits` |
| Saved models | `ASTRA_MODELS_DIR` | `models/saved` |
| Script outputs | `ASTRA_OUTPUT_DIR` | `outputs/` (git-ignored) |
| lightkurve cache | `ASTRA_LIGHTKURVE_CACHE` | `~/.lightkurve/cache` |

- Relative overrides and CLI path arguments (`resolve_cli_path`) resolve against the repository root.
- Training and evaluation scripts expose `--data-dir`, `--out-dir`, `--checkpoint` and `--seed` where relevant, with config defaults.
- `ASTRADataset` takes an explicit `splits_dir`. Otherwise it uses the configured splits dir for the configured processed dir, else a sibling `splits/`.
- Report writers create their output directory and write UTF-8. Generated reports link artifacts relatively.
- Guard tests fail on absolute home-directory paths or `file://` URLs in code, and on imported-but-undeclared dependencies.

## Consequences

- Every script runs from a fresh clone. Layouts such as "arrays from `astra-platform/data/processed`, splits rebuilt under `data/phase6/splits`" need only environment variables (used by WS-06's fresh-clone setup).
- Script outputs no longer land in the repository by default (`outputs/` is ignored); committed artifacts change only when a path is given explicitly. This includes training (`outputs/runs/`) and the fitted temperature (next to the calibration report); until 2026-11-10 both still defaulted to `models/saved/` and overwrote the published records.
- New scripts must use `get_paths()`; the guard test blocks hard-coded machine paths.
