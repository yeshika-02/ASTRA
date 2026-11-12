// Display preferences restored from localStorage on load.
//
// Audio on/off is deliberately not among them: sound may only start from a click in the
// current visit, never by itself when a page opens (SP-30, no autoplay audio).

export type QualityState = 'low' | 'medium' | 'high';

export const STORAGE_KEYS = {
  audioVolume: 'astra-audio-volume',
  quality: 'astra-quality-state',
  /** Written by earlier versions; removed on load so a stale "playing" is never honoured. */
  legacyAudioState: 'astra-audio-state',
} as const;

const QUALITY_STATES: readonly QualityState[] = ['low', 'medium', 'high'];

export interface StoredPreferences {
  audioVolume?: number;
  qualityState?: QualityState;
}

type PreferenceStorage = Pick<Storage, 'getItem' | 'removeItem'>;

/** Reads and validates saved preferences. Storage that is missing or throws yields {}. */
export function readPreferences(storage: PreferenceStorage | null | undefined): StoredPreferences {
  if (!storage) return {};
  const prefs: StoredPreferences = {};
  try {
    storage.removeItem(STORAGE_KEYS.legacyAudioState);

    const volume = storage.getItem(STORAGE_KEYS.audioVolume);
    if (volume !== null && volume.trim() !== '') {
      const value = Number(volume);
      if (Number.isFinite(value) && value >= 0 && value <= 1) prefs.audioVolume = value;
    }

    const quality = storage.getItem(STORAGE_KEYS.quality);
    if (quality !== null && (QUALITY_STATES as readonly string[]).includes(quality)) {
      prefs.qualityState = quality as QualityState;
    }
  } catch {
    // Storage blocked (private mode, disabled cookies): fall back to defaults.
  }
  return prefs;
}

/** window.localStorage, or null on the server or when the browser refuses access. */
export function browserStorage(): Storage | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** Saves one preference, ignoring storage that is unavailable. */
export function writePreference(key: string, value: string): void {
  try {
    browserStorage()?.setItem(key, value);
  } catch {
    // Ignore: the preference simply is not remembered.
  }
}
