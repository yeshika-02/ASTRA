import { describe, expect, it } from 'vitest';
import { MAX_FLUX_POINTS, parseTicId, validateUploadBody } from '@/lib/server/validation';
import { flux } from './helpers';

describe('parseTicId', () => {
  it('accepts plain and prefixed numeric ids', () => {
    expect(parseTicId('100009973')).toBe(100009973);
    expect(parseTicId('TIC_100009973')).toBe(100009973);
    expect(parseTicId(42)).toBe(42);
  });

  it.each([
    '',
    '0',
    '-5',
    '1.5',
    'abc',
    'TIC_',
    '123;rm -rf /',
    '123" && whoami',
    '$(id)',
    '`id`',
    '../../etc/passwd',
    '..%2F..%2Fetc',
    '1234567890123', // 13 digits
    'tic_123',
  ])('rejects %j', (raw) => {
    expect(parseTicId(raw)).toBeNull();
  });

  it('rejects non-string, non-integer values', () => {
    expect(parseTicId(null)).toBeNull();
    expect(parseTicId(1.5)).toBeNull();
    expect(parseTicId({})).toBeNull();
  });
});

describe('validateUploadBody', () => {
  const good = { period: 0.5, flux: flux(60) };

  it('accepts a well-formed body', () => {
    const r = validateUploadBody({ ...good, tic_id: 'TIC_123' });
    expect(r).toEqual({ ok: true, value: { ticId: 123, period: 0.5, flux: good.flux } });
  });

  it('treats tic_id as optional', () => {
    const r = validateUploadBody(good);
    expect(r.ok && r.value.ticId).toBe(null);
  });

  it.each([
    ['shell metacharacters in tic_id', { ...good, tic_id: 'x"; touch /tmp/pwned; echo "' }],
    ['command substitution in tic_id', { ...good, tic_id: '$(whoami)' }],
    ['flux sent as a string (old injection vector)', { ...good, flux: `${'1,'.repeat(60)}"; id; echo "` }],
    ['flux with string elements', { ...good, flux: [...flux(59), '1; id'] }],
    ['flux with null elements', { ...good, flux: [...flux(59), null] }],
    ['too few flux values', { ...good, flux: flux(49) }],
    ['too many flux values', { ...good, flux: flux(MAX_FLUX_POINTS + 1) }],
    ['period as a string', { ...good, period: '0.5; id' }],
    ['zero period', { ...good, period: 0 }],
    ['negative period', { ...good, period: -1 }],
    ['huge period', { ...good, period: 1e9 }],
    ['missing period', { flux: good.flux }],
    ['array body', [good]],
    ['null body', null],
  ])('rejects %s', (_label, body) => {
    expect(validateUploadBody(body).ok).toBe(false);
  });
});
