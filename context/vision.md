# Project Vision: ASTRA

> **Status:** Active | **Owner:** project team (repo `yeshika-02/ASTRA`)
> **Last Modified:** 2026-11-09

---

## 1. Problem Statement
Classify TESS light curves into five stellar-variability classes (RR Lyrae, Cepheid, Eclipsing Binary, Solar-like, Stable). Do it with a reproducible, honestly evaluated ML pipeline, and serve the results through an interactive research web platform.

## 2. Target Tech Stack
- ML / pipeline: Python 3.11–3.12, PyTorch, lightkurve, astropy, scikit-learn
- Platform: Next.js 16 / React 19 / TypeScript, SQLite (read-only), Three.js
- Profile: `ml`

## 3. Success Criteria
- Every published metric is reproducible from a clean clone (hosted weights plus documented commands).
- Model results are reported against a feature baseline, with CIs, on a de-confounded evaluation.
- The platform never shows fabricated output; inference is either real or clearly marked unavailable.
- CI green; AgentOS validator 100/100; QG-004 and QG-005 pass.

## 4. Scope & Milestones
- **M0 Honest platform:** Phase 0 of `UPDATED_ROADMAP.md` (fabrication removed, injection fixed)
- **M1 Reproducible v1:** weights hosted, config-driven paths, green CI
- **M2 Credible science:** de-confounded re-baseline vs baselines
- **M3 Real inference:** batch predictions + upload service
- **Target Deadline:** TBD (roadmap estimates M0–M3 at about 9 weeks)
