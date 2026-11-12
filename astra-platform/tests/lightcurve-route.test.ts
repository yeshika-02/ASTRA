import * as fs from 'node:fs';
import * as path from 'node:path';
import { NextRequest } from 'next/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GET as lightcurveGET } from '@/app/api/lightcurve/[id]/route';
import { KNOWN_TIC, tempDir } from './helpers';

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  vi.restoreAllMocks();
});

async function lightcurve(id: string) {
  const res = await lightcurveGET(new NextRequest(`http://localhost/api/lightcurve/x`), {
    params: Promise.resolve({ id }),
  });
  const text = await res.text();
  return { status: res.status, text, body: JSON.parse(text) };
}

describe('GET /api/lightcurve/[id]', () => {
  it.each([String(KNOWN_TIC), `TIC_${KNOWN_TIC}`])('returns the four flux series for %s', async (id) => {
    const { status, body } = await lightcurve(id);
    expect(status).toBe(200);
    expect(body.tic_id).toBe(KNOWN_TIC);
    expect(body.flux_1000).toHaveLength(1000);
    expect(body.flux_200).toHaveLength(200);
    expect(body.folded_flux_1000).toHaveLength(1000);
    expect(body.folded_flux_200).toHaveLength(200);
  });

  // The id is part of a file path: anything but a TIC number must stop before the filesystem.
  it.each(['..', '../../etc', '..\\..\\windows', 'TIC_1/../../x', 'abc', '0', '12abc'])(
    'rejects %j with 400',
    async (id) => {
      const { status, body } = await lightcurve(id);
      expect(status).toBe(400);
      expect(body).toEqual({ error: 'Invalid TIC identifier.' });
    },
  );

  it('answers a star without processed data with 404 and no server path', async () => {
    const { status, text, body } = await lightcurve('999999999999');
    expect(status).toBe(404);
    expect(body).toEqual({ error: 'Light curve not found.' });
    expect(text).not.toMatch(/ENOENT|processed|npy/i);
    expect(text).not.toContain(process.cwd().replace(/\\/g, '\\\\'));
  });

  it('answers a corrupt file with a generic 500', async () => {
    const root = tempDir();
    const dir = path.join(root, 'data', 'processed', 'TIC_42');
    fs.mkdirSync(dir, { recursive: true });
    for (const name of ['flux_1000', 'flux_200', 'folded_flux_1000', 'folded_flux_200']) {
      fs.writeFileSync(path.join(dir, `${name}.npy`), 'not numpy');
    }
    vi.spyOn(process, 'cwd').mockReturnValue(root);

    const { status, text, body } = await lightcurve('42');
    expect(status).toBe(500);
    expect(body).toEqual({ error: 'Failed to read light curve' });
    expect(text).not.toContain('npy');
  });
});
