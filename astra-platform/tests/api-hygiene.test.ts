// Static guards over every API route, so new routes keep the rules the existing ones follow.
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';

const API_DIR = path.resolve(__dirname, '..', 'src', 'app', 'api');

function routeFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return routeFiles(full);
    return entry.name === 'route.ts' ? [full] : [];
  });
}

const routes = routeFiles(API_DIR).map((file) => ({
  name: path.relative(API_DIR, path.dirname(file)).replace(/\\/g, '/'),
  source: fs.readFileSync(file, 'utf-8'),
}));

describe('API route hygiene', () => {
  it('finds the routes', () => {
    expect(routes.length).toBeGreaterThanOrEqual(15);
  });

  describe.each(routes)('$name', ({ source }) => {
    it('does not open its own database handle', () => {
      // Routes read through getDatabase(); only lib/server may construct DatabaseSync.
      expect(source).not.toMatch(/new DatabaseSync|from 'node:sqlite'/);
    });

    it('does not send exception text to the client', () => {
      expect(source).not.toMatch(/details:\s*(errorMessage|error|err)\b/);
      expect(source).not.toMatch(/errorMessage\(/);
      expect(source).not.toMatch(/\$\{(error|err|e)\}/);
      expect(source).not.toMatch(/(error|err)\.message/);
    });

    it('does not parse ids or numbers with bare parseInt', () => {
      expect(source).not.toMatch(/parseInt\(/);
    });
  });
});
