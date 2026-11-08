// Real model inference for the API routes, or an explicit "unavailable" answer.
//
// Rules (ADR-0058):
//  - Never invent predictions. If the model cannot run, say so (HTTP 503).
//  - Never build shell strings. Python is spawned with an argument array and shell: false;
//    bulk data (flux arrays) goes through stdin, not argv.
//  - Reasons returned to clients are short codes without server paths.

import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';

export type InferenceKind = 'predict' | 'explain' | 'upload';

export const CLASS_NAMES = ['rr_lyrae', 'cepheid', 'eclipsing_binary', 'solar_like', 'stable'] as const;

/** SHA256 of models/saved/best_star_transformer_shared.pt as published in the README. */
export const EXPECTED_CHECKPOINT_SHA256 =
  'bf374ce492825916f2f97a4e29673a1eca35f76cc08f603b384d103fbe95d388';

export interface InferenceConfig {
  projectRoot: string;
  dataDir: string;
  python: string;
  checkpoint: string;
  onnxExplain: string;
  expectedCheckpointSha256: string;
  scripts: Record<InferenceKind, string>;
  timeoutMs: number;
}

// Paths below point outside the Next.js app (repo root, venv, model files). They are resolved at
// runtime only and must not be pulled into the serverless bundle, hence the turbopackIgnore hints.
// The app's own data/ folder is bundled explicitly via outputFileTracingIncludes in next.config.ts.
export function resolveInferenceConfig(
  env: NodeJS.ProcessEnv = process.env,
  cwd: string = process.cwd(),
): InferenceConfig {
  const projectRoot = path.resolve(
    /*turbopackIgnore: true*/ env.ASTRA_PROJECT_ROOT ?? path.join(/*turbopackIgnore: true*/ cwd, '..'),
  );
  const defaultPython =
    process.platform === 'win32'
      ? path.join(/*turbopackIgnore: true*/ projectRoot, '.venv', 'Scripts', 'python.exe')
      : path.join(/*turbopackIgnore: true*/ projectRoot, '.venv', 'bin', 'python');
  const savedModels = path.join(/*turbopackIgnore: true*/ projectRoot, 'models', 'saved');
  return {
    projectRoot,
    dataDir: path.resolve(/*turbopackIgnore: true*/ env.ASTRA_DATA_DIR ?? path.join(/*turbopackIgnore: true*/ cwd, 'data')),
    python: env.ASTRA_PYTHON ?? defaultPython,
    checkpoint:
      env.ASTRA_CHECKPOINT ?? path.join(/*turbopackIgnore: true*/ savedModels, 'best_star_transformer_shared.pt'),
    onnxExplain:
      env.ASTRA_ONNX_EXPLAIN ??
      path.join(/*turbopackIgnore: true*/ savedModels, 'best_star_transformer_shared_explain.onnx'),
    expectedCheckpointSha256: env.ASTRA_EXPECTED_CHECKPOINT_SHA256 ?? EXPECTED_CHECKPOINT_SHA256,
    scripts: {
      predict: path.join(/*turbopackIgnore: true*/ projectRoot, 'training', 'predict_inference.py'),
      explain: path.join(/*turbopackIgnore: true*/ projectRoot, 'training', 'explain_inference.py'),
      upload: path.join(/*turbopackIgnore: true*/ projectRoot, 'training', 'upload_inference.py'),
    },
    timeoutMs: Number(env.ASTRA_INFERENCE_TIMEOUT_MS ?? 60_000),
  };
}

// ─── File checks ───────────────────────────────────────────────────────────────

const hashCache = new Map<string, { key: string; sha256: string }>();

/** SHA256 of a file, cached by size + mtime. Returns null if the file is missing. */
export function sha256File(filePath: string): string | null {
  let stat: fs.Stats;
  try {
    stat = fs.statSync(filePath);
  } catch {
    return null;
  }
  if (!stat.isFile()) return null;
  const key = `${stat.size}:${stat.mtimeMs}`;
  const cached = hashCache.get(filePath);
  if (cached && cached.key === key) return cached.sha256;
  const sha256 = createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
  hashCache.set(filePath, { key, sha256 });
  return sha256;
}

function isFile(filePath: string): boolean {
  try {
    return fs.statSync(filePath).isFile();
  } catch {
    return false;
  }
}

/**
 * ONNX models exported with external data reference "<name>.onnx.data".
 * Returns false when such a reference exists but the data file is missing.
 */
export function onnxWeightsPresent(onnxPath: string): boolean {
  if (!isFile(onnxPath)) return false;
  const dataName = `${path.basename(onnxPath)}.data`;
  const bytes = fs.readFileSync(onnxPath);
  if (!bytes.includes(Buffer.from(dataName))) return true; // weights are embedded
  return isFile(path.join(path.dirname(onnxPath), dataName));
}

// ─── Readiness ─────────────────────────────────────────────────────────────────

export interface Readiness {
  ready: boolean;
  reasons: string[];
}

export function checkInferenceReadiness(kind: InferenceKind, cfg: InferenceConfig): Readiness {
  const reasons: string[] = [];
  if (!isFile(cfg.python)) reasons.push('python_interpreter_missing');
  if (!isFile(cfg.scripts[kind])) reasons.push('inference_script_missing');

  if (kind === 'predict') {
    const sha = sha256File(cfg.checkpoint);
    if (sha === null) reasons.push('model_checkpoint_missing');
    else if (sha !== cfg.expectedCheckpointSha256) reasons.push('model_checkpoint_hash_mismatch');
  } else {
    if (!isFile(cfg.onnxExplain)) reasons.push('onnx_model_missing');
    else if (!onnxWeightsPresent(cfg.onnxExplain)) reasons.push('onnx_external_weights_missing');
  }
  return { ready: reasons.length === 0, reasons };
}

// ─── Responses ─────────────────────────────────────────────────────────────────

export interface InferenceUnavailableBody {
  status: 'inference_unavailable';
  capability: InferenceKind;
  reasons: string[];
  message: string;
}

export function unavailableBody(kind: InferenceKind, reasons: string[]): InferenceUnavailableBody {
  return {
    status: 'inference_unavailable',
    capability: kind,
    reasons,
    message: 'Model inference is not available on this deployment. No prediction was made.',
  };
}

/** True when the payload looks like a real classifier output. */
export function isPredictionPayload(data: unknown): data is Record<string, unknown> {
  if (typeof data !== 'object' || data === null) return false;
  const d = data as Record<string, unknown>;
  if (typeof d.predicted_class !== 'string' || !(CLASS_NAMES as readonly string[]).includes(d.predicted_class)) {
    return false;
  }
  const probs = d.probabilities;
  if (typeof probs !== 'object' || probs === null) return false;
  return CLASS_NAMES.every((c) => {
    const p = (probs as Record<string, unknown>)[c];
    return typeof p === 'number' && Number.isFinite(p) && p >= 0 && p <= 1;
  });
}

// ─── Process execution ─────────────────────────────────────────────────────────

export type RunResult =
  | { ok: true; data: Record<string, unknown> }
  | { ok: false; reason: string; detail?: string };

export interface RunOptions {
  cwd: string;
  timeoutMs: number;
  input?: string;
  maxOutputBytes?: number;
}

/**
 * Runs `command args...` without a shell and parses one JSON object from stdout.
 * Arguments are passed verbatim to the process; nothing is interpreted by a shell.
 */
export function runJsonProcess(command: string, args: string[], opts: RunOptions): Promise<RunResult> {
  const maxBytes = opts.maxOutputBytes ?? 16 * 1024 * 1024;
  return new Promise((resolve) => {
    let settled = false;
    const finish = (result: RunResult) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };

    let child: ReturnType<typeof spawn>;
    try {
      child = spawn(command, args, {
        cwd: opts.cwd,
        shell: false,
        windowsHide: true,
        stdio: ['pipe', 'pipe', 'pipe'],
      });
    } catch (err) {
      resolve({ ok: false, reason: 'inference_process_failed', detail: String(err) });
      return;
    }

    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      finish({ ok: false, reason: 'inference_timeout' });
    }, opts.timeoutMs);

    const out: Buffer[] = [];
    let outBytes = 0;
    let stderr = '';
    child.stdout?.on('data', (chunk: Buffer) => {
      outBytes += chunk.length;
      if (outBytes > maxBytes) {
        child.kill('SIGKILL');
        finish({ ok: false, reason: 'inference_output_too_large' });
        return;
      }
      out.push(chunk);
    });
    child.stderr?.on('data', (chunk: Buffer) => {
      if (stderr.length < 8192) stderr += chunk.toString();
    });
    child.on('error', (err) => finish({ ok: false, reason: 'inference_process_failed', detail: err.message }));
    child.on('close', (code) => {
      const text = Buffer.concat(out).toString('utf8').trim();
      let parsed: unknown;
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = undefined;
      }
      if (code !== 0) {
        const msg =
          parsed && typeof parsed === 'object' && 'error' in parsed
            ? String((parsed as { error: unknown }).error)
            : stderr;
        finish({ ok: false, reason: 'inference_process_failed', detail: msg });
        return;
      }
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        finish({ ok: false, reason: 'invalid_model_output', detail: text.slice(0, 500) });
        return;
      }
      if ('error' in parsed) {
        finish({ ok: false, reason: 'inference_process_failed', detail: String((parsed as { error: unknown }).error) });
        return;
      }
      finish({ ok: true, data: parsed as Record<string, unknown> });
    });

    if (opts.input !== undefined) {
      child.stdin?.on('error', () => undefined); // process may exit before reading stdin
      child.stdin?.end(opts.input);
    } else {
      child.stdin?.end();
    }
  });
}
