---
id: ADR-0066
title: "API input and error contract: validate before use, one read-only database handle, generic failures"
version: 1.0
status: accepted
owner: chief-architect
created: 2026-11-12
modified: 2026-11-16
related_adr: ADR-0058
related_standard: standards/api_design.md
related_checklist: QG-002
related_workflow: feature_development.md
related_agent: chief-architect
---

# Architecture Decision Record: ADR-0066

## Context

ADR-0058 made the inference routes validate their input and never invent output. The registry and artifact routes were never brought in line with it (sprint task SP-27, PR #14):
- every database route opened its own `DatabaseSync` per request and never closed it;
- `page` and `limit` came from bare `parseInt`, and `class`, `source` and `split` were not checked;
- LIKE wildcards in `q` were live, so `q=%` matched every star;
- `/api/stars/12abc` was served as TIC 12;
- `/api/lightcurve/<id>` built a file path from the raw id and echoed the exception, including the server path;
- ten routes returned `details: error.message`.

On the client:
- four pages showed a dead-end "System Error" box;
- three pages ignored failed requests entirely;
- OSINT rendered an error body as a report and crashed;
- Mission Replay presented a failed request as "Model inference unavailable".

## Problem Statement

What contract should every API route, and every page that calls one, follow for input, database access and failures?

## Alternatives Considered

- **Option A — Fix each route by hand.** Rejected: nothing would stop the next route repeating the same mistakes.
- **Option B — A schema library (for example zod) for every route.** Rejected for now: it adds a dependency for a handful of parameters that the existing `ValidationResult` pattern already covers.
- **Option C — Small shared server modules and client components, kept in place by static guards.** Selected.

## Decision Rationale

1. **One database handle.** `lib/server/db.ts` opens `data/astra.sqlite` once, read-only and `immutable`, and honours `ASTRA_DATA_DIR`. Routes call `getDatabase()` and never construct `DatabaseSync`.
2. **Input is parsed before it is used.**
   - Ids go through `parseTicId()`; query strings go through `parseStarQuery()` / `parseSearchQuery()`.
   - Limits: page 1–10 000; limit 1–1 000 (the sky map fetches all 944 stars); `q` up to 100 characters; class, source and split from fixed lists.
   - Invalid input gets a 400 whose message names the parameter. LIKE wildcards in `q` are matched literally.
3. **Failures.** A missing record is a 404 with a plain message. Anything unexpected goes through `serverError(route, error, message)`: the cause is logged on the server, and the client gets `{ error: message }` only. No response contains exception text.
4. **Client.**
   - `fetchJson` throws `ApiError` carrying the HTTP status. 4xx answers are not retried; network errors and 5xx answers are.
   - Data views render `PageLoading` / `LoadError` / `PageError` with Retry.
   - A failed request is never shown as "not found" or "inference unavailable".
5. **Guards.** `tests/api-hygiene.test.ts` scans every route for constructed handles, exception text in responses and bare `parseInt`. `tests/page-states.test.ts` requires every data page to handle `isError` and offer Retry. Both match the code as it was before this decision.

## Consequences

- Routes are shorter, and new routes inherit the rules through the guards.
- Clients see stable, generic error messages. Operators find causes in the server log.
- The registry routes now follow `ASTRA_DATA_DIR`. The artifact routes still read `./data/artifacts` under the working directory; with the variable unset the two are the same folder.
- The handle lives for the life of the server process. That is safe only because the database is never written at runtime; a writable database would need a different design.
