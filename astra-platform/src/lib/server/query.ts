// Query-string validation for the registry routes (/api/stars, /api/search).
// Values that reach SQL are already bound as parameters; this module makes sure they are
// also meaningful, so a typo answers 400 with a reason instead of an empty page or a 500.

import type { AstraClass, PeriodSource, Split } from '@/lib/types';
import { CLASS_NAMES } from './inference';
import type { ValidationResult } from './validation';

export const DEFAULT_PAGE = 1;
export const MAX_PAGE = 10_000;
export const DEFAULT_LIMIT = 50;
/** Large enough for the sky map, which asks for every star (944) in one call. */
export const MAX_LIMIT = 1_000;
export const MAX_QUERY_LENGTH = 100;
/** Shortest free-text query /api/search answers; shorter ones return no results. */
export const MIN_SEARCH_LENGTH = 2;

export const PERIOD_SOURCES = ['catalog', 'BLS'] as const satisfies readonly PeriodSource[];
export const SPLITS = ['train', 'val', 'test'] as const satisfies readonly Split[];

export interface StarQuery {
  /** Lower-cased, trimmed free text; '' means no text filter. */
  q: string;
  /** Empty means every class. */
  classes: AstraClass[];
  /** Empty means every period source. */
  sources: PeriodSource[];
  /** null means every split. */
  split: Split | null;
  page: number;
  limit: number;
}

function parseBoundedInt(
  name: string,
  raw: string | null,
  fallback: number,
  max: number,
): ValidationResult<number> {
  if (raw === null || raw.trim() === '') return { ok: true, value: fallback };
  const text = raw.trim();
  if (!/^\d{1,9}$/.test(text)) {
    return { ok: false, error: `${name} must be a whole number between 1 and ${max}.` };
  }
  const value = Number(text);
  if (value < 1 || value > max) {
    return { ok: false, error: `${name} must be a whole number between 1 and ${max}.` };
  }
  return { ok: true, value };
}

function parseList<T extends string>(
  name: string,
  raw: string | null,
  allowed: readonly T[],
): ValidationResult<T[]> {
  if (raw === null) return { ok: true, value: [] };
  const items = raw
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s !== '');
  const values: T[] = [];
  for (const item of items) {
    if (!(allowed as readonly string[]).includes(item)) {
      return { ok: false, error: `${name} must be one or more of: ${allowed.join(', ')}.` };
    }
    if (!values.includes(item as T)) values.push(item as T);
  }
  return { ok: true, value: values };
}

function parseText(raw: string | null): ValidationResult<string> {
  const text = (raw ?? '').trim().toLowerCase();
  if (text.length > MAX_QUERY_LENGTH) {
    return { ok: false, error: `q must be at most ${MAX_QUERY_LENGTH} characters.` };
  }
  return { ok: true, value: text };
}

/** Validates the query string of GET /api/stars. */
export function parseStarQuery(params: URLSearchParams): ValidationResult<StarQuery> {
  const q = parseText(params.get('q'));
  if (!q.ok) return q;

  const classes = parseList('class', params.get('class'), CLASS_NAMES);
  if (!classes.ok) return classes;

  const sources = parseList('source', params.get('source'), PERIOD_SOURCES);
  if (!sources.ok) return sources;

  const rawSplit = (params.get('split') ?? '').trim();
  let split: Split | null = null;
  if (rawSplit !== '' && rawSplit !== 'all') {
    if (!(SPLITS as readonly string[]).includes(rawSplit)) {
      return { ok: false, error: `split must be one of: all, ${SPLITS.join(', ')}.` };
    }
    split = rawSplit as Split;
  }

  const page = parseBoundedInt('page', params.get('page'), DEFAULT_PAGE, MAX_PAGE);
  if (!page.ok) return page;

  const limit = parseBoundedInt('limit', params.get('limit'), DEFAULT_LIMIT, MAX_LIMIT);
  if (!limit.ok) return limit;

  return {
    ok: true,
    value: {
      q: q.value,
      classes: classes.value,
      sources: sources.value,
      split,
      page: page.value,
      limit: limit.value,
    },
  };
}

/** Validates the `q` parameter of GET /api/search. */
export function parseSearchQuery(params: URLSearchParams): ValidationResult<string> {
  return parseText(params.get('q'));
}

/**
 * LIKE pattern matching `text` anywhere, with SQL wildcards in the text taken literally.
 * Use with `LIKE ? ESCAPE '\'`.
 */
export function containsPattern(text: string): string {
  return `%${text.replace(/[\\%_]/g, (c) => `\\${c}`)}%`;
}
