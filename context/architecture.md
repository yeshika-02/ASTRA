# System Architecture

> **Owner:** Chief Architect
> **Update Frequency:** Architecture changes only
> **Cross-refs:** `context/tech_stack.md` · `context/decisions.md`

---

## System Overview

ASTRA is a batch ML pipeline plus a read-mostly web app.
- The Python pipeline builds a labelled catalog, downloads and preprocesses TESS light curves into fixed-length raw and phase-folded arrays, freezes hash-locked splits, and trains dual-branch CNN+Transformer classifiers.
- A Next.js app serves the frozen dataset, precomputed metrics and per-star light curves.
- "Live" inference is designed as a shell-out to Python. It is non-functional in every deployment today, and the platform falls back to fabricated output (audit P1), which is slated for removal.

## Component Map

```
┌─────────────────┐   ┌──────────────────┐   ┌──────────────────────┐
│ Catalog builder │──▶│ Preprocess (TESS)│──▶│ Frozen dataset+splits│
│ VSX/Hipparcos/  │   │ clip→stitch→     │   │ CSV manifest (SHA256)│
│ Santos2021      │   │ detrend→BLS→fold │   │ 944 × 4 .npy arrays  │
└─────────────────┘   └──────────────────┘   └──────────┬───────────┘
                                                        ▼
┌─────────────────┐   ┌──────────────────┐   ┌──────────────────────┐
│ Next.js UI      │◀──│ Next.js API      │◀──│ Training / eval /    │
│ pages, charts   │   │ SQLite + JSON    │   │ calibration / export │
└─────────────────┘   │ artifacts        │   │ (weights NOT in repo)│
                      └──────────────────┘   └──────────────────────┘
```

## Data Flow

- **Build:** catalogs → candidate rows → TESS download → preprocessing → `processed/TIC_*` → audit → freeze CSV + split IDs
- **Train:** frozen arrays (2 × 1000) → HybridTransformer → best-val checkpoint → temperature scaling → ONNX export
- **Serve:** manually produced `data/artifacts/*.json` + `astra.sqlite` → read-only API routes → UI

## System Boundaries

| Boundary | Internal | External | Interface |
|---------|---------|---------|---------|
| Data acquisition | pipeline scripts | VizieR, MAST | astroquery / lightkurve HTTP |
| Platform ↔ model | API routes | Python scripts | `child_process.exec` (to be replaced) |

## Architectural Rationale

| Decision | Rationale | ADR |
|---------|-----------|-----|
| Integrity-first roadmap | Remove fabricated output and injection before features | [ADR-0057](../artifacts/decisions/ADR-0057-astra-audit-baseline-and-phase0.md) |

## Known Limitations

| Limitation | Impact | Planned Resolution |
|-----------|--------|-------------------|
| No hosted weights | Nothing reproducible or servable | Phase 1 (recover or retrain) |
| Class ≡ period source ≡ catalog | Accuracy not interpretable | Phase 2 uniform period search |
| No artifact generator | Metrics drift between README, JSON and UI | Phase 1 generator script |
| Python shell-out inference | Fails on serverless; injection risk | Phase 0 hardening, Phase 3 redesign |

*Architecture last updated: 2026-11-09.*
