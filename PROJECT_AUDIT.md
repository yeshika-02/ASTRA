# ASTRA — Technical Audit

**Audited:** 2026-11-09 · **Repository:** `yeshika-02/ASTRA` @ `7821d3f` (25 commits, 4,995 tracked files)
**Phase 0 fixes:** see §11 (resolution status), branch `phase0/integrity-security-hotfix`
**Live deployment checked:** `astra-platform-wine.vercel.app`
**Framework:** AgentOS (Raptors Way), profile `ml`. Applied: `standards/ai_ml.md`, `standards/research.md`, `standards/security.md`, gates QG-004 (research validation) and QG-005 (security review).
**Companion documents:** [PROJECT_STATUS.md](PROJECT_STATUS.md) · [UPDATED_ROADMAP.md](UPDATED_ROADMAP.md) · [PRIORITY_TASKS.md](PRIORITY_TASKS.md)

---

## 0. How this audit was done

I didn't treat any claim in the README or the `docs/engineering-log/` reports as true until code, data or a run confirmed it. Each finding is tagged with how it was checked:

| Tag | Meaning |
|---|---|
| **[RUN]** | I ran it and saw the result (tests, scripts, hashes, queries on the shipped data) |
| **[LIVE]** | Confirmed against the public deployment with a read-only request |
| **[CODE]** | Confirmed by reading the source; not executed |
| **[UNVERIFIED]** | Could not be checked; the reason is stated |

What I ran:
- Python unit tests (`pytest`, isolated venv), coverage, `ruff`.
- SHA256 checks of the dataset manifest and split files.
- SQL profiling of the shipped `astra-platform/data/astra.sqlite` (944 stars, all metadata).
- A metadata-only baseline classifier on the frozen train/test split (see §3, finding S2). The script and results are in `artifacts/experiments/`.
- Recomputing accuracy and per-class F1 from the committed test confusion matrix.
- Reading the GitHub Actions history.
- Two GET requests against the live site.

What I could **not** run:
- **Model inference or retraining.** No model weights are in the repository (finding R1), and PyTorch is not installed on this machine.
- **The Next.js build.** Installing npm packages was blocked by the session's permission policy. CI has never got as far as building it either (finding E1).

---

## 1. Executive summary

ASTRA has a careful data-integrity layer: hash-locked manifest, clean frozen splits, audit scripts. It also has a polished-looking web platform. Neither of its two central claims holds up when checked:

1. **"A Hybrid CNN+Transformer classifies stellar variability at 78.17% from TESS light curves."** The number is internally consistent, but:
   - It cannot be reproduced: no weights are in the repo.
   - A 3-feature Random Forest (log period, log amplitude, log SNR) scores **86.6%** on the same split.
   - The dataset has class-perfect confounds: period source, source catalog, and largely cadence all line up with the class labels.
   - The headline research finding ("period-source quality is the dominant bottleneck") is a direct product of those confounds.
2. **"A web platform with live ONNX inference."** There is no ONNX inference anywhere in the platform. On the live site, every "prediction", "attention map" and "uncertainty" is generated from the star's **ground-truth label plus deterministic noise**. Nothing in the UI says so. The upload endpoint also has a **shell command-injection** flaw.

The good news: most of what's needed already exists (processed arrays for 944 stars, frozen splits, a clean model codebase, a browse/search UI). The fix is mostly about honesty, reproducibility and de-confounding, not a rebuild.

### Top findings

| # | Severity | Finding | Evidence |
|---|---|---|---|
| P1 | 🔴 Critical | Live site shows fabricated predictions derived from the true label | [LIVE] [CODE] |
| P2 | 🔴 Critical (security) | Command injection / local file read in `/api/upload` | [CODE] |
| R1 | 🔴 Critical | No model weights anywhere in the repo; ONNX files are weightless stubs | [RUN] |
| S1 | 🔴 Critical | Class ≡ period source ≡ source catalog (perfect confound) | [RUN] |
| S2 | 🔴 Critical | Metadata-only baseline (86.6%) beats the deep model (78.2%) | [RUN] |
| S3–S6 | 🟠 High | Input discards amplitude and period; cadence-dependent detrending erases long-period signal; BLS misused; cadence confound | [RUN] [CODE] |
| S7 | 🟠 High | Cross-validation is optimistically biased and includes test stars | [CODE] |
| R2–R4 | 🟠 High | README commands don't run; 27 hardcoded paths to another machine; platform metrics have no generator and contradict each other | [RUN] [CODE] |
| E1–E2 | 🟠 High | CI red on every commit since creation; 8% test coverage | [RUN] |
| U1 | 🟠 High | ~310 MB of background video/audio committed and auto-played | [RUN] |

---

## 2. System map (as it actually is)

```
 VSX / Santos2021 / Hipparcos / literature lists          (catalog_full.json)
        │  pipeline/build_catalog.py, candidate_expander.py, stable_screen.py
        ▼
 TESS light curves via lightkurve (raw files NOT in repo)
        │  pipeline/preprocess.py  → sigma-clip, stitch, Savitzky-Golay(301 pts), BLS, fold
        ▼
 data/phase6/processed/TIC_*/{flux_1000, flux_200, folded_flux_1000, folded_flux_200}.npy
        │  (shipped copy: astra-platform/data/processed/, 944 stars, 30 MB)
        │  pipeline/freeze_phase6_splits.py → splits (shipped: docs/engineering-log/phase6_*_ids.json)
        ▼
 training/train_transformer.py · train_cnn.py · cross_validate.py · calibration.py · uncertainty.py
        │  → models/saved/*.pt (NOT in repo) → export_model.py → *.onnx + *.onnx.data (.data gitignored)
        ▼
 [manual, no script in repo] → astra-platform/data/artifacts/*.json + astra.sqlite
        ▼
 Next.js 16 app (astra-platform/)
   ├─ read-only APIs: stars, search, lightcurve, dataset, model, benchmark, calibration, research
   ├─ "inference" APIs: predict, explain, upload → exec(../.venv/bin/python …) → on failure: FABRICATED output
   └─ pages: dashboard, search, target, analysis, mission-replay, dataset, model, research, osint, visualization
```

Size: about 13.3k lines of Python in 40 files, and about 7.9k lines of TypeScript.

---

## 3. Scientific validity and ML

### S1 — Class labels are perfectly confounded with pipeline metadata 🔴 [RUN]
From `astra.sqlite` (identical to the hash-locked manifest):

| Class | Period source | Primary source | Cadence |
|---|---|---|---|
| Cepheid (230) | catalog 100% | VSX 100% | long 71% / short 29% |
| RR Lyrae (217) | catalog 100% | VSX 100% | long 92% |
| Eclipsing Binary (150) | catalog 100% | VSX 100% | long 91% |
| Solar-like (142) | **BLS 100%** | Santos2021 / literature | long 68% |
| Stable (205) | **BLS 100%** | Hipparcos | **short 100%** |

Consequences:
- **The headline research finding is a confound.** "Catalog-period stars classify more reliably than BLS-period stars (90.0% vs 57.7%)" — `research_findings.json`, README §Results — is not about period quality. The "catalog" subgroup is exactly the three variable classes, and the "BLS" subgroup is exactly Solar-like + Stable. The finding just restates which classes are hard.
- **The period source leaks into the input.** The folded channel is built differently per class: a clean catalog-period fold for variables, a BLS fold of mostly noise for the rest. The model can learn "clean fold ⇒ variable class" instead of morphology.
- **Train/serve mismatch.** For a new star, the class isn't known, so the period-selection rule (catalog if available, else BLS) is not the rule the model was trained under. A real RR Lyrae with no catalog period would arrive BLS-folded, which during training only ever meant Solar-like/Stable.

### S2 — A metadata-only baseline beats the deep model 🔴 [RUN]
Same frozen split (661 train / 142 test), no light curves used. Script: `artifacts/experiments/EXP-0001-metadata-baseline.py`.

| Features | Model | Test acc | Macro F1 |
|---|---|---|---|
| cadence, n_sectors | Random Forest | 43.7% | 0.353 |
| cadence, n_sectors, period_source | Random Forest | 62.7% | 0.572 |
| log period, log amplitude, log SNR | Logistic Regression | 81.7% | 0.792 |
| log period, log amplitude, log SNR | **Random Forest** | **86.6%** | **0.854** |
| all six | Random Forest | 90.9% | 0.897 |
| *HybridTransformer (shared), reported* | — | *78.2%* | *0.768* |

Caveats:
- For the three variable classes, `period` is the VSX catalog period. That's external information, legitimate only if catalog periods are assumed available at inference time.
- For Solar-like/Stable, `period` is a BLS value that is mostly noise (S5).

Either way, the 1.37M-parameter model is not shown to add anything over trivial features. No baseline comparison exists anywhere in the repo, which `standards/ai_ml.md` requires ("Compared to baseline; improvement quantified").

### S3 — The model never sees amplitude or period 🟠 [CODE]
- Every input channel is z-scored per star (`_resample_normalized` and `_phase_bin_normalized` in `pipeline/preprocess.py`). Amplitude, the single strongest stable-vs-variable signal (Stable median 0.0018 vs RR Lyrae 0.52), is destroyed.
- The folded channel's x-axis is phase, so the period itself is also lost. Period alone separates RR Lyrae (0.35–0.96 d) from Cepheids (1.55–69 d) perfectly in this dataset.

These are exactly the features the baseline in S2 uses. Feeding them to the network as scalar side inputs is the cheapest likely accuracy gain.

### S4 — Detrending is cadence-dependent and erases long-period signal 🟠 [CODE] [RUN]
- `preprocess.py` subtracts a Savitzky–Golay trend with a fixed window of **301 points** (`SAVGOL_WINDOW = 301`, polyorder 2). In time that is about **10 h at 2-min cadence**, **2.1 d at 10-min** and **6.3 d at 30-min**. Variability slower than the window is removed, so Cepheids (median period 6.2 d) and rotators are partly flattened, by an amount that depends on cadence.
- Both the raw and the folded channel are built from this detrended flux.
- Supporting evidence: the shipped `variability_amplitude` median is **0.023 for Cepheids vs 0.52 for RR Lyrae**, physically backwards for classical Cepheids. In the test confusion matrix, Cepheid errors go to Stable and Solar-like.
- The README and the "Pipeline" diagram describe "Spline Detrending (Biweight, window_length=0.5 days)", which is not what the code does.

### S5 — BLS is the wrong period search and returns noise for the BLS classes 🟠 [RUN] [CODE]
- Box Least Squares (built for transits) is run with a single fixed duration (0.05 d) on a **linear** 5,000-point grid from 0.1 to 50 d. That's too coarse for short periods (Δ ≈ 0.01 d) and unsuited to sinusoidal pulsation or rotation. Lomb–Scargle (plus BLS for eclipses) is the standard choice.
- BLS periods for Solar-like/Stable **pile up at the grid edges** (0.1 d and 42–50 d). Solar-like median "period" is 41.9 d, longer than one TESS sector, so the fold covers less than one cycle.
- `bls_power` values reach 9.6×10³², so it isn't usable as a feature.
- Solar-like targets come from the Santos2021 *rotation* catalog, which publishes rotation periods, yet those periods are discarded in favour of BLS.

### S6 — Cadence and sector count are additional shortcuts 🟠 [RUN]
- All 205 Stable stars are 2-min ("short") cadence; most other classes are 30-min. Combined with S4, the texture of the raw channel encodes cadence.
- Stable stars have a median of 2 sectors vs 6–8 for the rest, and the 1000-point index resampling compresses multi-sector light curves differently.
- On these artefacts alone the baseline reaches 43.7%; adding period source takes it to 62.7%, against 20% for chance.

### S7 — Cross-validation estimate is optimistically biased 🟠 [CODE]
`training/cross_validate.py`:
- Trains 50 epochs per fold and reports the **best epoch's accuracy on the same fold used to pick it** (lines 277–308). That is a max over 50 noisy estimates, not a held-out score.
- Runs over **all 944 stars, including the 142 test stars**, so the "held-out" test set took part in model development.
- Groups by `tic_id` (unique per star, so grouping does nothing) instead of `duplicate_group_id`, which the frozen split uses.

This explains why CV (84.7%) sits well above test (78.2%). The README's "95% CI [83.60%, 85.75%]" treats 15 correlated fold scores as independent.

### S8 — One 141-star validation set does three jobs 🟡 [RUN]
That set is used for checkpoint selection (max val accuracy over 50 epochs), temperature fitting, and the README's selective-prediction table. The per-class F1 drop from validation to test is large for exactly the BLS classes: Solar-like 0.78 → 0.52, Stable 0.83 → 0.66 (`models/saved/classification_report_transformer_shared.txt` vs the test confusion matrix). The calibration report text still describes an older 269-star dataset ("N=54"), so it is stale.

### S9 — Narrow and partly circular class definitions 🟡 [RUN] [CODE]
- Each variable class is exactly one VSX subtype: DCEP, RRAB and EA. There are no RRc, overtone Cepheids, W UMa or β Lyr binaries, so "Eclipsing Binary" means detached Algols only.
- "Stable" is selected by thresholds on the same TESS light curve (RMS, BLS power, Lomb–Scargle FAP; `pipeline/stable_screen.py`), so the model partly learns to reproduce the screening rule.
- Hipparcos stars are bright, which is a different brightness/saturation regime from the VSX variables.
- README attributes Solar-like's low F1 to it being under-represented (142), but Eclipsing Binary has 150 and scores 0.91. The cause is S1/S5, not sample size.

### S10 — Explainability is unvalidated 🟡 [CODE] [RUN]
- Explanations are raw head-averaged attention weights from the last encoder layer. There is no faithfulness test (deletion/occlusion), and attention is known not to be a reliable attribution.
- The project's own `astra-platform/data/artifacts/attention.json` says the ONNX explainability export is **`"status": "BLOCKED"`**, while `docs/engineering-log/phase8_final_verdict.md` marks the same item ✅ PASS.

### S11 — Reported uncertainty numbers conflict 🟡 [RUN]
There are three different selective-prediction tables:

| Source | Threshold 0.5 | Threshold 0.9 |
|---|---|---|
| README | 92.2% coverage / 88.46% acc (and 85.82% at threshold 0, which is the *validation* accuracy) | 48.2% / 92.65% |
| `src/lib/data/constants.ts` | 100% / 78.17% | 45% / 99.1% |
| `artifacts/uncertainty.json` | 86.6% / 84.6% | 43% / 98.4% |

Also, the README reports incorrect-vs-correct entropy as 0.84 vs 0.53 nats, while the artifact says 1.00 vs 0.50.

### S12 — Statistical resolution 🟢 [RUN]
- Test N = 142 gives a 95% CI of about ±7 pp. The variants (72.5–84.5%) mostly sit inside each other's CIs, and they were compared on the test set; the "separate" variant scored highest (84.5%) but was not chosen.
- Reported metrics are internally consistent: the committed confusion matrix reproduces 78.17% and every per-class F1 exactly.

### S13 — Spatial neighbours across splits 🟢 [RUN]
There are 5 cross-split star pairs within 63″ (3 TESS pixels), including TIC 351053243 (test) and TIC 351053268 (train) at **20.8″, inside one TESS pixel**, so their photometry overlaps. The impact is small (≤ 4 test stars).

---

## 4. Reproducibility

### R1 — No model weights in the repository 🔴 [RUN]
- None of the 9 checkpoints in the registry (`best_star_transformer_shared.pt`, etc.) is committed.
- Both shipped ONNX files (190 KB and 216 KB) reference **46 external tensors** in `*.onnx.data`, and `.gitignore` explicitly excludes `*.onnx.data`. A 1.37M-parameter float32 model needs about 5.5 MB.
- No TorchScript file exists either.

So none of the reported metrics can be reproduced from the repository, and no real inference is possible anywhere.

### R2 — Documented commands and paths don't exist 🟠 [CODE] [RUN]
- `train_transformer.py` has no `--seed`; the seed is hardcoded to 42 at line 446.
- `predict.py` takes `--input/--checkpoint/--attention`, not the README's `--model/--split/--temperature`, and it predicts a single star; it doesn't evaluate the test set.
- `calibration.py`, `uncertainty.py`, `cross_validate.py` and `export_model.py` take no CLI arguments at all.
- `visualize_attention.py` requires `--checkpoint` and `--output-dir`.
- The README's `splits/` and `data/phase6/` directories don't exist. The data actually lives in `astra-platform/data/` and the splits in `docs/engineering-log/phase6_*_ids.json`. The README's split-hash check script therefore fails as written.
- Training scripts default to `data/phase6/processed`, which a fresh clone doesn't have.

### R3 — 27 hardcoded absolute paths to the original author's machine 🟠 [RUN]
`/Users/soumyadebtripathy/.gemini/antigravity/brain/...` appears in 11 files, including `cross_validate.py`, `calibration.py`, `uncertainty.py`, `export_model.py`, `stress_test.py`, `stable_screen.py` and `variability_crosscheck.py`. These scripts write their outputs there and fail anywhere else.

### R4 — Platform metrics have no generator and contradict each other 🟠 [RUN]
- No script in the repo produces `astra-platform/data/artifacts/*.json` or `astra.sqlite`.
- `src/lib/data/constants.ts` hardcodes a second copy of the metrics, and they disagree:
  - ECE after calibration: README 0.0478; constants and artifact 0.0442.
  - **`calibration.json` reports NLL equal to ECE** (0.0442 / 0.081 for the transformer, 0.0907 for the CNN), clearly a copy bug. The README gives NLL 0.5332.
  - Per-class ECE in `constants.ts` (every class roughly halved) doesn't match `calibration.json`, where RR Lyrae and Eclipsing Binary get *worse* after scaling.
  - CNN macro-F1: README 0.7654, constants 0.7635.
  - The dataset-lineage funnel counts (3,200 → 2,847 → 1,621 → 1,102 → 978 → 944) have no source file.

### R5 — Environment not pinned 🟡 [RUN] [CODE]
- `requirements.txt` uses `>=` everywhere and omits `onnxruntime`, which `upload_inference.py` needs.
- There is no `package-lock.json`.
- `pyproject.toml` declares an invalid build backend (`setuptools.backends.legacy:build`), so `pip install .` fails.
- Experiment metadata records `"git_commit": "unknown"`.
- PyTorch 2.12 on MPS with a deterministic-algorithms fallback.

### R6 — Hash checks fail on Windows checkouts 🟡 [RUN]
There's no `.gitattributes`. With Git's default `core.autocrlf=true`, the split JSON files are converted to CRLF on checkout and their SHA256 no longer matches. I verified this on this machine: the committed blobs match; the working copy doesn't.

---

## 5. Backend (Next.js API routes)

### P1 — Fabricated predictions, attention maps and uncertainty 🔴 [LIVE] [CODE]
When the Python call fails, which happens on Vercel, Render, Docker and Windows every time (P4), these routes generate fake output:
- `astra-platform/src/app/api/predict/[id]/route.ts` and `astra-platform/src/app/api/explain/[id]/route.ts` read the star's **true class** from SQLite, give it 0.7 + noise and the other classes 0.05 + noise, and return that as `predicted_class` with `calibrated_confidence`, `entropy` and `variance`. Every prediction is therefore "correct".
- `/api/explain` also returns a synthetic 250×250 diagonal-band "attention matrix" made with `Math.random()`, plus synthetic "CNN feature importance".
- `astra-platform/src/app/api/upload/route.ts` guesses a class from period thresholds and returns about 75% confidence.
- The client does the same thing: `generateProbabilities(tic_id, true_class)` in `astra-platform/src/lib/utils.ts` (used by Mission Replay), plus a 0.7 default confidence in `target/[id]/page.tsx`.
- No page reads the `fallback: true` flag, so users are never told.

Confirmed live: `GET /api/predict/TIC_122784551` (a test-set Solar-like star; the real model gets only half of these right) returned `predicted_class = true_class = "solar_like"`, `fallback: true`.

This is the most serious issue in the project. It presents fabricated scientific output as model inference.

### P2 — Command injection and arbitrary file read in `/api/upload` 🔴 [CODE]
`upload/route.ts` line 39 builds a shell string from request JSON:

```ts
const command = `"${pythonPath}" "${scriptPath}" --flux "${fluxStr}" --period ${periodVal} --tic_id "${ticIdStr}"`;
await execPromise(command, …)
```

- `tic_id` is any string. If `flux` is sent as a string (not an array), it's also used verbatim, and the code comment claiming "digits and commas only" is false.
- A body such as `{"period":1,"flux":"<50 commas>","tic_id":"x\"; <command>; echo \""}` runs arbitrary commands.
- **Correction (2026-11-09):** an earlier version of this report limited the risk to hosts where the Python path exists. That was wrong. The string is executed by a shell, so the injected command runs **even when the Python binary is missing**: the first command fails and the shell carries on with the injected one, before the route falls back. It was therefore very likely exploitable on the live Vercel deployment (for example, to read the function's environment variables). This was concluded from the code and deliberately not tested against the live site. **Fixed in Phase 0** (see §11).
- Separately, `upload_inference.py` treats `--flux` as a **file path** if one exists, giving a local file-read primitive.

`predict` and `explain` interpolate the URL `id` too, but are gated by an `existsSync` on a `TIC_<id>` folder, so the risk there is lower. They should still use `execFile` with an argument array.

### P3 — Claimed ONNX Runtime inference doesn't exist 🟠 [CODE]
`onnxruntime-node` is listed in `package.json` but **never imported**. All inference paths shell out to Python, and the ONNX files couldn't load anyway (R1). README and Phase 8 docs claim "Server-side inference via exported ONNX model".

### P4 — Inference can't run on any supported deployment 🟠 [CODE]
- The Python path is hardcoded as `process.cwd()/../.venv/bin/python`. That's Unix-only, and it needs the full monorepo with a venv next to the app.
- Vercel and Render (`rootDir: astra-platform`) don't ship `../training` or `.venv`.
- The `Dockerfile` has no Python and **doesn't copy `data/`** into the runtime image, so in Docker even the dataset/SQLite routes fail and `/api/health` reports `BLOCKED`.

### P5 — Health endpoint is misleading 🟠 [LIVE] [CODE]
- `model_hash` is a hardcoded constant, never computed.
- `onnx_loaded` only means the file exists.
- The live site reports `READY` with `onnx_loaded: true` although no inference is possible.
- Phase 8 docs claim the "checkpoint hash [is] verified dynamically on startup".

### P6 — OSINT report contains invented fields 🟠 [CODE]
`osint/[id]/route.ts` returns:
- A constant cross-match distance of 0.24″.
- Fixed observation dates (2018-07-25 → 2023-04-12) for every star.
- A VSX "otype" derived from ASTRA's own label.
- A provenance step claiming "3σ" clipping (the code uses 5σ).
- Boilerplate notes ("well-defined … signature") for every star.

It also crashes when `period` is null (`star.period.toFixed`).

### P7 — Upload preprocessing differs from training 🟡 [CODE]
`upload_inference.py` skips sigma-clipping and Savitzky–Golay detrending, normalises by the median, assumes 30-min cadence for folding, and folds a 1000-point resampled array rather than real timestamps. The API also takes a JSON array, not the "raw TESS-format CSV" the README describes, and **no page in the UI calls `/api/upload`**.

### P8 — API robustness 🟡 [CODE]
- Every request opens a new SQLite handle and never closes it.
- No validation of `page`/`limit` (NaN or negative values reach SQL; bound parameters, so not injectable).
- `error.message` is returned to clients.
- No rate limiting on expensive routes.
- `/api/explain` returns roughly 1 MB of JSON per call.
- `/api/metrics` serves the hardcoded constants instead of the artifacts.

Positive: every SQL query uses bound parameters.

---

## 6. Frontend and UX

| # | Sev | Finding | Evidence |
|---|---|---|---|
| U1 | 🟠 | **~310 MB of MP4/MP3 in `public/`** (largest: `solar-system.mp4` 90 MB, `galaxy.mp4` 74 MB), one auto-playing background video per route plus ambient audio. Huge first load on `/analysis` and `/model`, and permanent git bloat. | [RUN] |
| U2 | 🟡 | `postcss.config.*`, the ESLint config, `components.json` and `package-lock.json` were **never committed** in any revision. Tailwind v4's `@import "tailwindcss"` needs the PostCSS plugin, so a fresh clone probably builds without utility classes. The deployed build presumably came from an uncommitted local folder. | [CODE] [UNVERIFIED: build blocked] |
| U3 | 🟡 | Metrics shown in the UI come partly from hardcoded `constants.ts` and partly from the API, and they disagree (R4). | [CODE] |
| U4 | 🟡 | Accessibility: no `prefers-reduced-motion` handling, only 8 `aria-*` attributes in the whole app, constant particle and video animation, ambient audio. | [RUN] |
| U5 | 🟢 | 38 uses of `any` in TypeScript; no frontend tests (unit or e2e). | [RUN] |

Positive: clear information architecture (dashboard → search → target dossier), React Query caching, a command palette, a light-curve viewer backed by the real arrays, and dataset/model pages that read the real artifacts.

---

## 7. Engineering, CI and documentation

### E1 — CI has failed on every recorded push 🟠 [RUN]
In GitHub Actions run 32371666892 (the latest), and in every run listed:

| Job | Result | Cause |
|---|---|---|
| Next.js Build | ❌ | No `package-lock.json`, so `setup-node` cache fails before `npm ci` |
| Dataset Integrity | ❌ | Looks for `phase6_*_ids.json` in the repo root; they're in `docs/engineering-log/` |
| Unit Tests (3.11/3.12) | ❌ | The 10 tests pass, but the inline smoke test calls `HybridTransformer.forward(x_raw, x_fold)` (the real API takes one `(B, 2, 1000)` tensor) and `StarCNN` with the wrong shape |
| Lint (ruff) | ✅ | — |

### E2 — Test coverage is 8% 🟠 [RUN]
There are 10 tests, all on Phase 6 pipeline utilities. Coverage: `dataset_audit.py` 75%, `phase6_utils.py` 64%, `preprocess.py` 14%, everything under `training/` 0%, API routes and frontend 0%. Nothing tests the model's forward pass, preprocessing parity between training and inference, or metric computation.

### E3 — Documentation overstates and contradicts the code 🟡 [RUN] [CODE]
- Claims contradicted by code are covered in P1, P3, P5, P7, R2 and S4.
- `docs/` has 24 broken links, mostly `file:///Users/soumyadebtripathy/...` paths and `../ground_truth_*.md` paths that don't exist. This is why the AgentOS validator scores Cross-reference 0/100.
- Three different canonical repos: the README/CITATION says `Rexy-5097/ASTRA`, `pyproject.toml` says `soumyadebtripathy/ASTRA`, and the actual remote is `yeshika-02/ASTRA`.
- `pyproject.toml` classifies the project as "Development Status :: 5 - Production/Stable".

### E4 — Pipeline code quality 🟢 [CODE]
- Many one-off scripts sit alongside the core path (`check_tess_iterative*.py`, `run_phase6a_expansion.py`, `cleanup_data.py`).
- `preprocess.py` monkey-patches lightkurve's FITS reader.
- Phase binning uses an O(N × bins) Python loop (slow for 600k-point light curves; `np.bincount` would do).

Positive: clear module boundaries, type hints, dataclasses, explicit failure stages, and hash-recorded outputs.

---

## 8. What is verified to work (preserve it)

| Component | Verdict | Evidence |
|---|---|---|
| Dataset manifest (944 stars) matches its published SHA256 | ✅ | [RUN] |
| Frozen splits: 661/141/142, zero overlap, consistent with SQLite, stratified by class | ✅ | [RUN] |
| Committed split files match published hashes (as git blobs) | ✅ | [RUN] |
| Reported test metrics are internally consistent with the committed confusion matrix | ✅ | [RUN] |
| Phase 6 pipeline unit tests (10/10 pass); ruff clean | ✅ | [RUN] |
| Processed arrays for all 944 stars are shipped (30 MB) | ✅ | [RUN] |
| Model architecture code (`hybrid_transformer.py`, 6 variants; `star_cnn.py`) | ✅ reads correctly; not executed | [CODE] |
| Read-only data APIs (stars, search, lightcurve, dataset, model, benchmark, calibration) with parameterised SQL | ✅ | [CODE] |
| UI shell, navigation, light-curve viewer, dataset/model/research pages | ✅ works on live site | [LIVE] partial |
| Temperature scaling fit on validation (not test) | ✅ correct protocol | [CODE] |

---

## 9. Scorecard against the AgentOS standards

**`standards/ai_ml.md` quality levels**

| Dimension | Current level | Gap to "Production Grade" |
|---|---|---|
| Experiment tracking | Manual notes (markdown reports) | No tracked runs; outputs written to another machine's paths |
| Train/val/test split | Stratified, documented | Need a shift analysis for period source / cadence / catalog |
| Evaluation metrics | Full suite including uncertainty | Numbers conflict between sources; CV biased |
| Reproducibility | Below minimum | No weights, unpinned env, broken commands |
| Bias testing | None | Subgroup analysis is confounded (S1) |
| Model card | None | Needed |
| Monitoring | None | — |
| Deployment gate | None; fabricated fallback shipped | — |

**QG-004 Research Validation: ❌ FAIL.**
- Baseline mapped ❌ (none exists, and a trivial baseline wins).
- Reproducibility run ❌ (no weights).
- Data split held out ⚠️ (test stars used in CV).
- Hypothesis logged ⚠️.

**QG-005 Security Review: ❌ FAIL.**
- Sanitised input ❌ (P2).
- Secrets in code ✅ (none found).
- Dependency CVEs not scanned.
- Auth not applicable (public read-only site), but rate limiting is missing.

---

## 10. Improvement opportunities, ranked by impact ÷ effort

| Rank | Opportunity | Impact | Effort | Addresses |
|---|---|---|---|---|
| 1 | Remove all fabricated fallbacks; return an explicit "inference unavailable" state; banner in UI | Very high (integrity) | S | P1 |
| 2 | Replace `exec` string building with `execFile` + strict validation (or remove shell-outs) | Very high (security) | S | P2 |
| 3 | Make `/api/health` truthful (compute hashes, test-load the model) | High | S | P5 |
| 4 | Recover or publish weights (GitHub Release / Git LFS / HF Hub) with hashes; single-file ONNX export | Very high | S–M (depends on access) | R1 |
| 5 | Commit the metadata baseline and report it next to the model | High (scientific honesty) | S | S2 |
| 6 | Get CI green (lockfile, paths, real smoke test) | High | S | E1 |
| 7 | Config-driven paths; fix the README/CLI mismatch; artifact + SQLite generator script; delete duplicated constants | High | M | R2–R4 |
| 8 | Uniform period search (Lomb–Scargle + BLS) for **every** star regardless of class; time-based detrending | Very high (science) | M–L | S1, S4, S5 |
| 9 | Add log-amplitude and log-period as scalar inputs to the network | High | S–M | S3 |
| 10 | Nested, test-free CV with `duplicate_group_id` groups | High | S | S7 |
| 11 | Real inference: precomputed predictions for the 944 stars + ONNX Runtime (Node or web) for uploads, sharing one preprocessing implementation | High | M–L | P3, P4, P7 |
| 12 | Media diet (≤ 10 MB, lazy, no autoplay audio, reduced-motion) | Medium–High | S | U1, U4 |
| 13 | Broader, de-confounded dataset (more subtypes; cadence and period source balanced across classes) | Very high, long-term | XL | S1, S6, S9 |

---

## 11. Resolution status (updated 2026-11-09, after Phase 0)

Branch `phase0/integrity-security-hotfix`. Decisions: ADR-0058 (inference contract), ADR-0059 (AgentOS GitHub files). Gate record: `artifacts/reviews/phase0-gate-review.md`.

| Finding | Status | What changed |
|---|---|---|
| P1 Fabricated predictions / attention / uncertainty | ✅ Fixed | Synthetic branches deleted from `predict`, `explain`, `upload`. `generateProbabilities` and the 0.7 defaults removed from the UI. Mission Replay no longer labels the true class as "Predicted". 503 `inference_unavailable` + an "unavailable" UI state + a site-wide notice. A static test forbids reintroducing it. |
| P2 Command injection / file read | ✅ Fixed | `spawn` with argument arrays and `shell: false`; flux over stdin; strict validation of every input; 4 MB body cap. `upload_inference.py` no longer reads a path from `--flux`. Verified: the tests fail against the original code and pass against the fix. |
| P5 Misleading health | ✅ Fixed | Recomputes dataset and checkpoint hashes, queries the DB (944 rows), checks ONNX external weights, probes Python modules. READY / DEGRADED / BLOCKED now reflect real readiness. The live deployment will report DEGRADED. |
| P6 Invented OSINT fields | ✅ Fixed | Match distance and observation dates are null; otype comes from the stored catalog label; provenance text matches the code (5σ); null-period crash fixed; id validation added |
| Hardcoded "Operational · Phase 8 Verified" / "Phase 8 Locked" / "Zero-Trust Audit Verified" badges | ✅ Fixed | Replaced with neutral or measured text |
| E1 CI red | ✅ Fixed — all 5 jobs green on GitHub (run 42519045208) | Lockfile committed; integrity job uses the real paths and now also checks hashes and split sizes; smoke test moved to `tests/test_model_smoke.py` with the correct API; new web job (typecheck, Vitest, build) |
| E2 Coverage | 🟨 Improved | +88 web tests (API, security, health, no-fabrication), +11 Python tests. `training/` coverage is still low (Phase 1, task 1.9) |
| U2 Missing build configs | ✅ Fixed, claim confirmed | Building without `postcss.config.mjs` produced 20 KB of CSS with zero Tailwind utilities; with it, 71 KB including utilities. `eslint.config.mjs` added. |
| R5 Env / packaging | 🟨 Partial | `package-lock.json` committed, Vitest pinned, `pyproject.toml` build backend fixed (wheel builds). Python requirements are still unpinned (Phase 1). |
| R6 Windows hash mismatch | ✅ Fixed | `.gitattributes` keeps JSON/CSV byte-identical; all four published hashes verified on Windows |
| R1, R2–R4, S1–S13, P3, P4, P7, P8, U1, U3–U5 | ⬜ Open | Phase 1+ (see UPDATED_ROADMAP.md) |

**Also verified during Phase 0:**
- The shared model has exactly 1,373,701 parameters, as published (CPU PyTorch smoke test).
- The build used to emit a tracing warning that would pull the whole repo into serverless bundles; this is resolved.

**New findings from Phase 0 (open):**
- **ESLint debt:** 86 problems (46 errors) across the app, now visible because the config exists. They include a `react-hooks/rules-of-hooks` violation (conditional `useMemo`) in `src/components/three/CosmicBackground.tsx`, which is a real bug, and 34 `any`. Lint isn't a CI gate yet.
- **Packaging:** the wheel installs top-level packages named `data` and `training`, which are generic names that can clash. Rename or namespace them in Phase 1.
- **AgentOS on Linux:** the validator expects `.github/PULL_REQUEST_TEMPLATE.md`, but ASTRA uses the lowercase name (hidden on Windows).

---

## Appendix A — Commands and evidence

```text
pytest tests/ -q                               → 10 passed
pytest --cov=pipeline --cov=training --cov=data → TOTAL 8%
ruff check pipeline training data tests        → All checks passed
sha256 scientific_dataset_freeze_v2.csv        → f99b4b06…dbf58 (matches)
git show HEAD:docs/engineering-log/phase6_*_ids.json | sha256 → match README
strings best_star_transformer_shared.onnx       → 46 × location=best_star_transformer_shared.onnx.data
gh run view 32371666892                         → 4/5 jobs failed (see E1)
GET /api/health                                 → status READY, onnx_loaded true
GET /api/predict/TIC_122784551                  → predicted_class == true_class, fallback true
python EXP-0001-metadata-baseline.py astra.sqlite → see S2 table
```

## Appendix B — Note on the AgentOS install

AgentOS was installed in this audit with `python ~/.agentos/agentos_init.py . --profile ml`. It copied 324 framework files and kept all 11 existing project files.

The GitHub files it added were reviewed in Phase 0 and committed in adapted form (ADR-0059):
- `CODEOWNERS` now names `@yeshika-02`.
- `lint.yml` and `validate.yml` are manual-trigger only until the validator reaches 100/100.
- `question.md` is reworded for ASTRA.
- `LABELS.md` was dropped.

The validator currently scores **94/100 (FAIL)**. The only failing category is Cross-reference, caused by the 24 pre-existing broken links in ASTRA's `docs/` (E3). Fixing those links is task T9 in [PRIORITY_TASKS.md](PRIORITY_TASKS.md).
