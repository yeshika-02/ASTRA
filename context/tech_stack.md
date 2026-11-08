# Technology Stack

> **Owner:** Technical Lead
> **Update Frequency:** When technologies are added, upgraded, or deprecated
> **Cross-refs:** `context/architecture.md` · `context/decisions.md`

---

## Core Stack

| Layer | Technology | Version | Purpose | Notes |
|-------|-----------|---------|---------|-------|
| Language (ML) | Python | 3.11–3.12 | Pipeline, training, inference | Unpinned `requirements.txt` (audit R5) |
| Language (web) | TypeScript | ≥ 5 | Platform | 38 `any` usages |
| Web framework | Next.js (App Router) | 16.2.9 | UI + API routes | React 19.2.4 |
| Database | SQLite via `node:sqlite` | Node ≥ 22.5 | Read-only star registry (944 rows, FTS5) | Opened immutable; no generator script in repo |
| Styling | Tailwind CSS | 4.x | Styling | PostCSS config not committed (audit U2) |
| 3D / charts | Three.js + R3F, Recharts | 0.184 / 3.8 | Visualisation | |
| State / data | Zustand, TanStack Query | 5.x | Client state, caching | |

## AI/ML Stack

| Component | Technology | Version | Purpose | Notes |
|-----------|-----------|---------|---------|-------|
| Framework | PyTorch | 2.12 (MPS) | Training, MC-dropout inference | Weights not in repo (audit R1) |
| Astro data | lightkurve, astropy, astroquery | ≥ 2.4 / 5.3 / 0.4.6 | TESS download, BLS, catalogs | |
| Classical ML | scikit-learn | ≥ 1.3 | Splits, metrics, baselines | |
| Experiment tracking | Markdown reports + JSON | — | `artifacts/experiments/` from 2026-11-09 | No MLflow/W&B |
| Model serving | ONNX (export only) | — | Intended inference | `onnxruntime-node` installed but unused (audit P3) |

## Infrastructure

| Component | Technology | Purpose | Notes |
|-----------|-----------|---------|-------|
| Hosting | Vercel (live), Render blueprint, Dockerfile | Platform | Docker image omits `data/` (audit P4) |
| CI/CD | GitHub Actions | ruff, pytest, Next build | Failing on every push (audit E1) |

## Development Tools

| Tool | Purpose |
|------|---------|
| pip (venv) | Package management |
| ruff | Linting (passes) |
| pytest | Testing (10 tests, 8% coverage) |

## Technology Constraints

| Constraint | Reason |
|-----------|--------|
| Free-tier hosting, no Python runtime on Vercel | Inference must be precomputed or served by a separate service (roadmap Phase 3) |
| Windows contributors | Use `python` (not `python3`); `.gitattributes` needed for hash checks |

## Technology Debt and Planned Changes

| Current | Target | Timeline |
|---------|--------|---------|
| `exec` shell-out to `../.venv/bin/python` | Batch predictions + FastAPI service or ONNX Runtime (ADR pending) | Phase 3 |
| Hardcoded metrics in `constants.ts` | Generated artifacts only | Phase 1 |
| BLS-only period search, Savitzky–Golay 301-point detrend | Lomb–Scargle + BLS for all stars, time-based window | Phase 2 |

*Tech stack last updated: 2026-11-09.*
