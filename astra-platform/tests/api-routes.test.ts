import { NextRequest } from 'next/server';
import { afterEach, describe, expect, it } from 'vitest';
import { GET as predictGET } from '@/app/api/predict/[id]/route';
import { GET as explainGET } from '@/app/api/explain/[id]/route';
import { POST as uploadPOST } from '@/app/api/upload/route';
import { GET as osintGET } from '@/app/api/osint/[id]/route';
import { flux, KNOWN_TIC, snapshotEnv, useFakeModelEnv, useMissingModelEnv } from './helpers';

let restoreEnv = snapshotEnv();
afterEach(() => {
  restoreEnv();
  restoreEnv = snapshotEnv();
});

const params = (id: string) => ({ params: Promise.resolve({ id }) });
const getReq = (url: string) => new NextRequest(`http://localhost${url}`);
const postUpload = (body: unknown) =>
  uploadPOST(
    new NextRequest('http://localhost/api/upload', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: typeof body === 'string' ? body : JSON.stringify(body),
    }),
  );

// Fields that only a real model may produce. None may appear in an "unavailable" answer.
const MODEL_FIELDS = ['predicted_class', 'probabilities', 'calibrated_confidence', 'entropy', 'variance', 'attention_weights', 'true_class'];

function expectNoModelOutput(body: Record<string, unknown>) {
  for (const f of MODEL_FIELDS) expect(body).not.toHaveProperty(f);
}

describe.each([
  ['predict', predictGET],
  ['explain', explainGET],
] as const)('GET /api/%s/[id]', (kind, handler) => {
  it.each(['1;rm -rf ~', '..', 'TIC_abc', '0', '$(id)', '12345678901234'])('rejects invalid id %j with 400', async (id) => {
    useMissingModelEnv();
    const res = await handler(getReq(`/api/${kind}/x`), params(id));
    expect(res.status).toBe(400);
  });

  it('returns 404 for a star that is not in the dataset', async () => {
    useMissingModelEnv();
    const res = await handler(getReq(`/api/${kind}/1`), params('1'));
    expect(res.status).toBe(404);
  });

  it('returns 503 inference_unavailable with no fabricated output when the model is missing', async () => {
    useMissingModelEnv();
    const res = await handler(getReq(`/api/${kind}/${KNOWN_TIC}`), params(`TIC_${KNOWN_TIC}`));
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.status).toBe('inference_unavailable');
    expect(body.capability).toBe(kind);
    expect(body.reasons.length).toBeGreaterThan(0);
    expectNoModelOutput(body);
    expect(JSON.stringify(body)).not.toMatch(/[A-Za-z]:\\|\/tmp\/|\/Users\//); // no server paths leaked
  });

  it('returns 503 when the model process fails, never a substitute answer', async () => {
    useFakeModelEnv();
    process.env.FAKE_MODEL_MODE = 'error';
    const res = await handler(getReq(`/api/${kind}/${KNOWN_TIC}`), params(String(KNOWN_TIC)));
    expect(res.status).toBe(503);
    expectNoModelOutput(await res.json());
  });

  it('returns 503 when the model output is malformed', async () => {
    useFakeModelEnv();
    process.env.FAKE_MODEL_MODE = 'bad_payload';
    const res = await handler(getReq(`/api/${kind}/${KNOWN_TIC}`), params(String(KNOWN_TIC)));
    expect(res.status).toBe(503);
    expect((await res.json()).reasons).toEqual(['invalid_model_output']);
  });

  it('returns the real model output, marked source=model, when inference runs', async () => {
    useFakeModelEnv();
    const res = await handler(getReq(`/api/${kind}/${KNOWN_TIC}`), params(String(KNOWN_TIC)));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.source).toBe('model');
    expect(body.predicted_class).toBe('cepheid');
    expect(body.received_args).toContain('--input');
  });
});

describe('POST /api/upload', () => {
  const good = { period: 0.5, flux: flux(120), tic_id: 'TIC_12345' };

  it.each([
    ['shell injection in tic_id', { ...good, tic_id: 'x"; touch /tmp/pwned; echo "' }],
    ['shell injection through a string flux', { ...good, flux: `${'1,'.repeat(60)}"; id; echo "` }],
    ['a server file path as flux', { ...good, flux: '/etc/passwd' }],
    ['non-numeric flux values', { ...good, flux: [...flux(60), 'x'] }],
    ['too few points', { ...good, flux: flux(10) }],
    ['invalid period', { ...good, period: 'abc' }],
  ])('rejects %s with 400 before any process starts', async (_label, body) => {
    useFakeModelEnv(); // a runnable model is present, so only validation can stop the request
    const res = await postUpload(body);
    expect(res.status).toBe(400);
    expectNoModelOutput(await res.json());
  });

  it('rejects malformed JSON with 400', async () => {
    useMissingModelEnv();
    const res = await postUpload('{"period": 1, "flux": [1,2');
    expect(res.status).toBe(400);
  });

  it('rejects oversized bodies with 413', async () => {
    useMissingModelEnv();
    const res = await postUpload(JSON.stringify({ period: 1, flux: [], pad: 'x'.repeat(5 * 1024 * 1024) }));
    expect(res.status).toBe(413);
  });

  it('returns 503 inference_unavailable (no period-based guess) when the model is missing', async () => {
    useMissingModelEnv();
    const res = await postUpload(good);
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body).toMatchObject({ status: 'inference_unavailable', capability: 'upload' });
    expectNoModelOutput(body);
  });

  it('runs the model with separate arguments and the flux on stdin', async () => {
    useFakeModelEnv();
    const res = await postUpload(good);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.source).toBe('model');
    expect(body.received_args).toEqual(expect.arrayContaining(['--flux-stdin', '--period', '0.5', '--tic_id', '12345']));
    expect(JSON.parse(body.received_stdin)).toEqual(good.flux);
  });
});

describe('GET /api/osint/[id]', () => {
  it('returns only stored fields, with no invented match distance or dates', async () => {
    const res = await osintGET(getReq(`/api/osint/${KNOWN_TIC}`), params(String(KNOWN_TIC)));
    expect(res.status).toBe(200);
    const body = await res.json();
    for (const m of body.cross_matches) expect(m.distance_arcsec).toBeNull();
    expect(body.observational_history[0].first_obs).toBeNull();
    expect(body.observational_history[0].last_obs).toBeNull();
    expect(body.scientific_notes).toMatch(/ground truth, not a model prediction/);
  });

  it('rejects an invalid id with 400', async () => {
    const res = await osintGET(getReq('/api/osint/x'), params('1; drop table stars'));
    expect(res.status).toBe(400);
  });
});
