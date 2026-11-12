'use client';

// Visitor preferences that decide whether decorative motion and media run at all.

import { useEffect, useState, useSyncExternalStore } from 'react';

export const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

function subscribeReducedMotion(onChange: () => void): () => void {
  const query = window.matchMedia(REDUCED_MOTION_QUERY);
  query.addEventListener('change', onChange);
  return () => query.removeEventListener('change', onChange);
}

/** True when the operating system asks for reduced motion. False while rendering on the server. */
export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeReducedMotion,
    () => window.matchMedia(REDUCED_MOTION_QUERY).matches,
    () => false,
  );
}

/** True when the browser reports a data-saver preference (Save-Data / Lite mode). */
export function prefersSavedData(): boolean {
  if (typeof navigator === 'undefined') return false;
  const { connection } = navigator as Navigator & { connection?: { saveData?: boolean } };
  return connection?.saveData === true;
}

/**
 * Becomes true once the page has finished loading and the browser is idle, so optional
 * media never competes with the page's own requests.
 */
export function usePageSettled(): boolean {
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let idleId: number | undefined;
    let timerId: number | undefined;

    const markSettled = () => {
      if (!cancelled) setSettled(true);
    };
    const schedule = () => {
      if (typeof window.requestIdleCallback === 'function') {
        idleId = window.requestIdleCallback(markSettled, { timeout: 3000 });
      } else {
        timerId = window.setTimeout(markSettled, 1000);
      }
    };

    if (document.readyState === 'complete') schedule();
    else window.addEventListener('load', schedule, { once: true });

    return () => {
      cancelled = true;
      window.removeEventListener('load', schedule);
      if (idleId !== undefined) window.cancelIdleCallback(idleId);
      if (timerId !== undefined) window.clearTimeout(timerId);
    };
  }, []);

  return settled;
}
