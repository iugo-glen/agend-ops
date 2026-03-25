import { readFileSync, existsSync, readdirSync } from 'fs';
import path from 'path';
import type {
  FeedEntry,
  TriageRecord,
  TodoRecord,
  InvoiceRecord,
  TaskRecord,
} from './types';

export const DATA_ROOT =
  process.env.DATA_DIR || path.join(process.cwd(), '..', 'data');

export function readNDJSON<T>(filePath: string): T[] {
  const fullPath = path.join(DATA_ROOT, filePath);
  if (!existsSync(fullPath)) return [];
  const content = readFileSync(fullPath, 'utf-8').trim();
  if (!content) return [];
  return content
    .split('\n')
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line) as T);
}

export function getFeedEntries(limit = 50): FeedEntry[] {
  return readNDJSON<FeedEntry>('feed.jsonl').slice(-limit).reverse();
}

export function getLatestTriage(): TriageRecord[] {
  const triageDir = path.join(DATA_ROOT, 'triage');
  if (!existsSync(triageDir)) return [];

  const files = readdirSync(triageDir)
    .filter((f) => f.endsWith('.jsonl'))
    .sort();

  if (files.length === 0) return [];

  const latestFile = files[files.length - 1];
  return readNDJSON<TriageRecord>(path.join('triage', latestFile))
    .filter((r) => !(r as TriageRecord & { dismissed?: boolean }).dismissed);
}

export function getTodos(): TodoRecord[] {
  return readNDJSON<TodoRecord>('todos/active.jsonl');
}

export function getInvoices(): InvoiceRecord[] {
  return readNDJSON<InvoiceRecord>('invoices/active.jsonl');
}

export function getTasks(): TaskRecord[] {
  return readNDJSON<TaskRecord>('tasks/active.jsonl');
}
