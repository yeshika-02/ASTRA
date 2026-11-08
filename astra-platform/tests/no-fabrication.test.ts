// Regression guard: the platform must never generate model-like output itself, and only the
// inference module may start processes (without a shell).
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC = path.resolve(__dirname, '..', 'src');

function sourceFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return sourceFiles(p);
    return /\.(ts|tsx)$/.test(e.name) ? [p] : [];
  });
}

const files = sourceFiles(SRC).map((f) => ({ rel: path.relative(SRC, f).replace(/\\/g, '/'), text: fs.readFileSync(f, 'utf8') }));

// Visual effects (particles, starfield, ambient audio) may use randomness; nothing else may.
const RANDOM_ALLOWED = new Set([
  'components/shared/ParticleLayer.tsx',
  'components/three/CosmicBackground.tsx',
  'components/three/StarGlobe.tsx',
  'lib/utils/SpaceHum.ts',
]);

describe('no fabricated model output', () => {
  it('uses Math.random only in visual-effect code', () => {
    const offenders = files.filter((f) => f.text.includes('Math.random') && !RANDOM_ALLOWED.has(f.rel)).map((f) => f.rel);
    expect(offenders).toEqual([]);
  });

  it('has no label-derived probability generators or fallback predictions', () => {
    const patterns = [/generateProbabilities/, /fallback:\s*true/, /trueClass\s*=/];
    const offenders = files.filter((f) => patterns.some((p) => p.test(f.text))).map((f) => f.rel);
    expect(offenders).toEqual([]);
  });

  it('only lib/server/inference.ts starts child processes, and never with a shell', () => {
    const spawners = files.filter((f) => /from ['"](node:)?child_process['"]/.test(f.text)).map((f) => f.rel);
    expect(spawners).toEqual(['lib/server/inference.ts']);
    const inference = files.find((f) => f.rel === 'lib/server/inference.ts')!.text;
    expect(inference).toMatch(/shell:\s*false/);
    expect(inference).not.toMatch(/\bexec(Sync)?\(/);
  });
});
