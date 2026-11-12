import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { serverError } from '@/lib/server/errors';

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
