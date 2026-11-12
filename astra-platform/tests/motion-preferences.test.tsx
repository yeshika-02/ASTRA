import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CosmicBackground } from '@/components/three/CosmicBackground';
import { prefersSavedData } from '@/lib/hooks/useMotionPreferences';

vi.mock('next/navigation', () => ({ usePathname: () => '/' }));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('prefersSavedData', () => {
  it('follows navigator.connection.saveData', () => {
    vi.stubGlobal('navigator', { connection: { saveData: true } });
    expect(prefersSavedData()).toBe(true);
    vi.stubGlobal('navigator', { connection: { saveData: false } });
    expect(prefersSavedData()).toBe(false);
  });

  it('is false when the browser does not report it', () => {
    vi.stubGlobal('navigator', {});
    expect(prefersSavedData()).toBe(false);
  });
});

describe('CosmicBackground', () => {
  it('renders no video before the page has settled, even on the landing page', () => {
    const html = renderToStaticMarkup(<CosmicBackground />);
    expect(html).not.toContain('<video');
    expect(html).toMatch(/^<div aria-hidden="true"/);
  });
});
