import { NextRequest } from 'next/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { closeDatabase, getDatabase } from '@/lib/server/db';
import { GET as starsGET } from '@/app/api/stars/route';
import { GET as searchGET } from '@/app/api/search/route';
import { GET as starGET } from '@/app/api/stars/[id]/route';
import { GET as osintGET } from '@/app/api/osint/[id]/route';
import { GET as datasetGET } from '@/app/api/dataset/route';
import { KNOWN_TIC, snapshotEnv, tempDir } from './helpers';

// Counts measured on the shipped registry (data/astra.sqlite, 944 stars).
const TOTAL_STARS = 944;
const CEPHEIDS = 230;
const BLS_PERIODS = 347;
const TEST_SPLIT = 142;

let restoreEnv = snapshotEnv();
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  vi.restoreAllMocks();
  closeDatabase();
  restoreEnv();
  restoreEnv = snapshotEnv();
});

const getReq = (url: string) => new NextRequest(`http://localhost${url}`);

interface StarsBody {
  stars: { tic_id: number; astra_class: string; period_source: string; split: string; primary_source: string }[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  error?: string;
}

async function stars(query: string): Promise<{ status: number; body: StarsBody }> {
  const res = await starsGET(getReq(`/api/stars?${query}`));
  return { status: res.status, body: await res.json() };
}

/** Points the data directory at an empty folder, so the registry cannot be opened. */
function useMissingDatabase(): string {
  closeDatabase();
  const dir = tempDir();
  process.env.ASTRA_DATA_DIR = dir;
  return dir;
}

describe('GET /api/stars', () => {
  it('pages through the whole registry with defaults', async () => {
    const { status, body } = await stars('');
    expect(status).toBe(200);
    expect(body.total).toBe(TOTAL_STARS);
    expect(body.stars).toHaveLength(50);
    expect(body).toMatchObject({ page: 1, limit: 50, pages: Math.ceil(TOTAL_STARS / 50) });
  });

  it('returns every star in one page for the sky map', async () => {
    const { body } = await stars(`limit=${TOTAL_STARS}`);
    expect(body.stars).toHaveLength(TOTAL_STARS);
  });

  it('filters by class, period source and split', async () => {
    const byClass = await stars('class=cepheid&limit=1000');
    expect(byClass.body.total).toBe(CEPHEIDS);
    expect(byClass.body.stars.every((s) => s.astra_class === 'cepheid')).toBe(true);

    expect((await stars('source=BLS')).body.total).toBe(BLS_PERIODS);
    expect((await stars('split=test')).body.total).toBe(TEST_SPLIT);
    expect((await stars('split=all')).body.total).toBe(TOTAL_STARS);

    const combined = await stars('class=cepheid&split=test&limit=1000');
    expect(combined.body.stars.every((s) => s.astra_class === 'cepheid' && s.split === 'test')).toBe(true);
    expect(combined.body.total).toBeLessThan(CEPHEIDS);
  });

  it('finds a star by TIC number', async () => {
    const { body } = await stars('q=100009973');
    expect(body.stars.map((s) => s.tic_id)).toContain(100009973);
  });

  it('takes LIKE wildcards in q literally', async () => {
    // Before escaping, "%" matched every star and "_" matched any single character.
    expect((await stars('q=%25')).body.total).toBe(0);
    const underscore = await stars('q=_&limit=1000');
    expect(underscore.body.total).toBeGreaterThan(0);
    expect(underscore.body.total).toBeLessThan(TOTAL_STARS);
    for (const s of underscore.body.stars) {
      expect(`${s.astra_class} ${s.primary_source}`).toContain('_');
    }
  });

  it('answers past the last page with no stars, not an error', async () => {
    const { status, body } = await stars('page=999');
    expect(status).toBe(200);
    expect(body.stars).toEqual([]);
    expect(body.total).toBe(TOTAL_STARS);
  });

  it.each(['page=0', 'page=abc', 'limit=0', 'limit=5000', 'class=quasar', 'source=VSX', 'split=training'])(
    'rejects %s with 400',
    async (query) => {
      const { status, body } = await stars(query);
      expect(status).toBe(400);
      expect(typeof body.error).toBe('string');
      expect(body).not.toHaveProperty('stars');
    },
  );

  it('reuses the shared database handle', async () => {
    const handle = getDatabase();
    await stars('');
    await stars('class=stable');
    expect(getDatabase() === handle).toBe(true);
  });

  it('answers a missing database with a generic 500', async () => {
    const dir = useMissingDatabase();
    const res = await starsGET(getReq('/api/stars'));
    expect(res.status).toBe(500);
    const text = await res.text();
    expect(JSON.parse(text)).toEqual({ error: 'Failed to query database' });
    expect(text).not.toContain(dir);
    expect(text).not.toMatch(/sqlite|unable to open/i);
  });
});

describe('GET /api/search', () => {
  const search = async (q: string) => {
    const res = await searchGET(getReq(`/api/search?q=${encodeURIComponent(q)}`));
    return { status: res.status, body: await res.json() };
  };

  it('returns no results for queries shorter than two characters', async () => {
    expect(await search('')).toEqual({ status: 200, body: { results: [] } });
    expect(await search('c')).toEqual({ status: 200, body: { results: [] } });
  });

  it('matches on catalogue label and caps results at 20', async () => {
    const { status, body } = await search('vsx');
    expect(status).toBe(200);
    expect(body.results.length).toBeGreaterThan(0);
    expect(body.results.length).toBeLessThanOrEqual(20);
  });

  it('takes LIKE wildcards literally', async () => {
    expect((await search('%%')).body.results).toEqual([]);
  });

  it('rejects an over-long query with 400', async () => {
    const { status, body } = await search('x'.repeat(101));
    expect(status).toBe(400);
    expect(body).not.toHaveProperty('results');
  });

  it('answers a missing database with a generic 500', async () => {
    const dir = useMissingDatabase();
    const res = await searchGET(getReq('/api/search?q=cepheid'));
    expect(res.status).toBe(500);
    const text = await res.text();
    expect(JSON.parse(text)).toEqual({ error: 'Failed to search database' });
    expect(text).not.toContain(dir);
  });
});

describe('GET /api/stars/[id]', () => {
  const params = (id: string) => ({ params: Promise.resolve({ id }) });
  const star = async (id: string) => {
    const res = await starGET(getReq(`/api/stars/${id}`), params(id));
    return { status: res.status, body: await res.json() };
  };

  it.each([String(KNOWN_TIC), `TIC_${KNOWN_TIC}`])('returns the star for %s', async (id) => {
    const { status, body } = await star(id);
    expect(status).toBe(200);
    expect(body.tic_id).toBe(KNOWN_TIC);
    expect(Array.isArray(body.source_catalogs)).toBe(true);
    expect(typeof body.has_folded_lc).toBe('boolean');
  });

  it('answers an unknown TIC with 404', async () => {
    expect((await star('999999999999')).status).toBe(404);
  });

  // parseInt() used to accept these: "12abc" became TIC 12 and "abc" became NaN.
  it.each(['abc', '12abc', '0', '-1', '1.5', 'TIC_', '1;DROP TABLE stars'])('rejects %j with 400', async (id) => {
    const { status, body } = await star(id);
    expect(status).toBe(400);
    expect(body).toEqual({ error: 'Invalid TIC identifier.' });
  });

  it('answers a missing database with a generic 500', async () => {
    const dir = useMissingDatabase();
    const res = await starGET(getReq(`/api/stars/${KNOWN_TIC}`), params(String(KNOWN_TIC)));
    expect(res.status).toBe(500);
    const text = await res.text();
    expect(JSON.parse(text)).toEqual({ error: 'Failed to query database' });
    expect(text).not.toContain(dir);
  });
});

describe('GET /api/dataset', () => {
  it('builds the class-by-split matrix from the shared handle', async () => {
    const res = await datasetGET();
    expect(res.status).toBe(200);
    const body = await res.json();
    const matrix = body.classSplitMatrix as Record<string, Record<string, number>>;
    const total = Object.values(matrix).reduce(
      (sum, splits) => sum + Object.values(splits).reduce((a, b) => a + b, 0),
      0,
    );
    expect(total).toBe(TOTAL_STARS);
    expect(Object.values(matrix).reduce((sum, splits) => sum + splits.test, 0)).toBe(TEST_SPLIT);
    expect(matrix.cepheid.train + matrix.cepheid.val + matrix.cepheid.test).toBe(CEPHEIDS);
  });

  it('answers a missing database with a generic 500', async () => {
    const dir = useMissingDatabase();
    const res = await datasetGET();
    expect(res.status).toBe(500);
    const text = await res.text();
    expect(JSON.parse(text)).toEqual({ error: 'Failed to load dataset details' });
    expect(text).not.toContain(dir);
  });
});

describe('GET /api/osint/[id]', () => {
  it('answers a missing database with a generic 500', async () => {
    const dir = useMissingDatabase();
    const res = await osintGET(getReq(`/api/osint/${KNOWN_TIC}`), {
      params: Promise.resolve({ id: String(KNOWN_TIC) }),
    });
    expect(res.status).toBe(500);
    const text = await res.text();
    expect(JSON.parse(text)).toEqual({ error: 'Failed to generate OSINT report' });
    expect(text).not.toContain(dir);
  });
});
