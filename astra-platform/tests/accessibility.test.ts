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

describe('top bar controls', () => {
  const topBar = read('components/layout/TopBar.tsx');

  it('labels the volume slider beyond a title attribute', () => {
    const slider = topBar.slice(topBar.indexOf('type="range"'), topBar.indexOf('/>', topBar.indexOf('type="range"')));
    expect(slider).toContain('aria-label="Ambient audio volume"');
    expect(slider).toContain('aria-valuetext=');
  });

  it('exposes the audio button as a toggle', () => {
    expect(topBar).toContain("aria-pressed={audioState === 'playing'}");
  });

  it('names the graphics quality button with its current state', () => {
    expect(topBar).toMatch(/aria-label=\{`Graphics quality: \$\{qualityState\}/);
  });
});

describe('keyboard navigation', () => {
  const container = read('components/layout/GlobalClientContainer.tsx');
  const sidebar = read('components/layout/Sidebar.tsx');

  it('offers a skip link to the main content before the navigation', () => {
    expect(container).toContain('href="#main-content"');
    expect(container).toContain('id="main-content"');
    expect(container.indexOf('href="#main-content"')).toBeLessThan(container.indexOf('<Sidebar />'));
  });

  it('marks the current page in the sidebar', () => {
    expect(sidebar).toContain("aria-current={isActive ? 'page' : undefined}");
    expect(sidebar).toContain('<nav aria-label="Main"');
  });
});

describe('headings', () => {
  const pages = [
    'app/page.tsx',
    'app/search/page.tsx',
    'app/analysis/page.tsx',
    'app/dataset/page.tsx',
    'app/model/page.tsx',
    'app/research/page.tsx',
    'app/mission-replay/page.tsx',
    'app/osint/page.tsx',
    'app/visualization/page.tsx',
    'app/target/[id]/page.tsx',
  ];

  it.each(pages)('%s has a level-one heading', (file) => {
    expect(read(file)).toMatch(/<h1[\s>]/);
  });

  it('panel titles are level-two headings', () => {
    expect(read('components/shared/UI.tsx')).toMatch(/<h2 className="[^"]*">\{title\}<\/h2>/);
  });

  it('no page skips from h1 to h4', () => {
    for (const file of pages) expect(read(file)).not.toMatch(/<h4[\s>]/);
  });
});

describe('scrollable tables', () => {
  const pageFiles = (dir: string): string[] =>
    fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) return e.name === 'api' ? [] : pageFiles(full);
      return e.name === 'page.tsx' ? [full] : [];
    });

  it('every horizontally scrolling table wrapper is a labelled, focusable region', () => {
    const offenders: string[] = [];
    for (const file of pageFiles(path.join(SRC, 'app'))) {
      const lines = fs.readFileSync(file, 'utf-8').split('\n');
      lines.forEach((line, i) => {
        if (!line.includes('overflow-x-auto')) return;
        const wrapsTable = lines.slice(i + 1, i + 4).some((l) => l.includes('<table'));
        const ok = line.includes('role="region"') && line.includes('aria-label=') && line.includes('tabIndex={0}');
        if (wrapsTable && !ok) offenders.push(`${path.relative(SRC, file)}:${i + 1}`);
      });
    }
    expect(offenders).toEqual([]);
  });
});

describe('charts', () => {
  it('every chart has a text alternative', () => {
    const offenders: string[] = [];
    const walk = (dir: string) => {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, e.name);
        if (e.isDirectory()) walk(full);
        else if (e.name.endsWith('.tsx')) {
          const src = fs.readFileSync(full, 'utf-8');
          const charts = (src.match(/<ResponsiveContainer/g) ?? []).length;
          const frames = (src.match(/<ChartFrame/g) ?? []).length;
          if (charts > frames) offenders.push(`${path.relative(SRC, full)}: ${charts} charts, ${frames} frames`);
        }
      }
    };
    walk(path.join(SRC, 'app'));
    expect(offenders).toEqual([]);
  });
});
