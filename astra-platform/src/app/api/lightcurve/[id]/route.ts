import { NextRequest, NextResponse } from 'next/server';
import * as path from 'path';
import { parseNPY } from '@/lib/data/parseNPY';
import { serverError } from '@/lib/server/errors';
import { parseTicId } from '@/lib/server/validation';

export const dynamic = 'force-dynamic';

function isMissingFile(error: unknown): boolean {
  return typeof error === 'object' && error !== null && (error as NodeJS.ErrnoException).code === 'ENOENT';
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  // The id becomes part of a file path, so only a plain TIC number may pass.
  const ticId = parseTicId(id);
  if (ticId === null) {
    return NextResponse.json({ error: 'Invalid TIC identifier.' }, { status: 400 });
  }

  const dataRoot = path.join(process.cwd(), 'data', 'processed', `TIC_${ticId}`);

  try {
    const flux1000 = parseNPY(path.join(dataRoot, 'flux_1000.npy'));
    const flux200 = parseNPY(path.join(dataRoot, 'flux_200.npy'));
    const foldedFlux1000 = parseNPY(path.join(dataRoot, 'folded_flux_1000.npy'));
    const foldedFlux200 = parseNPY(path.join(dataRoot, 'folded_flux_200.npy'));

    return NextResponse.json({
      tic_id: ticId,
      flux_1000: flux1000,
      flux_200: flux200,
      folded_flux_1000: foldedFlux1000,
      folded_flux_200: foldedFlux200,
    });
  } catch (error) {
    if (isMissingFile(error)) {
      return NextResponse.json({ error: 'Light curve not found.' }, { status: 404 });
    }
    return serverError('/api/lightcurve/[id]', error, 'Failed to read light curve');
  }
}
