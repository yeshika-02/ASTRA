import { describe, expect, it } from 'vitest';
import {
  containsPattern,
  DEFAULT_LIMIT,
  MAX_LIMIT,
  MAX_PAGE,
  MAX_QUERY_LENGTH,
  parseSearchQuery,
  parseStarQuery,
} from '@/lib/server/query';

const qs = (s: string) => new URLSearchParams(s);

describe('parseStarQuery', () => {
  it('fills defaults for an empty query string', () => {
    expect(parseStarQuery(qs(''))).toEqual({
      ok: true,
      value: { q: '', classes: [], sources: [], split: null, page: 1, limit: DEFAULT_LIMIT },
    });
  });

  it('accepts every filter the UI sends', () => {
    const r = parseStarQuery(qs('q=%20Cepheid%20&class=cepheid&source=BLS&split=test&page=3&limit=20'));
    expect(r).toEqual({
      ok: true,
      value: { q: 'cepheid', classes: ['cepheid'], sources: ['BLS'], split: 'test', page: 3, limit: 20 },
    });
  });

  it('accepts comma lists, drops blanks and duplicates', () => {
    const r = parseStarQuery(qs('class=rr_lyrae,,stable,rr_lyrae&source=catalog,BLS'));
    expect(r.ok && r.value.classes).toEqual(['rr_lyrae', 'stable']);
    expect(r.ok && r.value.sources).toEqual(['catalog', 'BLS']);
  });

  it('treats split=all and empty values as no filter', () => {
    const r = parseStarQuery(qs('split=all&page=&limit=&class='));
    expect(r.ok && r.value).toMatchObject({ split: null, page: 1, limit: DEFAULT_LIMIT, classes: [] });
  });

  it('allows the sky map to fetch the whole registry in one page', () => {
    const r = parseStarQuery(qs('limit=944'));
    expect(r.ok && r.value.limit).toBe(944);
  });

  it.each([
    ['page=0', 'page'],
    ['page=-1', 'page'],
    ['page=1.5', 'page'],
    ['page=abc', 'page'],
    ['page=1e3', 'page'],
    [`page=${MAX_PAGE + 1}`, 'page'],
    ['page=99999999999999999999', 'page'],
    ['limit=0', 'limit'],
    [`limit=${MAX_LIMIT + 1}`, 'limit'],
    ['limit=50;DROP', 'limit'],
    ['class=quasar', 'class'],
    ['class=cepheid,Cepheid', 'class'],
    ["class=cepheid') OR 1=1 --", 'class'],
    ['source=bls', 'source'],
    ['source=VSX', 'source'],
    ['split=training', 'split'],
    [`q=${'x'.repeat(MAX_QUERY_LENGTH + 1)}`, 'q'],
  ])('rejects %s', (query, field) => {
    const r = parseStarQuery(qs(query));
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error.startsWith(field)).toBe(true);
  });
});

describe('parseSearchQuery', () => {
  it('lower-cases and trims', () => {
    expect(parseSearchQuery(qs('q=%20VSX%20'))).toEqual({ ok: true, value: 'vsx' });
  });

  it('allows a missing query', () => {
    expect(parseSearchQuery(qs(''))).toEqual({ ok: true, value: '' });
  });

  it('rejects an over-long query', () => {
    expect(parseSearchQuery(qs(`q=${'a'.repeat(MAX_QUERY_LENGTH + 1)}`)).ok).toBe(false);
  });
});

describe('containsPattern', () => {
  it('wraps text in wildcards', () => {
    expect(containsPattern('vsx')).toBe('%vsx%');
  });

  it('escapes LIKE wildcards and the escape character', () => {
    expect(containsPattern('50%_a\\b')).toBe('%50\\%\\_a\\\\b%');
  });
});
