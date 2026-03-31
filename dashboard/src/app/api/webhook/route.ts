import { NextRequest, NextResponse } from 'next/server';
import { execSync } from 'child_process';
import crypto from 'crypto';

const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || '';
const DATA_ROOT = process.env.DATA_DIR || '/data';

function verifySignature(payload: string, signature: string): boolean {
  if (!WEBHOOK_SECRET) return false;
  const expected = 'sha256=' + crypto
    .createHmac('sha256', WEBHOOK_SECRET)
    .update(payload)
    .digest('hex');
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(signature));
}

export async function POST(req: NextRequest) {
  const body = await req.text();
  const signature = req.headers.get('x-hub-signature-256') || '';

  // Verify GitHub signature
  if (!verifySignature(body, signature)) {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
  }

  try {
    // Resolve the repo root from the data dir (data is bind-mounted from /opt/agend-ops/data)
    // The repo root is one level up from DATA_ROOT
    const repoRoot = DATA_ROOT.replace(/\/data\/?$/, '');

    // Pull latest changes
    const output = execSync('git pull --ff-only 2>&1', {
      cwd: repoRoot || '/opt/agend-ops',
      timeout: 30000,
      encoding: 'utf-8',
    });

    return NextResponse.json({
      ok: true,
      output: output.trim(),
      repo: repoRoot || '/opt/agend-ops',
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
