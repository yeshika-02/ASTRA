import { NextRequest, NextResponse } from 'next/server';
import { getDatabase } from '@/lib/server/db';
import { serverError } from '@/lib/server/errors';
import { containsPattern, MIN_SEARCH_LENGTH, parseSearchQuery } from '@/lib/server/query';
import type { StarRow } from '@/lib/types/artifacts';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const parsed = parseSearchQuery(request.nextUrl.searchParams);
  if (!parsed.ok) {
    return NextResponse.json({ error: parsed.error }, { status: 400 });
  }
  const query = parsed.value;
  if (query.length < MIN_SEARCH_LENGTH) {
    return NextResponse.json({ results: [] });
  }

  try {
    // Substring match on the TIC number, class, source catalogue and catalogue label.
    const stmt = getDatabase().prepare(`
      SELECT tic_id, astra_class, ra, dec, period, period_source, n_sectors
      FROM stars
      WHERE CAST(tic_id AS TEXT) LIKE ? ESCAPE '\\'
         OR LOWER(astra_class) LIKE ? ESCAPE '\\'
         OR LOWER(primary_source) LIKE ? ESCAPE '\\'
         OR LOWER(catalog_label) LIKE ? ESCAPE '\\'
      LIMIT 20
    `);

    const pattern = containsPattern(query);
    const rows = stmt.all(pattern, pattern, pattern, pattern) as unknown as StarRow[];

    const results = rows.map((r) => ({
      tic_id: r.tic_id,
      astra_class: r.astra_class,
      ra: r.ra,
      dec: r.dec,
      period: r.period,
      period_source: r.period_source,
      n_sectors: r.n_sectors,
    }));

    return NextResponse.json({ results });
  } catch (error) {
    return serverError('/api/search', error, 'Failed to search database');
  }
}
