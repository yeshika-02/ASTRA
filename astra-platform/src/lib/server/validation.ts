// Strict input validation for the inference API routes.
// Everything that ends up as a process argument must pass through here first.

export const MIN_FLUX_POINTS = 50;
export const MAX_FLUX_POINTS = 100_000;
export const MAX_PERIOD_DAYS = 1_000;

const TIC_ID_PATTERN = /^(?:TIC_)?([1-9]\d{0,11})$/;

export type ValidationResult<T> = { ok: true; value: T } | { ok: false; error: string };

/** Accepts "123", "TIC_123" or a positive integer. Returns the numeric TIC id, or null. */
export function parseTicId(raw: unknown): number | null {
  if (typeof raw === 'number') {
    return Number.isSafeInteger(raw) && raw > 0 && raw < 1e12 ? raw : null;
  }
  if (typeof raw !== 'string') return null;
  const match = TIC_ID_PATTERN.exec(raw.trim());
  return match ? Number(match[1]) : null;
}

export interface UploadInput {
  ticId: number | null;
  period: number;
  flux: number[];
}

/** Validates the JSON body of POST /api/upload. Only real JSON numbers are accepted. */
export function validateUploadBody(body: unknown): ValidationResult<UploadInput> {
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    return { ok: false, error: 'Request body must be a JSON object.' };
  }
  const { tic_id, period, flux } = body as Record<string, unknown>;

  let ticId: number | null = null;
  if (tic_id !== undefined && tic_id !== null && tic_id !== '') {
    ticId = parseTicId(tic_id);
    if (ticId === null) {
      return { ok: false, error: 'tic_id must be a positive integer of at most 12 digits.' };
    }
  }

  if (typeof period !== 'number' || !Number.isFinite(period) || period <= 0 || period > MAX_PERIOD_DAYS) {
    return { ok: false, error: `period must be a number of days in (0, ${MAX_PERIOD_DAYS}].` };
  }

  if (!Array.isArray(flux)) {
    return { ok: false, error: 'flux must be a JSON array of numbers.' };
  }
  if (flux.length < MIN_FLUX_POINTS || flux.length > MAX_FLUX_POINTS) {
    return {
      ok: false,
      error: `flux must contain between ${MIN_FLUX_POINTS} and ${MAX_FLUX_POINTS} values.`,
    };
  }
  for (const value of flux) {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      return { ok: false, error: 'flux must contain only finite numbers.' };
    }
  }

  return { ok: true, value: { ticId, period, flux: flux as number[] } };
}
