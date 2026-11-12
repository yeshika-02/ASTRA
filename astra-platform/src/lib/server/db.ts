// Shared read-only handle on the star registry (data/astra.sqlite).
//
// The database ships with the build and is never written at runtime, so one connection opened
// read-only with SQLite's `immutable` flag serves every request. Before this module each API
// call opened its own handle and never closed it. node:sqlite is synchronous and Node runs
// route handlers on one thread, so sharing the handle needs no locking.

import { DatabaseSync } from 'node:sqlite';
import * as path from 'node:path';
import { pathToFileURL } from 'node:url';

export const DATABASE_FILENAME = 'astra.sqlite';

/** Absolute path of the registry database: $ASTRA_DATA_DIR, else ./data under the app root. */
export function databaseFile(
  env: Record<string, string | undefined> = process.env,
  cwd: string = process.cwd(),
): string {
  const dataDir = env.ASTRA_DATA_DIR ?? path.join(/*turbopackIgnore: true*/ cwd, 'data');
  return path.resolve(/*turbopackIgnore: true*/ dataDir, DATABASE_FILENAME);
}

interface CachedHandle {
  file: string;
  db: DatabaseSync;
}

// Kept on globalThis so `next dev` module reloads reuse the handle instead of leaking one per edit.
const store = globalThis as typeof globalThis & { __astraDatabase?: CachedHandle };

/** Opens (once) and returns the read-only registry handle for the current data directory. */
export function getDatabase(): DatabaseSync {
  const file = databaseFile();
  const cached = store.__astraDatabase;
  if (cached && cached.file === file && cached.db.isOpen) {
    return cached.db;
  }
  closeDatabase();
  const db = new DatabaseSync(`${pathToFileURL(file).toString()}?immutable=1`, { readOnly: true });
  store.__astraDatabase = { file, db };
  return db;
}

/** Closes the shared handle, if any. The next getDatabase() call reopens it. */
export function closeDatabase(): void {
  const cached = store.__astraDatabase;
  store.__astraDatabase = undefined;
  if (cached?.db.isOpen) {
    cached.db.close();
  }
}
