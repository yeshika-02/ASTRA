import { NextRequest, NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';
import {
  checkInferenceReadiness,
  isPredictionPayload,
  resolveInferenceConfig,
  runJsonProcess,
  unavailableBody,
} from '@/lib/server/inference';
import { parseTicId } from '@/lib/server/validation';

export const dynamic = 'force-dynamic';

// Attention / feature explanations from the explainability ONNX model. Returns 503 when the
// model cannot run; it never returns synthetic attention maps or probabilities.
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const ticId = parseTicId(id);
  if (ticId === null) {
    return NextResponse.json({ error: 'Invalid TIC identifier.' }, { status: 400 });
  }

  const cfg = resolveInferenceConfig();
  const starDir = path.join(cfg.dataDir, 'processed', `TIC_${ticId}`);
  if (!fs.existsSync(starDir)) {
    return NextResponse.json({ error: `Target TIC_${ticId} not found.` }, { status: 404 });
  }

  const readiness = checkInferenceReadiness('explain', cfg);
  if (!readiness.ready) {
    return NextResponse.json(unavailableBody('explain', readiness.reasons), { status: 503 });
  }

  const result = await runJsonProcess(
    cfg.python,
    [cfg.scripts.explain, '--input', starDir, '--onnx', cfg.onnxExplain],
    { cwd: cfg.projectRoot, timeoutMs: cfg.timeoutMs },
  );
  if (!result.ok) {
    console.error(`[explain] TIC_${ticId}: ${result.reason} ${result.detail ?? ''}`);
    return NextResponse.json(unavailableBody('explain', [result.reason]), { status: 503 });
  }
  if (!isPredictionPayload(result.data) || !Array.isArray(result.data.attention_weights)) {
    return NextResponse.json(unavailableBody('explain', ['invalid_model_output']), { status: 503 });
  }
  return NextResponse.json({ ...result.data, source: 'model' });
}
