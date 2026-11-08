import { NextRequest, NextResponse } from 'next/server';
import {
  checkInferenceReadiness,
  isPredictionPayload,
  resolveInferenceConfig,
  runJsonProcess,
  unavailableBody,
} from '@/lib/server/inference';
import { validateUploadBody } from '@/lib/server/validation';

export const dynamic = 'force-dynamic';

const MAX_BODY_BYTES = 4 * 1024 * 1024;

// Classifies a user-supplied light curve with the explainability ONNX model.
// Input: JSON { period: number, flux: number[50..100000], tic_id?: number | "TIC_<digits>" }.
// The flux array is sent to Python over stdin; no user input is ever placed in a shell command.
export async function POST(request: NextRequest) {
  const declaredLength = Number(request.headers.get('content-length') ?? 0);
  if (declaredLength > MAX_BODY_BYTES) {
    return NextResponse.json({ error: 'Request body too large.' }, { status: 413 });
  }

  let raw: string;
  try {
    raw = await request.text();
  } catch {
    return NextResponse.json({ error: 'Could not read request body.' }, { status: 400 });
  }
  if (Buffer.byteLength(raw) > MAX_BODY_BYTES) {
    return NextResponse.json({ error: 'Request body too large.' }, { status: 413 });
  }

  let body: unknown;
  try {
    body = JSON.parse(raw);
  } catch {
    return NextResponse.json({ error: 'Request body must be valid JSON.' }, { status: 400 });
  }

  const validation = validateUploadBody(body);
  if (!validation.ok) {
    return NextResponse.json({ error: validation.error }, { status: 400 });
  }
  const { ticId, period, flux } = validation.value;

  const cfg = resolveInferenceConfig();
  const readiness = checkInferenceReadiness('upload', cfg);
  if (!readiness.ready) {
    return NextResponse.json(unavailableBody('upload', readiness.reasons), { status: 503 });
  }

  const args = [cfg.scripts.upload, '--flux-stdin', '--period', String(period), '--onnx', cfg.onnxExplain];
  if (ticId !== null) args.push('--tic_id', String(ticId));

  const result = await runJsonProcess(cfg.python, args, {
    cwd: cfg.projectRoot,
    timeoutMs: cfg.timeoutMs,
    input: JSON.stringify(flux),
  });
  if (!result.ok) {
    console.error(`[upload] ${result.reason} ${result.detail ?? ''}`);
    return NextResponse.json(unavailableBody('upload', [result.reason]), { status: 503 });
  }
  if (!isPredictionPayload(result.data)) {
    return NextResponse.json(unavailableBody('upload', ['invalid_model_output']), { status: 503 });
  }
  return NextResponse.json({ ...result.data, source: 'model' });
}
