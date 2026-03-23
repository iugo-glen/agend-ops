'use client';

import type {
  TriageRecord,
  TaskRecord,
  TodoRecord,
  InvoiceRecord,
} from '@/lib/types';

interface SummaryBarProps {
  triage: TriageRecord[];
  tasks: TaskRecord[];
  todos: TodoRecord[];
  invoices: InvoiceRecord[];
}

export function SummaryBar({ triage, tasks, todos, invoices }: SummaryBarProps) {
  const emailCount = triage.length;
  const starredCount = triage.filter((r) => r.starred).length;
  const pendingCount = tasks.filter(
    (t) => t.status === 'pending' || t.status === 'in-progress'
  ).length;
  const todoCount = todos.filter((t) => t.status === 'active').length;

  const now = new Date();
  const overdueCount = invoices.filter((inv) => {
    if (inv.status !== 'sent') return false;
    if (!inv.due_date) return false;
    return new Date(inv.due_date) < now;
  }).length;

  const pills: { label: string; value: number }[] = [
    { label: 'emails', value: emailCount },
    { label: 'starred', value: starredCount },
    { label: 'pending', value: pendingCount },
    { label: 'to-dos', value: todoCount },
    { label: 'overdue', value: overdueCount },
  ];

  return (
    <div
      className="flex gap-2 overflow-x-auto px-4 py-2 md:px-8"
      aria-live="polite"
    >
      {pills.map((pill) => (
        <span
          key={pill.label}
          className="inline-flex shrink-0 items-center gap-1 rounded bg-surface-secondary px-3 py-1 text-[length:var(--text-sm)] text-text-primary"
        >
          <span className="font-semibold">{pill.value}</span>
          <span>{pill.label}</span>
        </span>
      ))}
    </div>
  );
}
