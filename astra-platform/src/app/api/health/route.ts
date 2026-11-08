import { NextResponse } from 'next/server';
import { computeHealth } from '@/lib/server/health';
import { resolveInferenceConfig } from '@/lib/server/inference';

export const dynamic = 'force-dynamic';

// READY    = dataset + database verified, checkpoint hash verified, all inference capabilities runnable
// DEGRADED = data verified, but some or all inference is unavailable (no predictions are served)
// BLOCKED  = dataset manifest or star database missing / not matching
export async function GET() {
  try {
    const report = await computeHealth(resolveInferenceConfig());
    return NextResponse.json(report, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    console.error('[health]', error);
    return NextResponse.json(
      { status: 'BLOCKED', summary: 'Health check failed.', sqlite_loaded: false, onnx_loaded: false },
      { status: 500 },
    );
  }
}
