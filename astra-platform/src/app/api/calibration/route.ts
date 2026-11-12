import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';
import { serverError } from '@/lib/server/errors';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data', 'artifacts', 'calibration.json');
    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: 'Calibration metrics file not found.' }, { status: 404 });
    }
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    return NextResponse.json(data);
  } catch (error) {
    return serverError('/api/calibration', error, 'Failed to load calibration metrics');
  }
}
