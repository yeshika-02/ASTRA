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

// MC Dropout prediction from the PyTorch checkpoint. Returns 503 when the model cannot run;
// it never returns a prediction that did not come from the model.
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

  const readiness = checkInferenceReadiness('predict', cfg);
  if (!readiness.ready) {
    return NextResponse.json(unavailableBody('predict', readiness.reasons), { status: 503 });
  }

  const result = await runJsonProcess(
    cfg.python,
    [cfg.scripts.predict, '--input', starDir, '--checkpoint', cfg.checkpoint],
    { cwd: cfg.projectRoot, timeoutMs: cfg.timeoutMs },
  );
  if (!result.ok) {
    console.error(`[predict] TIC_${ticId}: ${result.reason} ${result.detail ?? ''}`);
    return NextResponse.json(unavailableBody('predict', [result.reason]), { status: 503 });
  }
  if (!isPredictionPayload(result.data)) {
    return NextResponse.json(unavailableBody('predict', ['invalid_model_output']), { status: 503 });
  }
  return NextResponse.json({ ...result.data, source: 'model' });
}
