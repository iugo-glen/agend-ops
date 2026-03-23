'use client';

import { formatDistanceToNow } from 'date-fns';
import type { TriageRecord } from '@/lib/types';

interface EmailCardProps {
  record: TriageRecord;
}

const PRIORITY_COLORS: Record<string, string> = {
  urgent: 'bg-priority-urgent',
  'needs-response': 'bg-priority-needs-response',
  informational: 'bg-priority-informational',
  'low-priority': 'bg-priority-low',
};

const PRIORITY_LABELS: Record<string, string> = {
  urgent: 'Urgent',
  'needs-response': 'Needs Response',
  informational: 'Info',
  'low-priority': 'Low',
};

const ACTION_TYPE_LABELS: Record<string, string> = {
  contract: 'Contract',
  invoice: 'Invoice',
  meeting: 'Meeting',
  deadline: 'Deadline',
};

export function EmailCard({ record }: EmailCardProps) {
  const senderDisplay = record.from_name || record.from;
  const threadUrl = `https://mail.google.com/mail/u/0/#inbox/${record.thread_id}`;
  const draftUrl = record.draft_id
    ? `https://mail.google.com/mail/u/0/#drafts/${record.draft_id}`
    : null;

  const relativeTime = record.received
    ? formatDistanceToNow(new Date(record.received), { addSuffix: true })
    : null;

  return (
    <a
      href={threadUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-lg border border-border-default bg-surface p-3 transition-colors hover:bg-[color:var(--border)]/50"
    >
      {/* Line 1: Sender + Priority badge */}
      <div className="flex items-start justify-between gap-2">
        <span className="text-[length:var(--text-body)] font-semibold text-text-primary">
          {record.starred && (
            <span className="mr-1 text-starred">{'\u2605'}</span>
          )}
          {senderDisplay}
        </span>
        <span
          className={`shrink-0 rounded px-2 py-0.5 text-[length:var(--text-sm)] font-semibold text-white ${PRIORITY_COLORS[record.priority] || ''}`}
        >
          {PRIORITY_LABELS[record.priority] || record.priority}
        </span>
      </div>

      {/* Line 2: Subject */}
      <p className="mt-1 line-clamp-2 text-[length:var(--text-body)] text-text-primary">
        {record.subject}
      </p>

      {/* Line 3: Snippet */}
      {record.snippet && (
        <p className="mt-0.5 line-clamp-1 text-[length:var(--text-sm)] text-text-secondary">
          {record.snippet}
        </p>
      )}

      {/* Line 4: Timestamp + action type + draft link */}
      <div className="mt-2 flex items-center gap-2">
        {relativeTime && (
          <span className="text-[length:var(--text-sm)] text-text-secondary">
            {relativeTime}
          </span>
        )}
        {record.action_type && record.action_type !== 'none' && (
          <span className="rounded bg-surface-secondary px-2 py-0.5 text-[length:var(--text-sm)] text-text-secondary">
            {ACTION_TYPE_LABELS[record.action_type] || record.action_type}
          </span>
        )}
        {draftUrl && (
          <a
            href={draftUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-[length:var(--text-sm)] font-semibold text-accent hover:underline"
          >
            View Draft
          </a>
        )}
      </div>
    </a>
  );
}
