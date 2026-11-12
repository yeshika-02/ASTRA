import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { backgroundVideoFor, HOME_BACKGROUND_VIDEO } from '@/components/three/backgroundVideo';

const ROOT = path.resolve(__dirname, '..');

function sourceFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(full);
    return /\.(ts|tsx|css)$/.test(entry.name) ? [full] : [];
  });
}

describe('backgroundVideoFor', () => {
  it('plays a video only on the landing page', () => {
    expect(backgroundVideoFor('/')).toBe(HOME_BACKGROUND_VIDEO);
    expect(fs.existsSync(path.join(ROOT, 'public', HOME_BACKGROUND_VIDEO))).toBe(true);
  });

  it.each([
    '/search',
    '/analysis',
    '/dataset',
    '/model',
    '/research',
    '/mission-replay',
    '/osint',
    '/visualization',
    '/target/100009973',
    '/no-such-page',
  ])('keeps %s static', (route) => {
    expect(backgroundVideoFor(route)).toBeNull();
  });
});

describe('media referenced by the app', () => {
  it('is limited to the landing-page video', () => {
    const referenced = new Set<string>();
    for (const file of sourceFiles(path.join(ROOT, 'src'))) {
      for (const match of fs.readFileSync(file, 'utf-8').matchAll(/['"`](\/[\w./-]+\.(?:mp4|webm|mov|mp3|wav|ogg))['"`]/g)) {
        referenced.add(match[1]);
      }
    }
    expect([...referenced]).toEqual([HOME_BACKGROUND_VIDEO]);
  });
});
