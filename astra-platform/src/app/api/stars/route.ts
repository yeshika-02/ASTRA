import { NextRequest, NextResponse } from 'next/server';
import { getDatabase } from '@/lib/server/db';
import { serverError } from '@/lib/server/errors';
import { containsPattern, parseStarQuery } from '@/lib/server/query';
import type { StarRow } from '@/lib/types/artifacts';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const parsed = parseStarQuery(request.nextUrl.searchParams);
  if (!parsed.ok) {
    return NextResponse.json({ error: parsed.error }, { status: 400 });
  }
  const { q, classes, sources, split, page, limit } = parsed.value;

  try {
    const db = getDatabase();

    let sql = 'SELECT * FROM stars WHERE 1=1';
    const params: (string | number)[] = [];

    if (q) {
      sql +=
        " AND (CAST(tic_id AS TEXT) LIKE ? ESCAPE '\\' OR LOWER(astra_class) LIKE ? ESCAPE '\\'" +
        " OR LOWER(primary_source) LIKE ? ESCAPE '\\')";
      const pattern = containsPattern(q);
      params.push(pattern, pattern, pattern);
    }

    if (classes.length > 0) {
      sql += ` AND astra_class IN (${classes.map(() => '?').join(',')})`;
      params.push(...classes);
    }

    if (sources.length > 0) {
      sql += ` AND period_source IN (${sources.map(() => '?').join(',')})`;
      params.push(...sources);
    }

    if (split) {
      sql += ' AND split = ?';
      params.push(split);
    }

    const { count: total } = db.prepare(`SELECT COUNT(*) AS count FROM (${sql})`).get(...params) as {
      count: number;
    };

    sql += ' LIMIT ? OFFSET ?';
    params.push(limit, (page - 1) * limit);

    const rows = db.prepare(sql).all(...params) as unknown as StarRow[];

    const stars = rows.map((r) => ({
      ...r,
      source_catalogs: r.source_catalogs ? JSON.parse(r.source_catalogs) : [],
      sector_information: r.sector_information ? JSON.parse(r.sector_information) : [],
      has_folded_lc: r.has_folded_lc === 1,
    }));

    return NextResponse.json({
      stars,
      total,
      page,
      limit,
      pages: Math.ceil(total / limit),
    });
  } catch (error) {
    return serverError('/api/stars', error, 'Failed to query database');
  }
}
