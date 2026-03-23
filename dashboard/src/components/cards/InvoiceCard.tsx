'use client';

import { format } from 'date-fns';
import type { InvoiceRecord } from '@/lib/types';
import { ActionButton } from '@/components/ActionButton';

interface InvoiceCardProps {
  record: InvoiceRecord;
}

const STATUS_COLORS: Record<string, string> = {
  reminder: 'bg-priority-needs-response',
  draft: 'bg-priority-low',
  sent: 'bg-priority-informational',
  paid: 'bg-status-completed',
  disputed: 'bg-destructive',
  'written-off': 'bg-priority-low',
};

function formatCurrency(amount: number | null | undefined, currency?: string): string {
  if (amount == null) return '';
  const cur = currency || 'AUD';
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: cur,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function InvoiceCard({ record }: InvoiceCardProps) {
  const now = new Date();
  const isOverdue =
    record.status === 'sent' && record.due_date && new Date(record.due_date) < now;

  const emailUrl = record.source_email_id
    ? `https://mail.google.com/mail/u/0/#inbox/${record.source_email_id}`
    : null;

  return (
    <div className="rounded-lg border border-border-default bg-surface p-3">
      {/* Project code + status */}
      <div className="flex items-start justify-between gap-2">
        <div>
          {record.project_code && (
            <span className="text-[length:var(--text-sm)] font-semibold text-accent">
              {record.project_code}
            </span>
          )}
          <p className="text-[length:var(--text-body)] font-semibold text-text-primary">
            {record.client_name}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span
            className={`rounded px-2 py-0.5 text-[length:var(--text-sm)] font-semibold text-white ${STATUS_COLORS[record.status] || 'bg-priority-low'}`}
          >
            {record.status.charAt(0).toUpperCase() + record.status.slice(1)}
          </span>
          {isOverdue && (
            <span className="rounded bg-destructive px-2 py-0.5 text-[length:var(--text-sm)] font-semibold text-white">
              OVERDUE
            </span>
          )}
        </div>
      </div>

      {/* Amount + due date */}
      <div className="mt-1 flex flex-wrap items-center gap-2">
        {record.amount != null && (
          <span className="text-[length:var(--text-body)] font-semibold text-text-primary">
            {formatCurrency(record.amount, record.currency)}
          </span>
        )}
        {record.due_date && (
          <span
            className={`text-[length:var(--text-sm)] ${isOverdue ? 'font-semibold text-destructive' : 'text-text-secondary'}`}
          >
            Due: {format(new Date(record.due_date), 'MMM d, yyyy')}
          </span>
        )}
      </div>

      {/* Invoice number */}
      {record.invoice_number && (
        <p className="mt-0.5 text-[length:var(--text-sm)] text-text-secondary">
          #{record.invoice_number}
        </p>
      )}

      {/* Email link */}
      {emailUrl && (
        <a
          href={emailUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-block text-[length:var(--text-sm)] font-semibold text-accent hover:underline"
        >
          View Email
        </a>
      )}

      {/* Action: Mark Paid for sent or reminder invoices */}
      {(record.status === 'sent' || record.status === 'reminder') && (
        <div className="mt-2">
          <ActionButton
            action="mark-paid"
            targetId={record.id}
            label="Mark Paid"
            variant="primary"
          />
        </div>
      )}
    </div>
  );
}
