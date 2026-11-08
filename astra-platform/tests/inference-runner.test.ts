import * as fs from 'node:fs';
import * as path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import {
  checkInferenceReadiness,
  isPredictionPayload,
  onnxWeightsPresent,
  resolveInferenceConfig,
  runJsonProcess,
} from '@/lib/server/inference';
import { FAKE_MODEL_SCRIPT, snapshotEnv, tempDir, useFakeModelEnv, useMissingModelEnv } from './helpers';

let restoreEnv = snapshotEnv();
afterEach(() => {
  restoreEnv();
  restoreEnv = snapshotEnv();
});

describe('runJsonProcess (no shell)', () => {
  it('passes shell metacharacters through as literal arguments and never runs them', async () => {
    const dir = tempDir();
    const marker = path.join(dir, 'pwned');
    const hostile = [
      `"; node -e "require('fs').writeFileSync('${marker.replace(/\\/g, '/')}','x')"; echo "`,
      `$(touch ${marker})`,
      `\`touch ${marker}\``,
      `& type nul > ${marker}`,
      `| echo pwned > ${marker}`,
    ];
    const r = await runJsonProcess(process.execPath, [FAKE_MODEL_SCRIPT, ...hostile], { cwd: dir, timeoutMs: 10_000 });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.data.received_args).toEqual(hostile);
    expect(fs.existsSync(marker)).toBe(false);
  });

  it('delivers bulk input over stdin', async () => {
    const payload = JSON.stringify(Array.from({ length: 50_000 }, (_, i) => i / 7));
    const r = await runJsonProcess(process.execPath, [FAKE_MODEL_SCRIPT], { cwd: tempDir(), timeoutMs: 10_000, input: payload });
    expect(r.ok && r.data.received_stdin).toBe(payload);
  });

  it('reports a failed process instead of returning data', async () => {
    process.env.FAKE_MODEL_MODE = 'error';
    const r = await runJsonProcess(process.execPath, [FAKE_MODEL_SCRIPT], { cwd: tempDir(), timeoutMs: 10_000 });
    expect(r).toMatchObject({ ok: false, reason: 'inference_process_failed' });
  });

  it('rejects non-JSON output', async () => {
    process.env.FAKE_MODEL_MODE = 'garbage';
    const r = await runJsonProcess(process.execPath, [FAKE_MODEL_SCRIPT], { cwd: tempDir(), timeoutMs: 10_000 });
    expect(r).toMatchObject({ ok: false, reason: 'invalid_model_output' });
  });

  it('kills a process that exceeds the timeout', async () => {
    process.env.FAKE_MODEL_MODE = 'hang';
    const r = await runJsonProcess(process.execPath, [FAKE_MODEL_SCRIPT], { cwd: tempDir(), timeoutMs: 500 });
    expect(r).toMatchObject({ ok: false, reason: 'inference_timeout' });
  });

  it('reports a missing interpreter', async () => {
    const r = await runJsonProcess(path.join(tempDir(), 'missing-python'), ['x'], { cwd: tempDir(), timeoutMs: 5_000 });
    expect(r).toMatchObject({ ok: false, reason: 'inference_process_failed' });
  });
});

describe('checkInferenceReadiness', () => {
  it('is not ready without interpreter, scripts or model', () => {
    useMissingModelEnv();
    const cfg = resolveInferenceConfig();
    expect(checkInferenceReadiness('predict', cfg).reasons).toEqual([
      'python_interpreter_missing',
      'inference_script_missing',
      'model_checkpoint_missing',
    ]);
    expect(checkInferenceReadiness('upload', cfg).reasons).toContain('onnx_model_missing');
  });

  it('refuses a checkpoint whose hash does not match', () => {
    useFakeModelEnv();
    process.env.ASTRA_EXPECTED_CHECKPOINT_SHA256 = '0'.repeat(64);
    const r = checkInferenceReadiness('predict', resolveInferenceConfig());
    expect(r).toEqual({ ready: false, reasons: ['model_checkpoint_hash_mismatch'] });
  });

  it('is ready when interpreter, scripts and verified model are present', () => {
    useFakeModelEnv();
    const cfg = resolveInferenceConfig();
    for (const kind of ['predict', 'explain', 'upload'] as const) {
      expect(checkInferenceReadiness(kind, cfg)).toEqual({ ready: true, reasons: [] });
    }
  });
});

describe('onnxWeightsPresent', () => {
  it('detects missing external weights (the state of the shipped ONNX files)', () => {
    const dir = tempDir();
    const onnx = path.join(dir, 'model.onnx');
    fs.writeFileSync(onnx, 'header location model.onnx.data footer');
    expect(onnxWeightsPresent(onnx)).toBe(false);
    fs.writeFileSync(path.join(dir, 'model.onnx.data'), 'weights');
    expect(onnxWeightsPresent(onnx)).toBe(true);
  });

  it('reports the shipped explain model as weightless', () => {
    const shipped = path.resolve(__dirname, '..', 'data', 'best_star_transformer_shared_explain.onnx');
    expect(onnxWeightsPresent(shipped)).toBe(false);
  });
});

describe('isPredictionPayload', () => {
  it('accepts real classifier output and rejects anything else', () => {
    const probs = { rr_lyrae: 0.2, cepheid: 0.2, eclipsing_binary: 0.2, solar_like: 0.2, stable: 0.2 };
    expect(isPredictionPayload({ predicted_class: 'stable', probabilities: probs })).toBe(true);
    expect(isPredictionPayload({ predicted_class: 'quasar', probabilities: probs })).toBe(false);
    expect(isPredictionPayload({ predicted_class: 'stable', probabilities: { ...probs, stable: 2 } })).toBe(false);
    expect(isPredictionPayload({ predicted_class: 'stable' })).toBe(false);
  });
});
