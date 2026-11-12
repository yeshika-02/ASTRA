// JSON fetch used by every data hook. A non-2xx answer becomes an ApiError carrying the
// API's own `error` message (routes never send exception text) and the HTTP status.

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function messageOf(body: unknown, status: number): string {
  if (typeof body === 'object' && body !== null) {
    const { error } = body as { error?: unknown };
    if (typeof error === 'string' && error.trim() !== '') return error;
  }
  return `Request failed (HTTP ${status}).`;
}

export async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(messageOf(body, response.status), response.status);
  }
  return (await response.json()) as T;
}

export const MAX_RETRIES = 3;

/**
 * React Query retry policy: a 4xx answer (bad input, missing record) will not change on
 * retry, so it fails at once; network errors and 5xx answers are retried up to MAX_RETRIES.
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < MAX_RETRIES;
}
