---
id: ADR-0067
title: "Decorative media and motion: landing page only, never by default for reduced motion or audio, accessibility baseline enforced by tests"
version: 1.0
status: accepted
owner: chief-architect
created: 2026-11-12
modified: 2026-11-16
related_adr: ADR-0066
related_standard: standards/ui_ux.md
related_checklist: QG-002
related_workflow: feature_development.md
related_agent: chief-architect
---

# Architecture Decision Record: ADR-0067

## Context

Sprint tasks SP-29 and SP-30 (PR #15) found:
- `public/` held 297 MB of MP4/MP3, and every route streamed its own full-screen background video. `/analysis` played the 90 MB `solar-system.mp4`, with 11 MB buffered within 25 seconds.
- Ambient audio restored a saved "playing" state, so it started without a click.
- Nothing checked `prefers-reduced-motion`.
- axe-core reported 3–4 violations on each of the 10 main pages: an unlabelled slider, an unfocusable scroll region, missing or skipped headings, content outside landmarks.
- No chart had a text alternative, and the Mission Replay stages could not be reached by keyboard.

## Problem Statement

When may the platform play decorative media and motion, and what accessibility baseline must every page keep?

## Alternatives Considered

- **Delete the unused media now.** Rejected: they are the owner's assets and deletion was not approved. Git history keeps them either way, so this stays an owner decision (D7).
- **Keep per-page videos with `preload="none"`.** Rejected: `autoplay` overrides it, so the video still streams on every visit.
- **Gate on Lighthouse CI.** Deferred: it adds a dependency and a browser to CI. axe-core, the engine behind Lighthouse's accessibility audit, plus static guards cover the same rules now. The owner can run Lighthouse by hand.
- **Landing-page-only media, preference-gated motion, and an enforced baseline.** Selected.

## Decision Rationale

1. **Video.**
   - Only `/` has a background video (`backgroundVideoFor()`).
   - It mounts after the page has loaded and the browser is idle.
   - It is skipped for `prefers-reduced-motion`, Save-Data and the "low" graphics setting. The dark backdrop layers act as the poster.
   - Data pages never load media. A test pins the set of media files the source references.
2. **Audio.** Sound starts only from a click in the current visit; on/off is not persisted. Only volume and graphics quality are restored, and both are validated.
3. **Motion.**
   - A CSS media query stops CSS animations and transitions.
   - framer-motion runs under `MotionConfig reducedMotion="user"`.
   - The particle canvas, globe spin and page transitions check `usePrefersReducedMotion()`.
   - There is no page fade on first load, because server rendering cannot know the preference.
4. **Accessibility baseline.**
   - axe-core WCAG 2.1 A/AA plus best-practice: zero violations on the 10 main pages.
   - A skip link to `<main>`; `aria-current` in the navigation; one h1 per page; panel titles are h2.
   - Every chart sits in a `ChartFrame` whose label is built from the data it draws.
   - Toggle controls carry `aria-pressed`; scrollable tables are focusable regions.
   - The command palette follows the dialog + combobox pattern.
   - Accessible names contain the visible text.
   - `tests/accessibility.test.ts` enforces each item.

## Consequences

- `/analysis` now loads 0.91 MB in total with no media requests, against the < 5 MB target.
- Data pages lose their per-page background videos. This visual change was approved in the sprint plan ("none on data pages").
- About 277 MB of unreferenced media stays in `public/` until the owner decides (D7).
- Not yet verified:
  - a Lighthouse run;
  - the video-on path in a browser with reduced motion off (the check machine has it on);
  - colour contrast, which axe reports as "needs review" because of translucent backgrounds.
