// Static accessibility guards (SP-29). Runtime checks were done with axe-core in a browser;
// these keep the fixes from regressing.
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC = path.resolve(__dirname, '..', 'src');
const read = (rel: string) => fs.readFileSync(path.join(SRC, rel), 'utf-8');

describe('reduced motion', () => {
  it('globals.css disables CSS animation and transitions on request', () => {
    const css = read('app/globals.css');
    const block = css.slice(css.indexOf('@media (prefers-reduced-motion: reduce)'));
    expect(block).toMatch(/animation-duration:\s*0\.01ms !important/);
    expect(block).toMatch(/transition-duration:\s*0\.01ms !important/);
  });

  it.each([
    'components/shared/ParticleLayer.tsx',
    'components/three/StarGlobe.tsx',
    'components/three/CosmicBackground.tsx',
    'components/layout/GlobalClientContainer.tsx',
  ])('%s checks the reduced-motion preference', (file) => {
    expect(read(file)).toContain('usePrefersReducedMotion()');
  });

  it('framer-motion follows the OS setting app-wide', () => {
    expect(read('components/layout/GlobalClientContainer.tsx')).toContain('<MotionConfig reducedMotion="user">');
  });
});
