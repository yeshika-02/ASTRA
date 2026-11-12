import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, fetchJson, MAX_RETRIES, shouldRetry } from '@/lib/hooks/fetchJson';

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetch(status: number, body: string) {
  const fetchMock = vi.fn(async () => new Response(body, { status, headers: { 'content-type': 'application/json' } }));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('fetchJson', () => {
  it('returns the parsed body on success', async () => {
    const fetchMock = stubFetch(200, JSON.stringify({ total: 944 }));
    await expect(fetchJson<{ total: number }>('/api/stars')).resolves.toEqual({ total: 944 });
    expect(fetchMock).toHaveBeenCalledWith('/api/stars');
  });

  it("throws ApiError with the API's message and status", async () => {
    stubFetch(400, JSON.stringify({ error: 'limit must be a whole number between 1 and 1000.' }));
    const error = await fetchJson('/api/stars?limit=0').catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 400, message: 'limit must be a whole number between 1 and 1000.' });
  });

  it('ignores any field other than error', async () => {
    stubFetch(500, JSON.stringify({ details: 'SQLITE_CANTOPEN /srv/data' }));
    const error = await fetchJson('/api/stars').catch((e: unknown) => e);
    expect(error).toMatchObject({ status: 500, message: 'Request failed (HTTP 500).' });
  });

  it('copes with a non-JSON error body', async () => {
    stubFetch(502, '<html>Bad gateway</html>');
    await expect(fetchJson('/api/stars')).rejects.toMatchObject({ status: 502, message: 'Request failed (HTTP 502).' });
  });
});

describe('shouldRetry', () => {
  it.each([400, 404, 422])('does not retry HTTP %i', (status) => {
    expect(shouldRetry(0, new ApiError('x', status))).toBe(false);
  });

  it.each([500, 503])('retries HTTP %i up to the limit', (status) => {
    expect(shouldRetry(0, new ApiError('x', status))).toBe(true);
    expect(shouldRetry(MAX_RETRIES, new ApiError('x', status))).toBe(false);
  });

  it('retries network failures', () => {
    expect(shouldRetry(1, new TypeError('fetch failed'))).toBe(true);
  });
});
