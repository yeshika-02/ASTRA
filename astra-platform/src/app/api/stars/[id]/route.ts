import { NextRequest, NextResponse } from 'next/server';
import { getDatabase } from '@/lib/server/db';
import { serverError } from '@/lib/server/errors';
import { parseTicId } from '@/lib/server/validation';
import type { StarRow } from '@/lib/types/artifacts';

export const dynamic = 'force-dynamic';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const ticId = parseTicId(id);
  if (ticId === null) {
    return NextResponse.json({ error: 'Invalid TIC identifier.' }, { status: 400 });
  }

  try {
    const r = getDatabase().prepare('SELECT * FROM stars WHERE tic_id = ?').get(ticId) as StarRow | undefined;

    if (!r) {
      return NextResponse.json({ error: 'Star not found' }, { status: 404 });
    }

    const star = {
      ...r,
      source_catalogs: r.source_catalogs ? JSON.parse(r.source_catalogs) : [],
      sector_information: r.sector_information ? JSON.parse(r.sector_information) : [],
      has_folded_lc: r.has_folded_lc === 1,
    };

    return NextResponse.json(star);
  } catch (error) {
    return serverError('/api/stars/[id]', error, 'Failed to query database');
  }
}
