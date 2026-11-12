import * as fs from 'node:fs';
import * as path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { serverError } from '@/lib/server/errors';
import { GET as benchmarkGET } from '@/app/api/benchmark/route';
import { GET as calibrationGET } from '@/app/api/calibration/route';
import { GET as checkpointsGET } from '@/app/api/checkpoints/route';
import { GET as modelGET } from '@/app/api/model/route';
import { GET as researchGET } from '@/app/api/research/route';
import { tempDir } from './helpers';

// Text that must never reach a client: exception messages, parser internals, server paths.
const SECRET = 'SECRET_INTERNAL_DETAIL /srv/astra/private.db';

let consoleError: MockInstance<typeof console.error>;
beforeEach(() => {
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe('serverError', () => {
  it('logs the cause and returns only the generic message', async () => {
    const res = serverError('/api/test', new Error(SECRET), 'Failed to load test data');
    expect(res.status).toBe(500);
    expect(await res.json()).toEqual({ error: 'Failed to load test data' });
    expect(consoleError).toHaveBeenCalledOnce();
    expect(String(consoleError.mock.calls[0][0])).toContain(SECRET);
  });

  it('handles non-Error throwables', async () => {
    const res = serverError('/api/test', SECRET, 'Failed');
    expect(await res.text()).not.toContain('SECRET');
  });
});

/** Points process.cwd() at a fake app root whose artifact files are all corrupt JSON. */
function useCorruptArtifacts(): string {
  const root = tempDir();
  const artifacts = path.join(root, 'data', 'artifacts');
  fs.mkdirSync(artifacts, { recursive: true });
  for (const name of ['benchmark', 'calibration', 'model_registry', 'research_findings', 'uncertainty']) {
    fs.writeFileSync(path.join(artifacts, `${name}.json`), `{"${SECRET}": `);
  }
  vi.spyOn(process, 'cwd').mockReturnValue(root);
  return root;
}

describe.each([
  ['/api/benchmark', benchmarkGET],
  ['/api/calibration', calibrationGET],
  ['/api/checkpoints', checkpointsGET],
  ['/api/model', modelGET],
  ['/api/research', researchGET],
] as const)('%s with an unreadable artifact', (route, handler) => {
  it('answers 500 without leaking the parser error or paths', async () => {
    const root = useCorruptArtifacts();
    const res = await handler();
    expect(res.status).toBe(500);
    const text = await res.text();
    const body = JSON.parse(text);
    expect(Object.keys(body)).toEqual(['error']);
    expect(text).not.toContain('SECRET');
    expect(text).not.toContain(root);
    expect(text).not.toMatch(/JSON|Unexpected|position/i);
    expect(consoleError).toHaveBeenCalled();
    expect(String(consoleError.mock.calls[0][0])).toContain(route);
  });
});
