import { appendFileSync, mkdirSync, readFileSync, existsSync } from 'fs';
import path from 'path';
import { DATA_ROOT } from './data';
import type { QueuedAction } from './types';

const QUEUE_FILE = path.join(DATA_ROOT, 'queue', 'actions.jsonl');

export function queueAction(
  action: QueuedAction['action'],
  target_id: string,
  requested_by: string
): QueuedAction {
  mkdirSync(path.dirname(QUEUE_FILE), { recursive: true });

  const entry: QueuedAction = {
    id: `action-${new Date().toISOString()}`,
    ts: new Date().toISOString(),
    action,
    target_id,
    status: 'queued',
    requested_by,
  };

  appendFileSync(QUEUE_FILE, JSON.stringify(entry) + '\n', 'utf-8');
  return entry;
}

export function getQueuedActions(): QueuedAction[] {
  if (!existsSync(QUEUE_FILE)) return [];
  const content = readFileSync(QUEUE_FILE, 'utf-8').trim();
  if (!content) return [];
  return content
    .split('\n')
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line) as QueuedAction);
}

export type { QueuedAction };
