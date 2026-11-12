// Static guards over every page: data views must handle failed requests, use the shared
// hooks (which check HTTP status) and never fall back to an unexplained "System Error".
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';

const APP_DIR = path.resolve(__dirname, '..', 'src', 'app');

function pageFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return entry.name === 'api' ? [] : pageFiles(full);
    return entry.name === 'page.tsx' ? [full] : [];
  });
}

// Hooks in src/lib/hooks that fetch registry or artifact data.
const DATA_HOOK = /\buse(Stars|Star|LightCurve|Osint|Search|ModelDetails|Checkpoints|DatasetDetails|ResearchFindings|BenchmarkMetrics|CalibrationDetails|Predict|Explain)\(/;

const pages = pageFiles(APP_DIR).map((file) => ({
  name: path.relative(APP_DIR, file).split(path.sep).join('/'),
  source: fs.readFileSync(file, 'utf-8'),
}));
const dataPages = pages.filter((p) => DATA_HOOK.test(p.source));

describe('page states', () => {
  it('finds the data pages', () => {
    expect(dataPages.map((p) => p.name).sort()).toEqual(
      [
        'analysis/page.tsx',
        'dataset/page.tsx',
        'mission-replay/page.tsx',
        'model/page.tsx',
        'osint/page.tsx',
        'page.tsx',
        'research/page.tsx',
        'search/page.tsx',
        'target/[id]/page.tsx',
        'visualization/page.tsx',
      ].sort(),
    );
  });

  describe.each(dataPages)('$name', ({ source }) => {
    it('handles failed requests', () => {
      expect(source).toMatch(/isError|combineQueries/);
    });

    it('renders the shared error state with a retry', () => {
      expect(source).toMatch(/<(LoadError|PageError)\b/);
      expect(source).toMatch(/onRetry=/);
    });
  });

  describe.each(pages)('$name', ({ source }) => {
    it('has no dead-end "System Error" box', () => {
      expect(source).not.toMatch(/System Error/);
    });

    it('fetches data through the shared hooks', () => {
      // Hooks in lib/hooks check the HTTP status; a raw useQuery + fetch().json() does not.
      expect(source).not.toMatch(/\buseQuery\s*[<(]/);
    });
  });
});
