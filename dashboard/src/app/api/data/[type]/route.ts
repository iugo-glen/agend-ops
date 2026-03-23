import { NextResponse } from 'next/server';
import { auth } from '@/auth';
import {
  readNDJSON,
  getFeedEntries,
  getLatestTriage,
  getTodos,
  getInvoices,
  getTasks,
} from '@/lib/data';

const DATA_MAP: Record<string, () => unknown[]> = {
  feed: () => getFeedEntries(),
  tasks: () => getTasks(),
  triage: () => getLatestTriage(),
  todos: () => getTodos(),
  invoices: () => getInvoices(),
};

export async function GET(
  request: Request,
  { params }: { params: Promise<{ type: string }> }
) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { type } = await params;

  const reader = DATA_MAP[type];
  if (!reader) {
    return NextResponse.json(
      { error: `Unknown data type: ${type}` },
      { status: 400 }
    );
  }

  const data = reader();
  return NextResponse.json(data);
}
