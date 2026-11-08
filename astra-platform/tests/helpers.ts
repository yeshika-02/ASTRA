import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { createHash } from 'node:crypto';

export const FAKE_MODEL_SCRIPT = path.resolve(__dirname, 'fixtures', 'fake_model.js');
export const REAL_DATA_DIR = path.resolve(__dirname, '..', 'data');
/** A star that exists in the shipped dataset. */
export const KNOWN_TIC = 100009973;

const ENV_KEYS = [
  'ASTRA_PROJECT_ROOT',
  'ASTRA_DATA_DIR',
  'ASTRA_PYTHON',
  'ASTRA_CHECKPOINT',
  'ASTRA_ONNX_EXPLAIN',
  'ASTRA_EXPECTED_CHECKPOINT_SHA256',
  'ASTRA_INFERENCE_TIMEOUT_MS',
  'FAKE_MODEL_MODE',
];

export function snapshotEnv(): () => void {
  const saved = Object.fromEntries(ENV_KEYS.map((k) => [k, process.env[k]]));
  return () => {
    for (const k of ENV_KEYS) {
      if (saved[k] === undefined) delete process.env[k];
      else process.env[k] = saved[k];
    }
  };
}

export function tempDir(prefix = 'astra-test-'): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

/** Points the app at a project root with no interpreter and no model: inference must be unavailable. */
export function useMissingModelEnv(): string {
  const root = tempDir();
  process.env.ASTRA_PROJECT_ROOT = root;
  process.env.ASTRA_DATA_DIR = REAL_DATA_DIR;
  process.env.ASTRA_PYTHON = path.join(root, 'no-such-python');
  delete process.env.ASTRA_CHECKPOINT;
  delete process.env.ASTRA_ONNX_EXPLAIN;
  delete process.env.ASTRA_EXPECTED_CHECKPOINT_SHA256;
  return root;
}

/**
 * Builds a project root whose "Python" is the Node binary and whose inference scripts are the
 * fake model, with a fake checkpoint (hash registered as expected) and a self-contained ONNX file.
 */
export function useFakeModelEnv(): string {
  const root = tempDir();
  const training = path.join(root, 'training');
  const saved = path.join(root, 'models', 'saved');
  fs.mkdirSync(training, { recursive: true });
  fs.mkdirSync(saved, { recursive: true });
  for (const name of ['predict_inference.py', 'explain_inference.py', 'upload_inference.py']) {
    fs.copyFileSync(FAKE_MODEL_SCRIPT, path.join(training, name));
  }
  const checkpoint = path.join(saved, 'best_star_transformer_shared.pt');
  fs.writeFileSync(checkpoint, 'fake checkpoint bytes');
  const onnx = path.join(saved, 'best_star_transformer_shared_explain.onnx');
  fs.writeFileSync(onnx, 'fake onnx with embedded weights');

  process.env.ASTRA_PROJECT_ROOT = root;
  process.env.ASTRA_DATA_DIR = REAL_DATA_DIR;
  process.env.ASTRA_PYTHON = process.execPath;
  process.env.ASTRA_CHECKPOINT = checkpoint;
  process.env.ASTRA_ONNX_EXPLAIN = onnx;
  process.env.ASTRA_EXPECTED_CHECKPOINT_SHA256 = createHash('sha256').update(fs.readFileSync(checkpoint)).digest('hex');
  process.env.ASTRA_INFERENCE_TIMEOUT_MS = '10000';
  return root;
}

export function flux(n: number): number[] {
  return Array.from({ length: n }, (_, i) => 1 + 0.01 * Math.sin(i / 5));
}
