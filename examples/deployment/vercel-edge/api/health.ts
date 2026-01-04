/**
 * Health Check Endpoint
 */

import { NextRequest, NextResponse } from 'next/server';
import { kv } from '@vercel/kv';

export const config = {
  runtime: 'edge',
};

export default async function handler(req: NextRequest) {
  try {
    // Check KV connectivity
    const kvHealthKey = 'health:check';
    await kv.set(kvHealthKey, Date.now(), { ex: 10 });
    const kvValue = await kv.get(kvHealthKey);

    return NextResponse.json({
      status: 'healthy',
      service: 'agenkit-vercel-edge',
      version: '0.45.0',
      timestamp: new Date().toISOString(),
      checks: {
        kv: kvValue !== null ? 'ok' : 'failed'
      }
    });

  } catch (error) {
    return NextResponse.json(
      {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 503 }
    );
  }
}
