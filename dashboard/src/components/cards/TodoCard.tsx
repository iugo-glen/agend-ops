'use client';

import { format } from 'date-fns';
import type { TodoRecord } from '@/lib/types';
import { ActionButton } from '@/components/ActionButton';
import { QueuedBadge } from '@/components/QueuedBadge';

interface TodoCardProps {
  record: TodoRecord;
}

const PRIORITY_BORDER: Record<string, string> = {
  high: 'border-l-destructive',
  normal: 'border-l-accent',
  low: 'border-l-text-secondary',
};

export function TodoCard({ record }: TodoCardProps) {
  const isOverdue =
    record.due_date && record.status === 'active' && new Date(record.due_date) < new Date();

  return (
    <div
      className={`rounded-lg border border-border-default border-l-4 bg-surface p-3 ${PRIORITY_BORDER[record.priority] || 'border-l-accent'}`}
    >
      {/* Text */}
      <p className="text-[length:var(--text-body)] text-text-primary">
        {record.text}
      </p>

      {/* Meta: category + due date */}
      <div className="mt-1 flex flex-wrap items-center gap-2">
        {record.category && (
          <span className="rounded bg-surface-secondary px-2 py-0.5 text-[length:var(--text-sm)] text-text-secondary">
            {record.category}
          </span>
        )}
        {record.due_date && (
          <span
            className={`text-[length:var(--text-sm)] ${isOverdue ? 'font-semibold text-destructive' : 'text-text-secondary'}`}
          >
            {isOverdue ? 'Overdue: ' : 'Due: '}
            {format(new Date(record.due_date), 'MMM d')}
          </span>
        )}
      </div>

      {/* Action */}
      {record.status === 'active' && (
        <div className="mt-2 flex items-center gap-2">
          <ActionButton
            action="complete-todo"
            targetId={record.id}
            label="Complete"
            icon={'\u2713'}
            variant="ghost"
          />
          <QueuedBadge targetId={record.id} />
        </div>
      )}
    </div>
  );
}
