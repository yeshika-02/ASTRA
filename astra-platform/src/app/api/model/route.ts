import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';
import { serverError } from '@/lib/server/errors';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data', 'artifacts', 'model_registry.json');
    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: 'Model registry file not found.' }, { status: 404 });
    }
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    return NextResponse.json(data.active_model);
  } catch (error) {
    return serverError('/api/model', error, 'Failed to load model details');
  }
}
