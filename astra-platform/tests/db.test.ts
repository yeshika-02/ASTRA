import * as fs from 'node:fs';
import * as path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { closeDatabase, databaseFile, DATABASE_FILENAME, getDatabase } from '@/lib/server/db';
import { REAL_DATA_DIR, snapshotEnv, tempDir } from './helpers';

let restoreEnv = snapshotEnv();
afterEach(() => {
  closeDatabase();
  restoreEnv();
  restoreEnv = snapshotEnv();
});

describe('databaseFile', () => {
  it('defaults to data/astra.sqlite under the working directory', () => {
    const cwd = path.resolve('some', 'app');
    expect(databaseFile({}, cwd)).toBe(path.join(cwd, 'data', DATABASE_FILENAME));
  });

  it('honours ASTRA_DATA_DIR', () => {
    const dir = path.resolve('elsewhere');
    expect(databaseFile({ ASTRA_DATA_DIR: dir }, path.resolve('ignored'))).toBe(path.join(dir, DATABASE_FILENAME));
  });
});

describe('getDatabase', () => {
  it('returns one shared handle across calls', () => {
    process.env.ASTRA_DATA_DIR = REAL_DATA_DIR;
    const first = getDatabase();
    expect(getDatabase() === first).toBe(true);
    const row = first.prepare('SELECT COUNT(*) AS n FROM stars').get() as { n: number };
    expect(row.n).toBeGreaterThan(0);
  });

  it('opens the database read-only', () => {
    process.env.ASTRA_DATA_DIR = REAL_DATA_DIR;
    expect(() => getDatabase().exec('DELETE FROM stars')).toThrow();
    const row = getDatabase().prepare('SELECT COUNT(*) AS n FROM stars').get() as { n: number };
    expect(row.n).toBeGreaterThan(0);
  });

  it('reopens after closeDatabase()', () => {
    process.env.ASTRA_DATA_DIR = REAL_DATA_DIR;
    const first = getDatabase();
    closeDatabase();
    expect(first.isOpen).toBe(false);
    const second = getDatabase();
    expect(second === first).toBe(false);
    expect(second.isOpen).toBe(true);
  });

  it('switches handles when the data directory changes', () => {
    process.env.ASTRA_DATA_DIR = REAL_DATA_DIR;
    const real = getDatabase();
    const copyDir = tempDir();
    fs.copyFileSync(path.join(REAL_DATA_DIR, DATABASE_FILENAME), path.join(copyDir, DATABASE_FILENAME));
    process.env.ASTRA_DATA_DIR = copyDir;
    const copy = getDatabase();
    expect(copy === real).toBe(false);
    expect(real.isOpen).toBe(false);
    closeDatabase();
    fs.rmSync(copyDir, { recursive: true, force: true });
  });

  it('throws when the database file is missing', () => {
    process.env.ASTRA_DATA_DIR = tempDir();
    expect(() => getDatabase()).toThrow();
  });
});
