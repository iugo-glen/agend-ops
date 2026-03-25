import { NextResponse } from 'next/server';
import { auth } from '@/auth';
import { queueAction, getQueuedActions } from '@/lib/queue';

const VALID_ACTIONS = [
  'mark-paid',
  'complete-todo',
  'complete-task',
  'trigger-triage',
  'dismiss-email',
] as const;

export async function POST(request: Request) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  let body: { action?: string; target_id?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: 'Invalid JSON body' },
      { status: 400 }
    );
  }

  const { action, target_id } = body;

  if (
    !action ||
    !VALID_ACTIONS.includes(action as (typeof VALID_ACTIONS)[number])
  ) {
    return NextResponse.json(
      { error: `Invalid action. Must be one of: ${VALID_ACTIONS.join(', ')}` },
      { status: 400 }
    );
  }

  // trigger-triage does not require a target_id
  if (action !== 'trigger-triage' && !target_id) {
    return NextResponse.json(
      { error: 'target_id is required for this action' },
      { status: 400 }
    );
  }

  const entry = queueAction(
    action as (typeof VALID_ACTIONS)[number],
    target_id || '',
    session.user?.email || 'unknown'
  );

  return NextResponse.json({ queued: true, id: entry.id });
}

export async function GET() {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const actions = getQueuedActions();
  const pending = actions.filter((a) => a.status === 'queued').length;

  return NextResponse.json({ pending, total: actions.length });
}
