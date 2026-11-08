import { NextRequest, NextResponse } from 'next/server';
import { DatabaseSync } from 'node:sqlite';
import { pathToFileURL } from 'node:url';
import * as path from 'path';
import { parseTicId } from '@/lib/server/validation';

export const dynamic = 'force-dynamic';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const ticId = parseTicId(id);
    if (ticId === null) {
      return NextResponse.json({ error: 'Invalid TIC identifier.' }, { status: 400 });
    }

    const dbPath = path.join(process.cwd(), 'data', 'astra.sqlite');
    const db = new DatabaseSync(pathToFileURL(dbPath).toString() + '?immutable=1', { readOnly: true });
    
    const stmt = db.prepare('SELECT * FROM stars WHERE tic_id = ?');
    const r = stmt.get(ticId) as any;
    
    if (!r) {
      return NextResponse.json({ error: 'Star not found in ASTRA registry' }, { status: 404 });
    }
    
    const star = {
      ...r,
      source_catalogs: r.source_catalogs ? JSON.parse(r.source_catalogs) : [],
      sector_information: r.sector_information ? JSON.parse(r.sector_information) : [],
      has_folded_lc: r.has_folded_lc === 1,
    };
    
    const ra = star.ra;
    const dec = star.dec;
    
    const crossMatches: any[] = [];
    
    // Only fields stored in the ASTRA registry are reported. No positional cross-match is run here,
    // so match distance and observation dates are null rather than invented.
    const isVsx = star.primary_source === 'VSX' || star.source_catalogs.includes('VSX');
    if (isVsx) {
      crossMatches.push({
        catalog: 'International Variable Star Index (VSX)',
        identifier: star.catalog_label ?? null,
        otype: star.catalog_label ?? null,
        distance_arcsec: null,
        notes: star.catalog_period ? `Catalog period: ${star.catalog_period.toFixed(6)} d` : 'No catalog period stored.',
      });
    }

    const observationalHistory = [
      {
        observatory: 'TESS Spacecraft',
        instrument: 'TESS Camera',
        filters: 'TESS',
        observations: star.n_sectors ?? null,
        first_obs: null,
        last_obs: null,
        cadence: star.cadence_type ?? null,
      }
    ];

    const dataProvenance = [
      { step: 'Photometric Acquisition', agent: 'NASA/MIT TESS Science Office', detail: `TESS light curves (${star.cadence_type ?? 'unknown'} cadence, ${star.n_sectors ?? 'unknown'} sectors).` },
      { step: 'Quality Filtering', agent: 'ASTRA preprocess.py', detail: `5σ sigma clipping (3 iterations) and NaN removal. ${star.n_points_clean ?? 'Unknown number of'} clean points.` },
      { step: 'Preprocessing Record', agent: 'ASTRA registry', detail: star.preprocessing_hash ? `Preprocessing hash recorded: ${star.preprocessing_hash.slice(0, 8)}…` : 'No preprocessing hash recorded.' }
    ];

    const periodText = typeof star.period === 'number' ? `${star.period.toFixed(6)} d` : 'not available';
    const periodSourceText = star.period_source === 'catalog' ? 'an external catalog' : star.period_source === 'BLS' ? 'a BLS search on the TESS light curve' : 'an unknown source';
    
    return NextResponse.json({
      tic_id: star.tic_id,
      astra_class: star.astra_class,
      period: star.period,
      period_source: star.period_source,
      ra,
      dec,
      cross_matches: crossMatches,
      simbad: null,
      vsx: isVsx ? { identifier: star.catalog_label, period: star.catalog_period } : null,
      gaia: null,
      status: crossMatches.length > 0 ? 'available' : 'not_available',
      observational_history: observationalHistory,
      related_objects: [], // Remove invented companion objects
      provenance: dataProvenance,
      scientific_notes: `TIC ${ticId} carries the catalog label "${star.astra_class.replace('_', ' ')}" (ground truth, not a model prediction). Stored period: ${periodText}, taken from ${periodSourceText}.`,
      audit_hash: star.preprocessing_hash ?? 'N/A',
    });
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to generate OSINT report', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}
