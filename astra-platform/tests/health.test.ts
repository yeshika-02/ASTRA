import * as fs from 'node:fs';
import * as path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { GET as healthGET } from '@/app/api/health/route';
import { computeHealth, EXPECTED_DATASET_SHA256, resetHealthCaches } from '@/lib/server/health';
import { resolveInferenceConfig } from '@/lib/server/inference';
import { REAL_DATA_DIR, snapshotEnv, tempDir, useFakeModelEnv, useMissingModelEnv } from './helpers';

let restoreEnv = snapshotEnv();
afterEach(() => {
  restoreEnv();
  restoreEnv = snapshotEnv();
  resetHealthCaches();
});

const allModules = async () => ({ numpy: true, torch: true, onnxruntime: true });

describe('/api/health', () => {
  it('is DEGRADED (not READY) when data is verified but no model can run — the current deployment state', async () => {
    useMissingModelEnv();
    const res = await healthGET();
    const body = await res.json();
    expect(body.status).toBe('DEGRADED');
    expect(body.dataset.hash_match).toBe(true);
    expect(body.dataset.sha256).toBe(EXPECTED_DATASET_SHA256);
    expect(body.database).toMatchObject({ ok: true, star_count: 944 });
    expect(body.model.checkpoint.exists).toBe(false);
    expect(body.model_hash).toBeNull(); // no longer a hardcoded constant
    for (const k of ['predict', 'explain', 'upload']) expect(body.inference[k].available).toBe(false);
    expect(body.onnx_loaded).toBe(false);
  });

  it('reports the shipped ONNX file as present but without weights', async () => {
    useMissingModelEnv();
    process.env.ASTRA_ONNX_EXPLAIN = path.join(REAL_DATA_DIR, 'best_star_transformer_shared_explain.onnx');
    const report = await computeHealth(resolveInferenceConfig());
    expect(report.model.onnx_explain).toMatchObject({ exists: true, weights_present: false });
    expect(report.inference.explain.reasons).toContain('onnx_external_weights_missing');
  });

  it('is BLOCKED when the dataset manifest does not match its hash', async () => {
    useMissingModelEnv();
    const dir = tempDir();
    fs.copyFileSync(path.join(REAL_DATA_DIR, 'astra.sqlite'), path.join(dir, 'astra.sqlite'));
    fs.writeFileSync(path.join(dir, 'scientific_dataset_freeze_v2.csv'), 'tampered\n');
    process.env.ASTRA_DATA_DIR = dir;
    const report = await computeHealth(resolveInferenceConfig());
    expect(report.status).toBe('BLOCKED');
    expect(report.dataset.hash_match).toBe(false);
  });

  it('is BLOCKED when the star database is missing', async () => {
    useMissingModelEnv();
    const dir = tempDir();
    fs.copyFileSync(path.join(REAL_DATA_DIR, 'scientific_dataset_freeze_v2.csv'), path.join(dir, 'scientific_dataset_freeze_v2.csv'));
    process.env.ASTRA_DATA_DIR = dir;
    const report = await computeHealth(resolveInferenceConfig());
    expect(report.status).toBe('BLOCKED');
    expect(report.database).toMatchObject({ ok: false, error: 'database_missing' });
  });

  it('is READY only when model files, checkpoint hash and Python modules all check out', async () => {
    useFakeModelEnv();
    const report = await computeHealth(resolveInferenceConfig(), { probe: allModules });
    expect(report.status).toBe('READY');
    expect(report.model.checkpoint.hash_match).toBe(true);
  });

  it('is DEGRADED when Python lacks torch, with the reason reported', async () => {
    useFakeModelEnv();
    const report = await computeHealth(resolveInferenceConfig(), {
      probe: async () => ({ numpy: true, torch: false, onnxruntime: true }),
    });
    expect(report.status).toBe('DEGRADED');
    expect(report.inference.predict).toEqual({ available: false, reasons: ['python_module_missing:torch'] });
    expect(report.inference.upload.available).toBe(true);
  });

  it('is DEGRADED when the checkpoint hash does not match', async () => {
    useFakeModelEnv();
    process.env.ASTRA_EXPECTED_CHECKPOINT_SHA256 = 'f'.repeat(64);
    const report = await computeHealth(resolveInferenceConfig(), { probe: allModules });
    expect(report.status).toBe('DEGRADED');
    expect(report.model.checkpoint.hash_match).toBe(false);
  });
});
