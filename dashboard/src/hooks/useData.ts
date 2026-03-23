'use client';

import useSWR from 'swr';
import type {
  FeedEntry,
  TriageRecord,
  TaskRecord,
  TodoRecord,
  InvoiceRecord,
} from '@/lib/types';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useData<T>(type: string) {
  return useSWR<T[]>(`/api/data/${type}`, fetcher, {
    refreshInterval: 30_000,
    revalidateOnFocus: true,
  });
}

export function useFeed() {
  return useData<FeedEntry>('feed');
}

export function useTriage() {
  return useData<TriageRecord>('triage');
}

export function useTasks() {
  return useData<TaskRecord>('tasks');
}

export function useTodos() {
  return useData<TodoRecord>('todos');
}

export function useInvoices() {
  return useData<InvoiceRecord>('invoices');
}
