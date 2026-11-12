import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';
import { getDatabase } from '@/lib/server/db';
import { serverError } from '@/lib/server/errors';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const auditPath = path.join(process.cwd(), 'data', 'artifacts', 'dataset_audit.json');
    const lineagePath = path.join(process.cwd(), 'data', 'artifacts', 'lineage.json');
    
    if (!fs.existsSync(auditPath) || !fs.existsSync(lineagePath)) {
      return NextResponse.json({ error: 'Dataset files not found.' }, { status: 404 });
    }
    
    const audit = JSON.parse(fs.readFileSync(auditPath, 'utf-8'));
    const lineage = JSON.parse(fs.readFileSync(lineagePath, 'utf-8'));
    
    // Compute split class matrix from database
    const splitClassCounts = getDatabase().prepare('SELECT split, astra_class, COUNT(*) as count FROM stars GROUP BY split, astra_class').all() as { split: string; astra_class: string; count: number }[];
    
    const classSplitMatrix: Record<string, Record<string, number>> = {
      rr_lyrae: { train: 0, val: 0, test: 0 },
      cepheid: { train: 0, val: 0, test: 0 },
      eclipsing_binary: { train: 0, val: 0, test: 0 },
      solar_like: { train: 0, val: 0, test: 0 },
      stable: { train: 0, val: 0, test: 0 }
    };
    
    for (const row of splitClassCounts) {
      if (classSplitMatrix[row.astra_class]) {
        classSplitMatrix[row.astra_class][row.split] = row.count;
      }
    }
    
    return NextResponse.json({
      audit,
      lineage,
      classSplitMatrix
    });
  } catch (error) {
    return serverError('/api/dataset', error, 'Failed to load dataset details');
  }
}

