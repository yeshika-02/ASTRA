import { describe, expect, it, vi } from 'vitest';
import { readPreferences, STORAGE_KEYS } from '@/lib/store/preferences';
import { useAstraStore } from '@/lib/store';

function memoryStorage(values: Record<string, string>) {
  const data = new Map(Object.entries(values));
  return {
    getItem: vi.fn((k: string) => data.get(k) ?? null),
    removeItem: vi.fn((k: string) => void data.delete(k)),
    data,
  };
}

describe('readPreferences', () => {
  it('restores volume and graphics quality', () => {
    const storage = memoryStorage({ [STORAGE_KEYS.audioVolume]: '0.25', [STORAGE_KEYS.quality]: 'low' });
    expect(readPreferences(storage)).toEqual({ audioVolume: 0.25, qualityState: 'low' });
  });

  it('never restores audio playback and drops the legacy key', () => {
    const storage = memoryStorage({ [STORAGE_KEYS.legacyAudioState]: 'playing' });
    const prefs = readPreferences(storage);
    expect(prefs).toEqual({});
    expect(prefs).not.toHaveProperty('audioState');
    expect(storage.data.has(STORAGE_KEYS.legacyAudioState)).toBe(false);
  });

  it.each(['abc', '', '-0.1', '1.5', 'NaN', 'Infinity'])('ignores the stored volume %j', (volume) => {
    expect(readPreferences(memoryStorage({ [STORAGE_KEYS.audioVolume]: volume }))).toEqual({});
  });

  it('ignores an unknown quality value', () => {
    expect(readPreferences(memoryStorage({ [STORAGE_KEYS.quality]: 'ultra' }))).toEqual({});
  });

  it('falls back to defaults when storage is missing or throws', () => {
    expect(readPreferences(null)).toEqual({});
    const throwing = {
      getItem: () => {
        throw new Error('SecurityError');
      },
      removeItem: () => {
        throw new Error('SecurityError');
      },
    };
    expect(readPreferences(throwing)).toEqual({});
  });
});

describe('store audio state', () => {
  it('starts muted', () => {
    expect(useAstraStore.getState().audioState).toBe('muted');
  });
});
