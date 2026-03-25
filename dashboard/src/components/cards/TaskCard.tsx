'use client';

import { formatDistanceToNow } from 'date-fns';
import type { TaskRecord } from '@/lib/types';
import { ActionButton } from '@/components/ActionButton';
import { QueuedBadge } from '@/components/QueuedBadge';

interface TaskCardProps {
  record: TaskRecord;
}

const STATUS_DOT: Record<string, string> = {
  pending: 'bg-status-pending',
  'in-progress': 'bg-status-in-progress',
  completed: 'bg-status-completed',
};

const TYPE_LABELS: Record<string, string> = {
  'contract-review': 'Contract Review',
  'meeting-prep': 'Meeting Prep',
  'document-summary': 'Doc Summary',
  'draft-comms': 'Draft Comms',
};

export function TaskCard({ record }: TaskCardProps) {
  const relativeTime = formatDistanceToNow(new Date(record.ts), {
    addSuffix: true,
  });
  const draftUrl = record.draft_id
    ? `https://mail.google.com/mail/u/0/#drafts/${record.draft_id}`
    : null;

  return (
    <div className="rounded-lg border border-border-default bg-surface p-3">
      {/* Line 1: Status dot + description */}
      <div className="flex items-start gap-2">
        <span
          className={`mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full ${STATUS_DOT[record.status] || 'bg-text-secondary'}`}
        />
        <p className="line-clamp-2 text-[length:var(--text-body)] text-text-primary">
          {record.description}
        </p>
      </div>

      {/* Line 2: Type badge + client name */}
      <div className="mt-1 flex flex-wrap items-center gap-2 pl-4">
        {record.task_type && (
          <span className="rounded bg-surface-secondary px-2 py-0.5 text-[length:var(--text-sm)] text-text-secondary">
            {TYPE_LABELS[record.task_type] || record.task_type}
          </span>
        )}
        {record.client_name && (
          <span className="text-[length:var(--text-sm)] text-text-secondary">
            {record.client_name}
          </span>
        )}
      </div>

      {/* Line 3: Timestamp + draft link */}
      <div className="mt-1 flex items-center gap-2 pl-4">
        <span className="text-[length:var(--text-sm)] text-text-secondary">
          {relativeTime}
        </span>
        {draftUrl && (
          <a
            href={draftUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[length:var(--text-sm)] font-semibold text-accent hover:underline"
          >
            View Draft
          </a>
        )}
      </div>

      {/* Action */}
      {record.status === 'pending' && (
        <div className="mt-2 flex items-center gap-2 pl-4">
          <ActionButton
            action="complete-task"
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
