// Health report for /api/health. Every field is measured, never assumed:
// hashes are recomputed, the database is queried, and inference readiness uses the same
// checks the inference routes use before they run (see ./inference.ts).

import { DatabaseSync } from 'node:sqlite';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { pathToFileURL } from 'node:url';
import {
  checkInferenceReadiness,
  InferenceConfig,
  InferenceKind,
  onnxWeightsPresent,
  runJsonProcess,
  sha256File,
} from './inference';

export const EXPECTED_DATASET_SHA256 =
  'f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58';
export const EXPECTED_STAR_COUNT = 944;

export type SystemStatus = 'READY' | 'DEGRADED' | 'BLOCKED';

export interface CapabilityStatus {
  available: boolean;
  reasons: string[];
}

export interface HealthReport {
  status: SystemStatus;
  summary: string;
  checked_at: string;
  node_version: string;
  application: { ok: true };
  dataset: { exists: boolean; sha256: string | null; expected_sha256: string; hash_match: boolean };
  database: { ok: boolean; exists: boolean; star_count: number | null; expected_star_count: number; error?: string };
  model: {
    checkpoint: { exists: boolean; sha256: string | null; expected_sha256: string; hash_match: boolean };
    onnx_explain: { exists: boolean; weights_present: boolean; sha256: string | null };
  };
  python: { interpreter_found: boolean; modules: Record<string, boolean> | null };
  inference: Record<InferenceKind, CapabilityStatus>;
  // Fields kept for older clients; all derived from the measurements above.
  dataset_hash: string;
  expected_dataset_hash: string;
  model_hash: string | null;
  sqlite_loaded: boolean;
  onnx_loaded: boolean;
}

// ─── Python dependency probe (cached) ──────────────────────────────────────────

const PROBE_TTL_MS = 5 * 60 * 1000;
let probeCache: { python: string; at: number; modules: Record<string, boolean> | null } | null = null;

const PROBE_SCRIPT =
  'import json, importlib.util as u; ' +
  'print(json.dumps({m: u.find_spec(m) is not None for m in ["numpy", "torch", "onnxruntime"]}))';

async function probePythonModules(python: string, cwd: string): Promise<Record<string, boolean> | null> {
  const now = Date.now();
  if (probeCache && probeCache.python === python && now - probeCache.at < PROBE_TTL_MS) {
    return probeCache.modules;
  }
  const result = await runJsonProcess(python, ['-c', PROBE_SCRIPT], { cwd, timeoutMs: 20_000 });
  const modules = result.ok
    ? Object.fromEntries(Object.entries(result.data).map(([k, v]) => [k, v === true]))
    : null;
  probeCache = { python, at: now, modules };
  return modules;
}

export function resetHealthCaches(): void {
  probeCache = null;
}

// ─── Report ────────────────────────────────────────────────────────────────────

function checkDatabase(dbPath: string): HealthReport['database'] {
  const base = { exists: fs.existsSync(dbPath), expected_star_count: EXPECTED_STAR_COUNT };
  if (!base.exists) return { ...base, ok: false, star_count: null, error: 'database_missing' };
  let db: DatabaseSync | null = null;
  try {
    db = new DatabaseSync(pathToFileURL(dbPath).toString() + '?immutable=1', { readOnly: true });
    const row = db.prepare('SELECT COUNT(*) AS n FROM stars').get() as { n: number };
    const count = Number(row.n);
    const ok = count === EXPECTED_STAR_COUNT;
    return { ...base, ok, star_count: count, ...(ok ? {} : { error: 'unexpected_star_count' }) };
  } catch {
    return { ...base, ok: false, star_count: null, error: 'database_unreadable' };
  } finally {
    db?.close();
  }
}

export type ModuleProbe = (python: string, cwd: string) => Promise<Record<string, boolean> | null>;

export async function computeHealth(
  cfg: InferenceConfig,
  options: { probe?: ModuleProbe } = {},
): Promise<HealthReport> {
  const probe = options.probe ?? probePythonModules;
  const csvPath = path.join(cfg.dataDir, 'scientific_dataset_freeze_v2.csv');
  const datasetSha = sha256File(csvPath);
  const dataset = {
    exists: datasetSha !== null,
    sha256: datasetSha,
    expected_sha256: EXPECTED_DATASET_SHA256,
    hash_match: datasetSha === EXPECTED_DATASET_SHA256,
  };

  const database = checkDatabase(path.join(cfg.dataDir, 'astra.sqlite'));

  const checkpointSha = sha256File(cfg.checkpoint);
  const onnxExists = fs.existsSync(cfg.onnxExplain);
  const model = {
    checkpoint: {
      exists: checkpointSha !== null,
      sha256: checkpointSha,
      expected_sha256: cfg.expectedCheckpointSha256,
      hash_match: checkpointSha === cfg.expectedCheckpointSha256,
    },
    onnx_explain: {
      exists: onnxExists,
      weights_present: onnxExists && onnxWeightsPresent(cfg.onnxExplain),
      sha256: onnxExists ? sha256File(cfg.onnxExplain) : null,
    },
  };

  const kinds: InferenceKind[] = ['predict', 'explain', 'upload'];
  const inference = Object.fromEntries(
    kinds.map((k) => {
      const r = checkInferenceReadiness(k, cfg);
      return [k, { available: r.ready, reasons: r.reasons }];
    }),
  ) as Record<InferenceKind, CapabilityStatus>;

  // Only probe Python when the file checks pass, so a missing model never spawns a process.
  const interpreterFound = fs.existsSync(cfg.python);
  let modules: Record<string, boolean> | null = null;
  if (interpreterFound && kinds.some((k) => inference[k].available)) {
    modules = await probe(cfg.python, cfg.projectRoot);
    const needs: Record<InferenceKind, string[]> = {
      predict: ['numpy', 'torch'],
      explain: ['numpy', 'onnxruntime'],
      upload: ['numpy', 'onnxruntime'],
    };
    for (const k of kinds) {
      if (!inference[k].available) continue;
      const missing = modules === null ? ['python_probe_failed'] : needs[k].filter((m) => !modules![m]).map((m) => `python_module_missing:${m}`);
      if (missing.length > 0) inference[k] = { available: false, reasons: missing };
    }
  }

  const allInference = kinds.every((k) => inference[k].available);
  let status: SystemStatus;
  let summary: string;
  if (!dataset.hash_match || !database.ok) {
    status = 'BLOCKED';
    summary = !dataset.hash_match
      ? 'Dataset manifest missing or its SHA256 does not match the frozen dataset.'
      : 'Star database missing or unreadable.';
  } else if (!allInference) {
    status = 'DEGRADED';
    summary = kinds.some((k) => inference[k].available)
      ? 'Data verified. Some model inference capabilities are unavailable.'
      : 'Data verified. Model inference is unavailable on this deployment; no predictions are served.';
  } else {
    status = 'READY';
    summary = 'Data verified, model checkpoint hash verified, inference available.';
  }

  return {
    status,
    summary,
    checked_at: new Date().toISOString(),
    node_version: process.version,
    application: { ok: true },
    dataset,
    database,
    model,
    python: { interpreter_found: interpreterFound, modules },
    inference,
    dataset_hash: datasetSha ?? 'NOT_FOUND',
    expected_dataset_hash: EXPECTED_DATASET_SHA256,
    model_hash: checkpointSha,
    sqlite_loaded: database.ok,
    onnx_loaded: model.onnx_explain.weights_present,
  };
}
